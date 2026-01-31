#!/usr/bin/env python3
"""
一键生成 pthread 版 tvmrt 并行流水线：
 1) 直接在 src/ 目录上操作（假设 TVM 生成的原始文件已在 src/）
 2) 运行静态化、op_args、调度生成、并行合并
 3) 生成 g_op_func_idx 映射表（执行索引 -> 函数索引）
 4) 注入双 barrier 同步的 pthread tvmrt 运行时
 5) 去掉 Makefile 中的 -fopenmp，增加 -pthread
 6) 可选 make / make test
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
import tempfile

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"


def run(cmd, cwd=REPO_ROOT, env=None):
    print("[CMD]", " ".join(cmd))
    res = subprocess.run(cmd, cwd=cwd, env=env)
    if res.returncode != 0:
        sys.exit(res.returncode)


def check_src_files():
    """检查 src 目录是否存在必要的文件"""
    required = ["lib0.c", "lib1.c"]
    missing = []
    for name in required:
        if not (SRC / name).exists():
            missing.append(name)
    if missing:
        print(f"[ERROR] src/ 目录缺少必要文件: {', '.join(missing)}", file=sys.stderr)
        print(f"[INFO] 请确保 TVM 生成的 lib0.c 和 lib1.c 已放置在 {SRC}/", file=sys.stderr)
        sys.exit(1)
    print(f"[INFO] 检测到源文件: {', '.join(required)}")


def patch_lib0_for_standalone(lib0: Path):
    """移除 TVM 依赖并修复 section 属性，便于 gcc/clang 直接编译。"""
    text = lib0.read_text()

    # 1) 头部：去掉 tvm/runtime 引用，加入宏和 stdint
    if '#include "tvm/runtime/c_runtime_api.h"' in text:
        header = (
            '#define TVM_DLL\n'
            '#include <stdint.h>\n'
            '#ifdef __APPLE__\n'
            '#define TVM_RODATA __attribute__((section("__DATA,.rodata_tvm")))\n'
            '#define TVM_BSS    __attribute__((aligned(16)))\n'
            '#else\n'
            '#define TVM_RODATA __attribute__((section(".rodata.tvm")))\n'
            '#define TVM_BSS    __attribute__((section(".bss.noinit.tvm"), aligned(16)))\n'
            '#endif\n'
        )
        text = text.replace('#include "tvm/runtime/c_runtime_api.h"', header, 1)

    # 2) rodata / bss section 属性
    text = text.replace('__attribute__((section(".rodata.tvm"), ))', 'TVM_RODATA')
    text = text.replace('__attribute__((section(".rodata.tvm")))', 'TVM_RODATA')
    text = text.replace('__attribute__((section(".bss.noinit.tvm"), aligned(16)))', 'TVM_BSS')
    # 恢复宏定义（防止上面替换误伤宏定义行）
    text = text.replace('#define TVM_RODATA TVM_RODATA', '#define TVM_RODATA __attribute__((section(".rodata.tvm")))')
    text = text.replace('#define TVM_BSS    TVM_BSS', '#define TVM_BSS    __attribute__((section(".bss.noinit.tvm"), aligned(16)))')

    # 3) 移除 tvmgen_default.h，改用简化的结构体声明
    text = text.replace('#include <tvmgen_default.h>', 'struct tvmgen_default_inputs { void* images; };\nstruct tvmgen_default_outputs { void* output; };')

    # 4) 修正 tvm_main 原型类型（避免 void* 警告）
    text = text.replace('tvmgen_default___tvm_main__(void* images,void* output0', 'tvmgen_default___tvm_main__(float* images, float* output0')

    lib0.write_text(text)
    print("[INFO] 已修复 lib0.c 头部与 section 属性以支持独立编译")


def remove_openmp_add_pthread(makefile: Path):
    if not makefile.exists():
        return
    content = makefile.read_text()
    content = content.replace("-fopenmp", "")
    if "-pthread" not in content:
        content = content.replace("LDFLAGS = -lm", "LDFLAGS = -lm -pthread")
        content = content.replace("CFLAGS = -O3 -Wall -fPIC", "CFLAGS = -O3 -Wall -fPIC -pthread")
        content = content.replace("CXXFLAGS = -O3 -Wall -fPIC", "CXXFLAGS = -O3 -Wall -fPIC -pthread")
    makefile.write_text(content)
    print("[INFO] Makefile 已移除 -fopenmp 并添加 -pthread")


# 使用双 barrier 同步的 tvmrt 运行时（避免竞争条件）
TVMRT_CODE = r"""
#include <pthread.h>
#include <stdlib.h>
#include <stdio.h>
#include <time.h>

