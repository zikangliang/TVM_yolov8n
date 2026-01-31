# TVM YOLOv5n C模型部署指南 (Linux)

**最简方案：不需要添加任何头文件，只需修改2个源文件**

---

## 一、修改 lib0.c

### 1.1 开头修改（第1-5行）

**原文：**
```c
#include "tvm/runtime/c_runtime_api.h"
#ifdef __cplusplus
extern "C" {
#endif
__attribute__((section(".rodata.tvm"), ))
```

**改为：**
```c
#define TVM_DLL
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
__attribute__((section(".rodata.tvm")))
```

### 1.2 末尾修改（约246415行）

**原文：**
```c
__attribute__((section(".bss.noinit.tvm"), aligned(16)))
static uint8_t global_workspace[23040256];
#include <tvmgen_default.h>
```

**改为：**
```c
__attribute__((section(".bss.noinit.tvm"), aligned(16)))
static uint8_t global_workspace[23040256];

struct tvmgen_default_inputs { void* images; };
struct tvmgen_default_outputs { void* output; };
```

---

## 二、修改 lib1.c

### 2.1 开头修改（第1-5行）

**原文：**
```c
// tvm target: c -keys=cpu
#define TVM_EXPORTS
#include "tvm/runtime/c_runtime_api.h"
#include "tvm/runtime/c_backend_api.h"
#include <math.h>
#include <stdbool.h>
```

**改为：**
```c
// tvm target: c -keys=cpu
#define TVM_DLL
#include <stdint.h>
#include <math.h>
#include <stdbool.h>
```

---

## 三、添加 Makefile

新建文件 `Makefile`，内容如下：

```makefile
CC = gcc
CFLAGS = -O3 -fPIC
LDFLAGS = -lm

BUILD_DIR = build
OBJ_DIR = $(BUILD_DIR)/obj

all: $(BUILD_DIR)/yolov5n_test

$(OBJ_DIR):
	@mkdir -p $(OBJ_DIR)

$(OBJ_DIR)/%.o: %.c | $(OBJ_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/yolov5n_test: $(OBJ_DIR)/lib0.o $(OBJ_DIR)/lib1.o $(OBJ_DIR)/test_main.o
	@mkdir -p $(BUILD_DIR)
	$(CC) -o $@ $^ $(LDFLAGS)

clean:
	rm -rf $(BUILD_DIR)

.PHONY: all clean
```

---

## 四、添加 test_main.c

新建文件 `test_main.c`，内容如下：

```c
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

struct tvmgen_default_inputs { void* images; };
struct tvmgen_default_outputs { void* output; };
int32_t tvmgen_default_run(struct tvmgen_default_inputs*, struct tvmgen_default_outputs*);

int main() {
    float* input = malloc(3 * 640 * 640 * sizeof(float));
    float* output = calloc(255 * 10647, sizeof(float));

    struct tvmgen_default_inputs inputs = { .images = input };
    struct tvmgen_default_outputs outputs = { .output = output };

    int ret = tvmgen_default_run(&inputs, &outputs);
    printf("Result: %d, output[0]=%f\n", ret, output[0]);

    free(input);
    free(output);
    return ret;
}
```

---

## 五、编译运行

```bash
make
./build/yolov5n_test
```

---

## 六、macOS 兼容性说明

macOS 的 section 属性格式与 Linux 不同，如果在 macOS 上编译，需要删除 section 属性：

**lib0.c 开头：** 删除 `__attribute__((section(".rodata.tvm")))`
**lib0.c 末尾：** 将 `__attribute__((section(".bss.noinit.tvm"), aligned(16)))` 改为 `__attribute__((aligned(16)))`

或在代码中使用条件编译：
```c
#if defined(__APPLE__)
__attribute__((section("__DATA,.rodata_tvm")))
#else
__attribute__((section(".rodata.tvm")))
#endif
```

---

## 七、修改总结

| 文件 | 位置 | 原文 | 改为 |
|------|------|------|------|
| lib0.c | 第1行 | `#include "tvm/runtime/c_runtime_api.h"` | `#define TVM_DLL` |
| lib0.c | 第1行后 | (无) | `#include <stdint.h>` |
| lib0.c | 第5行 | `__attribute__((section(".rodata.tvm"), ))` | `__attribute__((section(".rodata.tvm")))` |
| lib0.c | 末尾 | `#include <tvmgen_default.h>` | `struct tvmgen_default_inputs { void* images; };`<br>`struct tvmgen_default_outputs { void* output; };` |
| lib1.c | 第2行 | `#define TVM_EXPORTS` | `#define TVM_DLL` |
| lib1.c | 第3-4行 | `#include "tvm/runtime/c_runtime_api.h"`<br>`#include "tvm/runtime/c_backend_api.h"` | `#include <stdint.h>` |
