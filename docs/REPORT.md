# YOLOv8n TVM 运行时 Scheduler-Worker 闭环调度 - 工作汇报

## 0. 代码生成与文件转换

本节说明 TVM 原始输出 (`init/` 目录) 经过脚本处理后，文件结构发生的转换。

### 0.1 原始 TVM 生成文件结构 (init/lib1.c, 13473 行)

TVM `tvmc compile` 生成的代码结构：

```
init/lib1.c (13473 行)
├── 算子函数声明 (约 200 行)
│   └── TVM_DLL int32_t tvmgen_default_fused_xxx(...);  // 94 个算子声明
│
├── 算子函数实现 (约 13000 行)
│   └── 每个 fused_xxx 函数的具体实现（矩阵运算代码）
│
└── 主函数 (约 150 行，tvmgen_default___tvm_main__)
    └── 串行调用 94 个算子：
        if (tvmgen_default_fused_layout_transform(...) != 0) return -1;
        if (tvmgen_default_fused_nn_contrib_conv2d_xxx(...) != 0) return -1;
        if (tvmgen_default_fused_concatenate(...) != 0) return -1;
        ...
        return 0;
```

**特点**：
- 串行执行，无并行调度
- 无显式依赖关系（隐式按代码顺序）
- 无运行时状态管理

### 0.2 脚本处理后的文件结构 (src/lib1.c, 14765 行)

经过 `scripts/` 目录下脚本处理后：

```
src/lib1.c (14765 行)
│
├── 1. 头文件与类型定义 (约 60 行)
│   ├── #include <pthread.h>  // 新增
│   ├── typedef struct SchedulableEntity { ... }  // 建议书 3.2.3
│   ├── typedef struct RuntimeState { ... }       // 建议书 3.2.4
│   ├── typedef struct RuntimeContext { ... }     // 运行时上下文
│   ├── typedef struct SafeQueue { ... }          // 建议书 3.3.5
│   └── kernel_func_t 函数指针类型
│
├── 2. 算子函数声明 (约 100 行)
│   └── TVM_DLL int32_t tvmgen_default_fused_xxx();  // 保持不变
│
├── 3. 包装函数 (约 350 行)
│   └── static inline int32_t wrapped_tvmgen_default_fused_xxx(...)
│       // 将 void** 参数转换为具体类型，调用原始 TVM 函数
│
├── 4. SchedulableEntity 数组 (约 300 行，g_entities)
│   └── static const SchedulableEntity g_entities[94] = {
│       { .kernel = wrapped_xxx, .inputs = {...}, .outputs = {...}, .id = n },
│       ...
│   };
│
├── 5. DAG 依赖表 (约 1000 行，dag_schedule_generated.c)
│   ├── static const int g_successors_0[] = { 5, 12, 23, ... };
│   ├── static const int g_successor_counts[94] = { 3, 1, ... };
│   └── static const int g_initial_indegrees[94] = { 1, 0, ... };
│
├── 6. 调度运行时核心 (约 250 行)
│   ├── SafeQueue 队列操作函数 (queue_init, queue_push, queue_pop)
│   ├── RuntimeState 运行时状态
│   ├── RuntimeContext 运行时上下文
│   ├── worker_loop()     
│   ├── scheduler_loop()  
│   ├── init_runtime_context()  
│   ├── tvmrt_run_serial()  
│   ├── tvmrt_run_dag()     
│   └── tvmrt_run()         
│
├── 7. 主函数 tvmgen_default___tvm_main__ (约 150 行)
│   └── 调用 tvmrt_run() 执行调度
│       return tvmrt_run(cws, ws, g_entities);
│
└── 8. 兼容接口 (约 20 行)
    └── tvmgen_default_run()  // 外部调用入口
```

### 0.3 转换前后对比