typedef struct {
    pthread_mutex_t mtx;
    pthread_cond_t cv;
    int count;
    int arrived;
} tvmrt_barrier_t;

static int tvmrt_barrier_init(tvmrt_barrier_t* b, int count) {
    b->count = count;
    b->arrived = 0;
    if (pthread_mutex_init(&b->mtx, NULL)) return -1;
    if (pthread_cond_init(&b->cv, NULL)) return -1;
    return 0;
}

static void tvmrt_barrier_destroy(tvmrt_barrier_t* b) {
    pthread_mutex_destroy(&b->mtx);
    pthread_cond_destroy(&b->cv);
}

static void tvmrt_barrier_wait(tvmrt_barrier_t* b) {
    pthread_mutex_lock(&b->mtx);
    b->arrived++;
    if (b->arrived == b->count) {
        b->arrived = 0;
        pthread_cond_broadcast(&b->cv);
    } else {
        while (b->arrived != 0) pthread_cond_wait(&b->cv, &b->mtx);
    }
    pthread_mutex_unlock(&b->mtx);
}

typedef struct {
    const schedule_layer_t* schedule;
    int num_layers;
    int worker_count;
    int active_count;
    uint8_t* cws;
    uint8_t* ws;
    op_args_t* op_args;
    volatile int layer_idx;
    volatile int stop;
    volatile int err;
    tvmrt_barrier_t start_barrier;  // 等待 main 准备好
    tvmrt_barrier_t end_barrier;    // 等待所有人完成
} tvmrt_ctx_t;

typedef struct { tvmrt_ctx_t* ctx; int tid; } tvmrt_worker_arg_t;

static void* tvmrt_worker(void* arg) {
    tvmrt_worker_arg_t* wa = (tvmrt_worker_arg_t*)arg;
    tvmrt_ctx_t* ctx = wa->ctx;
    int tid = wa->tid;
    int participants = ctx->active_count;
    
    while (1) {
        // 等待 main 准备好 (start barrier)
        tvmrt_barrier_wait(&ctx->start_barrier);
        
        if (ctx->stop) break;
        
        int layer = ctx->layer_idx;
        const schedule_layer_t* sl = &ctx->schedule[layer];
        for (int j = tid; j < sl->count; j += participants) {
            int32_t op_idx = sl->op_indices[j];
            int ret = g_op_call_table[g_op_func_idx[op_idx]](&ctx->op_args[op_idx], ctx->cws, ctx->ws);
            if (ret != 0) ctx->err = ret;
        }
        
        // 等待所有人完成 (end barrier)
        tvmrt_barrier_wait(&ctx->end_barrier);
    }
    return NULL;
}

static int tvmrt_parse_workers(void) {
    const char* env = getenv("TVMRT_NUM_WORKERS");
    if (!env) env = getenv("OMP_NUM_THREADS");
    int n = env ? atoi(env) : 3;
    if (n < 1) n = 1;
    return n;
}

