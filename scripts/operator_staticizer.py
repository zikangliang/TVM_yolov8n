#!/usr/bin/env python3
"""
TVM 算子静态化脚本 - 生成 SchedulableEntity 和相关数据结构

此脚本解析 init/lib1.c 中的 tvmgen_default___tvm_main__ 函数，
提取算子调用序列和依赖关系，生成符合建议书规范的调度数据结构。

使用方法:
    python3 scripts/operator_staticizer.py
"""

import re
import os
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional

# ============================================================
# 数据结构定义
# ============================================================

@dataclass
class OperatorInfo:
    """单个算子的信息"""
    exec_idx: int                    # 执行顺序索引
    func_name: str                   # 函数名称
    inputs: List[str]                # 输入变量名列表
    outputs: List[str]               # 输出变量名列表（从参数推断）
    all_params: List[str]            # 所有参数（不含 cws, ws）

@dataclass 
class DAGInfo:
    """DAG 依赖信息"""
    num_ops: int
    predecessors: Dict[int, Set[int]]   # op_idx -> 前驱算子集合
    successors: Dict[int, Set[int]]     # op_idx -> 后继算子集合
    indegrees: Dict[int, int]           # op_idx -> 初始入度


# ============================================================
# 解析 lib1.c
# ============================================================

def parse_main_function(lib1_path: str) -> Tuple[List[OperatorInfo], Dict[str, str]]:
    """
    解析 tvmgen_default___tvm_main__ 函数，提取算子调用序列
    
    Returns:
        operators: 算子信息列表（按执行顺序）
        sid_definitions: sid 变量定义 {sid_name: offset_expr}
    """
    with open(lib1_path, 'r') as f:
        content = f.read()
    
    # 查找 __tvm_main__ 函数
    main_pattern = r'int32_t tvmgen_default___tvm_main__\([^)]+\)\s*\{'
    main_match = re.search(main_pattern, content)
    if not main_match:
        raise ValueError("找不到 tvmgen_default___tvm_main__ 函数")
    
    # 提取函数体
    start_pos = main_match.end()
    brace_count = 1
    end_pos = start_pos
    
    while brace_count > 0 and end_pos < len(content):
        if content[end_pos] == '{':
            brace_count += 1
        elif content[end_pos] == '}':
            brace_count -= 1
        end_pos += 1
    
    func_body = content[start_pos:end_pos-1]
    
    # 1. 解析 sid 变量定义
    # void* sid_59_let = (&(global_workspace_1_var[0]));
    sid_pattern = r'void\*\s+(sid_\d+_let)\s*=\s*\(\&\(global_workspace_1_var\[(\d+)\]\)\);'
    sid_definitions = {}
    for match in re.finditer(sid_pattern, func_body):
        sid_name = match.group(1)
        offset = match.group(2)
        sid_definitions[sid_name] = offset
    
    # 2. 解析算子调用序列
    # if (tvmgen_default_fused_xxx(arg1, arg2, ...) != 0 ) return -1;
    call_pattern = r'if\s*\(\s*(tvmgen_default_[a-zA-Z0-9_]+)\(([^)]+)\)\s*!=\s*0\s*\)'
    
    operators = []
    exec_idx = 0
    
    for match in re.finditer(call_pattern, func_body):
        func_name = match.group(1)
        args_str = match.group(2)
        
        # 解析参数列表
        args = [a.strip() for a in args_str.split(',')]
        
        # 最后两个参数是 global_const_workspace 和 global_workspace
        data_args = args[:-2]
        
        # 推断输入输出
        # 规则：
        # - 对于大多数算子，最后一个数据参数是输出
        # - 对于 split 类函数，最后两个是输出
        # - 对于 concatenate_layout_transform_reshape 特殊函数，最后两个是输出
        
        if 'split' in func_name.lower() or func_name.endswith('_7c5ad37d2665c07f_'):
            # split 类：最后两个参数是输出
            outputs = data_args[-2:]
            inputs = data_args[:-2]
        else:
            # 大多数算子：最后一个参数是输出
            outputs = [data_args[-1]]
            inputs = data_args[:-1]
        
        op = OperatorInfo(
            exec_idx=exec_idx,
            func_name=func_name,
            inputs=inputs,
            outputs=outputs,
            all_params=data_args
        )
        operators.append(op)
        exec_idx += 1
    
    print(f"[operator_staticizer] 解析到 {len(operators)} 个算子调用")
    print(f"[operator_staticizer] 解析到 {len(sid_definitions)} 个 sid 变量定义")
    
    return operators, sid_definitions