| 文件位置 | 转换前 (init/lib1.c) | 转换后 (src/lib1.c) |
|---------|---------------------|---------------------|
| 数据结构 | 无 | `SchedulableEntity`, `RuntimeState`, `SafeQueue` |
| 算子表示 | 独立函数声明 | 结构体数组 `g_entities[]` |
| 依赖关系 | 无（串行调用） | `g_successors[]` 邻接表 (建议书 3.3.3) |
| 调度方式 | 串行执行 | `scheduler_loop()` + `worker_loop()` (建议书 3.3.4) |
| 线程同步 | 无 | `SafeQueue` 线程安全队列 (建议书 3.3.5) |
| 运行时状态 | 无 | `RuntimeState` 动态入度 (建议书 3.2.4) |
| 执行模式 | 仅串行 | `tvmrt_run_serial()` / `tvmrt_run_dag()`|

### 0.4 代码生成流水线

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           代码生成流水线                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  TVM 原始输出 (init/)                                                       │
│      │                                                                      │
│      ▼                                                                      │
│  ┌────────────────┐     ┌─────────────────┐     ┌────────────────────────┐ │
│  │ operator_      │────>│ gen_parallel_   │────>│ dag_schedule_          │ │
│  │ staticizer.py  │     │ schedule.py     │     │ generated.c            │ │
│  │ 生成 wrapper   │     │ 生成 DAG 邻接表 │     │ (邻接表+入度表)        │ │
│  │ + g_entities   │     │                 │     │                        │ │
│  └────────────────┘     └─────────────────┘     └────────────────────────┘ │
│      │                          │                          │               │
│      │                          │                          │               │
│      ▼                          ▼                          ▼               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    merge_parallel_code.py                            │   │
│  │  1. 读取 scheduler_runtime.c 模板                                     │   │
│  │  2. 读取 dag_schedule_generated.c                                     │   │
│  │  3. 合并到 src/lib1.c                                                 │   │
│  │  4. 替换串行 main 函数为调度调用                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│      │                                                                      │
│      ▼                                                                      │
│  生成产物: src/lib1.c (14765 行)                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```


---

## 1. 项目概述



### 1.2 目标模型参数

| 参数 | 值 |
|------|-----|
| 模型名称 | yolov8n |
| 输入尺寸 | 1228800 floats (4.8 MB) |
| 输出尺寸 | 2714985 floats (10.6 MB) |
| 算子总数 | 94 个 |
| 构建产物 | libyolov8n.a + yolov8n_test |

---

## 2. 系统架构 (建议书 3.1 节对应)

### 2.1 架构总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TVM 运行时架构                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────────┐  │
│  │   输入层    │    │   算子层    │    │          调度层                 │  │
│  │ (Input)     │    │ (Operators) │    │  ┌─────────┐  ┌─────────────┐  │  │
│  │             │    │             │    │  │Scheduler│  │   Workers   │  │  │
│  │ images[1]   │───>│  Op_0       │───>│  │ Thread  │  │  Thread N   │  │  │
│  │             │    │  Op_1       │    │  │         │  │             │  │  │
│  │             │    │  ...        │    │  │ (单线程)│  │  (多线程)   │  │  │
│  │             │    │  Op_N       │    │  └────┬────┘  └──────┬──────┘  │  │
│  └─────────────┘    └─────────────┘    │       │              │         │  │
│                                        │       ▼              ▼         │  │
│                                        │  ┌─────────────────────────┐   │  │
│                                        │  │   SafeQueue (线程安全)  │   │  │
│                                        │  │  ReadyQ   CompleteQ    │   │  │
│                                        │  └─────────────────────────┘   │  │
│                                        └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 封闭式可调度实体 (建议书 3.2.3 节)

建议书 3.2.3 节定义了 `SchedulableEntity` 结构体，作为算子的静态描述单元。

**建议书定义**：
```
3.2.3 封闭式可调度实体
一个封闭式可调度实体应该包含：
  1. kernel(): 算子执行入口
  2. weights[]: 权重参数（常量）
  3. inputs[]: 输入数据指针
  4. outputs[]: 输出数据指针
  5. exec_config: 执行配置
  6. entry_count: 初始入度