static int tvmrt_run(uint8_t* cws, uint8_t* ws, op_args_t op_args[]) {
    const char* trace_env = getenv("TVMRT_TRACE");
    int trace_every = trace_env ? atoi(trace_env) : 0;
    const char* max_env = getenv("TVMRT_MAX_LAYERS");
    int max_layers = max_env ? atoi(max_env) : NUM_LAYERS;
    if (max_layers < 1 || max_layers > NUM_LAYERS) max_layers = NUM_LAYERS;

    int worker_count = tvmrt_parse_workers();
    tvmrt_ctx_t ctx = {
        .schedule = g_schedule,
        .num_layers = max_layers,
        .worker_count = worker_count,
        .active_count = worker_count + 1,  // workers + main
        .cws = cws,
        .ws = ws,
        .op_args = op_args,
        .layer_idx = -1,
        .stop = 0,
        .err = 0
    };

    int participants = ctx.active_count;
    tvmrt_barrier_init(&ctx.start_barrier, participants);
    tvmrt_barrier_init(&ctx.end_barrier, participants);

    pthread_t* threads = (pthread_t*)malloc(sizeof(pthread_t) * ctx.worker_count);
    tvmrt_worker_arg_t* args = (tvmrt_worker_arg_t*)malloc(sizeof(tvmrt_worker_arg_t) * ctx.worker_count);
    for (int i = 0; i < ctx.worker_count; ++i) {
        args[i].ctx = &ctx;
        args[i].tid = i;
        pthread_create(&threads[i], NULL, tvmrt_worker, &args[i]);
    }

    int main_tid = ctx.worker_count;
    struct timespec ts0, ts1;
    if (trace_every > 0) clock_gettime(CLOCK_MONOTONIC, &ts0);
    
    for (int layer = 0; layer < ctx.num_layers; ++layer) {
        ctx.layer_idx = layer;
        
        // 通知所有 workers 开始 (start barrier)
        tvmrt_barrier_wait(&ctx.start_barrier);
        
        // Main 线程也做自己的工作
        const schedule_layer_t* sl = &ctx.schedule[layer];
        for (int j = main_tid; j < sl->count; j += participants) {
            int32_t op_idx = sl->op_indices[j];
            int ret = g_op_call_table[g_op_func_idx[op_idx]](&ctx.op_args[op_idx], ctx.cws, ctx.ws);
            if (ret != 0) ctx.err = ret;
        }
        
        // 等待所有人完成 (end barrier)
        tvmrt_barrier_wait(&ctx.end_barrier);
        
        if (trace_every > 0 && (layer % trace_every == 0)) {
            clock_gettime(CLOCK_MONOTONIC, &ts1);
            double ms = (ts1.tv_sec - ts0.tv_sec) * 1000.0 +
                        (ts1.tv_nsec - ts0.tv_nsec) / 1e6;
            printf("[tvmrt] layer %d/%d done in %.2f ms\\n", layer, ctx.num_layers, ms);
            fflush(stdout);
            ts0 = ts1;
        }
        if (ctx.err) break;
    }

    // 通知 workers 停止
    ctx.stop = 1;
    tvmrt_barrier_wait(&ctx.start_barrier);

    for (int i = 0; i < ctx.worker_count; ++i) pthread_join(threads[i], NULL);

    tvmrt_barrier_destroy(&ctx.start_barrier);
    tvmrt_barrier_destroy(&ctx.end_barrier);
    free(threads);
    free(args);
    return ctx.err;
}
"""


def generate_op_func_idx(lib1: Path):
    """
    生成 g_op_func_idx 映射表：将执行索引映射到唯一函数索引。
    g_op_call_table 是按函数名排序的唯一函数列表，
    而调度表使用的是执行顺序的索引，因此需要这个映射。
    """
    content = lib1.read_text()
    
    # 1. 提取 g_op_call_table 函数指针列表 (唯一函数，按字母排序)
    table_match = re.search(r'static const op_func_t g_op_call_table\[OP_COUNT\] = \{([^}]+)\};', content, re.S)
    if not table_match:
        print("[ERROR] 未找到 g_op_call_table")
        sys.exit(1)
    table_funcs = [f.strip().replace('wrapped_', '') for f in table_match.group(1).split(',') if f.strip()]
    print(f"[INFO] g_op_call_table 唯一函数数量: {len(table_funcs)}")
    
    # 2. 提取 g_op_call_names (按执行顺序)
    names_match = re.search(r'static const char\* const g_op_call_names\[\d+\][^=]*= \{([^}]+)\};', content, re.S)
    if not names_match:
        print("[ERROR] 未找到 g_op_call_names")
        sys.exit(1)
    names = [n.strip().strip('"') for n in names_match.group(1).split(',') if n.strip()]
    print(f"[INFO] g_op_call_names 调用数量: {len(names)}")
    
    # 3. 建立从执行索引到函数表索引的映射
    func_to_idx = {f: i for i, f in enumerate(table_funcs)}
    mapping = []
    for i, name in enumerate(names):
        if name in func_to_idx:
            mapping.append(func_to_idx[name])
        else:
            print(f"[ERROR] 函数 {name} 未在 g_op_call_table 中找到")
            sys.exit(1)
    
    print(f"[INFO] 成功建立映射: {len(mapping)} 个")
    
    # 4. 生成映射表 C 代码
    mapping_code = "\n// 从执行索引到函数表索引的映射 (执行顺序 -> 唯一函数索引)\n"
    mapping_code += f"static const int32_t g_op_func_idx[{len(mapping)}] = {{\n"
    for i in range(0, len(mapping), 12):
        chunk = mapping[i:i+12]
        mapping_code += "  " + ", ".join(f"{x:3d}" for x in chunk) + ",\n"
    mapping_code = mapping_code.rstrip(',\n') + "\n};\n"
    
    # 5. 插入映射表 (在 g_op_call_names 之后)
    insert_pos = content.find('};', content.find('static const char* const g_op_call_names')) + 2
    new_content = content[:insert_pos] + mapping_code + content[insert_pos:]
    
    lib1.write_text(new_content)
    print("[INFO] 已生成 g_op_func_idx 映射表")


def inject_tvmrt(lib1: Path):
    content = lib1.read_text()
    if "#include <pthread.h>" not in content:
        content = content.replace("#include <stdbool.h>", "#include <stdbool.h>\n#include <pthread.h>")
    if "tvmrt_run(" not in content:
        # 插入在 NUM_LAYERS 定义之后，确保宏和 g_schedule 已就位
        marker = "#define NUM_LAYERS"
        idx = content.find(marker)
        if idx != -1:
            endline = content.find("\n", idx)
            content = content[:endline+1] + TVMRT_CODE + "\n" + content[endline+1:]
        else:
            content = TVMRT_CODE + "\n" + content

    # 替换主函数内的并行执行块
    if "// Parallel Execution Loop" in content:
        pattern = re.compile(r"// Parallel Execution Loop.*?return 0;\n\}", re.S)
        content = pattern.sub("    int tvmrt_ret = tvmrt_run(cws, ws, op_args);\n    return tvmrt_ret;\n}\n", content)
    lib1.write_text(content)
    print("[INFO] 已注入双 barrier tvmrt runtime 并替换主函数执行逻辑")


def dedup_call_tables(lib1: Path):
    text = lib1.read_text()

    # 1. 删除第一个空 op_args 表（在静态化函数之后）
    empty_op_args_pattern = r'// 算子参数配置表\n// 注意：需要手动填充每个算子的输入输出地址\n\nop_args_t op_args\[OP_COUNT\] = \{.*?\};\n\n'
    text = re.sub(empty_op_args_pattern, '', text, flags=re.DOTALL)

    # 2. g_op_call_table 去重
    matches = list(re.finditer(r"static const op_func_t g_op_call_table\[.*?\};", text, re.S))
    if len(matches) > 1:
        for m in matches[:-1]:
            text = text.replace(m.group(0), "")
        text = re.sub(r'\n{5,}', '\n\n\n', text)

    # 3. g_op_call_names 去重
    matches = list(re.finditer(r"static const char\* const g_op_call_names\[.*?\};", text, re.S))
    if len(matches) > 1:
        for m in matches[:-1]:
            text = text.replace(m.group(0), "")
        text = re.sub(r'\n{5,}', '\n\n\n', text)

    lib1.write_text(text)
    print("[INFO] 已去重 g_op_call_table / g_op_call_names / 空 op_args 表")


def mark_call_names_unused(lib1: Path):
    text = lib1.read_text()
    text, n = re.subn(r'(static const char\* const g_op_call_names\[\d+\])',
                      r'\1 __attribute__((unused))', text, count=1)
    if n:
        lib1.write_text(text)
        print("[INFO] 已添加 __attribute__((unused)) 标记到 g_op_call_names")


def main():
    ap = argparse.ArgumentParser(description="自动生成 pthread tvmrt 并测试")
    ap.add_argument("--skip-build", action="store_true", help="不执行 make/test")
    ap.add_argument("--run-test", action="store_true", help="完成后执行 make test")
    ap.add_argument("--keep-temp", action="store_true", help="保留临时文件")
    ap.add_argument("--serial", action="store_true", help="使用串行调度（每层1个算子，用于调试或对照）")
    args = ap.parse_args()

    print("=" * 60)
    print("  一键构建 pthread 并行 TVM Runtime")
    print("=" * 60)

    # 检查 src 目录文件
    check_src_files()
    
    # 修复 lib0.c 以支持独立编译
    patch_lib0_for_standalone(SRC / "lib0.c")

    tmpdir = tempfile.TemporaryDirectory()
    static_ops = Path(tmpdir.name) / "static_ops.c"
    op_args = Path(tmpdir.name) / "op_args.c"

    run([sys.executable, "scripts/operator_staticizer.py", "src/lib1.c", "-o", str(static_ops)])
    run([sys.executable, "scripts/extract_op_args.py", "src/lib1.c", "-o", str(op_args), "--no-var-def"])
    
    # 根据 --serial 选项选择调度生成脚本
    if args.serial:
        print("[INFO] 使用串行调度模式（每层1个算子）")
        run([sys.executable, "scripts/gen_serial_schedule.py", "init/lib1.c", "-o", "src/schedule_generated.c"])
    else:
        run([sys.executable, "scripts/gen_parallel_schedule.py", "src/lib1.c", "-o", "src/schedule_generated.c", "--op-args", str(op_args)])
    run([
        sys.executable, "scripts/merge_parallel_code.py", "src/lib1.c",
        "--schedule", "src/schedule_generated.c",
        "--op-args", str(op_args),
        "--wrappers", str(static_ops),
        "--no-makefile"
    ])

    dedup_call_tables(SRC / "lib1.c")
    generate_op_func_idx(SRC / "lib1.c")  # 生成映射表
    inject_tvmrt(SRC / "lib1.c")
    mark_call_names_unused(SRC / "lib1.c")

    run([sys.executable, "scripts/build_generator.py", "--force"])
    remove_openmp_add_pthread(REPO_ROOT / "Makefile")

    if not args.skip_build:
        (REPO_ROOT / "build").mkdir(exist_ok=True)
        run(["make", "clean"])
        run(["make"])
        if args.run_test:
            env = os.environ.copy()
            run(["make", "test"], env=env)

    if args.keep_temp:
        print(f"[INFO] 临时文件保留在 {tmpdir.name}")
    else:
        tmpdir.cleanup()

    print("=" * 60)
    print("  [OK] tvmrt 并行流水线构建完成！")
    print("=" * 60)
    print("\n使用方法:")
    print("  ./build/<model>_test                    # 默认 3 个 workers")
    print("  TVMRT_NUM_WORKERS=0 ./build/<model>_test  # 单线程模式")
    print("  TVMRT_TRACE=1 ./build/<model>_test        # 显示每层耗时")


if __name__ == "__main__":
    main()
