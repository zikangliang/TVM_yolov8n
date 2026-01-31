#!/usr/bin/env python3
"""
自动合并并行调度代码到项目

功能：
1. 读取 schedule_generated.c 提取并行层信息
2. 读取 operator_staticizer.py 和 extract_op_args.py 的输出（或自动运行）
3. 将上述内容合并到 lib1.c
4. 替换主执行循环为并行分层执行
5. 更新 Makefile 以支持 OpenMP (如果可用)

用法:
    python3 scripts/merge_parallel_code.py src/lib1.c
    python3 scripts/merge_parallel_code.py src/lib1.c --schedule src/schedule_generated.c
    python3 scripts/merge_parallel_code.py src/lib1.c --op-args generated_op_args.c
"""

import re
import sys
import argparse
from pathlib import Path


def find_all_main_functions(content: str) -> list:
    """查找所有主函数（声明和定义）的位置"""
    pattern = re.compile(r'^TVM_DLL\s+int32_t\s+(tvmgen_default___tvm_main__)\s*\([^)]*\)\s*\{?',
                         re.MULTILINE)

    matches = []
    for match in pattern.finditer(content):
        func_name = match.group(1)
        has_brace = '{' in match.group(0)
        matches.append({
            'name': func_name,
            'start': match.start(),
            'end': match.end(),
            'has_body': has_brace,
            'is_definition': has_brace
        })

    return matches


def extract_main_function_info(content: str) -> dict:
    """提取主函数的信息：签名、sid 定义、workspace 名字"""
    main_funcs = find_all_main_functions(content)

    if not main_funcs:
        return None

    # 找到第一个主函数定义（有函数体的）
    definition = None
    for m in main_funcs:
        if m['is_definition']:
            definition = m
            break

    if not definition:
        return None

    func_start = definition['start']
    # 找到函数签名结束（可能是 '{' 在当前行或下一行）
    func_sig_end = content.find('{', func_start)
    func_sig = content[func_start:func_sig_end + 1]

    # 提取函数体
    func_body_start = func_sig_end + 1
    brace_count = 1
    func_body_end = func_body_start
    while brace_count > 0 and func_body_end < len(content):
        if content[func_body_end] == '{':
            brace_count += 1
        elif content[func_body_end] == '}':
            brace_count -= 1
        func_body_end += 1

    func_body = content[func_body_start:func_body_end - 1]

    # 提取 sid 定义
    sid_defs = []
    for line in func_body.splitlines():
        if re.match(r'\s*void\*\s+(sid_\d+_let)\s*=', line):
            sid_defs.append(line.strip())

    # 提取 workspace 名字
    ws_vars = re.findall(r'uint8_t\*\s+(\w+)', func_sig)
    cws_name = ws_vars[-2] if len(ws_vars) >= 2 else "global_const_workspace_0_var"
    ws_name = ws_vars[-1] if len(ws_vars) >= 1 else "global_workspace_1_var"

    return {
        'signature': func_sig,
        'body': func_body,
        'sid_defs': sid_defs,
        'cws_name': cws_name,
        'ws_name': ws_name,
        'start': func_start,
        'end': func_body_end
    }


def run_script(script_name: str, args: list, cwd: Path, output_file: str = None) -> str:
    """运行辅助脚本"""
    import subprocess
    scripts_dir = Path(__file__).parent
    cmd = [sys.executable, str(scripts_dir / script_name)] + args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Error running {script_name}:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)

    # 如果指定了输出文件，读取文件内容
    if output_file:
        output_path = Path(output_file)
        if output_path.exists():
            return output_path.read_text()
    return result.stdout


def update_makefile(makefile_path: Path):
    """更新 Makefile 以支持 OpenMP"""
    if not makefile_path.exists():
        print("Makefile not found, skipping update.")
        return

    content = makefile_path.read_text()
    import platform

    if platform.system() == "Darwin":
        omp_cflags = ""
        omp_ldflags = ""
    else:
        omp_cflags = "-fopenmp"
        omp_ldflags = "-fopenmp"

    if "fopenmp" not in content and omp_cflags:
        content = content.replace("CFLAGS = -O3 -fPIC", f"CFLAGS = -O3 -fPIC {omp_cflags}")
        content = content.replace("LDFLAGS = -lm", f"LDFLAGS = -lm {omp_ldflags}")
        print("Updated Makefile with OpenMP flags.")

    makefile_path.write_text(content)