```

**当前实现** (src/lib1.c:40-55)：

```c
typedef struct SchedulableEntity {
    // 1. 执行入口 (建议书: kernel())
    kernel_func_t kernel;

    // 2. 数据指针 (建议书: inputs[], outputs[])
    void* inputs[MAX_INPUTS];
    void* outputs[MAX_OUTPUTS];

    // 3. 执行配置 (建议书: exec_config)
    ExecConfig config;

    // 4. 静态信息 (建议书: entry_count 暂存于 g_initial_indegrees[])
    int id;
} SchedulableEntity;
```

> **与建议书差异说明**：
> - `weights[]` 字段：TVM 权重混在 inputs 中，未单独分离
> - `entry_count` 字段：使用独立的 `g_initial_indegrees[]` 数组存储，调度初始化时复制到 RuntimeState

### 2.3 运行时状态 (建议书 3.2.4 节)


**当前实现** (src/lib1.c:906-909)：

```c
typedef struct {
    int32_t current_indegree;  // 当前剩余依赖数（动态更新）
} RuntimeState;
```

> **与建议书差异说明**：`status` 字段未使用，可通过入度值推断状态（入度>0=PENDING，入度=0且未执行=READY，执行中=RUNNING，完成=DONE）

---

## 3. 调度算法 (建议书 3.3.4 节)

### 3.1 闭环调度模型概述

建议书 3.3.4 节提出了"事件驱动的闭环调度"模型，核心思想：
- **Scheduler 线程**：监听完成事件，更新依赖图
- **Worker 线程**：从就绪队列取任务执行
- **两个队列**：Ready Queue + Complete Queue

### 3.2 线程安全队列 (建议书 3.3.5 节)

**建议书 3.3.5 节**：实现线程安全队列，使用 pthread_mutex 和 pthread_cond。

**当前实现** (src/lib1.c:862-895)：

```c
typedef struct {
    int32_t data[OP_COUNT + 16];  // 预留终止信号空间
    int head;
    int tail;
    int count;
    pthread_mutex_t lock;
    pthread_cond_t not_empty;
} SafeQueue;

// 主要操作
static void queue_init(SafeQueue *q);           // 初始化
static void queue_push(SafeQueue *q, int32_t value);  // 阻塞式插入
static int32_t queue_pop(SafeQueue *q);              // 阻塞式取出
```

### 3.3 Scheduler 线程逻辑

**建议书图 3-57**：Scheduler 处理流程
```
1. 从 CompleteQueue 取出完成的算子 ID
2. 更新该算子所有后继节点的入度
3. 如果后继入度变为 0，推入 ReadyQueue
4. 重复直到所有算子完成
```

**当前实现** (src/lib1.c:971-1007)：

```c
static void *scheduler_loop(void *arg) {
    RuntimeContext *ctx = (RuntimeContext *)arg;

    while (ctx->completed_ops < ctx->total_ops) {
        // A. 从 Complete Queue 获取完成事件
        int32_t finished_op_id = queue_pop(&ctx->complete_queue);
        __atomic_fetch_add(&ctx->completed_ops, 1, __ATOMIC_SEQ_CST);

        // B. 更新后继节点入度 (建议书步骤 2)
        int32_t num_succ = g_successor_counts[finished_op_id];
        const int32_t *successors = g_successors[finished_op_id];

        for (int i = 0; i < num_succ; i++) {
            int32_t succ_id = successors[i];

            // 原子递减入度
            pthread_mutex_lock(&ctx->indegree_lock);
            ctx->states[succ_id].current_indegree--;
            int32_t new_indegree = ctx->states[succ_id].current_indegree;
            pthread_mutex_unlock(&ctx->indegree_lock);

            // C. 入度为 0，推入 Ready Queue (建议书步骤 3)
            if (new_indegree == 0) {
                queue_push(&ctx->ready_queue, succ_id);
            }
        }

        if (ctx->error != 0) break;
    }

    // D. 发送终止信号给所有 Workers
    for (int i = 0; i < ctx->num_workers; i++) {
        queue_push(&ctx->ready_queue, -1);
    }

    return NULL;
}
```

### 3.4 Worker 线程逻辑

**建议书图 3-63**：Worker 处理流程
```
1. 从 ReadyQueue 取出就绪的算子 ID
2. 调用算子的 kernel() 函数执行
3. 将算子 ID 推入 CompleteQueue
4. 重复直到收到终止信号
```

**当前实现** (src/lib1.c:941-967)：

```c
static void *worker_loop(void *arg) {
    WorkerArg *wa = (WorkerArg *)arg;
    RuntimeContext *ctx = wa->ctx;

    while (1) {
        // A. 从 Ready Queue 获取任务
        int32_t op_id = queue_pop(&ctx->ready_queue);

        // B. 终止信号检测
        if (op_id < 0) break;

        // C. 执行算子 (建议书步骤 2)
        SchedulableEntity *entity = &ctx->entities[op_id];
        int ret = entity->kernel(entity->inputs, entity->outputs,
                                 ctx->cws, ctx->ws);
        if (ret != 0) ctx->error = ret;

        // D. 上报完成 (建议书步骤 3)
        queue_push(&ctx->complete_queue, op_id);
    }

    return NULL;
}
```

### 3.5 DAG 依赖表示 (建议书 3.3.3 节)

**建议书 3.3.3 节**：使用邻接表表示 DAG，每个算子记录其后继节点。

**生成代码** (dag_schedule_generated.c)：

```c
// 每个算子的后继节点列表
static const int g_successors_0[] = { 5, 12, 23, ... };
static const int g_successors_1[] = { 7, 15, ... };
// ...
static const int* g_successors[OP_COUNT] = {
    g_successors_0,
    g_successors_1,
    // ...
};

