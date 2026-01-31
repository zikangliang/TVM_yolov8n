#!/bin/bash
# 一键并行构建并运行模型
# 使用方法: ./run_parallel.sh [worker数量]

set -e  # 遇到错误立即退出

NUM_WORKERS=${1:-3}  # 默认 3 个 worker 线程

echo "======================================"
echo "  并行模式构建 & 测试"
echo "  Worker 线程数: $NUM_WORKERS"
echo "======================================"

cd "$(dirname "$0")"

echo ""
echo "[1/2] 构建中（并行调度）..."
python3 scripts/auto_tvmrt_build.py

echo ""
echo "[2/2] 运行测试..."
# 自动查找 build 目录下的 *_test 可执行文件
TEST_BIN=$(find build -maxdepth 1 -name "*_test" -type f | head -1)
if [ -z "$TEST_BIN" ]; then
    echo "错误: 找不到测试可执行文件"
    exit 1
fi
echo "运行: $TEST_BIN"
TVMRT_NUM_WORKERS=$NUM_WORKERS "$TEST_BIN"

echo ""
echo "======================================"
echo "  ✅ 并行模式完成"
echo "======================================"
