# TVM 并行运行时移植脚本

这些脚本用于将 TVM 编译的模型转换为支持 pthread 并行执行的独立 C 代码。

## 使用方法

### 1. 准备新模型目录
```bash
mkdir -p new_model/{src,scripts,test}
```

### 2. 复制脚本
```bash
cp /Users/liang/Desktop/program/c/tvm_parallel_scripts/*.py new_model/scripts/
```

### 3. 放置 TVM 生成的原始文件
将 TVM 编译输出的文件放入 `src/` 目录：
- `lib0.c` - 常量数据和 workspace（必需）
- `lib1.c` - 算子实现（必需）
- `devc.c` - 设备代码（可选）

### 4. 一键构建
```bash
cd new_model
python3 scripts/auto_tvmrt_build.py --run-test
```

## 脚本说明

| 文件 | 功能 |
|------|------|
| `auto_tvmrt_build.py` | 主入口：一键构建流程 |
| `operator_staticizer.py` | 生成静态化函数包装器 |
| `extract_op_args.py` | 提取算子参数表 |
| `gen_parallel_schedule.py` | 生成并行调度表 |
| `gen_serial_schedule.py` | 生成串行调度表（用于调试或对照） |
| `merge_parallel_code.py` | 合并所有生成代码 |
| `build_generator.py` | 生成 Makefile 和测试文件 |

## 运行选项

```bash
# 默认 3 个 worker 线程
./build/<model>_test

# 单线程模式
TVMRT_NUM_WORKERS=0 ./build/<model>_test

# 显示每层执行时间
TVMRT_TRACE=1 ./build/<model>_test

# 指定 worker 数量
TVMRT_NUM_WORKERS=4 ./build/<model>_test
```

## 构建选项

```bash
# 默认并行调度构建
python3 scripts/auto_tvmrt_build.py --run-test

# 使用串行调度（每层 1 个算子，用于调试或对照）
python3 scripts/auto_tvmrt_build.py --serial --run-test
```

## 目录结构

```
new_model/
├── src/                  # TVM 生成的原始文件
│   ├── lib0.c           # 必需
│   ├── lib1.c           # 必需
│   └── devc.c           # 可选
├── scripts/             # 复制这 6 个脚本
│   └── *.py
├── test/                # 自动生成
├── build/               # 自动生成
└── Makefile             # 自动生成
```
