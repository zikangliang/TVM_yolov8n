// ============================================================
// 自动生成的 Scheduler-Worker 运行时数据结构
// 算子数量: 94
// ============================================================

// ============ 类型定义 ============
#define MAX_INPUTS 8
#define MAX_OUTPUTS 2
#define OP_COUNT 94

// 执行配置（预留扩展）
typedef struct {
    int device_type;  // 0=CPU, 1=GPU, 2=NPU
    int priority;     // 调度优先级
} ExecConfig;

// 前向声明
struct SchedulableEntity;

// 内核函数指针类型：接收 inputs[], outputs[], cws, ws
typedef int32_t (*kernel_func_t)(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws);

// 可调度实体 = 函数指针 + 数据参数 + 配置
typedef struct SchedulableEntity {
    // 1. 执行入口（内核函数指针）
    kernel_func_t kernel;

    // 2. 数据参数
    void* inputs[MAX_INPUTS];
    void* outputs[MAX_OUTPUTS];
    int input_count;
    int output_count;

    // 3. 执行配置
    ExecConfig config;

    // 4. 标识
    int id;
} SchedulableEntity;

// ============ TVM 算子函数声明 ============
TVM_DLL int32_t tvmgen_default_fused_concatenate();
TVM_DLL int32_t tvmgen_default_fused_concatenate_1();
TVM_DLL int32_t tvmgen_default_fused_concatenate_10();
TVM_DLL int32_t tvmgen_default_fused_concatenate_2();
TVM_DLL int32_t tvmgen_default_fused_concatenate_3();
TVM_DLL int32_t tvmgen_default_fused_concatenate_4();
TVM_DLL int32_t tvmgen_default_fused_concatenate_5();
TVM_DLL int32_t tvmgen_default_fused_concatenate_6();
TVM_DLL int32_t tvmgen_default_fused_concatenate_7();
TVM_DLL int32_t tvmgen_default_fused_concatenate_8();
TVM_DLL int32_t tvmgen_default_fused_concatenate_9();
TVM_DLL int32_t tvmgen_default_fused_concatenate_layout_transform_reshape_concatenate_layout_transform_reshape__7c5ad37d2665c07f_();
TVM_DLL int32_t tvmgen_default_fused_layout_transform();
TVM_DLL int32_t tvmgen_default_fused_layout_transform_image_resize2d_layout_transform_concatenate_layout_transf_1bf4794317454c42_();
TVM_DLL int32_t tvmgen_default_fused_layout_transform_image_resize2d_layout_transform_concatenate_layout_transf_1bf4794317454c42__1();
TVM_DLL int32_t tvmgen_default_fused_layout_transform_reshape_strided_slice_subtract_strided_slice_add_add_divi_e52109f6a309057f_();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_1();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_2();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_3();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_4();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_5();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_1();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_10();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_11();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_12();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_13();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_14();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_15();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_16();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_17();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_18();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_19();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_2();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_20();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_21();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_22();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_23();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_24();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_25();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_26();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_27();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_28();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_29();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_3();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_30();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_31();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_32();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_33();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_34();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_35();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_36();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_37();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_38();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_39();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_4();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_40();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_41();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_42();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_43();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_44();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_45();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_46();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_47();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_48();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_49();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_5();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_50();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_6();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_7();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_8();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_9();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add_1();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add_2();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add_3();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add_4();
TVM_DLL int32_t tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add_5();
TVM_DLL int32_t tvmgen_default_fused_nn_max_pool2d();
TVM_DLL int32_t tvmgen_default_fused_nn_max_pool2d_1();
TVM_DLL int32_t tvmgen_default_fused_nn_max_pool2d_2();
TVM_DLL int32_t tvmgen_default_fused_nn_softmax();
TVM_DLL int32_t tvmgen_default_fused_reshape_transpose();
TVM_DLL int32_t tvmgen_default_fused_split();
TVM_DLL int32_t tvmgen_default_fused_split_1();
TVM_DLL int32_t tvmgen_default_fused_split_2();
TVM_DLL int32_t tvmgen_default_fused_split_3();
TVM_DLL int32_t tvmgen_default_fused_split_4();
TVM_DLL int32_t tvmgen_default_fused_split_5();
TVM_DLL int32_t tvmgen_default_fused_split_6();
TVM_DLL int32_t tvmgen_default_fused_split_7();
TVM_DLL int32_t tvmgen_default_fused_transpose_layout_transform();

