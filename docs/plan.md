### 核心目标

1. **结构体对齐**：将生成的 `op_args_t` 升级为建议书 3.2.3 节定义的 `SchedulableEntity`，明确区分算子入口、权重、输入输出和配置。
2. **调度逻辑对齐**：废弃简单的 OpenMP `parallel for`，实现建议书 3.3.4 节描述的 **Scheduler-Worker** 闭环模型（基于 `Ready Queue` 和 `Complete Queue` 两个队列）。

---

### 编码计划概览

#### 第一步：改造 `operator_staticizer.py` (实现 SchedulableEntity)

**目标**：修改 C 代码生成逻辑，使其输出符合建议书定义的"封闭式可调度实体"。

**修改点**：

1. **重命名结构体**：将 `op_args_t` 重命名为 `SchedulableEntity`。
2. **扩展字段**：
   * `kernel`: 函数指针（原 `g_op_call_table` 的内容移入实体内）。
   * `weights`: 权重指针数组（建议书中明确区分了常量）。
   * `exec_config`: 执行配置（如 device_id, priority）。
   * `entry_count`: 初始入度（静态信息，供调度器初始化使用）。

3. **生成静态数组**：不再生成分离的函数表和参数表，而是生成一个统一的 `const SchedulableEntity g_entities[]`。

#### 第二步：创建 `scheduler_core.c` 模板 (实现调度引擎)

**目标**：实现建议书中的"闭环调度"。这将是一个新的 C 模板，会被注入到 `lib1.c` 中。

**包含组件**：

1. **队列结构**：实现线程安全队列（`ReadyQueue`, `CompleteQueue`）。
2. **运行时状态**：`RuntimeState`，维护每个算子的动态入度（`current_indegree`）。
3. **Scheduler 线程函数**：
   * 等待 `CompleteQueue`。
   * 更新后继节点入度。
   * 将入度为 0 的节点推入 `ReadyQueue`。

4. **Worker 线程函数**：
   * 从 `ReadyQueue` 取任务。
   * 执行 `entity->kernel(...)`。
   * 将完成事件推入 `CompleteQueue`。

#### 第三步：修改 `merge_parallel_code.py` (集成)

**目标**：将上述两部分整合到 `lib1.c` 中。

**修改点**：

1. 移除旧的 OpenMP 循环。
2. 注入新的 `scheduler_core` 代码。
3. 在 `main` 函数中，初始化调度器，启动 Worker 线程，然后启动 Scheduler 循环。

---

### 详细实施细节

#### 1. 修改 `scripts/operator_staticizer.py`

你需要修改 `generate_type_defs` 和 `generate_op_args_template` 方法。

**建议修改后的生成代码示例 (C语言):**

```c
// [修改前] op_args_t
// typedef struct { void* inputs[...]; ... } op_args_t;

// [修改后] 符合建议书的 SchedulableEntity
typedef struct {
    // 1. 执行入口 (建议书: kernel())
    int32_t (*kernel)(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws);

    // 2. 数据 (建议书: weights[], inputs[], outputs[])
    void* inputs[MAX_INPUTS];
    void* outputs[MAX_OUTPUTS];
    // TVM 的权重通常混在参数里，这里作为占位符
    void* weights[MAX_WEIGHTS];

    // 3. 执行配置 (建议书: exec_config)
    struct {
        int device_type; // 0=CPU, 1=GPU, 2=NPU
        int priority;
    } config;

    // 4. 静态信息
    int id;
    int entry_count; // 初始入度（静态值，初始化时复制到 RuntimeState）
} SchedulableEntity;

// 统一的实体数组
static const SchedulableEntity g_entities[OP_COUNT] = {
    {
        .id = 0,
        .entry_count = 1,  // 初始入度
        .kernel = wrapped_tvmgen_default_fused_nn_conv2d,
        .inputs = { ... },
        .config = { .device_type = 0 }
    },
    // ...
};

// 从 SchedulableEntity 提取初始入度（供调度器初始化使用）
static const int g_initial_indegrees[OP_COUNT] = {
    1,  // entity[0].entry_count
    0,  // entity[1].entry_count
    // ...
};

```

**Python 脚本修改逻辑：**