def generate_call_tables(op_args_init: str) -> tuple:
    """根据 op_args 生成函数指针表"""
    func_names = re.findall(r'// \[\d+\] (tvmgen_default_\w+)', op_args_init)
    op_count = len(func_names)

    table_code = f"static const op_func_t g_op_call_table[{op_count}] = {{\n"
    for name in func_names:
        table_code += f"  wrapped_{name},\n"
    table_code += "};\n"

    names_code = f"static const char* const g_op_call_names[{op_count}] = {{\n"
    for name in func_names:
        names_code += f'  "{name}",\n'
    names_code += "};\n"

    return table_code + "\n" + names_code, op_count


def parse_max_io_from_op_args(op_args_init: str) -> tuple:
    """从 op_args 代码中解析 MAX_INPUTS 和 MAX_OUTPUTS"""
    # 尝试从注释中提取
    max_inputs_match = re.search(r'最大输入数:\s*(\d+)', op_args_init)
    max_outputs_match = re.search(r'最大输出数:\s*(\d+)', op_args_init)
    
    if max_inputs_match and max_outputs_match:
        return int(max_inputs_match.group(1)), int(max_outputs_match.group(1))
    
    # 回退：从结构体中计算
    # 计算 .inputs 中最多有几个非零值
    inputs_matches = re.findall(r'\.inputs\s*=\s*\{([^}]+)\}', op_args_init)
    max_inputs = 1
    for inputs_str in inputs_matches:
        count = len([x for x in inputs_str.split(',') if x.strip() and x.strip() != '0'])
        max_inputs = max(max_inputs, count)
    
    # 检查是否有 outputs 数组
    if '.outputs' in op_args_init:
        outputs_matches = re.findall(r'\.outputs\s*=\s*\{([^}]+)\}', op_args_init)
        max_outputs = 1
        for outputs_str in outputs_matches:
            count = len([x for x in outputs_str.split(',') if x.strip() and x.strip() != '0'])
            max_outputs = max(max_outputs, count)
    else:
        max_outputs = 1
    
    return max(max_inputs, 4), max(max_outputs, 1)  # 至少保持兼容


def clean_lib1_content(content: str) -> str:
    """清理 lib1.c 中可能存在的旧静态化代码"""
    print("Cleaning existing staticization artifacts...")

    # 使用更简单的方法：使用正则表达式移除所有旧的主函数和 extern "C" 块

    # 1. 移除 extern "C" 块 + 主函数声明（无函数体）
    # 这个模式匹配 extern "C" + 主函数声明
    extern_c_main_decl_pattern = re.compile(
        r'(?:\s*#ifdef __cplusplus\s*\n\s*extern "C"\s*\n\s*#endif\s*)?'
        r'\s*TVM_DLL\s+int32_t\s+tvmgen_default___tvm_main__\s*\([^)]*\);\s*',
        re.DOTALL
    )

    # 2. 移除 extern "C" 块 + 主函数定义（有函数体）
    # 这个模式匹配：
    # - 可选的 #ifdef __cplusplus / extern "C" / #endif
    # - TVM_DLL int32_t tvmgen_default___tvm_main__(...)
    # - 函数体（匹配平衡的 {...}）
    extern_c_main_def_pattern = re.compile(
        r'(?:\s*#ifdef __cplusplus\s*\n\s*extern "C"\s*\n\s*#endif\s*)?'
        r'\s*TVM_DLL\s+int32_t\s+tvmgen_default___tvm_main__\s*\([^)]*\)\s*\{',
        re.DOTALL
    )

    # 先移除声明
    content = extern_c_main_decl_pattern.sub('', content)

    # 再移除定义 - 使用位置信息移除完整的主函数
    # 先用正则找到开始位置，再用代码找到对应的结束括号
    match = extern_c_main_def_pattern.search(content)
    if match:
        func_start = match.start()
        # 找到函数签名结束（'{' 的位置）
        func_sig_end = content.find('{', match.start())
        if func_sig_end != -1:
            # 平衡括号找到函数体结束
            brace_count = 1
            func_body_end = func_sig_end + 1
            while brace_count > 0 and func_body_end < len(content):
                if content[func_body_end] == '{':
                    brace_count += 1
                elif content[func_body_end] == '}':
                    brace_count -= 1
                func_body_end += 1
            # 移除从 extern "C" 块开始到函数体结束的内容
            content = content[:func_start] + content[func_body_end:]

    # 3. 移除并行代码区域标记及其内容
    content = re.sub(
        r'//\s*=============\s*Parallel Runtime Types\s*=============.*?//\s*===============\s*',
        '// ================================================\n',
        content,
        flags=re.DOTALL
    )

    content = re.sub(
        r'//\s*=============\s*Parallel Schedule Table\s*=============.*?//\s*===============\s*',
        '// ================================================\n',
        content,
        flags=re.DOTALL
    )

    # 4. 移除 static const 表定义
    content = re.sub(
        r'static const op_func_t g_op_call_table\[[^\]]*\]\s*=\{[^}]*\};',
        '',
        content
    )

    content = re.sub(
        r'static const char\* const g_op_call_names\[[^\]]*\]\s*=\{[^}]*\};',
        '',
        content
    )

    content = re.sub(
        r'static const schedule_layer_t g_schedule\[[^\]]*\]\s*=\{[^}]*\};',
        '',
        content
    )

    # 5. 移除 layer 数组
    content = re.sub(
        r'static const int32_t g_layer_\d+\[[^\]]*\]\s*=\{[^}]*\};',
        '',
        content
    )

    # 6. 移除 NUM_LAYERS 定义
    content = re.sub(r'#define NUM_LAYERS\s*\d+', '', content)

    # 7. 移除 typedef 定义
    content = re.sub(
        r'typedef struct\s*\{[^}]*\}\s*op_args_t;',
        '',
        content
    )

    content = re.sub(
        r'typedef int32_t \(\*op_func_t\)\s*\([^)]*\)\s*op_args_t;',
        '',
        content
    )

    content = re.sub(
        r'typedef struct\s*\{[^}]*\}\s*schedule_layer_t;',
        '',
        content
    )

    # 8. 移除 OP_COUNT 定义
    content = re.sub(r'#define OP_COUNT\s*\d+', '', content)

    # 9. 移除 op_args 数组
    content = re.sub(
        r'op_args_t op_args\[OP_COUNT\]\s*=\{[^}]*\};',
        '',
        content
    )

    # 10. 移除 wrapped 函数
    content = re.sub(
        r'static inline int32_t wrapped_tvmgen_\w+\s*\([^)]*\)\s*\{[^}]*\}',
        '',
        content
    )

    # 11. 移除脚本日志
    content = re.sub(r'===.*\n', '', content)

    # 移除多余的空行
    content = re.sub(r'\n{3,}', '\n\n', content)

    return content


