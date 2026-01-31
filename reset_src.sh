#!/bin/bash
# 从 init 目录恢复 src 目录的原始文件
# 使用方法: ./reset_src.sh

set -e

echo "======================================"
echo "  恢复 src 目录"
echo "======================================"

cd "$(dirname "$0")"

if [ ! -d "init" ]; then
    echo "错误: init 目录不存在"
    exit 1
fi

echo "正在复制文件..."
cp init/lib0.c src/lib0.c && echo "  ✓ lib0.c"
cp init/lib1.c src/lib1.c && echo "  ✓ lib1.c"

# 如果存在 devc.c 也复制
if [ -f "init/devc.c" ]; then
    cp init/devc.c src/devc.c && echo "  ✓ devc.c"
fi

echo ""
echo "✅ src 目录已恢复到初始状态"