def build_dag(operators: List[OperatorInfo]) -> DAGInfo:
    """
    根据算子的输入输出依赖关系构建 DAG
    
    规则：如果算子 B 的输入包含算子 A 的输出，则 A -> B
    """
    num_ops = len(operators)
    
    # 构建变量到产生者的映射
    # var_name -> (producer_idx, is_primary_output)
    var_producers: Dict[str, int] = {}
    
    # 外部输入（模型输入）
    external_inputs = {'images_buffer_var', 'output_buffer_var'}
    
    predecessors: Dict[int, Set[int]] = {i: set() for i in range(num_ops)}
    successors: Dict[int, Set[int]] = {i: set() for i in range(num_ops)}
    
    for op in operators:
        # 记录这个算子产生的输出
        for out_var in op.outputs:
            var_producers[out_var] = op.exec_idx
    
    # 第二遍：根据输入建立依赖关系
    for op in operators:
        for in_var in op.inputs:
            if in_var in external_inputs:
                continue
            if in_var in var_producers:
                pred_idx = var_producers[in_var]
                if pred_idx != op.exec_idx:  # 不能自依赖
                    predecessors[op.exec_idx].add(pred_idx)
                    successors[pred_idx].add(op.exec_idx)
    
    # 计算入度
    indegrees = {i: len(predecessors[i]) for i in range(num_ops)}
    
    # 统计信息
    zero_indegree = sum(1 for i in indegrees.values() if i == 0)
    max_indegree = max(indegrees.values()) if indegrees else 0
    max_outdegree = max(len(s) for s in successors.values()) if successors else 0
    
    print(f"[operator_staticizer] DAG 构建完成:")
    print(f"    入度为0的算子数: {zero_indegree}")
    print(f"    最大入度: {max_indegree}")
    print(f"    最大出度: {max_outdegree}")
    
    return DAGInfo(
        num_ops=num_ops,
        predecessors=predecessors,
        successors=successors,
        indegrees=indegrees
    )


# ============================================================
# 代码生成
# ============================================================

def extract_function_declarations(lib1_path: str) -> List[str]:
    """提取所有 TVM 函数声明"""
    with open(lib1_path, 'r') as f:
        content = f.read()
    
    # 匹配函数声明（不是定义）
    # TVM_DLL int32_t tvmgen_default_xxx(...);
    decl_pattern = r'TVM_DLL\s+int32_t\s+(tvmgen_default_[a-zA-Z0-9_]+)\s*\([^)]+\)\s*;'
    
    func_names = set()
    for match in re.finditer(decl_pattern, content):
        func_name = match.group(1)
        if func_name != 'tvmgen_default___tvm_main__':
            func_names.add(func_name)
    
    return sorted(func_names)


