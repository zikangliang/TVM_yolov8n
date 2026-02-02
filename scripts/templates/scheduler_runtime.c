// ============================================================
// Scheduler-Worker 运行时核心代码
// 基于建议书 3.3.4 节的闭环调度模型
// ============================================================

#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

// ============ 线程安全队列 ============

typedef struct {
  int32_t data[OP_COUNT + 16]; // 预留终止信号空间
  int head;
  int tail;
  int count;
  pthread_mutex_t lock;
  pthread_cond_t not_empty;
} SafeQueue;

static void queue_init(SafeQueue *q) {
  memset(q->data, 0, sizeof(q->data));
  q->head = 0;
  q->tail = 0;
  q->count = 0;
  pthread_mutex_init(&q->lock, NULL);
  pthread_cond_init(&q->not_empty, NULL);
}

static void queue_destroy(SafeQueue *q) {
  pthread_mutex_destroy(&q->lock);
  pthread_cond_destroy(&q->not_empty);
}

static void queue_push(SafeQueue *q, int32_t value) {
  pthread_mutex_lock(&q->lock);
  q->data[q->tail] = value;
  q->tail = (q->tail + 1) % (OP_COUNT + 16);
  q->count++;
  pthread_cond_signal(&q->not_empty);
  pthread_mutex_unlock(&q->lock);
}

static int32_t queue_pop(SafeQueue *q) {
  pthread_mutex_lock(&q->lock);
  while (q->count == 0) {
    pthread_cond_wait(&q->not_empty, &q->lock);
  }
  int32_t value = q->data[q->head];
  q->head = (q->head + 1) % (OP_COUNT + 16);
  q->count--;
  pthread_mutex_unlock(&q->lock);
  return value;
}

// ============ 运行时上下文 ============

typedef struct {
  int32_t current_indegree; // 当前剩余依赖数（动态）
                            // int32_t status;         // 暂不使用
} RuntimeState;

typedef struct {
  // 静态数据
  int total_ops;

  // 动态状态
  RuntimeState *states;
  SafeQueue ready_queue;
  SafeQueue complete_queue;

  // 工作空间
  uint8_t *cws;
  uint8_t *ws;
  SchedulableEntity *entities;

  // 控制
  int num_workers;
  volatile int completed_ops;
  volatile int error;

  // 同步
  pthread_mutex_t indegree_lock; // 保护入度更新
} RuntimeContext;

typedef struct {
  RuntimeContext *ctx;
  int worker_id;
} WorkerArg;

// ============ Worker 线程 ============

static void *worker_loop(void *arg) {
  WorkerArg *wa = (WorkerArg *)arg;
  RuntimeContext *ctx = wa->ctx;

  while (1) {
    // A. 从 Ready Queue 获取任务
    int32_t op_id = queue_pop(&ctx->ready_queue);

    // B. 终止信号检测
    if (op_id < 0) {
      break;
    }

    // C. 执行算子（直接从实体调用 kernel）
    SchedulableEntity *entity = &ctx->entities[op_id];
    int ret =
        entity->kernel(entity->inputs, entity->outputs, ctx->cws, ctx->ws);
    if (ret != 0) {
      ctx->error = ret;
    }

    // D. 上报完成
    queue_push(&ctx->complete_queue, op_id);
  }

  return NULL;
}

// ============ Scheduler 线程 ============

static void *scheduler_loop(void *arg) {
  RuntimeContext *ctx = (RuntimeContext *)arg;

  while (ctx->completed_ops < ctx->total_ops) {
    // A. 从 Complete Queue 获取完成事件
    int32_t finished_op_id = queue_pop(&ctx->complete_queue);

    if (finished_op_id < 0)
      break; // 终止信号

    __atomic_fetch_add(&ctx->completed_ops, 1, __ATOMIC_SEQ_CST);

    // B. 更新后继节点入度
    int32_t num_succ = g_successor_counts[finished_op_id];
    const int32_t *successors = g_successors[finished_op_id];

    for (int i = 0; i < num_succ; i++) {
      int32_t succ_id = successors[i];

      // 原子递减入度
      pthread_mutex_lock(&ctx->indegree_lock);
      ctx->states[succ_id].current_indegree--;
      int32_t new_indegree = ctx->states[succ_id].current_indegree;
      pthread_mutex_unlock(&ctx->indegree_lock);

      // C. 入度为 0，推入 Ready Queue
      if (new_indegree == 0) {
        queue_push(&ctx->ready_queue, succ_id);
      }
    }

    // 错误检测
    if (ctx->error != 0)
      break;
  }

  // D. 发送终止信号给所有 Workers
  for (int i = 0; i < ctx->num_workers; i++) {
    queue_push(&ctx->ready_queue, -1); // -1 作为终止信号
  }

  return NULL;
}

