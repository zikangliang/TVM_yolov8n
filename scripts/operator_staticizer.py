#!/usr/bin/env python3
"""
TVM 算子静态化工具（通用版本 - 支持多输入多输出）
自动将 TVM 生成的多样性函数签名转换为统一的静态接口

适用于任何 TVM 生成的模型，不限于特定模型名称。

功能：
1. 解析 TVM 生成的函数签名
2. 自动检测最大输入/输出数量
3. 生成 wrapped 适配器函数（支持多输出）
4. 生成函数指针表、名称表
5. 生成参数配置表模板
"""

import re
import sys
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional


class OperatorInfo:
    """算子信息（支持多输入多输出）"""

    def __init__(self, name: str, inputs: int, outputs: int = 1, has_ws: bool = True, prefix: str = ""):
        self.name = name              # 函数名
        self.inputs = inputs          # 输入参数数量
        self.outputs = outputs        # 输出参数数量
        self.has_ws = has_ws          # 是否有 workspace 参数
        self.wrapped_name = f"wrapped_{name}"
        self.prefix = prefix

    def wrapper_code(self, op_args_name: str) -> str:
        """生成 wrapped 适配器代码（支持多输出）"""
        input_params = ", ".join([f"args->inputs[{i}]" for i in range(self.inputs)])
        output_params = ", ".join([f"args->outputs[{i}]" for i in range(self.outputs)])
        
        if input_params and output_params:
            all_params = f"{input_params}, {output_params}"
        elif input_params:
            all_params = input_params
        else:
            all_params = output_params
            
        return f"""static inline int32_t {self.wrapped_name}({op_args_name} *args, uint8_t *cws, uint8_t *ws) {{
  return {self.name}({all_params}, cws, ws);
}}"""

    def __repr__(self):
        return f"OperatorInfo({self.name}, inputs={self.inputs}, outputs={self.outputs})"


class TVMCodeParser:
    """解析 TVM 生成的 C 代码（支持多输入多输出）"""

    # 匹配 TVM 函数声明: TVM_DLL int32_t tvmgen_default_...(type* name, ...)
    FUNC_PATTERN = re.compile(
        r'^TVM_DLL\s+int32_t\s+(tvmgen_default_\w+)\s*\(([^)]+)\);',
        re.MULTILINE
    )

    # 匹配参数类型: float*, void*, int32_t, uint8_t*
    PARAM_PATTERN = re.compile(
        r'(?:float|void|int32_t|uint8_t|int)\s*\*?\s*(\w+)'
    )

    def __init__(self, source_file: Path):
        self.source_file = source_file
        self.operators: List[OperatorInfo] = []
        self.max_inputs = 0
        self.max_outputs = 0

    def parse(self, prefix: str = "") -> List[OperatorInfo]:
        """解析源文件，提取所有算子函数"""
        content = self.source_file.read_text()

        # 找所有函数声明
        for match in self.FUNC_PATTERN.finditer(content):
            func_name = match.group(1)
            params_str = match.group(2)

            # 跳过主函数
            if "__tvm_main__" in func_name:
                continue

            # 解析参数（输入和输出）
            inputs, outputs = self._count_io_params(params_str)
            
            # 更新最大值
            self.max_inputs = max(self.max_inputs, inputs)
            self.max_outputs = max(self.max_outputs, outputs)

            self.operators.append(OperatorInfo(func_name, inputs, outputs, True, prefix))

        return self.operators

    def _count_io_params(self, params_str: str) -> Tuple[int, int]:
        """
        解析参数字符串，区分输入和输出数量
        TVM 函数签名模式: (input1, input2, ..., output1, output2, ..., cws, ws)
        
        输出参数的特征:
        - 名称包含 'output', 'T_', 'concatenate_ext', 'pool_max', 'conv2d_NCHWc' 等
        - 通常位于 workspace 参数之前
        """
        # 提取参数名
        param_names = self.PARAM_PATTERN.findall(params_str)

        # 过滤掉 workspace 参数
        filtered = [p for p in param_names
                    if not p.startswith("global_const_workspace_")
                    and not p.startswith("global_workspace_")]

        # 识别输出参数的特征模式
        output_patterns = [
            'output', 'T_', 'concatenate_ext', 'pool_max', 'conv2d_NCHWc',
            'T_add', 'T_multiply', 'T_layout_trans', 'T_softmax', 'T_transpose',
            'T_split', 'T_split_1'
        ]
        
        # 从后向前扫描，找出输出参数
        outputs = 0
        inputs = len(filtered)
        
        # 简单启发式：检查最后几个参数是否匹配输出模式
        for i in range(len(filtered) - 1, -1, -1):
            param = filtered[i]
            is_output = any(pattern in param for pattern in output_patterns)
            
            # 如果发现输入参数模式（p0, p1 等），停止
            if param.startswith('p') and (param[1:].isdigit() or param[1:].startswith('0_')):
                break
            
            if is_output:
                outputs += 1
            else:
                break
        
        inputs = len(filtered) - outputs
        
        # 确保至少有1个输出
        if outputs == 0:
            outputs = 1
            inputs = max(0, len(filtered) - 1)
        
        return inputs, outputs