// 每个算子的后继节点数量
static const int g_successor_counts[OP_COUNT] = {
    3,  // op_0 有 3 个后继
    1,  // op_1 有 1 个后继
    // ...
};

// 初始入度表
static const int g_initial_indegrees[OP_COUNT] = {
    1,  // op_0 依赖其他算子
    0,  // op_1 无依赖（入口算子）
    // ...
};
```

---

## 4. 运行时初始化与调度入口

### 4.1 初始化流程 (建议书 3.3.6 节)

**当前实现** (src/lib1.c:1017-1052)：

```c
static void init_runtime_context(RuntimeContext *ctx,
                                 uint8_t *cws, uint8_t *ws,
                                 SchedulableEntity *entities,
                                 int num_workers) {
    ctx->total_ops = OP_COUNT;
    ctx->cws = cws;
    ctx->ws = ws;
    ctx->entities = entities;
    ctx->num_workers = num_workers;
    ctx->completed_ops = 0;
    ctx->error = 0;

    // 从 g_initial_indegrees 复制初始入度
    ctx->states = (RuntimeState *)malloc(sizeof(RuntimeState) * OP_COUNT);
    for (int i = 0; i < OP_COUNT; i++) {
        ctx->states[i].current_indegree = g_initial_indegrees[i];
    }

    // 初始化队列
    queue_init(&ctx->ready_queue);
    queue_init(&ctx->complete_queue);
    pthread_mutex_init(&ctx->indegree_lock, NULL);

    // 将初始入度为 0 的算子推入 Ready Queue
    for (int i = 0; i < OP_COUNT; i++) {
        if (ctx->states[i].current_indegree == 0) {
            queue_push(&ctx->ready_queue, i);
        }
    }
}
```

### 4.2 调度入口函数

**建议书 3.3.7 节**：统一调度入口，支持串行/并行模式切换。

```c
static int tvmrt_run(uint8_t *cws, uint8_t *ws,
                     SchedulableEntity entities[]) {
    const char *env = getenv("TVMRT_NUM_WORKERS");
    int num_workers = env ? atoi(env) : 0;  // 0 = 串行

    if (num_workers == 0) {
        // 串行模式 (兼容旧版)
        return tvmrt_run_serial(cws, ws, entities);
    } else {
        // 并行模式 (建议书闭环调度)
        return tvmrt_run_dag(cws, ws, entities);
    }
}
```

### 4.3 线程启动与同步

```c
static int tvmrt_run_dag(uint8_t *cws, uint8_t *ws,
                         SchedulableEntity entities[]) {
    int num_workers = 3;  // 默认 3 个 Worker
    const char *env = getenv("TVMRT_NUM_WORKERS");
    if (env) num_workers = atoi(env);
    if (num_workers < 1) num_workers = 1;

    RuntimeContext ctx;
    init_runtime_context(&ctx, cws, ws, entities, num_workers);

    // 1. 启动 Scheduler 线程 (单线程)
    pthread_t sched_thread;
    pthread_create(&sched_thread, NULL, scheduler_loop, &ctx);

    // 2. 启动 Worker 线程 (多线程)
    pthread_t *workers = (pthread_t *)malloc(sizeof(pthread_t) * num_workers);
    WorkerArg *worker_args = (WorkerArg *)malloc(sizeof(WorkerArg) * num_workers);

    for (int i = 0; i < num_workers; i++) {
        worker_args[i].ctx = &ctx;
        worker_args[i].worker_id = i;
        pthread_create(&workers[i], NULL, worker_loop, &worker_args[i]);
    }

    // 3. 等待完成
    pthread_join(sched_thread, NULL);
    for (int i = 0; i < num_workers; i++) {
        pthread_join(workers[i], NULL);
    }

    int error = ctx.error;
    cleanup_runtime_context(&ctx);
    free(workers);
    free(worker_args);

    return error;
}
```

---

## 5. 代码生成流水线

### 5.1 生成脚本清单

| 脚本文件 | 对应功能 | 建议书章节 |
|---------|---------|-----------|
| scripts/operator_staticizer.py | 生成 SchedulableEntity 和 wrapper | 3.2.3 |
| scripts/gen_parallel_schedule.py | 生成 DAG 邻接表 | 3.3.3 |
| scripts/merge_parallel_code.py | 集成调度代码到 lib1.c | 3.3.7 |

### 5.2 生成文件清单

| 生成文件 | 内容 |
|---------|------|
| entity_generated.c | SchedulableEntity 定义、wrapper 函数 |
| dag_schedule_generated.c | g_successors, g_successor_counts, g_initial_indegrees |
| entities_generated.c | g_entities 数组初始化 |

### 5.3 构建产物

```
build/
├── lib/
│   └── libyolov8n.a      # 静态库
├── obj/
│   ├── lib0.o
│   ├── lib1.o
│   └── test_main.o
└── yolov8n_test          # 测试程序
```

---

## 6. 配置与使用

### 6.1 环境变量

| 变量 | 说明 | 默认值 | 对应建议书 |
|------|------|-------|-----------|
| TVMRT_NUM_WORKERS | Worker 线程数 | 3 | 3.3.4 |
| OMP_NUM_THREADS | 备选配置 | - | - |

### 6.2 使用示例

```bash
# 串行模式 (调试用)
TVMRT_NUM_WORKERS=0 ./build/yolov8n_test -n 10

# 并行模式 (默认 3 Worker)
./build/yolov8n_test -n 10

# 4 Worker 并行
TVMRT_NUM_WORKERS=4 ./build/yolov8n_test
```

### 6.3 测试输出示例

```
=== yolov8n Test ===
Input size: 1228800 floats (4800.0 KB)
Output size: 2714985 floats (10605.4 KB)
Iterations: 10

Running inference...
  Iteration 1: 156.32 ms
  Iteration 2: 148.67 ms
  ...

=== Results ===
Total time: 1542.10 ms
Average time: 154.21 ms
FPS: 6.5
```


---

## 9. 后续优化方向

| 优先级 | 优化项 |
|--------|--------|
| 高 | 跑通一个真正能并行的例子（仅有数据依赖，无ws冲突） |
| 中 | 添加 SchedulableEntity.weights 字段 |
| 中 | 添加 SchedulableEntity.entry_count 字段 |
| 低 | 添加 RuntimeState.status 字段 |
| 低 | 支持 GPU/NPU 异构调度 |
| 低 | 调度可视化日志 |

---

**文档版本**：v1.0
**生成日期**：2026-02-02
**参考文档**：《NEU_TVM_建议书_1212_v0.8》
