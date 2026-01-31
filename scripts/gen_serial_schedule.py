#!/usr/bin/env python3
"""
生成串行调度表（每层只有 1 个算子，从 0 到 N-1 编号）

这是最简单的调度方式，不做任何并行分析，直接按原始执行顺序串行执行。
用于：
1. 作为并行版本的对照基准
2. 调试时确保执行顺序正确
3. 不需要并行的场景
"""

import re
import sys
from pathlib import Path


def count_operators(source_file: Path) -> int:
    """从 lib1.c 中统计算子调用数量"""
    content = source_file.read_text()
    
    # 方法1: 解析主函数中的算子调用
    # 匹配: if (tvmgen_default_XXX(...) != 0 ) return -1;
    func_calls = re.findall(
        r'if\s*\(\s*tvmgen_default_(?!_tvm_main__)(\w+)\s*\([^)]+\)\s*!=\s*0\s*\)',
        content
    )
    
    if func_calls:
        return len(func_calls)
    
    # 方法2: 从外部 op_args 文件（如果传入）
    return 0


def generate_serial_schedule(op_count: int, prefix: str = "") -> str:
    """生成串行调度表 C 代码"""
    type_prefix = prefix.replace('.', '_').rstrip('_') + '_' if prefix else ""
    layer_struct = f"{type_prefix}schedule_layer_t" if prefix else "schedule_layer_t"
    
    lines = [
        "// ============================================================",
        "// 串行调度表 - 每层 1 个算子，按原始执行顺序",
        "// 用于对照测试或无并行场景",
        "// ============================================================",
        "",
    ]

    # 生成每层的数组定义
    for i in range(op_count):
        lines.append(f"static const int32_t g_layer_{i}[] = {{ {i} }};")

    lines.append("")
    lines.append(f"static const {layer_struct} g_schedule[] = {{")

    for i in range(op_count):
        lines.append(f"    {{ g_layer_{i}, 1 }},")

    lines.append("};")
    lines.append("")
    lines.append(f"#define NUM_LAYERS {op_count}")

    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='生成串行调度表（每层 1 个算子）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 从 lib1.c 自动检测算子数量
  python3 scripts/gen_serial_schedule.py src/lib1.c

  # 手动指定算子数量
  python3 scripts/gen_serial_schedule.py -n 94

  # 输出到指定文件
  python3 scripts/gen_serial_schedule.py src/lib1.c -o src/schedule_serial.c
        """
    )
    parser.add_argument(
        'input',
        type=Path,
        nargs='?',
        help='TVM 生成的源文件 (lib1.c)，用于自动检测算子数量'
    )
    parser.add_argument(
        '-n', '--op-count',
        type=int,
        help='算子数量（如果不从文件检测）'
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        default=Path('schedule_serial.c'),
        help='输出文件路径 (默认: schedule_serial.c)'
    )
    parser.add_argument(
        '--prefix',
        type=str,
        default='',
        help='命名前缀，用于避免多模型冲突'
    )

    args = parser.parse_args()

    # 确定算子数量
    if args.op_count:
        op_count = args.op_count
    elif args.input and args.input.exists():
        op_count = count_operators(args.input)
        if op_count == 0:
            print(f"错误: 无法从 {args.input} 检测算子数量，请使用 -n 手动指定", file=sys.stderr)
            return 1
    else:
        print("错误: 请提供输入文件或使用 -n 指定算子数量", file=sys.stderr)
        return 1

    print(f"=== 串行调度表生成工具 ===")
    print(f"算子数量: {op_count}")
    print(f"输出文件: {args.output}")
    if args.prefix:
        print(f"命名前缀: {args.prefix}")
    print()

    # 生成代码
    c_code = generate_serial_schedule(op_count, args.prefix)

    # 输出
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(c_code)
    print(f"✓ 已生成串行调度表: {args.output}")
    print(f"  - 层数: {op_count}")
    print(f"  - 每层算子数: 1")

    return 0


if __name__ == "__main__":
    sys.exit(main())
