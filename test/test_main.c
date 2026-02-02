/**
 * 自动生成的测试入口文件
 * 模型: yolov8n
 * 输入大小: 1228800 floats (4800.0 KB)
 * 输出大小: 2714985 floats (10605.4 KB)
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>

// TVM 模型输入输出结构体
struct tvmgen_default_inputs {
    void* images;
};

struct tvmgen_default_outputs {
    void* output;
};

// 模型运行函数声明
int32_t tvmgen_default_run(struct tvmgen_default_inputs*, struct tvmgen_default_outputs*);

// 打印前 N 个元素
void print_first_elements(const char* name, float* data, int count) {
    printf("%s (first %d elements):\n", name, count);
    for (int i = 0; i < count; i++) {
        printf("  [%2d] %.6f\n", i, data[i]);
    }
}

int main(int argc, char* argv[]) {
    // 解析命令行参数
    int iterations = 1;
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-n") == 0 && i + 1 < argc) {
            iterations = atoi(argv[++i]);
        }
    }

    // 分配输入内存（全0）
    float* input = (float*)calloc(1228800, sizeof(float));
    if (!input) {
        fprintf(stderr, "Failed to allocate input memory\n");
        return 1;
    }

    // 分配输出内存
    float* output = (float*)calloc(2714985, sizeof(float));
    if (!output) {
        fprintf(stderr, "Failed to allocate output memory\n");
        free(input);
        return 1;
    }

    struct tvmgen_default_inputs inputs = { .images = input };
    struct tvmgen_default_outputs outputs = { .output = output };

    printf("=== yolov8n Test ===\n");
    printf("Input size: 1228800 floats (4800.0 KB)\n");
    printf("Output size: 2714985 floats (10605.4 KB)\n");
    printf("Iterations: %d\n", iterations);

    printf("\nRunning inference...\n");
    double total_time = 0.0;

    for (int i = 0; i < iterations; i++) {
        clock_t start = clock();
        int ret = tvmgen_default_run(&inputs, &outputs);
        clock_t end = clock();
        double elapsed = (double)(end - start) / CLOCKS_PER_SEC * 1000.0;
        total_time += elapsed;

        if (ret != 0) {
            fprintf(stderr, "Inference %d failed with error: %d\n", i + 1, ret);
            free(input);
            free(output);
            return ret;
        }
        printf("  Iteration %d: %.2f ms\n", i + 1, elapsed);
    }

    double avg_time = total_time / iterations;
    printf("\n=== Results ===\n");
    printf("Total time: %.2f ms\n", total_time);
    printf("Average time: %.2f ms\n", avg_time);
    printf("FPS: %.1f\n", 1000.0 / avg_time);

    // 打印前20个输出元素
    print_first_elements("Output", output, 20);

    free(input);
    free(output);

    printf("\nTest completed successfully!\n");
    return 0;
}
