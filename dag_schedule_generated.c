// ============================================================
// DAG 调度数据结构
// ============================================================

// 初始入度表（编译期静态）
static const int32_t g_initial_indegrees[94] = {
    0, 1, 1, 1, 1, 1, 2, 2, 1, 1, 1, 1, 1, 2, 1, 2,
    3, 1, 1, 1, 1, 1, 2, 1, 2, 3, 1, 1, 1, 1, 1, 2,
    2, 1, 1, 1, 1, 1, 4, 1, 2, 1, 1, 1, 1, 2, 1, 2,
    1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1,
    1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1,
    2, 1, 1, 1, 1, 1, 1, 1, 6, 1, 1, 1, 1, 2
};

// 后继节点邻接表
static const int32_t g_successors_0[] = { 1 };
static const int32_t g_successors_1[] = { 2 };
static const int32_t g_successors_2[] = { 3 };
static const int32_t g_successors_3[] = { 4 };
static const int32_t g_successors_4[] = { 5, 6, 7 };
static const int32_t g_successors_5[] = { 6 };
static const int32_t g_successors_6[] = { 7 };
static const int32_t g_successors_7[] = { 8 };
static const int32_t g_successors_8[] = { 9 };
static const int32_t g_successors_9[] = { 10 };
static const int32_t g_successors_10[] = { 11 };
static const int32_t g_successors_11[] = { 12, 13, 16 };
static const int32_t g_successors_12[] = { 13 };
static const int32_t g_successors_13[] = { 14, 15, 16 };
static const int32_t g_successors_14[] = { 15 };
static const int32_t g_successors_15[] = { 16 };
static const int32_t g_successors_16[] = { 17 };
static const int32_t g_successors_17[] = { 18, 47 };
static const int32_t g_successors_18[] = { 19 };
static const int32_t g_successors_19[] = { 20 };
static const int32_t g_successors_20[] = { 21, 22, 25 };
static const int32_t g_successors_21[] = { 22 };
static const int32_t g_successors_22[] = { 23, 24, 25 };
static const int32_t g_successors_23[] = { 24 };
static const int32_t g_successors_24[] = { 25 };
static const int32_t g_successors_25[] = { 26 };
static const int32_t g_successors_26[] = { 27, 40 };
static const int32_t g_successors_27[] = { 28 };
static const int32_t g_successors_28[] = { 29 };
static const int32_t g_successors_29[] = { 30, 31, 32 };
static const int32_t g_successors_30[] = { 31 };
static const int32_t g_successors_31[] = { 32 };
static const int32_t g_successors_32[] = { 33 };
static const int32_t g_successors_33[] = { 34 };
static const int32_t g_successors_34[] = { 35, 38 };
static const int32_t g_successors_35[] = { 36, 38 };
static const int32_t g_successors_36[] = { 37, 38 };
static const int32_t g_successors_37[] = { 38 };
static const int32_t g_successors_38[] = { 39 };
static const int32_t g_successors_39[] = { 40, 75 };
static const int32_t g_successors_40[] = { 41 };
static const int32_t g_successors_41[] = { 42 };
static const int32_t g_successors_42[] = { 43, 45 };
static const int32_t g_successors_43[] = { 44 };
static const int32_t g_successors_44[] = { 45 };
static const int32_t g_successors_45[] = { 46 };
static const int32_t g_successors_46[] = { 47, 61 };
static const int32_t g_successors_47[] = { 48 };
static const int32_t g_successors_48[] = { 49 };
static const int32_t g_successors_49[] = { 50, 52 };
static const int32_t g_successors_50[] = { 51 };
static const int32_t g_successors_51[] = { 52 };
static const int32_t g_successors_52[] = { 53 };
static const int32_t g_successors_53[] = { 54, 57, 60 };
static const int32_t g_successors_54[] = { 55 };
static const int32_t g_successors_55[] = { 56 };
static const int32_t g_successors_56[] = { 88 };
static const int32_t g_successors_57[] = { 58 };
static const int32_t g_successors_58[] = { 59 };
static const int32_t g_successors_59[] = { 88 };
static const int32_t g_successors_60[] = { 61 };
static const int32_t g_successors_61[] = { 62 };
static const int32_t g_successors_62[] = { 63 };
static const int32_t g_successors_63[] = { 64, 66 };
static const int32_t g_successors_64[] = { 65 };
static const int32_t g_successors_65[] = { 66 };
static const int32_t g_successors_66[] = { 67 };
static const int32_t g_successors_67[] = { 68, 71, 74 };
static const int32_t g_successors_68[] = { 69 };
static const int32_t g_successors_69[] = { 70 };
static const int32_t g_successors_70[] = { 88 };
static const int32_t g_successors_71[] = { 72 };
static const int32_t g_successors_72[] = { 73 };
static const int32_t g_successors_73[] = { 88 };
static const int32_t g_successors_74[] = { 75 };
static const int32_t g_successors_75[] = { 76 };
static const int32_t g_successors_76[] = { 77 };
static const int32_t g_successors_77[] = { 78, 80 };
static const int32_t g_successors_78[] = { 79 };
static const int32_t g_successors_79[] = { 80 };
static const int32_t g_successors_80[] = { 81 };
static const int32_t g_successors_81[] = { 82, 85 };
static const int32_t g_successors_82[] = { 83 };
static const int32_t g_successors_83[] = { 84 };
static const int32_t g_successors_84[] = { 88 };
static const int32_t g_successors_85[] = { 86 };
static const int32_t g_successors_86[] = { 87 };
static const int32_t g_successors_87[] = { 88 };
static const int32_t g_successors_88[] = { 89, 93 };
static const int32_t g_successors_89[] = { 90 };
static const int32_t g_successors_90[] = { 91 };
static const int32_t g_successors_91[] = { 92 };
static const int32_t g_successors_92[] = { 93 };
static const int32_t g_successors_93[] = { -1 };  // 无后继（哨兵值）