def clean_lib1_content_keep_main(content: str) -> str:
    """清理 lib1.c 中可能存在的旧静态化代码（保留主函数）"""
    print("Cleaning existing staticization artifacts (keeping main function)...")

    # 移除旧的静态化代码区域标记及其内容
    content = re.sub(
        r'//\s*=============\s*Parallel Runtime Types\s*=============.*?//\s*===============\s*',
        '// ================================================\n',
        content,
        flags=re.DOTALL
    )

    content = re.sub(
        r'//\s*=============\s*Parallel Schedule Table\s*=============.*?//\s*===============\s*',
        '// ================================================\n',
        content,
        flags=re.DOTALL
    )

    # 移除 static const 表定义
    content = re.sub(
        r'static const op_func_t g_op_call_table\[[^\]]*\]\s*=\{[^}]*\};',
        '',
        content
    )

    content = re.sub(
        r'static const char\* const g_op_call_names\[[^\]]*\]\s*=\{[^}]*\};',
        '',
        content
    )

    content = re.sub(
        r'static const schedule_layer_t g_schedule\[[^\]]*\]\s*=\{[^}]*\};',
        '',
        content
    )

    # 移除 layer 数组
    content = re.sub(
        r'static const int32_t g_layer_\d+\[[^\]]*\]\s*=\{[^}]*\};',
        '',
        content
    )

    # 移除 NUM_LAYERS 定义
    content = re.sub(r'#define NUM_LAYERS\s*\d+', '', content)

    # 移除 typedef 定义
    content = re.sub(
        r'typedef struct\s*\{[^}]*\}\s*op_args_t;',
        '',
        content
    )

    content = re.sub(
        r'typedef int32_t \(\*op_func_t\)\s*\([^)]*\)\s*op_args_t;',
        '',
        content
    )

    content = re.sub(
        r'typedef struct\s*\{[^}]*\}\s*schedule_layer_t;',
        '',
        content
    )

    # 移除 OP_COUNT 定义
    content = re.sub(r'#define OP_COUNT\s*\d+', '', content)

    # 移除 op_args 数组
    content = re.sub(
        r'op_args_t op_args\[OP_COUNT\]\s*=\{[^}]*\};',
        '',
        content
    )

    # 移除 wrapped 函数
    content = re.sub(
        r'static inline int32_t wrapped_tvmgen_\w+\s*\([^)]*\)\s*\{[^}]*\}',
        '',
        content
    )

    # 移除脚本日志
    content = re.sub(r'===.*\n', '', content)

    # 移除多余的空行
    content = re.sub(r'\n{3,}', '\n\n', content)

    return content


