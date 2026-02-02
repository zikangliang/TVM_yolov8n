#!/usr/bin/env python3
"""
合并脚本 - 将生成的调度代码注入到 lib1.c

此脚本：
1. 从 init/ 复制原始 lib0.c 和 lib1.c 到 src/
2. 修改 lib1.c 头部，添加运行时类型定义
3. 提取算子函数实现（保留）
4. 替换 tvmgen_default___tvm_main__ 函数为新的入口

使用方法:
    python3 scripts/merge_scheduler_code.py
"""

import os
import re
import sys
import shutil

def copy_init_to_src(project_root: str):
    """从 init/ 复制源文件到 src/"""
    init_dir = os.path.join(project_root, 'init')
    src_dir = os.path.join(project_root, 'src')
    
    os.makedirs(src_dir, exist_ok=True)
    
    files_to_copy = ['lib0.c', 'lib1.c', 'devc.c']
    for fname in files_to_copy:
        src_file = os.path.join(init_dir, fname)
        dst_file = os.path.join(src_dir, fname)
        if os.path.exists(src_file):
            shutil.copy2(src_file, dst_file)
            print(f"    复制: {fname}")


def modify_lib0_header(lib0_path: str):
    """修改 lib0.c 头部以去除 TVM 依赖"""
    with open(lib0_path, 'r') as f:
        content = f.read()
    
    # 替换 TVM 头文件
    old_header = '#include "tvm/runtime/c_runtime_api.h"'
    new_header = '#define TVM_DLL\n#include <stdint.h>'
    content = content.replace(old_header, new_header)
    
    # 移除 section 属性（包含尾随的空白和换行，但保持 static 等关键字）
    # 匹配: __attribute__((section("xxx"), )) 或 __attribute__((section("xxx"), aligned(16)))
    content = re.sub(
        r'__attribute__\(\(section\("[^"]+"\),\s*\)\)\s*\n',
        '',
        content
    )
    content = re.sub(
        r'__attribute__\(\(section\("[^"]+"\),\s*aligned\(\d+\)\)\)',
        '',
        content
    )
    
    # 移除 static 关键字，使 workspace 变量外部可见
    content = re.sub(r'\bstatic struct global_const_workspace\b', 'struct global_const_workspace', content)
    content = re.sub(r'\bstatic uint8_t global_workspace\b', 'uint8_t global_workspace', content)
    
    # 移除 tvmgen_default_run 函数（将在 lib1.c 中定义）
    content = re.sub(
        r'int32_t tvmgen_default_run\([^)]+\)\s*\{[^}]+\}',
        '// tvmgen_default_run 移至 lib1.c',
        content
    )
    
    # 替换 tvmgen_default.h 包含
    content = re.sub(
        r'#include <tvmgen_default\.h>',
        '''struct tvmgen_default_inputs { void* images; };
struct tvmgen_default_outputs { void* output; };''',
        content
    )
    
    with open(lib0_path, 'w') as f:
        f.write(content)


def read_generated_files(project_root: str):
    """读取生成的代码文件"""
    files = {}
    
    entity_file = os.path.join(project_root, 'entity_generated.c')
    dag_file = os.path.join(project_root, 'dag_schedule_generated.c')
    entities_file = os.path.join(project_root, 'entities_generated.c')
    runtime_file = os.path.join(project_root, 'scripts', 'templates', 'scheduler_runtime.c')
    
    if os.path.exists(entity_file):
        with open(entity_file, 'r') as f:
            files['entity'] = f.read()
    
    if os.path.exists(dag_file):
        with open(dag_file, 'r') as f:
            files['dag'] = f.read()
    
    if os.path.exists(entities_file):
        with open(entities_file, 'r') as f:
            files['entities'] = f.read()
    
    if os.path.exists(runtime_file):
        with open(runtime_file, 'r') as f:
            files['runtime'] = f.read()
    
    return files


def extract_operator_implementations(lib1_content: str) -> str:
    """提取算子函数的实现代码"""
    
    # 找第一个函数定义（定义以 { 结尾，不是声明）
    # 形如：TVM_DLL int32_t tvmgen_default_fused_xxx(...) {
    first_impl_pattern = r'TVM_DLL\s+int32_t\s+tvmgen_default_fused_[a-zA-Z0-9_]+\s*\([^)]+\)\s*\{'
    first_match = re.search(first_impl_pattern, lib1_content)
    
    if not first_match:
        raise ValueError("找不到算子函数实现")
    
    start_pos = first_match.start()
    print(f"    函数实现起始位置: {start_pos}")
    
    # 找 __tvm_main__ 函数定义的位置（也是以 { 结尾）
    main_pattern = r'TVM_DLL\s+int32_t\s+tvmgen_default___tvm_main__\s*\([^)]+\)\s*\{'
    main_match = re.search(main_pattern, lib1_content)
    
    if not main_match:
        raise ValueError("找不到 __tvm_main__ 函数定义")
    
    end_pos = main_match.start()
    print(f"    __tvm_main__ 位置: {end_pos}")
    
    if end_pos <= start_pos:
        raise ValueError(f"位置错误: impl_start={start_pos}, main_start={end_pos}")
    
    # 提取实现代码
    implementations = lib1_content[start_pos:end_pos]
    
    return implementations


