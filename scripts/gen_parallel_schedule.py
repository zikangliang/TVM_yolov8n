#!/usr/bin/env python3
"""
生成并行调度表（通用版本）

基于数据依赖关系和内存冲突分析，生成安全的并行执行层次。

适用于任何 TVM 生成的模型。

并行安全检查（阶段1）：
1. 数据流依赖 - op_args 输入→输出关系
2. 输出地址冲突 - 同一地址写-写
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


# ============================================================
# 解析器：从 lib1.c 提取信息
# ============================================================

class OpArgsParser:
    """解析 op_args 表（支持多输出）"""

    # 新格式: 多输出 (.outputs 数组)
    OP_ARGS_PATTERN_NEW = re.compile(
        r'\{\.inputs\s*=\s*\{([^}]+)\},\s*\.outputs\s*=\s*\{([^}]+)\},\s*\.input_count\s*=\s*(\d+),\s*\.output_count\s*=\s*(\d+)\},\s*//\s*\[(\d+)\]'
    )

    # 格式1: 旧数组初始化格式 (单输出 .output)
    OP_ARGS_PATTERN_1 = re.compile(
        r'\{\.inputs\s*=\s*\{([^}]+)\},\s*\.output\s*=\s*(\w+),\s*\.input_count\s*=\s*(\d+)\},\s*//\s*\[(\d+)\]'
    )

    # 格式2: 逐个赋值格式
    OP_ARGS_PATTERN_2 = re.compile(
        r'op_args\[(\d+)\]\s*=\s*\([^)]+\)\{\.inputs\s*=\s*\{([^}]+)\},\s*\.output\s*=\s*(\w+),\s*\.input_count\s*=\s*(\d+)\}'
    )

    # 匹配 op_args 注释中的函数名: // [ID] tvmgen_default_XXX
    FUNC_NAME_PATTERN = re.compile(
        r'//\s*\[(\d+)\]\s+(tvmgen_default_\w+)'
    )

    def __init__(self, source_file: Path):
        self.source_file = source_file
        self.op_args: List[Dict] = []
        self.op_to_func: Dict[int, str] = {}  # op_id -> func_name

    def parse(self) -> Tuple[List[Dict], Dict[str, int], Dict[int, str]]:
        """解析 op_args 表

        Returns:
            (op_args列表, output_var->op_id映射, op_id->func_name映射)
        """
        content = self.source_file.read_text()

        # 先提取函数名映射
        for match in self.FUNC_NAME_PATTERN.finditer(content):
            op_id = int(match.group(1))
            func_name = match.group(2)
            self.op_to_func[op_id] = func_name

        # 尝试新格式 (多输出)
        matches = list(self.OP_ARGS_PATTERN_NEW.finditer(content))
        if matches:
            for match in matches:
                inputs_str = match.group(1)
                outputs_str = match.group(2)
                input_count = int(match.group(3))
                output_count = int(match.group(4))
                op_id = int(match.group(5))

                inputs = [var.strip() for var in inputs_str.split(',') if var.strip() and var.strip() != '0']
                outputs = [var.strip() for var in outputs_str.split(',') if var.strip() and var.strip() != '0']

                self.op_args.append({
                    'id': op_id,
                    'inputs': inputs,
                    'outputs': outputs,
                    'output': outputs[0] if outputs else '',  # 兼容旧代码
                    'input_count': input_count,
                    'output_count': output_count,
                    'func_name': self.op_to_func.get(op_id, '')
                })
        else:
            # 尝试格式1 (旧单输出)
            matches = list(self.OP_ARGS_PATTERN_1.finditer(content))

            if not matches:
                # 尝试格式2
                matches = list(self.OP_ARGS_PATTERN_2.finditer(content))
                for match in matches:
                    op_id = int(match.group(1))
                    inputs_str = match.group(2)
                    output = match.group(3)
                    input_count = int(match.group(4))

                    inputs = [var.strip() for var in inputs_str.split(',') if var.strip() and var.strip() != '0']

                    self.op_args.append({
                        'id': op_id,
                        'inputs': inputs,
                        'outputs': [output],
                        'output': output,
                        'input_count': input_count,
                        'output_count': 1,
                        'func_name': self.op_to_func.get(op_id, '')
                    })
            else:
                for match in matches:
                    inputs_str = match.group(1)
                    output = match.group(2)
                    input_count = int(match.group(3))
                    op_id = int(match.group(4))

                    inputs = [var.strip() for var in inputs_str.split(',') if var.strip()]

                    self.op_args.append({
                        'id': op_id,
                        'inputs': inputs,
                        'outputs': [output],
                        'output': output,
                        'input_count': input_count,
                        'output_count': 1,
                        'func_name': self.op_to_func.get(op_id, '')
                    })

        self.op_args.sort(key=lambda x: x['id'])

        # 建立 output -> op_id 映射 (支持多输出)
        output_to_op: Dict[str, int] = {}
        for op in self.op_args:
            for out_var in op.get('outputs', [op.get('output', '')]):
                if out_var:
                    output_to_op[out_var] = op['id']

        return self.op_args, output_to_op, self.op_to_func


class SidAddressParser:
    """解析 sid 变量地址定义

    提取: void* sid_X_let = (&(global_workspace_1_var[offset]));
    """

    # 匹配 sid 变量定义: void* sid_XXX_let = (&(global_workspace_1_var[offset]));
    SID_PATTERN = re.compile(
        r'(\w+_let)\s*=\s*\(\&\((\w+)\[(\d+)\]\)\)'
    )

    def __init__(self, source_file: Path):
        self.source_file = source_file
        self.sid_addresses: Dict[str, Tuple[str, int]] = {}  # var -> (base_array, offset)

    def parse(self) -> Dict[str, Tuple[str, int]]:
        """解析 sid 变量地址

        Returns:
            sid_var -> (base_array, offset)
        """
        content = self.source_file.read_text()

        for match in self.SID_PATTERN.finditer(content):
            var_name = match.group(1)
            base_array = match.group(2)
            offset = int(match.group(3))

            # 只关注 global_workspace_1_var 的变量（主要的数据存储区）
            if base_array == 'global_workspace_1_var':
                self.sid_addresses[var_name] = (base_array, offset)

        return self.sid_addresses


class WorkspaceRangeParser:
    """解析算子函数的 workspace 使用范围

    提取每个算子函数内使用的 global_workspace_X_var[offset] 范围

    注意：所有算子实际上使用同一块 global_workspace_1_var 内存，
    不同的 global_workspace_X_var 参数名只是形式上的区别
    """

    # 匹配算子函数定义
    FUNC_DEF_PATTERN = re.compile(
        r'TVM_DLL\s+int32_t\s+(tvmgen_default_\w+)\s*\([^)]*\)\s*\{',
        re.MULTILINE
    )

    def __init__(self, source_file: Path):
        self.source_file = source_file
        self.ws_ranges: List[Tuple[int, int, int]] = []  # [(min, max, has), ...]

    def parse(self, op_args: List[Dict]) -> List[Tuple[int, int, int]]:
        """解析每个算子的 workspace 使用范围

        Args:
            op_args: 包含 func_name 的 op_args 列表

        Returns:
            每个算子的 (min_offset, max_offset, has_workspace) 列表
        """
        content = self.source_file.read_text()

        # 1. 找到所有算子函数定义的位置和它们的 workspace 使用
        func_workspaces = {}  # func_name -> [offsets]

        for match in self.FUNC_DEF_PATTERN.finditer(content):
            func_name = match.group(1)
            func_start = match.end()

            # 找到函数结束位置
            # 查找下一个 TVM_DLL 或文件末尾
            next_match = self.FUNC_DEF_PATTERN.search(content, func_start)
            if next_match:
                func_end = next_match.start()
            else:
                func_end = len(content)

            func_body = content[func_start:func_end]

            # 提取所有 workspace 使用:(&(global_workspace_X_var[offset]))
            offsets = []
            for ws_match in re.finditer(r'\(&\(global_workspace_\w+\[(\d+)\]\)\)', func_body):
                offset = int(ws_match.group(1))
                offsets.append(offset)

            func_workspaces[func_name] = offsets

        # 2. 为每个算子构建 workspace 范围
        self.ws_ranges = []
        for op in op_args:
            func_name = op.get('func_name', '')
            if func_name in func_workspaces:
                offsets = func_workspaces[func_name]
                if offsets:
                    min_offset = min(offsets)
                    max_offset = max(offsets)
                    self.ws_ranges.append((min_offset, max_offset, 1))
                else:
                    self.ws_ranges.append((0, 0, 0))
            else:
                self.ws_ranges.append((0, 0, 0))

        return self.ws_ranges


# ============================================================
# 依赖生成器
# ============================================================

class DepsGenerator:
    """从 op_args 生成数据流依赖"""

    EXTERNAL_INPUTS = {'images_buffer_var', 'input_buffer_var', 'input'}

    def __init__(self, op_args: List[Dict], output_to_op: Dict[str, int], sid_addresses: Dict[str, Tuple[str, int]]):
        self.op_args = op_args
        self.output_to_op = output_to_op
        self.sid_addresses = sid_addresses
        self.op_count = len(op_args)

    def compute(self) -> List[List[int]]:
        """计算依赖表 (包含数据流依赖和内存复用依赖)

        Returns:
            每个算子的依赖列表
        """
        dependencies = [[] for _ in range(self.op_count)]

        # 内存访问状态跟踪
        # offset -> last_writer_op_id
        last_writer: Dict[int, int] = {}
        # offset -> list of current_reader_op_ids (since last write)
        current_readers: Dict[int, List[int]] = {}

        for op in self.op_args:
            op_id = op['id']
            deps = set()

            # 1. 处理输入 (读取)
            for input_var in op['inputs']:
                if input_var in self.EXTERNAL_INPUTS:
                    continue

                # A. 显式数据流依赖 (基于变量名)
                if input_var in self.output_to_op:
                    producer_id = self.output_to_op[input_var]
                    deps.add(producer_id)

                # B. 内存依赖 (基于地址)
                # 如果我们知道变量的地址，检查该地址的 Last Writer (RAW)
                # 注意：显式数据流通常已经覆盖了 RAW，但内存分析可以作为双重检查
                if input_var in self.sid_addresses:
                    _, offset = self.sid_addresses[input_var]
                    if offset in last_writer:
                        deps.add(last_writer[offset])

                    # 注册为读者
                    if offset not in current_readers:
                        current_readers[offset] = []
                    current_readers[offset].append(op_id)

            # 2. 处理所有输出 (写入) - 支持多输出
            for output_var in op.get('outputs', [op.get('output', '')]):
                if not output_var or output_var == '0':
                    continue
                if output_var not in self.sid_addresses:
                    continue
                    
                _, offset = self.sid_addresses[output_var]

                # WAW (Write-After-Write): 依赖于上一个写入者
                if offset in last_writer:
                    deps.add(last_writer[offset])

                # WAR (Write-After-Read): 依赖于当前所有的读者
                if offset in current_readers:
                    for reader_id in current_readers[offset]:
                        # 排除自依赖 (如果存在)
                        if reader_id != op_id:
                            deps.add(reader_id)

                # 更新状态
                last_writer[offset] = op_id
                current_readers[offset] = []  # 清空读者列表，因为被覆盖了

            # 移除自身依赖 (just in case)
            if op_id in deps:
                deps.remove(op_id)

            dependencies[op_id] = sorted(list(deps))

        return dependencies


# ============================================================
# 冲突检查器
# ============================================================

class ConflictChecker:
    """并行安全检查"""

    def __init__(self, op_args: List[Dict], sid_addresses: Dict[str, Tuple[str, int]],
                 dependencies: List[List[int]], ws_ranges: List[Tuple[int, int, int]]):
        self.op_args = op_args
        self.sid_addresses = sid_addresses
        self.dependencies = dependencies
        self.ws_ranges = ws_ranges
        self.op_count = len(op_args)

        # 构建输出地址映射：offset -> op_id (支持多输出)
        self.output_offset_to_ops: Dict[int, List[int]] = {}
        for op in self.op_args:
            for output_var in op.get('outputs', [op.get('output', '')]):
                if not output_var or output_var == '0':
                    continue
                if output_var in self.sid_addresses:
                    _, offset = self.sid_addresses[output_var]
                    if offset not in self.output_offset_to_ops:
                        self.output_offset_to_ops[offset] = []
                    self.output_offset_to_ops[offset].append(op['id'])

    def has_data_dependency(self, op1: int, op2: int) -> bool:
        """检查数据流依赖"""
        return op2 in self.dependencies[op1] or op1 in self.dependencies[op2]

    def has_output_conflict(self, op1: int, op2: int) -> bool:
        """检查输出地址冲突（同一地址写-写）- 支持多输出"""
        outputs1 = self.op_args[op1].get('outputs', [self.op_args[op1].get('output', '')])
        outputs2 = self.op_args[op2].get('outputs', [self.op_args[op2].get('output', '')])

        # 比较所有输出
        for out1 in outputs1:
            if not out1 or out1 == '0':
                continue
            for out2 in outputs2:
                if not out2 or out2 == '0':
                    continue
                # 直接比较变量名
                if out1 == out2:
                    return True
                # 比较地址偏移
                if out1 in self.sid_addresses and out2 in self.sid_addresses:
                    _, offset1 = self.sid_addresses[out1]
                    _, offset2 = self.sid_addresses[out2]
                    if offset1 == offset2:
                        return True

        return False

    def has_workspace_conflict(self, op1: int, op2: int) -> bool:
        """检查 workspace 范围重叠"""
        min1, max1, has1 = self.ws_ranges[op1]
        min2, max2, has2 = self.ws_ranges[op2]

        # 至少有一个不使用 workspace
        if not has1 or not has2:
            return False

        # 检查区间是否重叠
        return not (max1 < min2 or max2 < min1)

    def has_output_in_workspace(self, op1: int, op2: int) -> bool:
        """检查 op1 的任意输出是否在 op2 的 workspace 范围内 - 支持多输出"""
        outputs1 = self.op_args[op1].get('outputs', [self.op_args[op1].get('output', '')])
        min2, max2, has2 = self.ws_ranges[op2]

        # op2 不使用 workspace
        if not has2:
            return False

        # 检查所有输出
        for output_var in outputs1:
            if not output_var or output_var == '0':
                continue
            if output_var not in self.sid_addresses:
                continue
            _, offset = self.sid_addresses[output_var]
            if min2 <= offset <= max2:
                return True

        return False

    def has_input_covered_by_workspace(self, op1: int, op2: int) -> bool:
        """检查 op1 的输入是否被 op2 的 workspace 覆盖"""
        inputs1 = self.op_args[op1]['inputs']
        min2, max2, has2 = self.ws_ranges[op2]

        # op2 不使用 workspace
        if not has2:
            return False

        # 检查每个输入
        for inp in inputs1:
            # 跳过外部输入
            if inp in {'images_buffer_var', 'input_buffer_var', 'input'}:
                continue
            if inp not in self.sid_addresses:
                continue

            _, offset = self.sid_addresses[inp]
            if min2 <= offset <= max2:
                return True

        return False

    def can_parallel(self, op1: int, op2: int) -> bool:
        """检查两个算子是否可以并行（阶段1+阶段2）"""
        # === 阶段1 检查 ===
        # 条件1: 无数据流依赖
        if self.has_data_dependency(op1, op2):
            return False

        # 条件2: 无输出地址冲突（同一地址写-写）
        if self.has_output_conflict(op1, op2):
            return False

        # === 阶段2 检查 ===
        # 条件3: 无 workspace 范围重叠
        if self.has_workspace_conflict(op1, op2):
            return False

        # 条件4: 输出不在对方 workspace 内
        if self.has_output_in_workspace(op1, op2):
            return False
        if self.has_output_in_workspace(op2, op1):
            return False

        # 条件5: 输入不被对方 workspace 覆盖
        if self.has_input_covered_by_workspace(op1, op2):
            return False
        if self.has_input_covered_by_workspace(op2, op1):
            return False

        return True


# ============================================================
# 调度生成器
# ============================================================

class TopologicalSorter:
    """拓扑分层"""

    def __init__(self, dependencies: List[List[int]]):
        self.dependencies = dependencies
        self.op_count = len(dependencies)

    def compute_layers(self) -> List[List[int]]:
        """计算拓扑层次

        Returns:
            每层的算子列表
        """
        completed = set()
        layers = []

        while len(completed) < self.op_count:
            # 找出所有依赖已满足的算子
            ready = []
            for op in range(self.op_count):
                if op in completed:
                    continue
                deps = self.dependencies[op]
                if all(d in completed for d in deps):
                    ready.append(op)

            if not ready:
                # 循环依赖检测
                print("错误: 检测到循环依赖")
                for op in range(self.op_count):
                    if op not in completed:
                        deps = self.dependencies[op]
                        uncompleted = [d for d in deps if d not in completed]
                        print(f"  算子 {op}: 未完成的依赖 = {uncompleted}")
                raise ValueError("Circular dependency detected")

            layers.append(ready)
            completed.update(ready)

        return layers


class ParallelGrouper:
    """贪心着色分组"""

    def __init__(self, checker: ConflictChecker):
        self.checker = checker

    def group_within_layer(self, ops_in_layer: List[int]) -> List[List[int]]:
        """在一层内分组可并行的算子

        使用贪心算法：将每个算子放入第一个不冲突的组
        """
        groups = []

        for op in ops_in_layer:
            placed = False
            for group in groups:
                # 检查 op 是否与组内所有算子都无冲突
                if all(self.checker.can_parallel(op, g) for g in group):
                    group.append(op)
                    placed = True
                    break
            if not placed:
                groups.append([op])

        return groups


# ============================================================
# 代码生成器
# ============================================================

class ScheduleCodeGenerator:
    """生成调度表 C 代码"""

    def __init__(self, prefix: str = ""):
        self.prefix = prefix
        type_prefix = prefix.replace('.', '_').rstrip('_') + '_' if prefix else ""
        self.op_count_macro = f"{type_prefix}OP_COUNT"
        self.layer_struct_name = f"{type_prefix}schedule_layer_t" if prefix else "schedule_layer_t"

    def generate_c_code(self, layers: List[List[int]]) -> str:
        """生成 C 代码"""
        lines = [
            "// ============================================================",
            "// 自动生成的并行调度表",
            "// 基于数据流依赖和内存冲突分析",
            "// ============================================================",
            "",
        ]

        # 生成每层的数组定义
        for i, layer_ops in enumerate(layers):
            ops_str = ", ".join(str(op) for op in layer_ops)
            lines.append(f"static const int32_t g_layer_{i}[] = {{ {ops_str} }};")

        lines.append("")
        lines.append(f"static const {self.layer_struct_name} g_schedule[] = {{")

        for i in range(len(layers)):
            lines.append(f"    {{ g_layer_{i}, {len(layers[i])} }},")

        lines.append("};")
        lines.append("")
        lines.append(f"#define NUM_LAYERS {len(layers)}")

        return "\n".join(lines)


# ============================================================
# 主程序
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='生成并行调度表（通用版本）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本用法（从 lib1.c 中的 op_args 表解析）
  python3 scripts/gen_parallel_schedule.py src/lib1.c

  # 使用外部 op_args 文件
  python3 scripts/gen_parallel_schedule.py src/lib1.c --op-args generated_op_args.c

  # 输出到文件
  python3 scripts/gen_parallel_schedule.py src/lib1.c -o src/schedule_generated.c

  # 添加命名前缀
  python3 scripts/gen_parallel_schedule.py src/lib1.c --prefix mymodel
        """
    )
    parser.add_argument(
        'input',
        type=Path,
        help='TVM 生成的源文件 (lib1.c)'
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='输出文件路径 (默认: schedule_generated.c)'
    )
    parser.add_argument(
        '--op-args',
        type=Path,
        help='外部 op_args 文件 (可选，默认从 input 中解析)'
    )
    parser.add_argument(
        '--prefix',
        type=str,
        default='',
        help='命名前缀，用于避免多模型冲突'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='显示详细信息'
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"错误: 文件不存在: {args.input}", file=sys.stderr)
        return 1

    print(f"=== 并行调度表生成工具 ===")
    print(f"输入文件: {args.input}")
    if args.op_args:
        print(f"op_args 文件: {args.op_args}")
    if args.prefix:
        print(f"命名前缀: {args.prefix}")
    print()

    # 1. 解析 op_args
    print("1. 解析 op_args 表...")
    if args.op_args and args.op_args.exists():
        # 从外部文件解析
        op_args_parser = OpArgsParser(args.op_args)
        op_args, output_to_op, op_to_func = op_args_parser.parse()
    else:
        # 从 input 文件解析
        op_args_parser = OpArgsParser(args.input)
        op_args, output_to_op, op_to_func = op_args_parser.parse()
    op_count = len(op_args)
    print(f"   ✓ 解析到 {op_count} 个算子")

    # 2. 解析 sid 地址
    print("2. 解析 sid 变量地址...")
    sid_parser = SidAddressParser(args.input)
    sid_addresses = sid_parser.parse()
    print(f"   ✓ 解析到 {len(sid_addresses)} 个地址定义")

    # 3. 解析 workspace 范围
    print("3. 解析 workspace 范围...")
    ws_parser = WorkspaceRangeParser(args.input)
    ws_ranges = ws_parser.parse(op_args)
    ws_count = sum(1 for ws in ws_ranges if ws[2])
    print(f"   ✓ {ws_count} 个算子使用 workspace")

    # 4. 计算依赖
    print("4. 计算数据流依赖 (含内存复用依赖)...")
    deps_gen = DepsGenerator(op_args, output_to_op, sid_addresses)
    dependencies = deps_gen.compute()
    max_deps = max((len(deps) for deps in dependencies), default=0)
    print(f"   ✓ 最大依赖数: {max_deps}")

    # 5. 创建冲突检查器
    checker = ConflictChecker(op_args, sid_addresses, dependencies, ws_ranges)

    # 6. 拓扑分层
    print("5. 拓扑分层...")
    topo_sorter = TopologicalSorter(dependencies)
    topo_layers = topo_sorter.compute_layers()
    print(f"   ✓ 拓扑层数: {len(topo_layers)}")

    # 7. 并行分组
    print("6. 并行分组...")
    grouper = ParallelGrouper(checker)
    parallel_layers = []
    for layer_ops in topo_layers:
        groups = grouper.group_within_layer(layer_ops)
        parallel_layers.extend(groups)

    print(f"   ✓ 并行层数: {len(parallel_layers)}")

    # 8. 统计
    # 串行版本：每个算子一层 = op_count
    serial_layers = op_count
    parallel_layers_count = len(parallel_layers)
    reduction = serial_layers - parallel_layers_count
    reduction_pct = (reduction / serial_layers) * 100 if serial_layers > 0 else 0
    max_parallel = max((len(layer) for layer in parallel_layers), default=1)

    # 计算实际的并行层（包含 >1 个算子的层）
    parallel_layer_count = sum(1 for layer in parallel_layers if len(layer) > 1)

    print()
    print("=== 统计信息 ===")
    print(f"算子总数: {op_count}")
    print(f"串行层数: {serial_layers}")
    print(f"并行层数: {parallel_layers_count}")
    print(f"减少层数: {reduction} ({reduction_pct:.1f}%)")
    print(f"实际并行层数: {parallel_layer_count} (包含 >1 个算子)")
    print(f"最大并行度: {max_parallel}")

    # 9. 显示并行层
    if args.verbose:
        print()
        print("=== 并行调度表 ===")
        for i, layer_ops in enumerate(parallel_layers):
            if len(layer_ops) > 1:
                print(f"Layer {i:3d}: {layer_ops}  <-- 并行 ({len(layer_ops)} 个算子)")
            else:
                if i < 20 or i >= len(parallel_layers) - 10:  # 只显示部分
                    print(f"Layer {i:3d}: {layer_ops}")
            if i == 20 and len(parallel_layers) > 30:
                print("  ...")

    # 10. 生成 C 代码
    print()
    print("7. 生成 C 代码...")
    code_gen = ScheduleCodeGenerator(args.prefix)
    c_code = code_gen.generate_c_code(parallel_layers)

    # 11. 输出
    output = args.output or Path("schedule_generated.c")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(c_code)
    print(f"   ✓ 已保存: {output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
