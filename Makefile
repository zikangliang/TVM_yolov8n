# ============================================================
# 自动生成的 Makefile
# 模型: yolov8n
# 算子数量: 94
# ============================================================

CC ?= gcc
CXX ?= g++
AR ?= ar

# 编译选项
CFLAGS = -O3 -Wall -fPIC -pthread 
CXXFLAGS = -O3 -Wall -fPIC -pthread 
LDFLAGS = -lm -pthread 

# 构建目录
BUILD_DIR = build
OBJ_DIR = $(BUILD_DIR)/obj
LIB_DIR = $(BUILD_DIR)/lib

# 源文件目录
SRC_DIR = src
TEST_DIR = test

# 源文件列表
SRCS = $(SRC_DIR)/lib0.c $(SRC_DIR)/lib1.c 
OBJS = $(SRCS:$(SRC_DIR)/%.c=$(OBJ_DIR)/%.o)

# 库文件
STATIC_LIB = $(LIB_DIR)/libyolov8n.a

# 测试可执行文件
TEST_BIN = $(BUILD_DIR)/yolov8n_test

# 默认目标
.PHONY: all
all: $(STATIC_LIB) $(TEST_BIN)

# 创建目录
$(OBJ_DIR):
	@mkdir -p $(OBJ_DIR)

$(LIB_DIR):
	@mkdir -p $(LIB_DIR)

# 编译源文件
$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c | $(OBJ_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

# 生成静态库
$(STATIC_LIB): $(OBJS) | $(LIB_DIR)
	$(AR) rcs $@ $^

# 编译测试
$(TEST_BIN): $(OBJS) $(OBJ_DIR)/test_main.o | $(BUILD_DIR)
	$(CC) -o $@ $^ $(LDFLAGS)

$(OBJ_DIR)/test_main.o: $(TEST_DIR)/test_main.c | $(OBJ_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

# 运行测试
.PHONY: run
run: $(TEST_BIN)
	@echo "Running yolov8n test..."
	./$(TEST_BIN)

# 仅编译静态库
.PHONY: lib
lib: $(STATIC_LIB)

# 仅编译测试
.PHONY: test
test: $(TEST_BIN)

# 清理
.PHONY: clean
clean:
	rm -rf $(BUILD_DIR)

# 调试编译
.PHONY: debug
debug: CFLAGS = -g -O0 -Wall -fPIC 
debug: clean all