def build_new_lib1(
    orig_lib1_content: str,
    generated_files: dict,
    operators_impl: str
) -> str:
    """构建新的 lib1.c 内容"""
    
    lines = []
    
    # 1. 新头部
    lines.append("// tvm target: c -keys=cpu")
    lines.append("#define TVM_DLL")
    lines.append("#define TVM_EXPORTS")
    lines.append("#include <stdint.h>")
    lines.append("#include <math.h>")
    lines.append("#include <stdbool.h>")
    lines.append("#include <pthread.h>")
    lines.append("#include <stdlib.h>")
    lines.append("#include <stdio.h>")
    lines.append("#include <string.h>")
    lines.append("#include <time.h>")
    lines.append("")
    
    # 2. 外部变量声明（来自 lib0.c）
    lines.append("// 外部变量声明（来自 lib0.c）")
    lines.append("extern uint8_t global_const_workspace[];")
    lines.append("extern uint8_t global_workspace[];")
    lines.append("")
    
    # 3. 生成的数据结构定义
    if 'entity' in generated_files:
        lines.append(generated_files['entity'])
    
    # 4. DAG 调度表
    if 'dag' in generated_files:
        lines.append(generated_files['dag'])
    
    # 5. 运行时代码
    if 'runtime' in generated_files:
        lines.append(generated_files['runtime'])
    
    # 6. 算子实现代码
    lines.append("")
    lines.append("// ============ 算子实现 ============")
    lines.append(operators_impl)
    
    # 7. 新的入口函数
    lines.append("")
    lines.append("// ============ 模型入口函数 ============")
    lines.append("")
    lines.append("#ifdef __cplusplus")
    lines.append('extern "C"')
    lines.append("#endif")
    lines.append("TVM_DLL int32_t tvmgen_default___tvm_main__(")
    lines.append("    float* images_buffer_var,")
    lines.append("    float* output_buffer_var,")
    lines.append("    uint8_t* global_const_workspace_0_var,")
    lines.append("    uint8_t* global_workspace_1_var) {")
    lines.append("")
    
    # 注入 entities 初始化代码（包含 sid 定义和 g_entities 数组）
    if 'entities' in generated_files:
        entities_content = generated_files['entities']
        for line in entities_content.split('\n'):
            if line.strip():
                lines.append("    " + line)
    
    lines.append("")
    lines.append("    // 运行 Scheduler-Worker 调度")
    lines.append("    return tvmrt_run(global_const_workspace_0_var, global_workspace_1_var, g_entities);")
    lines.append("}")
    lines.append("")
    
    # 8. tvmgen_default_run 封装函数
    lines.append("// ============ 兼容接口 ============")
    lines.append("")
    lines.append("struct tvmgen_default_inputs { void* images; };")
    lines.append("struct tvmgen_default_outputs { void* output; };")
    lines.append("")
    lines.append("#ifdef __cplusplus")
    lines.append('extern "C"')
    lines.append("#endif")
    lines.append("TVM_DLL int32_t tvmgen_default_run(")
    lines.append("    struct tvmgen_default_inputs* inputs,")
    lines.append("    struct tvmgen_default_outputs* outputs) {")
    lines.append("    return tvmgen_default___tvm_main__(")
    lines.append("        (float*)inputs->images,")
    lines.append("        (float*)outputs->output,")
    lines.append("        global_const_workspace,")
    lines.append("        global_workspace);")
    lines.append("}")
    lines.append("")
    
    return '\n'.join(lines)