* 在 `OperatorInfo` 类中，尝试区分 `const` 参数（权重）和非 `const` 参数。
* 将生成的 `op_func_t` 签名标准化。
* 根据算子依赖关系计算 `entry_count` 并填入结构体。

#### 2. 新增 `scripts/templates/scheduler_runtime.c`

建议创建一个单独的文件存放调度器逻辑，方便 `merge_parallel_code.py` 读取。

**核心逻辑草稿：**

```c
// === 建议书 3.3.4 调度引擎实现 ===

// 1. 运行时状态 (动态部分，与静态 SchedulableEntity 分离)
// 注意：SchedulableEntity 是编译期 const，RuntimeState 是运行时可变
typedef struct {
    int current_indegree; // 当前剩余依赖数（动态）
    int status;           // 0=PENDING, 1=READY, 2=RUNNING, 3=DONE
} RuntimeState;

// 2. 线程安全队列 (简化版)
// 只有两个队列：ReadyQueue 和 CompleteQueue（建议书图 3-57）
typedef struct {
    int data[OP_COUNT];
    int head;
    int tail;
    int count;  // 队列中元素数量
    pthread_mutex_t lock;
    pthread_cond_t cond;
} SafeQueue;

// 3. 全局上下文
struct RuntimeContext {
    RuntimeState states[OP_COUNT];     // 运行时状态（动态）
    SafeQueue ready_queue;             // 就绪队列
    SafeQueue complete_queue;          // 完成队列
    const SchedulableEntity* entities; // 指向 g_entities
    int total_ops;
    int completed_ops;
    volatile int stop;                 // 终止标志
};

// 4. Scheduler 核心逻辑 (对应建议书图 3-57)
void* scheduler_loop(void* arg) {
    struct RuntimeContext* ctx = (struct RuntimeContext*)arg;

    while (ctx->completed_ops < ctx->total_ops) {
        // A. 等待算子完成 (从 CompleteQueue 获取完成事件)
        int finished_op_id = queue_pop(&ctx->complete_queue);
        ctx->completed_ops++;

        // B. 资源回收 (Last-use check - 暂略，留作扩展)

        // C. 推进依赖 - 更新后继节点入度
        // g_successors[op_id] 返回该算子的后继节点列表
        const int* successors = g_successors[finished_op_id];
        int num_succ = g_successor_counts[finished_op_id];

        for (int i = 0; i < num_succ; i++) {
            int succ_id = successors[i];

            // 递减入度
            ctx->states[succ_id].current_indegree--;

            // D. 就绪判定 - 入度为 0 则推入就绪队列
            if (ctx->states[succ_id].current_indegree == 0) {
                queue_push(&ctx->ready_queue, succ_id);
            }
        }
    }

    // E. 发送终止信号给所有 Workers
    // 发送 N 个 -1 信号（每个 worker 一个）
    for (int i = 0; i < ctx->num_workers; i++) {
        queue_push(&ctx->ready_queue, -1);
    }

    return NULL;
}

// 5. Worker 逻辑 (对应建议书图 3-63)
void* worker_loop(void* arg) {
    struct RuntimeContext* ctx = arg;

    while (true) {
        // A. 从就绪队列获取任务
        int op_id = queue_pop(&ctx->ready_queue);

        // B. 终止信号检测
        if (op_id == -1) {
            // 将终止信号传回（让其他 worker 也退出）
            queue_push(&ctx->ready_queue, -1);
            break;
        }

        // C. 执行算子 (调用 SchedulableEntity 中的 kernel)
        const SchedulableEntity* entity = &ctx->entities[op_id];
        entity->kernel(entity->inputs, entity->outputs, ctx->cws, ctx->ws);

        // D. 上报完成 (推入 CompleteQueue)
        queue_push(&ctx->complete_queue, op_id);
    }

    return NULL;
}

// 6. 运行时初始化
void init_runtime_context(struct RuntimeContext* ctx,
                          const SchedulableEntity* entities,
                          uint8_t* cws, uint8_t* ws,
                          int num_workers) {
    ctx->entities = entities;
    ctx->cws = cws;
    ctx->ws = ws;
    ctx->num_workers = num_workers;
    ctx->total_ops = OP_COUNT;
    ctx->completed_ops = 0;
    ctx->stop = 0;

    // 初始化运行时状态：从 g_initial_indegrees 复制
    for (int i = 0; i < OP_COUNT; i++) {
        ctx->states[i].current_indegree = g_initial_indegrees[i];
        ctx->states[i].status = 0; // PENDING
    }

    // 初始化队列
    queue_init(&ctx->ready_queue);
    queue_init(&ctx->complete_queue);

    // 将初始入度为 0 的算子推入就绪队列
    for (int i = 0; i < OP_COUNT; i++) {
        if (ctx->states[i].current_indegree == 0) {
            queue_push(&ctx->ready_queue, i);
        }
    }
}

```

