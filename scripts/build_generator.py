#!/usr/bin/env python3
"""
Makefile 和测试文件生成器

在 src/lib0.c、src/lib1.c 完成后，自动生成：
1. Makefile - 支持多种编译选项
2. test/test_main.c - 测试入口文件

用法：
    python3 scripts/build_generator.py [--model-name MODEL_NAME]
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional, Tuple


class BuildGenerator:
    """构建配置生成器"""

    def __init__(self, src_dir: Path = Path("src"), test_dir: Path = Path("test")):
        self.src_dir = src_dir
        self.test_dir = test_dir

    def analyze_lib0(self) -> dict:
        """分析 lib0.c 的常量内存使用"""
        lib0_path = self.src_dir / "lib0.c"
        if not lib0_path.exists():
            return {"total_size": 0, "constants": []}

        content = lib0_path.read_text()

        # 匹配常量定义
        pattern = re.compile(
            r'float\s+fused_constant_\w+\s*\[\s*(\d+)\].*?//\s*(\d+)\s*bytes',
            re.MULTILINE
        )

        constants = []
        total_bytes = 0
        for match in pattern.finditer(content):
            size = int(match.group(1)) * 4  # float = 4 bytes
            comment = match.group(0)
            total_bytes += size
            constants.append({
                "size": size,
                "comment": comment.strip()
            })

        # 查找 total size 注释
        total_match = re.search(r'total.*?(\d+)\s*bytes', content, re.I)
        if total_match:
            total_bytes = int(total_match.group(1))

        return {
            "total_size": total_bytes,
            "constants": constants,
            "mb_size": total_bytes / (1024 * 1024)
        }

    def analyze_lib1(self) -> dict:
        """分析 lib1.c 的算子信息"""
        lib1_path = self.src_dir / "lib1.c"
        if not lib1_path.exists():
            return {"op_count": 0, "has_openmp": False}

        content = lib1_path.read_text()

        # 统计算子数量
        op_pattern = re.compile(r'TVM_DLL\s+int32_t\s+(tvmgen_default_\w+)\s*\(')
        ops = op_pattern.findall(content)

        # 检查是否有并行支持
        has_openmp = "_OPENMP" in content or "#include <omp.h>" in content

        # 检查是否有并行调度表
        has_schedule = "schedule_layer_t" in content or "g_schedule" in content

        # 检查是否有并行执行框架
        has_parallel = "parallel_run_ops" in content or "parallel_layer" in content

        return {
            "op_count": len(ops),
            "has_openmp": has_openmp,
            "has_schedule": has_schedule,
            "has_parallel": has_parallel,
            "ops": ops[:5]  # 只保存前5个用于显示
        }

    def detect_model_info(self) -> dict:
        """从项目目录名推断模型信息"""
        # 从当前工作目录获取模型名称
        cwd = Path.cwd()
        model_name = cwd.name  # 使用项目目录名作为模型名
        
        # 清理名称中的特殊字符
        model_name = re.sub(r'[^a-zA-Z0-9_]', '_', model_name)
        
        # 尝试推断输入形状 (粗略估计)
        input_shape = [1, 3, 640, 640]  # 默认

        return {
            "model_name": model_name,
            "input_shape": input_shape
        }

    def generate_makefile(self, model_name: str = "model", lib_files: list = None) -> str:
        """生成 Makefile"""
        if lib_files is None:
            lib_files = ["lib0", "lib1"]

        info = self.analyze_lib0()
        lib1_info = self.analyze_lib1()

        parallel_flag = "-fopenmp" if lib1_info["has_openmp"] else ""
        omp_cflags = "-fopenmp" if lib1_info["has_openmp"] else ""

        makefile = f'''# ============================================================
# 自动生成的 Makefile
# 模型: {model_name}
# 算子数量: {lib1_info['op_count']}
# 常量内存: {info['mb_size']:.2f} MB
# 并行支持: {'是' if lib1_info['has_openmp'] else '否'}
# ============================================================

CC ?= gcc
CXX ?= g++
AR ?= ar

# 编译选项
CFLAGS = -O3 -Wall -fPIC {omp_cflags}
CXXFLAGS = -O3 -Wall -fPIC {omp_cflags}
LDFLAGS = -lm {parallel_flag}

# 构建目录
BUILD_DIR = build
OBJ_DIR = $(BUILD_DIR)/obj
LIB_DIR = $(BUILD_DIR)/lib

# 源文件目录
SRC_DIR = src
TEST_DIR = test

# 源文件列表
SRCS = {''.join([f'$(SRC_DIR)/{f}.c ' for f in lib_files])}
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
	@mkdir -p $(OBJ_DIR)

$(LIB_DIR):
	@mkdir -p $(LIB_DIR)

# 编译源文件
$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c | $(OBJ_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

# 生成静态库
$(STATIC_LIB): $(OBJS) | $(LIB_DIR)
	$(AR) rcs $@ $^

# 编译测试
$(TEST_BIN): $(OBJS) $(OBJ_DIR)/test_main.o | $(BUILD_DIR)
	$(CC) -o $@ $^ $(LDFLAGS)

$(OBJ_DIR)/test_main.o: $(TEST_DIR)/test_main.c | $(OBJ_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

# 运行测试
.PHONY: run
run: $(TEST_BIN)
	@echo "Running {model_name} test..."
	./$(TEST_BIN)

# 仅编译静态库
.PHONY: lib
lib: $(STATIC_LIB)

# 仅编译测试
.PHONY: test
test: $(TEST_BIN)

# 清理
.PHONY: clean
clean:
	rm -rf $(BUILD_DIR)

# 完全清理（包括生成的 Makefile 和测试文件）
.PHONY: distclean
distclean: clean
	rm -f $(TEST_DIR)/test_main.c Makefile

# 查看算子信息
.PHONY: info
info:
	@echo "Model: {model_name}"
	@echo "Operators: {lib1_info['op_count']}"
	@echo "Constants Memory: {info['mb_size']:.2f} MB"
	@echo "OpenMP Support: {'Yes' if lib1_info['has_openmp'] else 'No'}"
	@echo "Parallel Schedule: {'Yes' if lib1_info['has_schedule'] else 'No'}"

# 调试编译（不优化）
.PHONY: debug
debug: CFLAGS = -g -O0 -Wall -fPIC {omp_cflags}
debug: CXXFLAGS = -g -O0 -Wall -fPIC {omp_cflags}
debug: clean all

# 发布编译（去除调试信息）
.PHONY: release
release: CFLAGS = -O3 -Wall -fPIC -DNDEBUG {omp_cflags}
release: $(TEST_BIN)
'''

        return makefile

    def generate_test_main(self, model_name: str = "model",
                          input_shape: list = None) -> str:
        """生成测试入口文件"""
        if input_shape is None:
            input_shape = [1, 3, 640, 640]

        # 计算输入输出元素数量
        input_elements = 1
        for dim in input_shape:
            input_elements *= dim

        # YOLOv5n 输出: 255 * (80*80 + 40*40 + 20*20) = 255 * 10647
        output_elements = 255 * 10647  # 默认 YOLOv5n

        # 尝试从 lib1.c 推断输出大小
        lib1_path = self.src_dir / "lib1.c"
        if lib1_path.exists():
            content = lib1_path.read_text()
            # 查找 output 相关的内存分配
            match = re.search(r'output.*?=\s*(?:calloc|malloc).*?(\d+)\s*\*', content)
            if match:
                output_elements = int(match.group(1))

        test_code = f'''/**
 * 自动生成的测试入口文件
 * 模型: {model_name}
 * 输入形状: {input_shape}
 * 输入大小: {input_elements} floats ({input_elements * 4 / 1024:.1f} KB)
 * 输出大小: {output_elements} floats ({output_elements * 4 / 1024:.1f} KB)
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

// 工具函数：打印前 N 个元素
void print_first_elements(const char* name, float* data, int count) {{
    printf("%s (first %d elements):\\n", name, count);
    for (int i = 0; i < count; i++) {{
        printf("  [%2d] %.6f\\n", i, data[i]);
    }}
}}

int main(int argc, char* argv[]) {{
    // 解析命令行参数
    int warmup = 0;
    int iterations = 1;
    for (int i = 1; i < argc; i++) {{
        if (strcmp(argv[i], "--warmup") == 0) {{
            warmup = 1;
        }} else if (strcmp(argv[i], "-n") == 0 && i + 1 < argc) {{
            iterations = atoi(argv[++i]);
        }}
    }}

    // 分配输入内存
    float* input = (float*)calloc({input_elements}, sizeof(float));
    if (!input) {{
        fprintf(stderr, "Failed to allocate input memory\\n");
        return 1;
    }}

    // 分配输出内存
    float* output = (float*)calloc({output_elements}, sizeof(float));
    if (!output) {{
        fprintf(stderr, "Failed to allocate output memory\\n");
        free(input);
        return 1;
    }}

    // 输入数据初始化为全0（calloc已将内存清零）
    // 如需使用随机值，取消注释以下代码：
    // srand(42);
    // for (int i = 0; i < {input_elements}; i++) {{
    //     input[i] = (float)rand() / RAND_MAX;
    // }}

    // 初始化输入输出结构体
    struct tvmgen_default_inputs inputs = {{ .images = input }};
    struct tvmgen_default_outputs outputs = {{ .output = output }};

    printf("=== {model_name} Test ===\\n");
    printf("Input shape: [{', '.join(str(x) for x in input_shape)}]\\n");
    printf("Input size: {input_elements} floats ({input_elements * 4 / 1024:.1f} KB)\\n");
    printf("Output size: {output_elements} floats ({output_elements * 4 / 1024:.1f} KB)\\n");
    printf("Iterations: %d\\n", iterations);

    // 预热运行
    if (warmup) {{
        printf("\\nWarmup run...\\n");
        int ret = tvmgen_default_run(&inputs, &outputs);
        if (ret != 0) {{
            fprintf(stderr, "Warmup failed with error: %d\\n", ret);
            free(input);
            free(output);
            return ret;
        }}
    }}

    // 计时运行
    printf("\\nRunning inference...\\n");
    double total_time = 0.0;

    for (int i = 0; i < iterations; i++) {{
        clock_t start = clock();

        int ret = tvmgen_default_run(&inputs, &outputs);

        clock_t end = clock();
        double elapsed = (double)(end - start) / CLOCKS_PER_SEC * 1000.0;  // ms
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

    // 释放内存
    free(input);
    free(output);

    printf("\\nTest completed successfully!\\n");
    return 0;
}}
'''
        return test_code

    def generate(self, model_name: str = None) -> dict:
        """执行完整的生成流程"""
        # 自动检测模型信息
        lib1_info = self.analyze_lib1()
        model_info = self.detect_model_info()

        if model_name is None:
            model_name = model_info["model_name"]

        # 生成 Makefile
        lib_files = ["lib0", "lib1"]
        makefile_content = self.generate_makefile(model_name, lib_files)

        # 生成测试文件
        test_content = self.generate_test_main(
            model_name,
            model_info["input_shape"]
        )

        return {
            "makefile": makefile_content,
            "test_main": test_content,
            "model_name": model_name,
            "op_count": lib1_info["op_count"],
            "has_openmp": lib1_info["has_openmp"],
            "has_parallel": lib1_info["has_parallel"]
        }


def main():
    parser = argparse.ArgumentParser(
        description='Makefile 和测试文件生成器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用默认配置生成
  python3 scripts/build_generator.py

  # 指定模型名称
  python3 scripts/build_generator.py --model-name yolov5n

  # 仅生成 Makefile
  python3 scripts/build_generator.py --no-test

  # 仅生成测试文件
  python3 scripts/build_generator.py --makefile-only
        """
    )
    parser.add_argument(
        '--model-name',
        type=str,
        default=None,
        help='模型名称 (默认: 从代码自动检测)'
    )
    parser.add_argument(
        '--makefile-only',
        action='store_true',
        help='仅生成 Makefile'
    )
    parser.add_argument(
        '--test-only',
        action='store_true',
        help='仅生成测试文件'
    )
    parser.add_argument(
        '--src-dir',
        type=Path,
        default=Path('src'),
        help='源文件目录 (默认: src)'
    )
    parser.add_argument(
        '--test-dir',
        type=Path,
        default=Path('test'),
        help='测试文件目录 (默认: test)'
    )
    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='强制覆盖已存在的文件'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='静默模式'
    )

    args = parser.parse_args()

    # 检查源文件是否存在
    lib0_path = args.src_dir / "lib0.c"
    lib1_path = args.src_dir / "lib1.c"

    if not lib0_path.exists():
        print(f"错误: 找不到 {lib0_path}", file=sys.stderr)
        print("请确保 src/lib0.c 已存在", file=sys.stderr)
        return 1

    if not lib1_path.exists():
        print(f"错误: 找不到 {lib1_path}", file=sys.stderr)
        print("请确保 src/lib1.c 已存在", file=sys.stderr)
        return 1

    # 创建生成器
    generator = BuildGenerator(args.src_dir, args.test_dir)

    # 执行生成
    result = generator.generate(args.model_name)

    # 输出结果
    if not args.quiet:
        print(f"=== 构建配置生成器 ===")
        print(f"模型名称: {result['model_name']}")
        print(f"算子数量: {result['op_count']}")
        print(f"OpenMP支持: {'是' if result['has_openmp'] else '否'}")
        print()

    # 生成文件
    if not args.test_only:
        makefile_path = Path("Makefile")
        if makefile_path.exists() and not args.force:
            print(f"警告: {makefile_path} 已存在，使用 -f 强制覆盖")
        else:
            makefile_path.write_text(result["makefile"])
            if not args.quiet:
                print(f"✓ 生成 Makefile")

    if not args.makefile_only:
        test_path = args.test_dir / "test_main.c"
        if test_path.exists() and not args.force:
            print(f"警告: {test_path} 已存在，使用 -f 强制覆盖")
        else:
            args.test_dir.mkdir(parents=True, exist_ok=True)
            test_path.write_text(result["test_main"])
            if not args.quiet:
                print(f"✓ 生成测试文件: {test_path}")

    if not args.quiet:
        print()
        print("使用说明:")
        print("  make          - 编译静态库和测试程序")
        print("  make run      - 运行测试")
        print("  make clean    - 清理构建文件")
        print("  make info     - 显示模型信息")
        print("  make debug    - 调试模式编译")
        print("  make release  - 发布模式编译")

    return 0


if __name__ == "__main__":
    sys.exit(main())
