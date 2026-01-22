# OOMOL Data Analysis Subflows 使用指南

本项目提供两种数据分析 subflow,适用于不同场景。

---

## 📊 Subflow 1: Complete Data Analysis (快速单轮分析)

**路径**: `subflows/complete-data-analysis/`

**适用场景**:
- ✅ 快速回答单个明确的问题
- ✅ 需要精确控制分析步骤
- ✅ 问题已经明确定义 (如 "显示前10名销售区域")
- ✅ 只需要一个图表的简单报告

**工作流程**:
```
Load Data → Transform (NL-to-SQL) → Recommend Chart → Generate Chart → Generate Report
```

**输入参数**:
- `data_file`: 数据文件路径
- `analysis_question`: 具体的分析问题
- `source_type`: 文件类型 (csv/excel/json)

**输出**:
- `final_report`: Markdown 格式报告
- `transformed_data`: 转换后的数据表
- `chart_image`: 生成的图表

**特点**:
- ⚡ 快速 (单轮分析)
- 🎯 精确 (针对特定问题)
- 📈 单图表输出
- 🔄 可重复 (相同输入产生相同输出)

**示例测试**:
```bash
# 运行测试
flows/test-complete-analysis/flow.oo.yaml
```

---

## 🧠 Subflow 2: Smart Data Analysis (AI 多轮探索)

**路径**: `subflows/smart-data-analysis/`

**适用场景**:
- ✅ 探索式数据分析
- ✅ 发现隐藏的模式和洞察
- ✅ 问题不明确,需要 AI 引导分析方向
- ✅ 需要多个图表和深度洞察

**工作流程**:
```
Load Data → Multi-Round Exploration (AI Agent) → Generate Comprehensive Report
```

**输入参数**:
- `data_file`: 数据文件路径
- `analysis_goal`: 高层次的分析目标 (如 "发现销售趋势和异常")
- `source_type`: 文件类型
- `max_iterations`: 探索轮数 (默认 3)

**输出**:
- `final_report`: 包含多图表和深度洞察的报告
- `exploration_steps`: AI 探索的详细步骤

**特点**:
- 🤖 智能 (AI 自主决策分析方向)
- 🔍 深度 (多轮迭代发现洞察)
- 📊 多图表输出
- 💡 自动发现模式和异常

**示例测试**:
```bash
# 运行测试
flows/test-smart-analysis/flow.oo.yaml
```

---

## 🆚 对比表

| 维度 | Complete Analysis | Smart Analysis |
|-----|-------------------|----------------|
| **分析方式** | 单轮问答 | 多轮探索 |
| **问题明确度** | 需要明确问题 | 可以模糊目标 |
| **执行时间** | ~30秒 | ~2-3分钟 |
| **输出图表数** | 1个 | 3-5个 |
| **AI 自主性** | 低 (用户指定) | 高 (AI 自主探索) |
| **适用用户** | 知道要分析什么 | 不确定从何入手 |
| **成本** | 低 (单次 LLM 调用) | 中 (多次 LLM 调用) |

---

## 📝 使用建议

### 何时使用 Complete Analysis

**场景 1**: 业务报表
```yaml
analysis_question: "按产品类别汇总本月销售额,降序排列"
```

**场景 2**: KPI 监控
```yaml
analysis_question: "显示各区域转化率,标记低于平均值的区域"
```

**场景 3**: 快速验证假设
```yaml
analysis_question: "新产品发布后,周销售额是否有显著增长?"
```

### 何时使用 Smart Analysis

**场景 1**: 初次探索新数据集
```yaml
analysis_goal: "理解这个数据集的整体特征和主要模式"
```

**场景 2**: 寻找业务机会
```yaml
analysis_goal: "发现未被充分利用的市场机会和增长点"
```

**场景 3**: 根因分析
```yaml
analysis_goal: "找出销售下滑的根本原因和相关因素"
```

---

## 🔧 技术细节

### Complete Analysis 节点结构

1. **Data Loader** - 加载数据
2. **NL-to-SQL** - 自然语言转 SQL 转换
3. **Chart Recommender** - AI 推荐图表类型
4. **Chart Generator** - 生成 Vega-Lite 图表
5. **Scriptlet** - 包装图表为数组
6. **Report Generator** - 生成 Markdown 报告

### Smart Analysis 节点结构

1. **Data Loader** - 加载数据
2. **Exploration Agent** - AI 多轮探索 (内部包含多次转换和可视化)
3. **Report Generator** - 综合多轮结果生成报告

---

## 🎯 最佳实践

### 1. 问题描述质量

**Complete Analysis**:
- ✅ "显示前10个销售额最高的产品"
- ✅ "按月份统计用户注册数,显示趋势"
- ❌ "分析数据" (太模糊)

**Smart Analysis**:
- ✅ "发现影响客户留存率的关键因素"
- ✅ "识别异常交易模式和潜在风险"
- ❌ "显示前10个产品" (太具体,应该用 Complete Analysis)

### 2. 参数调优

**max_iterations 设置**:
- `1-2`: 快速概览
- `3` (默认): 平衡深度和速度
- `4-5`: 深度分析 (时间较长)

### 3. 组合使用

可以先用 **Smart Analysis** 探索数据,发现洞察后,再用 **Complete Analysis** 生成标准化报表。

---

## 📚 相关文档

- [OOMOL_DATA_ANALYSIS_BLOCKS_GUIDE.md](OOMOL_DATA_ANALYSIS_BLOCKS_GUIDE.md) - 详细的 blocks 技术文档
- [README.md](README.md) - 项目整体说明

---

**更新时间**: 2026-01-22