// ============ 运行时初始化 ============

static void init_runtime_context(RuntimeContext *ctx, uint8_t *cws, uint8_t *ws,
                                 SchedulableEntity *entities, int num_workers) {
  ctx->total_ops = OP_COUNT;
  ctx->cws = cws;
  ctx->ws = ws;
  ctx->entities = entities;
  ctx->num_workers = num_workers;
  ctx->completed_ops = 0;
  ctx->error = 0;

  // 分配并初始化运行时状态
  ctx->states = (RuntimeState *)malloc(sizeof(RuntimeState) * OP_COUNT);
  for (int i = 0; i < OP_COUNT; i++) {
    ctx->states[i].current_indegree = g_initial_indegrees[i];
  }

  // 初始化队列
  queue_init(&ctx->ready_queue);
  queue_init(&ctx->complete_queue);

  // 初始化锁
  pthread_mutex_init(&ctx->indegree_lock, NULL);

  // 将初始入度为 0 的算子推入 Ready Queue
  for (int i = 0; i < OP_COUNT; i++) {
    if (ctx->states[i].current_indegree == 0) {
      queue_push(&ctx->ready_queue, i);
    }
  }
}

static void cleanup_runtime_context(RuntimeContext *ctx) {
  queue_destroy(&ctx->ready_queue);
  queue_destroy(&ctx->complete_queue);
  pthread_mutex_destroy(&ctx->indegree_lock);
  free(ctx->states);
}

// ============ DAG 调度运行入口 ============

static int tvmrt_run_dag(uint8_t *cws, uint8_t *ws,
                         SchedulableEntity entities[]) {
  int num_workers = 0;
  const char *env = getenv("TVMRT_NUM_WORKERS");
  if (!env)
    env = getenv("OMP_NUM_THREADS");
  num_workers = env ? atoi(env) : 3;
  if (num_workers < 1)
    num_workers = 1;

  RuntimeContext ctx;
  init_runtime_context(&ctx, cws, ws, entities, num_workers);

  // 启动 Scheduler 线程
  pthread_t sched_thread;
  pthread_create(&sched_thread, NULL, scheduler_loop, &ctx);

  // 启动 Worker 线程
  pthread_t *workers = (pthread_t *)malloc(sizeof(pthread_t) * num_workers);
  WorkerArg *worker_args = (WorkerArg *)malloc(sizeof(WorkerArg) * num_workers);

  for (int i = 0; i < num_workers; i++) {
    worker_args[i].ctx = &ctx;
    worker_args[i].worker_id = i;
    pthread_create(&workers[i], NULL, worker_loop, &worker_args[i]);
  }

  // 等待完成
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

// ============ 串行执行路径（兼容模式）============

static int tvmrt_run_serial(uint8_t *cws, uint8_t *ws,
                            SchedulableEntity entities[]) {
  for (int i = 0; i < OP_COUNT; i++) {
    SchedulableEntity *entity = &entities[i];
    int ret = entity->kernel(entity->inputs, entity->outputs, cws, ws);
    if (ret != 0)
      return ret;
  }
  return 0;
}

// ============ 统一运行时入口 ============

static int tvmrt_run(uint8_t *cws, uint8_t *ws, SchedulableEntity entities[]) {
  const char *env = getenv("TVMRT_NUM_WORKERS");
  int num_workers = env ? atoi(env) : 0; // 默认串行模式

  // TVMRT_NUM_WORKERS=0 表示串行模式
  if (num_workers == 0) {
    return tvmrt_run_serial(cws, ws, entities);
  } else {
    return tvmrt_run_dag(cws, ws, entities);
  }
}
