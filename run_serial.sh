#!/bin/bash
# 一键串行构建并运行 YOLOv8n 模型
# 使用方法: ./run_serial.sh

set -e  # 遇到错误立即退出

echo "======================================"
echo "  串行模式构建 & 测试"
echo "======================================"

cd "$(dirname "$0")"

echo ""
echo "[1/2] 构建中（串行调度）..."
python3 scripts/auto_tvmrt_build.py --serial

echo ""
echo "[2/2] 运行测试..."
# 自动查找 build 目录下的 *_test 可执行文件
TEST_BIN=$(find build -maxdepth 1 -name "*_test" -type f | head -1)
if [ -z "$TEST_BIN" ]; then
    echo "错误: 找不到测试可执行文件"
    exit 1
fi
echo "运行: $TEST_BIN"
TVMRT_NUM_WORKERS=0 "$TEST_BIN"

echo ""
echo "======================================"
echo "  ✅ 串行模式完成"
echo "======================================"