def modify_lib1_for_standalone(content: str) -> str:
    """修改 lib1.c 使其脱离 TVM 运行时独立编译"""
    lines = content.split('\n')
    result = []
    processed_tvm_includes = False

    for line in lines:
        # 1. 替换 TVM_EXPORTS 为 TVM_DLL
        if '#define TVM_EXPORTS' in line:
            result.append('#define TVM_DLL')
            continue

        # 2. 移除 TVM runtime includes，添加 stdint.h
        if '#include "tvm/runtime/c_runtime_api.h"' in line:
            if not processed_tvm_includes:
                result.append('#include <stdint.h>')
                processed_tvm_includes = True
            continue

        if '#include "tvm/runtime/c_backend_api.h"' in line:
            continue

        # 3. 移除 macOS section 属性问题（如果存在）
        if '__attribute__((section(".rodata.tvm"), ))' in line:
            result.append(line.replace(', )', ')'))
            continue

        result.append(line)

    return '\n'.join(result)


def extract_fused_function_declarations(content: str) -> str:
    """提取所有 tvmgen_default_fused_* 函数的声明"""
    # 匹配 TVM_DLL int32_t tvmgen_default_fused_* 函数声明（以分号结尾）
    pattern = re.compile(
        r'(TVM_DLL\s+int32_t\s+tvmgen_default_fused_\w+\s*\([^)]*\)\s*;)',
        re.MULTILINE
    )
    matches = pattern.findall(content)
    if matches:
        return "// TVM Generated Function Declarations\n" + "\n".join(matches) + "\n"
    return ""


