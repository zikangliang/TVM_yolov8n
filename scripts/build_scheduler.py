#!/usr/bin/env python3
"""
一键构建脚本 - Scheduler-Worker 调度器版本

此脚本执行完整的构建流程：
1. 从 init/ 复制源文件到 src/
2. 解析 lib1.c，生成调度数据结构
3. 合并代码到 src/lib1.c
4. 编译生成可执行文件

使用方法:
    python3 scripts/build_scheduler.py [--serial]
    
选项:
    --serial  仅生成串行调度（不含 DAG 调度器）
"""

import os
import sys
import subprocess
import argparse

def run_command(cmd: list, cwd: str = None) -> int:
    """运行命令并返回退出码"""
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode

def main():
    parser = argparse.ArgumentParser(description='Scheduler-Worker 构建脚本')
    parser.add_argument('--serial', action='store_true', help='仅串行模式')
    args = parser.parse_args()
    
    # 获取项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    print("=" * 60)
    print("  Scheduler-Worker 调度器构建")
    print("=" * 60)
    print(f"项目目录: {project_root}")
    print(f"模式: {'串行' if args.serial else '并行 (Scheduler-Worker)'}")
    print()
    
    # 1. 运行算子静态化脚本
    print("[1/3] 解析算子并生成调度数据结构 ...")
    staticizer_script = os.path.join(script_dir, 'operator_staticizer.py')
    ret = run_command([sys.executable, staticizer_script], cwd=project_root)
    if ret != 0:
        print("错误: 算子静态化失败")
        return ret
    
    # 2. 运行合并脚本
    print("\n[2/3] 合并代码到 src/lib1.c ...")
    merge_script = os.path.join(script_dir, 'merge_scheduler_code.py')
    ret = run_command([sys.executable, merge_script], cwd=project_root)
    if ret != 0:
        print("错误: 代码合并失败")
        return ret
    
    # 3. 编译
    print("\n[3/3] 编译 ...")
    ret = run_command(['make', 'clean'], cwd=project_root)
    ret = run_command(['make'], cwd=project_root)
    if ret != 0:
        print("错误: 编译失败")
        return ret
    
    print()
    print("=" * 60)
    print("  ✅ 构建完成")
    print("=" * 60)
    print()
    model_name = os.path.basename(project_root)
    print("运行测试:")
    print(f"  串行模式: TVMRT_NUM_WORKERS=0 ./build/{model_name}_test")
    print(f"  并行模式: TVMRT_NUM_WORKERS=3 ./build/{model_name}_test")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