def generate_schedulable_entity_code(
    operators: List[OperatorInfo],
    dag: DAGInfo,
    sid_definitions: Dict[str, str],
    func_names: List[str]
) -> str:
    """生成 SchedulableEntity 相关的 C 代码（符合建议书规范）"""
    
    lines = []
    lines.append("// ============================================================")
    lines.append("// 自动生成的 Scheduler-Worker 运行时数据结构")
    lines.append(f"// 算子数量: {len(operators)}")
    lines.append("// ============================================================")
    lines.append("")
    
    # 1. 类型定义
    lines.append("// ============ 类型定义 ============")
    lines.append("#define MAX_INPUTS 8")
    lines.append("#define MAX_OUTPUTS 2")
    lines.append(f"#define OP_COUNT {len(operators)}")
    lines.append("")
    
    # 执行配置结构体
    lines.append("// 执行配置（预留扩展）")
    lines.append("typedef struct {")
    lines.append("    int device_type;  // 0=CPU, 1=GPU, 2=NPU")
    lines.append("    int priority;     // 调度优先级")
    lines.append("} ExecConfig;")
    lines.append("")
    
    # 前向声明 SchedulableEntity（包装函数需要）
    lines.append("// 前向声明")
    lines.append("struct SchedulableEntity;")
    lines.append("")
    
    # 内核函数指针类型
    lines.append("// 内核函数指针类型：接收 inputs[], outputs[], cws, ws")
    lines.append("typedef int32_t (*kernel_func_t)(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws);")
    lines.append("")
    
    # SchedulableEntity 结构体
    lines.append("// 可调度实体 = 函数指针 + 数据参数 + 配置")
    lines.append("typedef struct SchedulableEntity {")
    lines.append("    // 1. 执行入口（内核函数指针）")
    lines.append("    kernel_func_t kernel;")
    lines.append("")
    lines.append("    // 2. 数据参数")
    lines.append("    void* inputs[MAX_INPUTS];")
    lines.append("    void* outputs[MAX_OUTPUTS];")
    lines.append("    int input_count;")
    lines.append("    int output_count;")
    lines.append("")
    lines.append("    // 3. 执行配置")
    lines.append("    ExecConfig config;")
    lines.append("")
    lines.append("    // 4. 标识")
    lines.append("    int id;")
    lines.append("} SchedulableEntity;")
    lines.append("")
    
    # 2. TVM 函数声明
    lines.append("// ============ TVM 算子函数声明 ============")
    for func_name in func_names:
        lines.append(f"TVM_DLL int32_t {func_name}();")
    lines.append("")
    
    # 3. 包装函数（新签名：inputs[], outputs[], cws, ws）
    lines.append("// ============ 包装函数 ============")
    lines.append("// 签名: (void** inputs, void** outputs, uint8_t* cws, uint8_t* ws)")
    lines.append("")
    
    # 收集所有用到的函数及其参数模式
    func_param_patterns: Dict[str, OperatorInfo] = {}
    for op in operators:
        if op.func_name not in func_param_patterns:
            func_param_patterns[op.func_name] = op
    
    for func_name, op in sorted(func_param_patterns.items()):
        in_count = len(op.inputs)
        out_count = len(op.outputs)
        
        # 生成包装函数（新签名）
        lines.append(f"static inline int32_t wrapped_{func_name}(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {{")
        
        # 构建调用参数
        call_args = []
        for i in range(in_count):
            call_args.append(f"inputs[{i}]")
        for i in range(out_count):
            call_args.append(f"outputs[{i}]")
        call_args.append("cws")
        call_args.append("ws")
        
        lines.append(f"    return {func_name}({', '.join(call_args)});")
        lines.append("}")
        lines.append("")
    
    # 4. 函数名表（用于调试）
    lines.append("// ============ 调试信息 ============")
    lines.append(f"static const char* const g_op_names[{len(operators)}] __attribute__((unused)) = {{")
    for op in operators:
        lines.append(f'    "{op.func_name}",')
    lines.append("};")
    lines.append("")
    
    return '\n'.join(lines)


def generate_dag_schedule_code(dag: DAGInfo) -> str:
    """生成 DAG 调度相关的 C 代码"""
    
    lines = []
    lines.append("// ============================================================")
    lines.append("// DAG 调度数据结构")
    lines.append("// ============================================================")
    lines.append("")
    
    # 1. 初始入度表
    lines.append("// 初始入度表（编译期静态）")
    lines.append(f"static const int32_t g_initial_indegrees[{dag.num_ops}] = {{")
    
    row = []
    for i in range(dag.num_ops):
        row.append(str(dag.indegrees[i]))
        if len(row) == 16:
            lines.append(f"    {', '.join(row)},")
            row = []
    if row:
        lines.append(f"    {', '.join(row)}")
    lines.append("};")
    lines.append("")
    
    # 2. 后继节点表
    lines.append("// 后继节点邻接表")
    
    # 先生成各个后继数组
    for i in range(dag.num_ops):
        succs = sorted(dag.successors[i])
        if succs:
            succs_str = ', '.join(str(s) for s in succs)
            lines.append(f"static const int32_t g_successors_{i}[] = {{ {succs_str} }};")
        else:
            # 使用空数组定义，而不是 NULL 指针赋值
            lines.append(f"static const int32_t g_successors_{i}[] = {{ -1 }};  // 无后继（哨兵值）")
    lines.append("")
    
    # 后继节点指针表
    lines.append(f"static const int32_t* g_successors[{dag.num_ops}] = {{")
    for i in range(dag.num_ops):
        lines.append(f"    g_successors_{i},")
    lines.append("};")
    lines.append("")
    
    # 后继节点数量表
    lines.append("// 后继节点数量")
    lines.append(f"static const int32_t g_successor_counts[{dag.num_ops}] = {{")
    
    row = []
    for i in range(dag.num_ops):
        row.append(str(len(dag.successors[i])))
        if len(row) == 16:
            lines.append(f"    {', '.join(row)},")
            row = []
    if row:
        lines.append(f"    {', '.join(row)}")
    lines.append("};")
    lines.append("")
    
    return '\n'.join(lines)