#### 3. 修改 `scripts/gen_parallel_schedule.py`

为了支持上面的调度器，需要生成**邻接表（Adjacency List）**，而不仅仅是现在的分层表。现在的调度是基于 Layer 的（Layer 0, Layer 1...），这是隐式的同步。建议书的调度是基于 DAG 的，需要显式的后继关系。

**修改点**：

1. **生成邻接表**：
   ```c
   // 每个算子的后继节点列表
   static const int g_successors_0[] = { 5, 12, ... };
   static const int g_successors_1[] = { 7, ... };
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
   ```

2. **生成初始入度表**：
   ```c
   static const int g_initial_indegrees[OP_COUNT] = {
       1,  // op_0
       2,  // op_1
       0,  // op_2 (无依赖)
       // ...
   };
   ```

3. **从 Layer 表推导依赖关系**：
   * 遍历所有 Layer，记录每个算子所属的 Layer 编号
   * 如果算子 A 在 Layer N，算子 B 在 Layer M，且 M > N，则 A 可能是 B 的前驱
   * 通过输入输出 Buffer 指针精确确定依赖关系

---

### 执行步骤总结

1. **修改 `gen_parallel_schedule.py`**：
   * 新增输出：生成 `g_successors[]`、`g_successor_counts[]` 和 `g_initial_indegrees[]`。
   * 实现从 Layer 表到 DAG 邻接表的转换算法。

2. **修改 `operator_staticizer.py`**：
   * 将结构体定义改为 `SchedulableEntity`。
   * 添加 `entry_count` 字段。
   * 尝试解析参数列表中的 `global_const_workspace` 变量，将其指针放入 `weights` 数组。

3. **编写 `scheduler_runtime.c`**：
   * 实现 SafeQueue（线程安全队列）。
   * 实现 `scheduler_loop` 和 `worker_loop`。
   * 实现 `init_runtime_context`。

4. **修改 `merge_parallel_code.py`**：
   * 读取 `scheduler_runtime.c` 的内容。
   * 在生成的 `main` 函数中，不再生成 `for (layers) { omp parallel }`，而是生成：
   ```c
   // 初始化
   struct RuntimeContext ctx;
   init_runtime_context(&ctx, g_entities, cws, ws, num_workers);

   // 启动 Scheduler 线程
   pthread_t sched_thread;
   pthread_create(&sched_thread, NULL, scheduler_loop, &ctx);

   // 启动 Worker 线程
   pthread_t worker_threads[N];
   for (int i = 0; i < N; i++) {
       pthread_create(&worker_threads[i], NULL, worker_loop, &ctx);
   }

   // 等待结束
   pthread_join(sched_thread, NULL);
   for (int i = 0; i < N; i++) {
       pthread_join(worker_threads[i], NULL);
   }
   ```

---

### 设计要点回顾

| 概念 | 说明 |
|------|------|
| **SchedulableEntity** | 静态、不可变的算子描述（编译期生成） |
| **RuntimeState** | 动态、可变的运行时状态（当前入度、状态） |
| **Ready Queue** | 存放入度为 0、可以执行的算子 |
| **Complete Queue** | 存放已完成的算子，供 Scheduler 消费 |
| **Scheduler** | 单线程，监听 Complete Queue，更新依赖，入度归零时推入 Ready Queue |
| **Worker** | 多线程，从 Ready Queue 取任务执行，完成后推入 Complete Queue |

这将使你的代码与建议书的**高度一致**，并且真正实现了一个**动态、事件驱动的运行时**，而不是仅仅依赖 OpenMP 的静态分层执行。