class StaticCodeGenerator:
    """生成静态化代码（支持多输入多输出）"""

    def __init__(self, operators: List[OperatorInfo], op_count: int, 
                 max_inputs: int, max_outputs: int, prefix: str = ""):
        self.operators = operators
        self.op_count = op_count
        self.max_inputs = max(max_inputs, 1)  # 至少1个
        self.max_outputs = max(max_outputs, 1)  # 至少1个
        self.prefix = prefix

        # 类型名称
        type_prefix = prefix.replace('.', '_').rstrip('_') + '_' if prefix else ""
        self.op_args_name = f"{type_prefix}op_args_t"
        self.op_func_name = f"{type_prefix}op_func_t"
        self.op_count_macro = f"{type_prefix}OP_COUNT"
        self.max_inputs_macro = f"{type_prefix}MAX_INPUTS"
        self.max_outputs_macro = f"{type_prefix}MAX_OUTPUTS"

    def generate_type_defs(self) -> str:
        """生成类型定义"""
        return f"""// 动态计算的最大输入/输出数量
#define {self.max_inputs_macro} {self.max_inputs}
#define {self.max_outputs_macro} {self.max_outputs}

typedef struct {{
    void* inputs[{self.max_inputs_macro}];
    void* outputs[{self.max_outputs_macro}];
    int input_count;
    int output_count;
}} {self.op_args_name};

typedef int32_t (*{self.op_func_name})({self.op_args_name}* args, uint8_t* cws, uint8_t* ws);
"""

    def generate_wrappers(self) -> str:
        """生成所有 wrapped 函数"""
        lines = [
            "// Wrapped operator adapters for unified call signature.",
            ""
        ]
        for op in self.operators:
            lines.append(op.wrapper_code(self.op_args_name))
            lines.append("")
        return "\n".join(lines)

    def generate_call_table(self) -> str:
        """生成函数指针表"""
        lines = [
            f"static const {self.op_func_name} g_op_call_table[{self.op_count_macro}] = {{"
        ]
        for op in self.operators:
            lines.append(f"  {op.wrapped_name},")
        lines.append("};")
        return "\n".join(lines)

    def generate_names_table(self) -> str:
        """生成函数名称表"""
        lines = [
            f"static const char* const g_op_call_names[{self.op_count_macro}] = {{"
        ]
        for op in self.operators:
            # 使用原始函数名（不带 wrapped_ 前缀）
            lines.append(f'  "{op.name}",')
        lines.append("};")
        return "\n".join(lines)

    def generate_op_args_template(self) -> str:
        """生成参数配置表模板"""
        lines = [
            "// 算子参数配置表",
            "// 注意：需要手动填充每个算子的输入输出地址",
            "",
            f"{self.op_args_name} op_args[{self.op_count_macro}] = {{",
        ]
        for i, op in enumerate(self.operators):
            inputs = ", ".join(["0" for _ in range(self.max_inputs)])
            outputs = ", ".join(["0" for _ in range(self.max_outputs)])
            line = f"  {{.inputs = {{ {inputs} }}, .outputs = {{ {outputs} }}, .input_count = {op.inputs}, .output_count = {op.outputs}}},  // [{i}] {op.name}"
            lines.append(line)
        lines.append("};")
        return "\n".join(lines)

    def generate_all(self) -> str:
        """生成完整代码"""
        sections = [
            "/**",
            " * 自动生成的算子静态化代码",
            f" * 算子数量: {len(self.operators)}",
            f" * 最大输入数: {self.max_inputs}",
            f" * 最大输出数: {self.max_outputs}",
            " */",
            "",
            self.generate_wrappers(),
            "",
            self.generate_names_table(),
            "",
            self.generate_call_table(),
            "",
            self.generate_op_args_template(),
        ]
        return "\n".join(sections)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='TVM 算子静态化工具（通用版本 - 支持多输入多输出）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本用法
  python3 scripts/operator_staticizer.py src/lib1.c

  # 指定输出文件
  python3 scripts/operator_staticizer.py src/lib1.c -o generated_ops.c

  # 添加命名前缀（避免多模型冲突）
  python3 scripts/operator_staticizer.py src/lib1.c --prefix mymodel
        """
    )
    parser.add_argument(
        'input',
        type=Path,
        help='TVM 生成的源文件 (如 lib1.c 或 initial/lib1.c)'
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        default=Path('generated_static_ops.c'),
        help='输出文件路径 (默认: generated_static_ops.c)'
    )
    parser.add_argument(
        '-n', '--op-count',
        type=int,
        default=None,
        help='算子总数 (默认: 自动检测)'
    )
    parser.add_argument(
        '--format',
        choices=['full', 'wrappers', 'tables', 'template', 'types'],
        default='full',
        help='生成内容格式 (默认: full)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='输出 JSON 格式的算子信息'
    )
    parser.add_argument(
        '--prefix',
        type=str,
        default='',
        help='命名前缀，用于避免多模型冲突 (如: mymodel -> mymodel_OP_COUNT)'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='静默模式，只输出代码不输出日志'
    )

    args = parser.parse_args()

    # 检查输入文件
    if not args.input.exists():
        print(f"错误: 文件不存在: {args.input}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"=== TVM 算子静态化工具 (多输入多输出版) ===")
        print(f"输入文件: {args.input}")
        print(f"输出文件: {args.output}")
        if args.prefix:
            print(f"命名前缀: {args.prefix}")
        print()

    # 解析 TVM 代码
    parser_inst = TVMCodeParser(args.input)
    operators = parser_inst.parse(args.prefix)
    
    # 获取最大输入输出数
    max_inputs = parser_inst.max_inputs
    max_outputs = parser_inst.max_outputs
    
    # 使用检测到的算子数量，除非用户指定
    op_count = args.op_count if args.op_count else len(operators)

    if not args.quiet:
        print(f"解析到 {len(operators)} 个算子函数")
        print(f"最大输入数: {max_inputs}")
        print(f"最大输出数: {max_outputs}")
        print()

        # 显示算子列表
        print("算子列表:")
        for i, op in enumerate(operators):
            print(f"  [{i:2d}] {op.name:60s} inputs={op.inputs}, outputs={op.outputs}")
        print()

    # 生成代码
    generator = StaticCodeGenerator(operators, op_count, max_inputs, max_outputs, args.prefix)

    if args.format == 'full':
        code = generator.generate_all()
    elif args.format == 'wrappers':
        code = generator.generate_wrappers()
    elif args.format == 'tables':
        code = generator.generate_names_table() + "\n\n" + generator.generate_call_table()
    elif args.format == 'template':
        code = generator.generate_op_args_template()
    elif args.format == 'types':
        code = generator.generate_type_defs()

    # 写入输出文件
    args.output.write_text(code)
    if not args.quiet:
        print(f"✓ 代码已生成: {args.output}")

    # 输出 JSON (如果需要)
    if args.json:
        json_path = args.output.with_suffix('.json')
        data = {
            'max_inputs': max_inputs,
            'max_outputs': max_outputs,
            'op_count': len(operators),
            'operators': [
                {
                    'index': i,
                    'name': op.name,
                    'wrapped_name': op.wrapped_name,
                    'inputs': op.inputs,
                    'outputs': op.outputs
                }
                for i, op in enumerate(operators)
            ]
        }
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        if not args.quiet:
            print(f"✓ JSON 信息: {json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