def generate_makefile(project_root: str, model_name: str, op_count: int):
    """生成 Makefile"""
    makefile_content = f'''# ============================================================
# 自动生成的 Makefile
# 模型: {model_name}
# 算子数量: {op_count}
# ============================================================

CC ?= gcc
CXX ?= g++
AR ?= ar

# 编译选项
CFLAGS = -O3 -Wall -fPIC -pthread 
CXXFLAGS = -O3 -Wall -fPIC -pthread 
LDFLAGS = -lm -pthread 

# 构建目录
BUILD_DIR = build
OBJ_DIR = $(BUILD_DIR)/obj
LIB_DIR = $(BUILD_DIR)/lib

# 源文件目录
SRC_DIR = src
TEST_DIR = test

# 源文件列表
SRCS = $(SRC_DIR)/lib0.c $(SRC_DIR)/lib1.c 
OBJS = $(SRCS:$(SRC_DIR)/%.c=$(OBJ_DIR)/%.o)

# 库文件
STATIC_LIB = $(LIB_DIR)/lib{model_name}.a

# 测试可执行文件
TEST_BIN = $(BUILD_DIR)/{model_name}_test

# 默认目标
.PHONY: all
all: $(STATIC_LIB) $(TEST_BIN)

# 创建目录
$(OBJ_DIR):
\t@mkdir -p $(OBJ_DIR)

$(LIB_DIR):
\t@mkdir -p $(LIB_DIR)

# 编译源文件
$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c | $(OBJ_DIR)
\t$(CC) $(CFLAGS) -c $< -o $@

# 生成静态库
$(STATIC_LIB): $(OBJS) | $(LIB_DIR)
\t$(AR) rcs $@ $^

# 编译测试
$(TEST_BIN): $(OBJS) $(OBJ_DIR)/test_main.o | $(BUILD_DIR)
\t$(CC) -o $@ $^ $(LDFLAGS)

$(OBJ_DIR)/test_main.o: $(TEST_DIR)/test_main.c | $(OBJ_DIR)
\t$(CC) $(CFLAGS) -c $< -o $@

# 运行测试
.PHONY: run
run: $(TEST_BIN)
\t@echo "Running {model_name} test..."
\t./$(TEST_BIN)

# 仅编译静态库
.PHONY: lib
lib: $(STATIC_LIB)

# 仅编译测试
.PHONY: test
test: $(TEST_BIN)

# 清理
.PHONY: clean
clean:
\trm -rf $(BUILD_DIR)

# 调试编译
.PHONY: debug
debug: CFLAGS = -g -O0 -Wall -fPIC 
debug: clean all
'''
    makefile_path = os.path.join(project_root, 'Makefile')
    with open(makefile_path, 'w') as f:
        f.write(makefile_content)
    return makefile_path


def generate_test_main(project_root: str, model_name: str, input_size: int, output_size: int):
    """生成 test_main.c（全0输入，打印前20个输出）"""
    input_kb = input_size * 4 / 1024
    output_kb = output_size * 4 / 1024
    
    test_content = f'''/**
 * 自动生成的测试入口文件
 * 模型: {model_name}
 * 输入大小: {input_size} floats ({input_kb:.1f} KB)
 * 输出大小: {output_size} floats ({output_kb:.1f} KB)
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>

// TVM 模型输入输出结构体
struct tvmgen_default_inputs {{
    void* images;
}};

struct tvmgen_default_outputs {{
    void* output;
}};

// 模型运行函数声明
int32_t tvmgen_default_run(struct tvmgen_default_inputs*, struct tvmgen_default_outputs*);

// 打印前 N 个元素
void print_first_elements(const char* name, float* data, int count) {{
    printf("%s (first %d elements):\\n", name, count);
    for (int i = 0; i < count; i++) {{
        printf("  [%2d] %.6f\\n", i, data[i]);
    }}
}}

int main(int argc, char* argv[]) {{
    // 解析命令行参数
    int iterations = 1;
    for (int i = 1; i < argc; i++) {{
        if (strcmp(argv[i], "-n") == 0 && i + 1 < argc) {{
            iterations = atoi(argv[++i]);
        }}
    }}

    // 分配输入内存（全0）
    float* input = (float*)calloc({input_size}, sizeof(float));
    if (!input) {{
        fprintf(stderr, "Failed to allocate input memory\\n");
        return 1;
    }}

    // 分配输出内存
    float* output = (float*)calloc({output_size}, sizeof(float));
    if (!output) {{
        fprintf(stderr, "Failed to allocate output memory\\n");
        free(input);
        return 1;
    }}

    struct tvmgen_default_inputs inputs = {{ .images = input }};
    struct tvmgen_default_outputs outputs = {{ .output = output }};

    printf("=== {model_name} Test ===\\n");
    printf("Input size: {input_size} floats ({input_kb:.1f} KB)\\n");
    printf("Output size: {output_size} floats ({output_kb:.1f} KB)\\n");
    printf("Iterations: %d\\n", iterations);

    printf("\\nRunning inference...\\n");
    double total_time = 0.0;

    for (int i = 0; i < iterations; i++) {{
        clock_t start = clock();
        int ret = tvmgen_default_run(&inputs, &outputs);
        clock_t end = clock();
        double elapsed = (double)(end - start) / CLOCKS_PER_SEC * 1000.0;
        total_time += elapsed;

        if (ret != 0) {{
            fprintf(stderr, "Inference %d failed with error: %d\\n", i + 1, ret);
            free(input);
            free(output);
            return ret;
        }}
        printf("  Iteration %d: %.2f ms\\n", i + 1, elapsed);
    }}

    double avg_time = total_time / iterations;
    printf("\\n=== Results ===\\n");
    printf("Total time: %.2f ms\\n", total_time);
    printf("Average time: %.2f ms\\n", avg_time);
    printf("FPS: %.1f\\n", 1000.0 / avg_time);

    // 打印前20个输出元素
    print_first_elements("Output", output, 20);

    free(input);
    free(output);

    printf("\\nTest completed successfully!\\n");
    return 0;
}}
'''
    test_dir = os.path.join(project_root, 'test')
    os.makedirs(test_dir, exist_ok=True)
    test_path = os.path.join(test_dir, 'test_main.c')
    with open(test_path, 'w') as f:
        f.write(test_content)
    return test_path