def main():
    parser = argparse.ArgumentParser(
        description='自动合并并行调度代码到 lib1.c',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 scripts/merge_parallel_code.py src/lib1.c
  python3 scripts/merge_parallel_code.py src/lib1.c --schedule src/schedule_generated.c
  python3 scripts/merge_parallel_code.py src/lib1.c --op-args generated_op_args.c
        """
    )
    parser.add_argument('input', type=Path, help='源文件路径 (如 src/lib1.c)')
    parser.add_argument('-o', '--output', type=Path, help='输出文件路径 (默认: 直接修改输入文件)')
    parser.add_argument('--schedule', type=Path, help='调度表文件路径 (默认: 同目录下的 schedule_generated.c)')
    parser.add_argument('--op-args', type=Path, help='已有的 op_args 文件')
    parser.add_argument('--wrappers', type=Path, help='已有的包装器代码文件')
    parser.add_argument('--no-makefile', action='store_true', help='不更新 Makefile')

    args = parser.parse_args()

    if not args.input.exists():
        print(f"错误: 文件不存在: {args.input}", file=sys.stderr)
        return 1

    project_root = args.input.parent.parent
    scripts_dir = Path(__file__).parent

    # 确定输出文件
    target_lib1 = args.output if args.output else args.input

    # 确定调度表文件
    if args.schedule:
        schedule_file = args.schedule
    else:
        schedule_file = project_root / "schedule_generated.c"

    if not schedule_file.exists():
        print(f"错误: 调度表文件不存在: {schedule_file}", file=sys.stderr)
        print("请先运行: python3 scripts/gen_parallel_schedule.py src/lib1.c", file=sys.stderr)
        return 1

    print("=== Merge Parallel Schedule Tool ===")
    print(f"输入文件: {args.input}")
    print(f"输出文件: {target_lib1}")
    print()

    # 1. 读取 lib1.c 内容
    print("1. 读取 lib1.c...")
    lib1_content = args.input.read_text()

    # 2. 提取主函数信息（sid 定义等）
    print("2. 提取主函数信息...")
    main_info = extract_main_function_info(lib1_content)
    if not main_info:
        print("错误: 无法找到主函数", file=sys.stderr)
        return 1
    print(f"   找到 {len(main_info['sid_defs'])} 个 sid 定义")

    # 3. 生成/读取 op_args（必须在清理之前，因为清理会删除主函数体）
    if args.op_args and args.op_args.exists():
        print("3. 使用已有的 op_args 代码...")
        op_args_init = args.op_args.read_text()
    else:
        print("3. 生成 op_args 代码...")
        op_args_init = run_script("extract_op_args.py",
                                  [str(args.input), "-o", "/tmp/op_args.c"], project_root,
                                  output_file="/tmp/op_args.c")

    # 4. 生成函数指针表
    print("4. 生成函数指针表...")
    tables_code, op_count = generate_call_tables(op_args_init)
    print(f"   算子数量: {op_count}")

    # 5. 清理旧的静态化代码（不包含主函数的清理，保存位置信息）
    print("5. 清理旧代码...")
    original_len = len(lib1_content)
    lib1_content = clean_lib1_content_keep_main(lib1_content)
    cleaned_len = len(lib1_content)
    len_diff = original_len - cleaned_len
    print(f"   清理后文件缩短 {len_diff} 字符")

    # 6. 计算清理后的主函数位置（基于原始位置减去偏移量）
    main_start_clean = main_info['start'] - len_diff if main_info['start'] >= len_diff else 0
    print(f"   主函数清理后位置: {main_start_clean}")

    # 7. 从清理后的内容中提取 extern "C" 保护
    extern_c_block = ""
    if main_start_clean >= 3:
        lines = lib1_content.splitlines()
        line_starts = []
        pos = 0
        for line in lines:
            line_starts.append(pos)
            pos += len(line) + 1  # +1 for newline

        # 找到主函数签名所在的行号
        line_num = -1
        for i, start in enumerate(line_starts):
            if start <= main_start_clean < start + len(lines[i]):
                line_num = i
                break

        if line_num >= 3:
            prev1 = lines[line_num - 3] if line_num - 3 >= 0 else ""
            prev2 = lines[line_num - 2] if line_num - 2 >= 0 else ""
            prev3 = lines[line_num - 1] if line_num - 1 >= 0 else ""
            curr = lines[line_num]

            # 检查是否是 extern "C" 块
            if (re.match(r'\s*#ifdef __cplusplus\s*$', prev1) and
                re.match(r'\s*extern "C"\s*$', prev2) and
                re.match(r'\s*#endif\s*$', prev3)):
                # 保留 extern "C" 块，末尾添加空行
                extern_c_block = f"{prev1}\n{prev2}\n{prev3}\n"

    # 8. 生成/读取静态包装器
    if args.wrappers and args.wrappers.exists():
        print("8. 使用已有的包装器代码...")
        static_wrappers = args.wrappers.read_text()
    else:
        print("8. 生成静态算子包装器...")
        static_wrappers = run_script("operator_staticizer.py",
                                     [str(args.input), "--format", "wrappers", "--quiet",
                                      "-o", "/tmp/static_wrappers.c"], project_root,
                                     output_file="/tmp/static_wrappers.c")

    # 9. 读取调度表
    print("9. 读取调度表...")
    schedule_code = schedule_file.read_text()
    print(f"   调度表大小: {len(schedule_code)} bytes")

    # 10. 执行合并
    print("10. 合并代码...")

    # 添加 OpenMP 头文件
    if "#include <omp.h>" not in lib1_content:
        lib1_content = lib1_content.replace(
            "#include <stdint.h>",
            "#include <stdint.h>\n#ifdef _OPENMP\n#include <omp.h>\n#endif"
        )

    # 从 op_args 解析 max_inputs 和 max_outputs
    max_inputs, max_outputs = parse_max_io_from_op_args(op_args_init)
    print(f"   最大输入数: {max_inputs}, 最大输出数: {max_outputs}")

    # 构建类型定义（动态输入输出数组大小）
    type_defs = f"""// ============ Parallel Runtime Types ============
#define MAX_INPUTS {max_inputs}
#define MAX_OUTPUTS {max_outputs}

typedef struct {{
    void* inputs[MAX_INPUTS];
    void* outputs[MAX_OUTPUTS];
    int input_count;
    int output_count;
}} op_args_t;

typedef int32_t (*op_func_t)(op_args_t* args, uint8_t* cws, uint8_t* ws);

typedef struct {{
    const int32_t* op_indices;
    int32_t count;
}} schedule_layer_t;
// ================================================
#define OP_COUNT {op_count}
"""

    # 构建调度表
    schedule_section = f"""// ============ Parallel Schedule Table ============
{schedule_code}
// ================================================
"""

    # 构建新的主函数
    # 清理 op_args_init（移除所有注释行，只保留 op_args 数组定义）
    op_args_clean = op_args_init
    # 移除所有 // 注释行（包括中文字符）
    op_args_clean = re.sub(r'^//.*$', '', op_args_clean, flags=re.MULTILINE)
    # 移除空行
    op_args_clean = re.sub(r'\n\s*\n', '\n', op_args_clean)
    # 替换类型名和数组大小
    op_args_clean = re.sub(r'\w+_op_args_t', 'op_args_t', op_args_clean)
    op_args_clean = re.sub(r'op_args_t op_args\[\w+\]', 'op_args_t op_args[OP_COUNT]', op_args_clean)
    op_args_clean = re.sub(r'op_args\[\d+\]', 'op_args[OP_COUNT]', op_args_clean)
    op_args_clean = op_args_clean.strip()

    # 构建 sid 定义
    sid_block = '\n'.join(main_info['sid_defs'])
    if sid_block:
        sid_block = '\n' + sid_block

    # 构建新函数体
    new_body = f"""
    uint8_t *cws = {main_info['cws_name']};
    uint8_t *ws = {main_info['ws_name']};

    // Buffer Definitions
{sid_block}

    // Operator Arguments Initialization
{op_args_clean}

    // Parallel Execution Loop
    for (int i = 0; i < NUM_LAYERS; ++i) {{
        const schedule_layer_t* layer = &g_schedule[i];
#ifdef _OPENMP
        #pragma omp parallel for
#endif
        for (int j = 0; j < layer->count; ++j) {{
            int32_t op_idx = layer->op_indices[j];
            if (g_op_call_table[op_idx](&op_args[op_idx], cws, ws) != 0) {{
            }}
        }}
    }}

    return 0;
}}
"""

    # 替换主函数（使用清理后的位置）
    # 从清理后的内容中提取主函数签名和函数体
    main_info_clean = extract_main_function_info(lib1_content)
    if not main_info_clean:
        print("错误: 无法从清理后的内容中提取主函数", file=sys.stderr)
        return 1

    # 构建新的函数签名
    params_match = re.search(r'\(([^)]*)\)', main_info_clean['signature'])
    if params_match:
        params = params_match.group(1)
        new_sig = f"TVM_DLL int32_t tvmgen_default___tvm_main__({params})"
    else:
        new_sig = main_info_clean['signature'].rstrip('{').strip()

    # 注意：不要在这里添加 extern "C" 保护，因为它已经在 content_before 中
    # （main_info_clean['start'] 指向 TVM_DLL，extern "C" 块在其前面）
    new_func = new_sig + " {\n" + new_body

    # 替换
    content_before = lib1_content[:main_info_clean['start']]
    content_after = lib1_content[main_info_clean['end']:]
    lib1_content = content_before + new_func + content_after

    # 11. 在主函数前插入类型定义、包装器、调度表
    # 找到主函数的 extern "C" 块之前
    extern_c_marker = '#ifdef __cplusplus\nextern "C"\n#endif'
    insert_pos = lib1_content.find(extern_c_marker)
    if insert_pos == -1:
        insert_pos = lib1_content.find('#ifdef __cplusplus', main_info_clean['start'] - 500)
    if insert_pos == -1:
        insert_pos = main_info_clean['start']

    # 找到该行的行首
    line_start = lib1_content.rfind('\n', 0, insert_pos) + 1

    # 提取 TVM 函数声明（在清理之前）
    fused_decls = extract_fused_function_declarations(lib1_content)
    if fused_decls:
        print(f"   提取到 {fused_decls.count('TVM_DLL')} 个函数声明")

    # 构建注入代码
    # 顺序：类型 → TVM函数声明 → 包装器 → 函数表 → 调度表
    injection = type_defs + '\n' + fused_decls + '\n' + static_wrappers + '\n' + tables_code + '\n' + schedule_section + '\n'

    new_lib1 = lib1_content[:line_start] + injection + lib1_content[line_start:]

    # 12. 应用 standalone 修改
    print("12. 应用 standalone 修改...")
    new_lib1 = modify_lib1_for_standalone(new_lib1)

    # 13. 写入输出
    print(f"13. 写入输出文件: {target_lib1}...")
    target_lib1.write_text(new_lib1)

    # 14. 更新 Makefile
    if not args.no_makefile:
        print("14. 更新 Makefile...")
        makefile_path = project_root / "Makefile"
        update_makefile(makefile_path)

    print()
    print("完成！现在可以运行: make")
    return 0


if __name__ == "__main__":
    sys.exit(main())