// ============ 包装函数 ============
// 签名: (void** inputs, void** outputs, uint8_t* cws, uint8_t* ws)

static inline int32_t wrapped_tvmgen_default_fused_concatenate(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_concatenate(inputs[0], inputs[1], inputs[2], inputs[3], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_concatenate_1(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_concatenate_1(inputs[0], inputs[1], inputs[2], inputs[3], inputs[4], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_concatenate_10(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_concatenate_10(inputs[0], inputs[1], inputs[2], inputs[3], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_concatenate_2(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_concatenate_2(inputs[0], inputs[1], inputs[2], inputs[3], inputs[4], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_concatenate_3(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_concatenate_3(inputs[0], inputs[1], inputs[2], inputs[3], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_concatenate_4(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_concatenate_4(inputs[0], inputs[1], inputs[2], inputs[3], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_concatenate_5(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_concatenate_5(inputs[0], inputs[1], inputs[2], inputs[3], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_concatenate_6(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_concatenate_6(inputs[0], inputs[1], inputs[2], inputs[3], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_concatenate_7(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_concatenate_7(inputs[0], inputs[1], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_concatenate_8(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_concatenate_8(inputs[0], inputs[1], inputs[2], inputs[3], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_concatenate_9(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_concatenate_9(inputs[0], inputs[1], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_concatenate_layout_transform_reshape_concatenate_layout_transform_reshape__7c5ad37d2665c07f_(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_concatenate_layout_transform_reshape_concatenate_layout_transform_reshape__7c5ad37d2665c07f_(inputs[0], inputs[1], inputs[2], inputs[3], inputs[4], inputs[5], outputs[0], outputs[1], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_layout_transform(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_layout_transform(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_layout_transform_image_resize2d_layout_transform_concatenate_layout_transf_1bf4794317454c42_(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_layout_transform_image_resize2d_layout_transform_concatenate_layout_transf_1bf4794317454c42_(inputs[0], inputs[1], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_layout_transform_image_resize2d_layout_transform_concatenate_layout_transf_1bf4794317454c42__1(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_layout_transform_image_resize2d_layout_transform_concatenate_layout_transf_1bf4794317454c42__1(inputs[0], inputs[1], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_layout_transform_reshape_strided_slice_subtract_strided_slice_add_add_divi_e52109f6a309057f_(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_layout_transform_reshape_strided_slice_subtract_strided_slice_add_add_divi_e52109f6a309057f_(inputs[0], inputs[1], inputs[2], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_1(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_1(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_2(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_2(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_3(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_3(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_4(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_4(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_5(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_5(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_1(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_1(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_10(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_10(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_11(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_11(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_12(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_12(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_13(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_13(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_14(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_14(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_15(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_15(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_16(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_16(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_17(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_17(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_18(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_18(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_19(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_19(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_2(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_2(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_20(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_20(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_21(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_21(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_22(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_22(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_23(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_23(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_24(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_24(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_25(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_25(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_26(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_26(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_27(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_27(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_28(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_28(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_29(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_29(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_3(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_3(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_30(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_30(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_31(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_31(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_32(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_32(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_33(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_33(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_34(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_34(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_35(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_35(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_36(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_36(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_37(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_37(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_38(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_38(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_39(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_39(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_4(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_4(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_40(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_40(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_41(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_41(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_42(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_42(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_43(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_43(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_44(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_44(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_45(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_45(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_46(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_46(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_47(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_47(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_48(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_48(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_49(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_49(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_5(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_5(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_50(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_50(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_6(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_6(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_7(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_7(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_8(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_8(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_9(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_9(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add(inputs[0], inputs[1], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add_1(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add_1(inputs[0], inputs[1], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add_2(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add_2(inputs[0], inputs[1], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add_3(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add_3(inputs[0], inputs[1], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add_4(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add_4(inputs[0], inputs[1], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add_5(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add_5(inputs[0], inputs[1], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_max_pool2d(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_max_pool2d(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_max_pool2d_1(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_max_pool2d_1(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_max_pool2d_2(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_max_pool2d_2(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_nn_softmax(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_nn_softmax(inputs[0], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_reshape_transpose(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_reshape_transpose(inputs[0], inputs[1], outputs[0], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_split(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_split(inputs[0], outputs[0], outputs[1], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_split_1(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_split_1(inputs[0], outputs[0], outputs[1], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_split_2(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_split_2(inputs[0], outputs[0], outputs[1], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_split_3(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_split_3(inputs[0], outputs[0], outputs[1], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_split_4(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_split_4(inputs[0], outputs[0], outputs[1], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_split_5(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_split_5(inputs[0], outputs[0], outputs[1], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_split_6(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_split_6(inputs[0], outputs[0], outputs[1], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_split_7(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_split_7(inputs[0], outputs[0], outputs[1], cws, ws);
}

static inline int32_t wrapped_tvmgen_default_fused_transpose_layout_transform(void** inputs, void** outputs, uint8_t* cws, uint8_t* ws) {
    return tvmgen_default_fused_transpose_layout_transform(inputs[0], outputs[0], cws, ws);
}

// ============ 调试信息 ============
static const char* const g_op_names[94] __attribute__((unused)) = {
    "tvmgen_default_fused_layout_transform",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_1",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_2",
    "tvmgen_default_fused_split",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_3",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add",
    "tvmgen_default_fused_concatenate",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_4",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_5",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_6",
    "tvmgen_default_fused_split_1",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_7",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add_1",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_8",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add_2",
    "tvmgen_default_fused_concatenate_1",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_9",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_10",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_11",
    "tvmgen_default_fused_split_2",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_12",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add_3",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_13",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add_4",
    "tvmgen_default_fused_concatenate_2",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_14",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_15",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_16",
    "tvmgen_default_fused_split_3",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_17",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_add_5",
    "tvmgen_default_fused_concatenate_3",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_18",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_19",
    "tvmgen_default_fused_nn_max_pool2d",
    "tvmgen_default_fused_nn_max_pool2d_1",
    "tvmgen_default_fused_nn_max_pool2d_2",
    "tvmgen_default_fused_concatenate_4",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_20",
    "tvmgen_default_fused_layout_transform_image_resize2d_layout_transform_concatenate_layout_transf_1bf4794317454c42_",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_21",
    "tvmgen_default_fused_split_4",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_22",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_23",
    "tvmgen_default_fused_concatenate_5",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_24",
    "tvmgen_default_fused_layout_transform_image_resize2d_layout_transform_concatenate_layout_transf_1bf4794317454c42__1",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_25",
    "tvmgen_default_fused_split_5",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_26",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_27",
    "tvmgen_default_fused_concatenate_6",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_28",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_29",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_30",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_31",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_32",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_1",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_33",
    "tvmgen_default_fused_concatenate_7",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_34",
    "tvmgen_default_fused_split_6",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_35",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_36",
    "tvmgen_default_fused_concatenate_8",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_37",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_38",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_39",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_2",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_40",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_41",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_3",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_42",
    "tvmgen_default_fused_concatenate_9",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_43",
    "tvmgen_default_fused_split_7",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_44",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_45",
    "tvmgen_default_fused_concatenate_10",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_46",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_47",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_48",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_4",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_49",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_sigmoid_multiply_50",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc_add_5",
    "tvmgen_default_fused_concatenate_layout_transform_reshape_concatenate_layout_transform_reshape__7c5ad37d2665c07f_",
    "tvmgen_default_fused_reshape_transpose",
    "tvmgen_default_fused_nn_softmax",
    "tvmgen_default_fused_transpose_layout_transform",
    "tvmgen_default_fused_nn_contrib_conv2d_NCHWc",
    "tvmgen_default_fused_layout_transform_reshape_strided_slice_subtract_strided_slice_add_add_divi_e52109f6a309057f_",
};