def parse_io_sizes(lib1_path: str):
    """从 lib1.c 解析输入输出大小"""
    with open(lib1_path, 'r') as f:
        content = f.read()
    
    # 默认值（YOLOv8n）
    input_size = 1228800   # 3*640*640
    output_size = 2714985  # 从模型推断
    
    # 尝试从 __tvm_main__ 函数参数推断
    # 这里使用默认值，因为精确解析比较复杂
    return input_size, output_size


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_name = os.path.basename(project_root)
    
    print("[merge_scheduler_code] 项目根目录:", project_root)
    print(f"[merge_scheduler_code] 模型名称: {model_name}")
    
    # 1. 从 init 复制到 src
    print("\\n[1/6] 从 init/ 复制源文件到 src/ ...")
    copy_init_to_src(project_root)
    
    # 2. 修改 lib0.c
    print("\\n[2/6] 修改 lib0.c 头部 ...")
    lib0_path = os.path.join(project_root, 'src', 'lib0.c')
    modify_lib0_header(lib0_path)
    
    # 3. 读取生成的代码
    print("\\n[3/6] 读取生成的代码文件 ...")
    generated_files = read_generated_files(project_root)
    
    if not generated_files:
        print("警告: 未找到生成的代码文件，请先运行 operator_staticizer.py")
        return 1
    
    for name in generated_files:
        print(f"    加载: {name}")
    
    # 4. 读取原始 lib1.c（从 init/ 目录读取）
    print("\\n[4/6] 提取算子实现 ...")
    init_lib1_path = os.path.join(project_root, 'init', 'lib1.c')
    with open(init_lib1_path, 'r') as f:
        orig_content = f.read()
    
    operators_impl = extract_operator_implementations(orig_content)
    print(f"    提取了 {len(operators_impl)} 字节的算子实现代码")
    
    # 5. 构建新的 lib1.c
    print("\\n[5/6] 构建新的 lib1.c ...")
    new_content = build_new_lib1(orig_content, generated_files, operators_impl)
    
    # 写入 src/lib1.c
    src_lib1_path = os.path.join(project_root, 'src', 'lib1.c')
    with open(src_lib1_path, 'w') as f:
        f.write(new_content)
    
    print(f"    写入: {src_lib1_path}")
    print(f"    新文件大小: {len(new_content)} 字节")
    
    # 6. 生成 Makefile 和测试文件
    print("\\n[6/6] 生成 Makefile 和测试文件 ...")
    
    # 从 entity_generated.c 获取算子数量
    entity_path = os.path.join(project_root, 'entity_generated.c')
    op_count = 94  # 默认值
    if os.path.exists(entity_path):
        with open(entity_path, 'r') as f:
            entity_content = f.read()
        match = re.search(r'#define OP_COUNT (\d+)', entity_content)
        if match:
            op_count = int(match.group(1))
    
    # 获取输入输出大小
    input_size, output_size = parse_io_sizes(init_lib1_path)
    
    makefile_path = generate_makefile(project_root, model_name, op_count)
    print(f"    生成: {makefile_path}")
    
    test_path = generate_test_main(project_root, model_name, input_size, output_size)
    print(f"    生成: {test_path}")
    
    print("\\n[merge_scheduler_code] 完成!")
    return 0


if __name__ == '__main__':
    sys.exit(main())