static const int32_t* g_successors[94] = {
    g_successors_0,
    g_successors_1,
    g_successors_2,
    g_successors_3,
    g_successors_4,
    g_successors_5,
    g_successors_6,
    g_successors_7,
    g_successors_8,
    g_successors_9,
    g_successors_10,
    g_successors_11,
    g_successors_12,
    g_successors_13,
    g_successors_14,
    g_successors_15,
    g_successors_16,
    g_successors_17,
    g_successors_18,
    g_successors_19,
    g_successors_20,
    g_successors_21,
    g_successors_22,
    g_successors_23,
    g_successors_24,
    g_successors_25,
    g_successors_26,
    g_successors_27,
    g_successors_28,
    g_successors_29,
    g_successors_30,
    g_successors_31,
    g_successors_32,
    g_successors_33,
    g_successors_34,
    g_successors_35,
    g_successors_36,
    g_successors_37,
    g_successors_38,
    g_successors_39,
    g_successors_40,
    g_successors_41,
    g_successors_42,
    g_successors_43,
    g_successors_44,
    g_successors_45,
    g_successors_46,
    g_successors_47,
    g_successors_48,
    g_successors_49,
    g_successors_50,
    g_successors_51,
    g_successors_52,
    g_successors_53,
    g_successors_54,
    g_successors_55,
    g_successors_56,
    g_successors_57,
    g_successors_58,
    g_successors_59,
    g_successors_60,
    g_successors_61,
    g_successors_62,
    g_successors_63,
    g_successors_64,
    g_successors_65,
    g_successors_66,
    g_successors_67,
    g_successors_68,
    g_successors_69,
    g_successors_70,
    g_successors_71,
    g_successors_72,
    g_successors_73,
    g_successors_74,
    g_successors_75,
    g_successors_76,
    g_successors_77,
    g_successors_78,
    g_successors_79,
    g_successors_80,
    g_successors_81,
    g_successors_82,
    g_successors_83,
    g_successors_84,
    g_successors_85,
    g_successors_86,
    g_successors_87,
    g_successors_88,
    g_successors_89,
    g_successors_90,
    g_successors_91,
    g_successors_92,
    g_successors_93,
};

// 后继节点数量
static const int32_t g_successor_counts[94] = {
    1, 1, 1, 1, 3, 1, 1, 1, 1, 1, 1, 3, 1, 3, 1, 1,
    1, 2, 1, 1, 3, 1, 3, 1, 1, 1, 2, 1, 1, 3, 1, 1,
    1, 1, 2, 2, 2, 1, 1, 2, 1, 1, 2, 1, 1, 1, 2, 1,
    1, 2, 1, 1, 1, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2,
    1, 1, 1, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1,
    1, 2, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 0
};
