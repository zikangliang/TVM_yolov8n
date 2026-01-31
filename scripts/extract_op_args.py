#!/usr/bin/env python3
"""
自动提取 TVM 主函数中的 op_args 信息（通用版本 - 支持多输入多输出）

解析主函数中的：
1. 变量定义 (sid_X_let = global_workspace_1_var[offset])
2. 函数调用 (tvmgen_default_XXX(sid_A_let, sid_B_let, ...))

自动识别输入和输出参数，生成完整的 op_args 表

适用于任何 TVM 生成的模型，不限于特定模型名称。
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class MainFunctionParser:
    """解析 TVM 主函数，提取算子调用关系（支持多输出）"""

    # 匹配变量定义: void* sid_48_let = (&(global_workspace_1_var[5817600]));
    VAR_DEF_PATTERN = re.compile(
        r'void\*\s+(sid_\d+_let)\s*=\s*\(\&\(global_workspace_1_var\[(\d+)\]\)\);'
    )

    # 匹配函数调用: if (tvmgen_default_XXX(sid_A_let, sid_B_let, ..., global_const_workspace_0_var, global_workspace_1_var) != 0 ) return -1;
    FUNC_CALL_PATTERN = re.compile(
        r'if\s*\(\s*(tvmgen_default_\w+)\s*\(([^)]+)\)\s*!=\s*0\s*\)\s*return\s*-1;'
    )

    # 匹配函数声明来判断输入输出
    FUNC_DECL_PATTERN = re.compile(
        r'TVM_DLL\s+int32_t\s+(tvmgen_default_\w+)\s*\(([^)]+)\);',
        re.MULTILINE
    )

    # 匹配函数参数中的变量名
    PARAM_PATTERN = re.compile(r'(sid_\d+_let|output_buffer_var|images_buffer_var)')
    
    # 输出参数的特征模式
    OUTPUT_PATTERNS = [
        'output', 'T_', 'concatenate_ext', 'pool_max', 'conv2d_NCHWc',
        'T_add', 'T_multiply', 'T_layout_trans', 'T_softmax', 'T_transpose',
        'T_split'
    ]

    def __init__(self, source_file: Path):
        self.source_file = source_file
        self.var_offsets: Dict[str, int] = {}  # 变量名 -> 偏移量
        self.op_calls: List[Dict] = []  # {func_name, inputs, outputs}
        self.func_signatures: Dict[str, Tuple[int, int]] = {}  # func_name -> (inputs, outputs)
        self.max_inputs = 0
        self.max_outputs = 0

    def parse(self) -> Tuple[Dict[str, int], List[Dict], int, int]:
        """解析主函数
        
        Returns:
            (var_offsets, op_calls, max_inputs, max_outputs)
        """
        content = self.source_file.read_text()

        # 1. 先解析函数声明，了解每个函数的输入输出数量
        self._parse_function_declarations(content)

        # 2. 提取主函数内容
        main_func = self._extract_main_function(content)
        if not main_func:
            raise ValueError("无法找到主函数 tvmgen_default___tvm_main__")

        # 3. 解析变量定义
        self._parse_variable_definitions(main_func)

        # 4. 解析函数调用
        self._parse_function_calls(main_func)

        return self.var_offsets, self.op_calls, self.max_inputs, self.max_outputs

    def _parse_function_declarations(self, content: str):
        """解析函数声明，确定每个函数的输入输出数量"""
        for match in self.FUNC_DECL_PATTERN.finditer(content):
            func_name = match.group(1)
            params_str = match.group(2)
            
            if "__tvm_main__" in func_name:
                continue
            
            inputs, outputs = self._analyze_signature(params_str)
            self.func_signatures[func_name] = (inputs, outputs)
            self.max_inputs = max(self.max_inputs, inputs)
            self.max_outputs = max(self.max_outputs, outputs)

    def _analyze_signature(self, params_str: str) -> Tuple[int, int]:
        """分析函数签名，区分输入和输出参数"""
        # 提取参数名和类型
        param_pattern = re.compile(r'(?:float|void|int32_t|uint8_t|int)\s*\*?\s*(\w+)')
        params = param_pattern.findall(params_str)
        
        # 过滤 workspace 参数
        filtered = [p for p in params
                    if not p.startswith("global_const_workspace_")
                    and not p.startswith("global_workspace_")]
        
        # 从后向前扫描，识别输出参数
        outputs = 0
        for i in range(len(filtered) - 1, -1, -1):
            param = filtered[i]
            is_output = any(pattern in param for pattern in self.OUTPUT_PATTERNS)
            
            # 如果发现输入参数模式（p0, p1 等），停止
            if param.startswith('p') and (param[1:].isdigit() or param[1:].replace('_', '').isdigit()):
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

    def _extract_main_function(self, content: str) -> str:
        """提取主函数内容"""
        pattern = re.compile(
            r'TVM_DLL\s+int32_t\s+tvmgen_default___tvm_main__\s*\([^)]+\)\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}',
            re.DOTALL
        )
        match = pattern.search(content)
        if match:
            return match.group(0)
        return ""

    def _parse_variable_definitions(self, main_func: str):
        """解析变量定义，建立变量名到偏移量的映射"""
        for match in self.VAR_DEF_PATTERN.finditer(main_func):
            var_name = match.group(1)
            offset = int(match.group(2))
            self.var_offsets[var_name] = offset

        # 添加特殊变量（输入输出）
        self.var_offsets['images_buffer_var'] = -1  # 输入，标记为 -1
        self.var_offsets['output_buffer_var'] = -2  # 输出，标记为 -2

    def _parse_function_calls(self, main_func: str):
        """解析函数调用，区分输入和输出"""
        for match in self.FUNC_CALL_PATTERN.finditer(main_func):
            func_name = match.group(1)
            params_str = match.group(2)

            # 提取参数中的变量名（排除 workspace）
            param_vars = [p for p in self.PARAM_PATTERN.findall(params_str)]

            if not param_vars:
                continue

            # 从函数签名获取输入输出数量
            if func_name in self.func_signatures:
                num_inputs, num_outputs = self.func_signatures[func_name]
            else:
                # 默认：最后一个是输出
                num_outputs = 1
                num_inputs = len(param_vars) - 1
            
            # 分割输入和输出
            inputs = param_vars[:num_inputs]
            outputs = param_vars[num_inputs:num_inputs + num_outputs]
            
            self.op_calls.append({
                'func_name': func_name,
                'inputs': inputs,
                'outputs': outputs
            })


class OpArgsGenerator:
    """生成 op_args 代码（支持多输出）"""

    def __init__(self, var_offsets: Dict[str, int], op_calls: List[Dict],
                 max_inputs: int, max_outputs: int, prefix: str = ""):
        self.var_offsets = var_offsets
        self.op_calls = op_calls
        self.max_inputs = max(max_inputs, 1)
        self.max_outputs = max(max_outputs, 1)
        self.prefix = prefix

        # 类型名称
        type_prefix = prefix.replace('.', '_').rstrip('_') + '_' if prefix else ""
        self.op_args_name = f"{type_prefix}op_args_t"
        self.op_count_macro = f"{type_prefix}OP_COUNT"
        self.max_inputs_macro = f"{type_prefix}MAX_INPUTS"
        self.max_outputs_macro = f"{type_prefix}MAX_OUTPUTS"

    def generate(self, with_var_def: bool = True, use_sid: bool = True) -> str:
        """生成 op_args 表代码

        Args:
            with_var_def: 是否生成 sid 变量定义（如果主函数已有，设为 false）
            use_sid: 使用 sid 变量名还是 workspace 地址
        """
        lines = [
            "// 自动生成的算子参数配置表（多输入多输出版）",
            f"// 算子数量: {len(self.op_calls)}",
            f"// 最大输入数: {self.max_inputs}",
            f"// 最大输出数: {self.max_outputs}",
            f"// 使用 {'sid 变量名' if use_sid else 'workspace 地址'}",
            "",
        ]

        # 如果使用 sid 变量名且需要变量定义
        if use_sid and with_var_def:
            lines.append("// sid 变量定义（指向 workspace 地址）")
            for var_name in sorted(self.var_offsets.keys()):
                if var_name in ['images_buffer_var', 'output_buffer_var']:
                    continue
                offset = self.var_offsets[var_name]
                lines.append(f"void* {var_name} = (&(global_workspace_1_var[{offset}]));")
            lines.append("")
            lines.append("// op_args 表（使用 sid 变量名）")
        elif use_sid:
            lines.append("// op_args 表（使用主函数内已有的 sid 变量名）")
        else:
            lines.append("// op_args 表（使用 workspace 地址）")

        lines.append(f"{self.op_args_name} op_args[{self.op_count_macro}] = {{")

        for i, op_call in enumerate(self.op_calls):
            func_name = op_call['func_name']
            inputs = op_call['inputs']
            outputs = op_call['outputs']

            # 构建输入数组
            inputs_arr = [self._var_to_c_code(v, use_sid) for v in inputs]
            # 填充到 max_inputs
            while len(inputs_arr) < self.max_inputs:
                inputs_arr.append("0")
            inputs_str = ", ".join(inputs_arr)

            # 构建输出数组
            outputs_arr = [self._var_to_c_code(v, use_sid) for v in outputs]
            # 填充到 max_outputs
            while len(outputs_arr) < self.max_outputs:
                outputs_arr.append("0")
            outputs_str = ", ".join(outputs_arr)

            comment = f"// [{i}] {func_name}"

            line = f"  {{.inputs = {{ {inputs_str} }}, .outputs = {{ {outputs_str} }}, .input_count = {len(inputs)}, .output_count = {len(outputs)}}}, {comment}"
            lines.append(line)

        lines.append("};")

        return "\n".join(lines)

    def _var_to_c_code(self, var_name: str, use_sid: bool) -> str:
        """将变量名转换为 C 代码"""
        if var_name in ['images_buffer_var', 'output_buffer_var']:
            return var_name
        elif var_name in self.var_offsets:
            if use_sid:
                return var_name
            else:
                offset = self.var_offsets[var_name]
                return f"(&(global_workspace_1_var[{offset}]))"
        else:
            return f"/* UNKNOWN: {var_name} */"


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='自动提取 TVM 主函数中的 op_args 信息（支持多输入多输出）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本用法
  python3 scripts/extract_op_args.py src/lib1.c

  # 不生成 sid 变量定义（主函数已有时）
  python3 scripts/extract_op_args.py src/lib1.c --no-var-def

  # 使用 workspace 地址而不是 sid 变量名
  python3 scripts/extract_op_args.py src/lib1.c --use-workspace

  # 添加命名前缀
  python3 scripts/extract_op_args.py src/lib1.c --prefix mymodel
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
        default=Path('op_args_generated.c'),
        help='输出文件路径 (默认: op_args_generated.c)'
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='生成完整代码（包含 wrapped 函数和查找表）'
    )
    parser.add_argument(
        '--use-workspace',
        action='store_true',
        help='使用 workspace 地址而不是 sid 变量名（默认使用 sid 变量名）'
    )
    parser.add_argument(
        '--no-var-def',
        action='store_true',
        help='不生成 sid 变量定义（主函数已有时使用）'
    )
    parser.add_argument(
        '--prefix',
        type=str,
        default='',
        help='命名前缀，用于避免多模型冲突 (如: mymodel -> mymodel_OP_COUNT)'
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"错误: 文件不存在: {args.input}", file=sys.stderr)
        return 1

    print(f"=== TVM op_args 自动提取工具（多输入多输出版）===")
    print(f"输入文件: {args.input}")
    if args.prefix:
        print(f"命名前缀: {args.prefix}")
    print()

    # 解析主函数
    parser_inst = MainFunctionParser(args.input)
    var_offsets, op_calls, max_inputs, max_outputs = parser_inst.parse()

    print(f"解析到 {len(var_offsets)} 个变量")
    print(f"解析到 {len(op_calls)} 个函数调用")
    print(f"最大输入数: {max_inputs}")
    print(f"最大输出数: {max_outputs}")
    print()

    # 显示变量列表
    print("变量列表 (部分):")
    for var, offset in sorted(var_offsets.items(), key=lambda x: x[1])[:10]:
        if offset >= 0:
            print(f"  {var:20s} -> global_workspace_1_var[{offset}]")
    print("  ...")
    print()

    # 显示函数调用列表
    print("函数调用列表 (部分):")
    for i, op_call in enumerate(op_calls[:10]):
        func_name = op_call['func_name']
        inputs_str = ", ".join(op_call['inputs'])
        outputs_str = ", ".join(op_call['outputs'])
        print(f"  [{i:2d}] {func_name}")
        print(f"       输入({len(op_call['inputs'])}): {inputs_str}")
        print(f"       输出({len(op_call['outputs'])}): {outputs_str}")
    print("  ...")
    print()

    # 生成代码
    use_sid = not args.use_workspace
    with_var_def = not args.no_var_def
    generator = OpArgsGenerator(var_offsets, op_calls, max_inputs, max_outputs, args.prefix)
    code = generator.generate(with_var_def=with_var_def, use_sid=use_sid)

    # 如果需要完整代码
    if args.full:
        print("生成完整代码...")
        print("提示: 使用 --full 需要结合 operator_staticizer.py")

    # 写入输出文件
    args.output.write_text(code)
    print(f"✓ 代码已生成: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