def generate_entities_code(
    operators: List[OperatorInfo],
    sid_definitions: Dict[str, str]
) -> str:
    """生成统一的 g_entities[] 数组初始化代码"""
    
    lines = []
    lines.append("// ============================================================")
    lines.append("// SchedulableEntity 实体初始化")
    lines.append("// ============================================================")
    lines.append("")
    
    # 1. sid 变量定义
    lines.append("// workspace 偏移量变量")
    for sid_name in sorted(sid_definitions.keys(), key=lambda x: int(re.search(r'\d+', x).group())):
        offset = sid_definitions[sid_name]
        lines.append(f"void* {sid_name} = (&(global_workspace_1_var[{offset}]));")
    lines.append("")
    
    # 2. g_entities 初始化表
    lines.append("// 可调度实体数组")
    lines.append("SchedulableEntity g_entities[OP_COUNT] = {")
    
    for op in operators:
        in_count = len(op.inputs)
        out_count = len(op.outputs)
        
        inputs_str = ', '.join(op.inputs)
        outputs_str = ', '.join(op.outputs)
        
        lines.append(f"    {{ // [{op.exec_idx}] {op.func_name}")
        lines.append(f"        .kernel = wrapped_{op.func_name},")
        lines.append(f"        .inputs = {{ {inputs_str} }},")
        lines.append(f"        .outputs = {{ {outputs_str} }},")
        lines.append(f"        .input_count = {in_count},")
        lines.append(f"        .output_count = {out_count},")
        lines.append(f"        .config = {{ .device_type = 0, .priority = 0 }},")
        lines.append(f"        .id = {op.exec_idx}")
        lines.append("    },")
    
    lines.append("};")
    lines.append("")
    
    return '\n'.join(lines)


# ============================================================
# 主流程
# ============================================================

def main():
    # 路径配置
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    init_lib1 = os.path.join(project_root, 'init', 'lib1.c')
    output_dir = project_root
    
    print(f"[operator_staticizer] 项目根目录: {project_root}")
    print(f"[operator_staticizer] 输入文件: {init_lib1}")
    
    if not os.path.exists(init_lib1):
        print(f"错误: 找不到 {init_lib1}")
        sys.exit(1)
    
    # 1. 解析 lib1.c
    print("\n[1/4] 解析 lib1.c ...")
    operators, sid_definitions = parse_main_function(init_lib1)
    func_names = extract_function_declarations(init_lib1)
    
    # 2. 构建 DAG
    print("\n[2/4] 构建 DAG ...")
    dag = build_dag(operators)
    
    # 3. 生成 SchedulableEntity 代码
    print("\n[3/4] 生成代码 ...")
    entity_code = generate_schedulable_entity_code(operators, dag, sid_definitions, func_names)
    dag_code = generate_dag_schedule_code(dag)
    entities_init_code = generate_entities_code(operators, sid_definitions)
    
    # 4. 写入输出文件
    print("\n[4/4] 写入文件 ...")
    
    # 实体和函数表
    entity_output = os.path.join(output_dir, 'entity_generated.c')
    with open(entity_output, 'w') as f:
        f.write(entity_code)
    print(f"    -> {entity_output}")
    
    # DAG 调度表
    dag_output = os.path.join(output_dir, 'dag_schedule_generated.c')
    with open(dag_output, 'w') as f:
        f.write(dag_code)
    print(f"    -> {dag_output}")
    
    # 实体初始化表
    entities_output = os.path.join(output_dir, 'entities_generated.c')
    with open(entities_output, 'w') as f:
        f.write(entities_init_code)
    print(f"    -> {entities_output}")
    
    print("\n[operator_staticizer] 完成!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
