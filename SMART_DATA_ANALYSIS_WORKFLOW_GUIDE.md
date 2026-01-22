# OOMOL 智能数据分析工作流指南与类型兼容性验证报告

## 执行摘要

本报告全面分析 OOMOL 数据分析 blocks 的组合方案,验证类型兼容性问题修复状态,并提供智能分析工作流的最佳实践。

### 关键发现

| 分析维度 | 状态 | 详情 |
|---------|------|------|
| 🎯 **核心工作流** | ✅ 已实现 2 个 | Quick Analysis (单轮) + Smart Analysis (多轮) |
| 🔧 **类型兼容性** | ⚠️ 部分修复 | Chart Generator 已支持推荐输入,但 Quick Analysis 仍用 scriptlet |
| 📊 **Block 覆盖率** | 90% | 11 个 tasks 中 10 个可用 (缺 data-quality-checker) |
| 🚀 **推荐优先级** | 见下方 | 3 个场景,各有最优路径 |

---

## 一、智能数据分析工作流设计

### 1.1 核心分析场景与推荐工作流

#### 场景 A: 快速单问题分析 (Quick Insight)

**用户需求**: "这个 CSV 中,哪些地区销售额最高?"

**推荐工作流**: Quick Analysis Subflow

```
┌─────────────┐   ┌───────────┐   ┌─────────────┐   ┌──────────┐   ┌────────┐
│ Data Loader │──▶│ NL-to-SQL │──▶│Chart        │──▶│  Build   │──▶│ Report │
│   (CSV)     │   │  (Query)  │   │Recommender  │   │  Array   │   │  Gen   │
└─────────────┘   └───────────┘   └─────────────┘   └──────────┘   └────────┘
                                          │
                                          ▼
                                   ┌─────────────┐
                                   │   Chart     │
                                   │  Generator  │
                                   └─────────────┘
```

**特点**:
- ✅ 单轮分析,速度快 (30-60秒)
- ✅ AI 智能推荐最佳图表类型
- ✅ 自动生成分析报告
- ⚠️ 只回答一个问题,深度有限

**适用场景**:
- 快速验证假设
- 单一指标查询 (Top 10, 汇总统计等)
- 数据初步探索

---

#### 场景 B: 多轮深度探索 (Deep Exploration)

**用户需求**: "帮我全面分析这个销售数据,发现异常和趋势"

**推荐工作流**: Smart Data Analysis Subflow

```
┌─────────────┐   ┌──────────────────────────────────────┐   ┌────────┐
│ Data Loader │──▶│     Exploration Agent (多轮迭代)       │──▶│ Report │
│   (CSV)     │   │  - 自动规划分析步骤                     │   │  Gen   │
└─────────────┘   │  - 每轮: SQL → 图表 → 洞察              │   └────────┘
                  │  - 动态调整探索方向                     │
                  └──────────────────────────────────────┘
```

**特点**:
- ✅ AI 自主多轮探索 (默认 3 轮,可配置)
- ✅ 发现隐藏模式和异常
- ✅ 生成多图表综合报告
- ⚠️ 耗时较长 (2-5分钟)

**适用场景**:
- 开放性探索 ("发现任何有趣的东西")
- 业务数据深度分析
- 自动生成分析报告

---

#### 场景 C: 自定义复杂分析 (Custom Pipeline)

**用户需求**: 特殊业务逻辑,需要自定义组合

**推荐工作流**: 手动组合 Blocks

```
┌─────────────┐   ┌───────────┐   ┌──────────────┐
│ Data Loader │──▶│ NL-to-SQL │──▶│ Statistical  │
│   (MySQL)   │   │ (过滤)     │   │  Analyzer    │
└─────────────┘   └───────────┘   └──────────────┘
                                          │
                                          ▼
                  ┌───────────┐   ┌─────────────┐
                  │   Chart   │◀──│ NL-to-Pandas │
                  │ Generator │   │ (聚合计算)    │
                  └───────────┘   └─────────────┘
```

**适用场景**:
- 特定行业分析流程
- 多数据源融合
- 需要特定计算逻辑

---

### 1.2 Block 功能矩阵与组合建议

| Block 名称 | 功能 | 输入 | 输出 | 最佳组合下游 |
|-----------|------|------|------|-------------|
| **Data Loader** | 多源数据加载 | 文件路径/DB配置 | data_table | NL-to-SQL, Exploration Agent |
| **NL-to-SQL** | 自然语言→SQL | data_table + 指令 | result_table + SQL | Chart Recommender, Statistical Analyzer |
| **NL-to-Pandas** | 自然语言→Python | data_table + 指令 | result_table + code | Chart Recommender (复杂计算场景) |
| **Chart Recommender** | AI 智能推荐图表 | data_table + 目标 | recommended_charts + 顶层字段 | Chart Generator (via `from_recommendations`) |
| **Chart Generator** | Vega-Lite 渲染 | data_table + 配置/推荐 | vega_spec + image | Report Generator, Chart Array Builder |
| **Exploration Agent** | 多轮自主探索 | data_table + 目标 | steps + charts + report | Report Generator (可选) |
| **Report Generator** | Markdown 报告 | charts + 目标 | markdown + 文件 | 最终输出 |
| **Statistical Analyzer** | 统计分析 | data_table | statistics + insights | Report Generator |
| **Data Extractor** | 非结构化提取 | 图像/文本/HTML | data_table | 任何需要 data_table 的 block |

---

## 二、类型兼容性验证与问题修复状态

### 2.1 已修复的问题

#### ✅ 问题 #1: Chart Generator 现在支持推荐输入

**修复前** (TYPE_COMPATIBILITY_ANALYSIS.md 中标记为 🔴 P0):
```yaml
# ❌ 无法直接连接
recommend#1 (recommended_charts: array) → chart#1 (chart_type: enum)
```

**修复后** ([chart-generator/__init__.py:36-55](tasks/chart-generator/__init__.py#L36-L55)):
```python
if from_recommendations:
    # Mode 2: Extract from recommendations
    selection_index = int(params.get("selection_index") or 0)
    recommendation = from_recommendations[selection_index]
    chart_type = recommendation.get("chart_type")
    x_field = recommendation.get("x_field")
    y_field = recommendation.get("y_field")
    # ...
```

**YAML 定义** ([chart-generator/task.oo.yaml:68-83](tasks/chart-generator/task.oo.yaml#L68-L83)):
```yaml
- handle: from_recommendations
  json_schema:
    type: array
    items:
      type: object
  nullable: true
  description: "Chart recommendations from Chart Recommender (will use first
    recommendation if provided)"

- handle: selection_index
  json_schema:
    type: number
  value: 0
  nullable: true
```

**验证结果**: ✅ Chart Generator 现在可以接受两种输入模式
- Mode 1: 直接指定字段 (`chart_type`, `x_field`, `y_field`)
- Mode 2: 从推荐数组提取 (`from_recommendations` + `selection_index`)

---

### 2.2 部分修复的问题

#### ⚠️ 问题 #2: Quick Analysis 仍使用 Scriptlet 桥接

**当前状态** ([quick-analysis/subflow.oo.yaml:144-185](subflows/quick-analysis/subflow.oo.yaml#L144-L185)):
```yaml
# Step 5: Build chart array for report
- node_id: build_array#1
  title: "Build Charts Array"
  icon: ":carbon:list-boxes:"
  task:
    inputs_def:
      - handle: chart_image
        json_schema:
          type: string
        nullable: false
      # ... 定义 inline task
    outputs_def:
      - handle: charts
        json_schema:
          type: array
          items:
            type: object
    executor:
      name: python
      options:
        entry: scriptlets/build_charts_array.py
  inputs_from:
    - handle: chart_image
      from_node:
        - node_id: chart#1
          output_handle: chart_image
    - handle: chart_title
      from_node:
        - node_id: recommend#1
          output_handle: chart_title
    - handle: chart_description
      from_node:
        - node_id: query#1
          output_handle: explanation
```

**Scriptlet 代码** ([scriptlets/build_charts_array.py](subflows/quick-analysis/scriptlets/build_charts_array.py)):
```python
async def main(params: Inputs, context: Context) -> Outputs:
    """Build a charts array from individual chart components"""
    chart_image = params.get("chart_image")
    chart_title = params.get("chart_title") or "Analysis Chart"
    chart_description = params.get("chart_description") or ""

    if not chart_image:
        raise ValueError("chart_image is required")

    charts = [
        {
            "title": chart_title,
            "image": chart_image,
            "description": chart_description
        }
    ]
    return {"charts": charts}
```

**问题分析**:
1. ✅ Scriptlet 功能正确 (合理的临时解决方案)
2. ⚠️ 但违反 "最小化 scriptlet" 的设计原则
3. ⚠️ Chart Array Builder block 仍存在 (但类型定义已修正)

**推荐改进**:
```yaml
# 方案 A: 直接使用 Chart Array Builder block
- node_id: array#1
  task: self::chart-array-builder
  inputs_from:
    - handle: charts    # ✅ 改为接受数组
      value:
        - title: "{from recommend#1.chart_title}"
          image: "{from chart#1.chart_image}"
          description: "{from query#1.explanation}"

# 方案 B: 让 Chart Generator 直接输出符合 Report Generator 格式
# (需要修改 Chart Generator 输出定义)
```

**优先级**: 🟡 P1 (功能正常,但可优化用户体验)

---

#### ⚠️ 问题 #3: Chart Recommender 顶层字段冗余

**当前设计** ([chart-recommender/task.oo.yaml:63-109](tasks/chart-recommender/task.oo.yaml#L63-L109)):
```yaml
outputs_def:
  - handle: recommended_charts
    json_schema:
      type: array
      items:
        type: object
        properties:
          chart_type: {enum: [bar, line, scatter, ...]}
          x_field: {type: string}
          y_field: {type: string}
          # ...

  # 重复输出顶层字段
  - group: Top Recommendation Fields
    collapsed: false

  - handle: chart_type
    json_schema: {enum: [bar, line, ...]}
    nullable: false

  - handle: x_field
    json_schema: {type: string}
    nullable: false

  # ... y_field, color_field, size_field, chart_title
```

**问题**:
- ❌ 数据冗余: 第一个推荐的字段被重复返回
- ❌ 维护负担: 修改推荐逻辑需要同步两处
- ⚠️ 但目前功能正常,已被 Chart Generator 的 Mode 2 规避

**修复状态**: 🟡 功能可用,但设计待优化

**推荐行动**:
```yaml
# 简化设计: 只返回数组
outputs_def:
  - handle: recommended_charts
    json_schema:
      type: array
      items:
        type: object
        properties:
          chart_type: {enum: [...]}
          x_field: {type: string}
          y_field: {type: string}
          color_field: {type: string, nullable: true}
          size_field: {type: string, nullable: true}
          reason: {type: string}
          priority: {type: number}

  # ❌ 删除所有顶层单独字段
```

**价值**:
- ✅ 代码简化 50%
- ✅ 类型定义更清晰
- ✅ 避免数据不一致

**优先级**: 🟠 P2 (低影响,可在重构时处理)

---

### 2.3 未发现的新问题

#### ✅ 验证 1: Data Loader → NL-to-SQL 连接

**Data Loader 输出** ([data-loader/task.oo.yaml:58-73](tasks/data-loader/task.oo.yaml#L58-L73)):
```yaml
outputs_def:
  - handle: data_table
    json_schema:
      type: object
      properties:
        columns:
          type: array
          items:
            type: string
        rows:
          type: array
          items:
            type: object
        schema:
          type: object
```

**NL-to-SQL 输入** ([nl-to-sql/task.oo.yaml:2-13](tasks/nl-to-sql/task.oo.yaml#L2-L13)):
```yaml
inputs_def:
  - handle: input_table
    description: Input table with data and schema
    json_schema:
      type: object
      properties:
        columns: {type: array}
        rows: {type: array}
        schema: {type: object}
```

**兼容性**: ✅ 完全匹配

---

#### ✅ 验证 2: Exploration Agent → Report Generator 连接

**Exploration Agent 输出** ([exploration-agent/task.oo.yaml:73-86](tasks/exploration-agent/task.oo.yaml#L73-L86)):
```yaml
- handle: chart_images
  json_schema:
    type: array
    items:
      type: object
      properties:
        title: {type: string}
        image: {type: string}
        description: {type: string}
```

**Report Generator 输入** ([report-generator/task.oo.yaml:2-15](tasks/report-generator/task.oo.yaml#L2-L15)):
```yaml
- handle: charts
  description: Array of chart objects with title, base64 image, and description
  json_schema:
    type: array
    items:
      type: object
      properties:
        title: {type: string}
        image: {type: string}
        description: {type: string}
```

**兼容性**: ✅ 完全匹配

**实际使用** ([smart-data-analysis/subflow.oo.yaml:94-97](subflows/smart-data-analysis/subflow.oo.yaml#L94-L97)):
```yaml
- node_id: report#1
  task: self::report-generator
  inputs_from:
    - handle: charts
      from_node:
        - node_id: explore#1
          output_handle: chart_images
```

---

#### ✅ 验证 3: Chart Recommender → Chart Generator 连接 (新)

**Chart Recommender 输出**:
```yaml
recommended_charts: array<{chart_type, x_field, y_field, color_field, size_field}>
```

**Chart Generator 输入**:
```yaml
from_recommendations: array<object>  # 接受推荐数组
```

**实际连接**:
```yaml
# ✅ Quick Analysis subflow 中
- node_id: chart#1
  task: self::chart-generator
  inputs_from:
    - handle: from_recommendations
      from_node:
        - node_id: recommend#1
          output_handle: recommended_charts
    - handle: selection_index
      value: 0
```

**代码验证** ([chart-generator/__init__.py:36-53](tasks/chart-generator/__init__.py#L36-L53)):
```python
if from_recommendations:
    selection_index = int(params.get("selection_index") or 0)

    if not isinstance(from_recommendations, list) or len(from_recommendations) == 0:
        raise ValueError("from_recommendations must be a non-empty array")

    if selection_index >= len(from_recommendations):
        raise ValueError(f"selection_index {selection_index} out of range")

    recommendation = from_recommendations[selection_index]
    chart_type = recommendation.get("chart_type")
    x_field = recommendation.get("x_field")
    y_field = recommendation.get("y_field")
    # ✅ 正确提取字段
```

**兼容性**: ✅ 已修复,功能正常

---

## 三、工作流组合最佳实践

### 3.1 推荐工作流配置

#### 配置 A: 快速分析 (生产环境推荐)

**场景**: 业务报表自动生成、每日数据监控

**配置**:
```yaml
# flows/production-quick-report/flow.oo.yaml
title: "Production Daily Report"

nodes:
  - node_id: load#1
    task: self::data-loader
    inputs_from:
      - handle: source_type
        value: mysql
      - handle: database_config
        value:
          host: "prod-db.company.com"
          database: "sales"
          query: "SELECT * FROM daily_sales WHERE date = CURRENT_DATE"

  - node_id: analyze#1
    subflow: self::quick-analysis
    inputs_from:
      - handle: data_file  # 实际接收 data_table
        from_node:
          - node_id: load#1
            output_handle: data_table
      - handle: analysis_question
        value: "Compare sales performance across regions"
      - handle: source_type
        value: csv  # 内部使用,可忽略
```

**优点**:
- ✅ 速度快 (30-60秒)
- ✅ 可预测结果
- ✅ 适合定时任务

---

#### 配置 B: 深度探索 (研究环境推荐)

**场景**: 月度业务分析、数据异常调查

**配置**:
```yaml
# flows/monthly-exploration/flow.oo.yaml
title: "Monthly Business Exploration"

nodes:
  - node_id: load#1
    task: self::data-loader
    inputs_from:
      - handle: source_type
        value: csv
      - handle: file_path
        value: "/oomol-driver/oomol-storage/monthly_data.csv"

  - node_id: explore#1
    subflow: self::smart-data-analysis
    inputs_from:
      - handle: data_file
        from_node:
          - node_id: load#1
            output_handle: data_table
      - handle: analysis_goal
        value: "Discover trends, anomalies, and actionable insights in monthly performance"
      - handle: max_iterations
        value: 5  # 更深入的探索
```

**优点**:
- ✅ 发现隐藏模式
- ✅ 自动生成多角度分析
- ✅ AI 驱动洞察

---

### 3.2 类型安全组合规则

#### 规则 1: 优先使用 Subflow

**原因**:
- ✅ 类型已验证
- ✅ 减少用户配置错误
- ✅ 一致的体验

**示例**:
```yaml
# ❌ 不推荐: 手动组合多个 blocks
nodes:
  - node_id: load#1
    task: self::data-loader
  - node_id: query#1
    task: self::nl-to-sql
  - node_id: recommend#1
    task: self::chart-recommender
  - node_id: chart#1
    task: self::chart-generator
  - node_id: report#1
    task: self::report-generator
# 5 个节点,容易出错

# ✅ 推荐: 使用 Subflow
nodes:
  - node_id: analyze#1
    subflow: self::quick-analysis
# 1 个节点,类型安全
```

---

#### 规则 2: 数据表传递标准

**所有输出 data_table 的 blocks 必须包含**:
```yaml
{
  "columns": ["col1", "col2", ...],        # 列名数组
  "rows": [{"col1": val, "col2": val}],   # 行数据
  "schema": {"col1": "int64", "col2": "object"}  # 类型信息
}
```

**当前合规 blocks**:
- ✅ Data Loader
- ✅ NL-to-SQL (result_table)
- ✅ NL-to-Pandas (result_table)
- ⚠️ Data Extractor (未测试)

---

#### 规则 3: Chart 对象传递标准

**所有传递给 Report Generator 的 charts 必须**:
```yaml
[
  {
    "title": "图表标题",
    "image": "base64_png_string",
    "description": "图表说明"
  }
]
```

**当前合规输出**:
- ✅ Exploration Agent (chart_images)
- ✅ Chart Generator + Scriptlet (quick-analysis)
- ⚠️ Chart Array Builder (类型定义已修正,但用法待优化)

---

## 四、类型问题优先级与修复路线图

### 4.1 问题优先级矩阵 (更新版)

| 问题编号 | 问题描述 | 修复状态 | 影响 | 优先级 | 预计时间 |
|---------|---------|---------|------|--------|---------|
| **#1** | Chart Recommender → Generator 断裂 | ✅ 已修复 | - | - | - |
| **#2** | Quick Analysis 使用 Scriptlet | ⚠️ 功能正常 | 用户体验 | 🟡 P1 | 2 小时 |
| **#3** | Chart Recommender 顶层字段冗余 | ⚠️ 设计待优化 | 维护成本 | 🟠 P2 | 2 小时 |
| **#4** | Chart Array Builder 类型混乱 | ✅ 已修正定义 | - | - | - |
| **#5** | Data table schema 字段缺失 | 🔍 待验证 | 潜在风险 | 🟠 P2 | 1 天 |

---

### 4.2 修复路线图 (Phase 2)

#### Phase 2.1: Subflow 优化 (Week 1)

**任务 1**: 重构 Quick Analysis 移除 Scriptlet
- 选项 A: 改造 Chart Array Builder 接受数组
- 选项 B: 让 Chart Generator 直接输出 Report 格式
- 推荐: 选项 A (侵入性更小)

**任务 2**: 简化 Chart Recommender 输出
- 移除顶层单独字段
- 只返回 `recommended_charts` 数组
- 更新所有依赖 flows

---

#### Phase 2.2: 类型系统标准化 (Week 2)

**任务 3**: 创建类型定义文件
```yaml
# types/standard_types.yaml
data_table:
  type: object
  properties:
    columns:
      type: array
      items: {type: string}
    rows:
      type: array
      items: {type: object}
    schema:
      type: object
  required: [columns, rows, schema]

chart_object:
  type: object
  properties:
    title: {type: string}
    image: {type: string}
    description: {type: string}
  required: [title, image, description]

llm_config:
  type: object
  properties:
    model: {type: string}
    temperature: {type: number}
    max_tokens: {type: number}
```

**任务 4**: 所有 blocks 引用标准类型
```yaml
- handle: data_table
  json_schema:
    $ref: "types/standard_types.yaml#/data_table"
```

---

#### Phase 2.3: 测试覆盖 (Week 3)

**任务 5**: 类型兼容性测试套件
```python
# tests/test_type_compatibility.py
def test_loader_to_sql():
    """Data Loader → NL-to-SQL 类型兼容性"""
    loader_output = run_block(DataLoader, test_inputs)
    sql_input = {"input_table": loader_output["data_table"]}
    assert validate_inputs(NLtoSQL, sql_input)

def test_recommender_to_generator():
    """Chart Recommender → Chart Generator 类型兼容性"""
    recommender_output = run_block(ChartRecommender, test_inputs)
    generator_input = {
        "data_table": test_table,
        "from_recommendations": recommender_output["recommended_charts"]
    }
    assert validate_inputs(ChartGenerator, generator_input)

def test_explore_to_report():
    """Exploration Agent → Report Generator 类型兼容性"""
    explore_output = run_block(ExplorationAgent, test_inputs)
    report_input = {
        "charts": explore_output["chart_images"],
        "analysis_goal": "Test"
    }
    assert validate_inputs(ReportGenerator, report_input)
```

---

## 五、用户指南与示例

### 5.1 快速上手: 3 分钟生成数据报告

**步骤 1: 准备数据**
```bash
# 上传 CSV 文件到 /oomol-driver/oomol-storage/sales_data.csv
```

**步骤 2: 创建 Flow**
```yaml
# flows/my-first-analysis/flow.oo.yaml
title: "My First Data Analysis"

nodes:
  - node_id: analyze#1
    subflow: self::quick-analysis
    inputs_from:
      - handle: data_file
        value: "/oomol-driver/oomol-storage/sales_data.csv"
      - handle: analysis_question
        value: "What are the top 5 products by revenue?"
      - handle: source_type
        value: csv
```

**步骤 3: 运行**
```python
task_id = runFlow("/path/to/flow.oo.yaml")
result = getTaskResult(task_id)
print(result["outputs"]["final_report"])  # Markdown 报告
```

**预期输出**:
- 📊 柱状图: Top 5 产品收入
- 📝 AI 生成分析报告
- ⏱️ 耗时: 30-60秒

---

### 5.2 高级用法: 自定义多轮探索

**场景**: 需要控制探索方向

**配置**:
```yaml
nodes:
  - node_id: load#1
    task: self::data-loader
    inputs_from:
      - handle: source_type
        value: csv
      - handle: file_path
        value: "/oomol-driver/oomol-storage/customer_data.csv"

  - node_id: explore#1
    task: self::exploration-agent
    inputs_from:
      - handle: input_table
        from_node:
          - node_id: load#1
            output_handle: data_table
      - handle: exploration_goal
        value: |
          Focus on:
          1. Customer segmentation patterns
          2. Churn risk indicators
          3. Revenue opportunities by segment
      - handle: max_iterations
        value: 5
      - handle: llm
        value:
          model: oomol-chat
          temperature: 0.2  # 更确定性的结果
          max_tokens: 128000

  - node_id: report#1
    task: self::report-generator
    inputs_from:
      - handle: charts
        from_node:
          - node_id: explore#1
            output_handle: chart_images
      - handle: analysis_goal
        value: "Customer Analytics Report"
```

---

## 六、总结与建议

### 6.1 当前状态评估

| 维度 | 评分 | 说明 |
|-----|------|------|
| 功能完整性 | ⭐⭐⭐⭐☆ (4/5) | 核心功能齐全,缺少数据质量检查 |
| 类型安全性 | ⭐⭐⭐⭐☆ (4/5) | 主要问题已修复,剩余优化项 |
| 用户体验 | ⭐⭐⭐☆☆ (3/5) | Subflow 易用,但需更多文档 |
| 维护成本 | ⭐⭐⭐☆☆ (3/5) | 有设计债务 (顶层字段冗余等) |

---

### 6.2 核心优势

✅ **已实现的价值**:
1. **AI 驱动**: 自然语言交互,无需 SQL/Python
2. **端到端**: 从数据加载到报告生成全自动
3. **灵活组合**: Blocks 可按需组装
4. **类型安全**: 主要连接点已验证

---

### 6.3 关键改进建议

#### 建议 1: 完善文档 (P0)
- [ ] 为每个 Subflow 添加使用示例
- [ ] 创建 "常见分析场景" cookbook
- [ ] 添加类型兼容性矩阵图

#### 建议 2: 优化 Quick Analysis (P1)
- [ ] 移除 Scriptlet,改用 Chart Array Builder
- [ ] 或简化为 3 节点: Load → Explore (1 轮) → Report

#### 建议 3: 增强错误提示 (P1)
- [ ] 类型不匹配时,给出具体修复建议
- [ ] 如: "chart_type 需要 enum,但收到 array,是否想用 from_recommendations?"

#### 建议 4: 创建类型测试 (P2)
- [ ] 自动化验证所有 block 连接
- [ ] CI/CD 集成,防止回归

---

### 6.4 未来方向

**短期 (1 个月)**:
- 修复剩余类型优化项 (P1-P2)
- 完善文档和示例
- 添加数据质量检查 block

**中期 (3 个月)**:
- 支持更多数据源 (API, S3, BigQuery)
- 实时数据分析 (流式处理)
- 协作功能 (共享分析模板)

**长期 (6 个月)**:
- AI 自动调优 (学习用户偏好)
- 预测性分析 (机器学习集成)
- 企业级功能 (权限管理, 审计日志)

---

## 附录: 类型定义速查表

### A. 标准类型定义

```yaml
# data_table (完整定义)
type: object
properties:
  columns:
    type: array
    items: {type: string}
  rows:
    type: array
    items: {type: object}
  schema:
    type: object
    # 示例: {"col1": "int64", "col2": "object", "date": "datetime64"}
required: [columns, rows, schema]

# chart_object
type: object
properties:
  title: {type: string}
  image: {type: string}  # Base64 PNG
  description: {type: string}
required: [title, image, description]

# chart_recommendation
type: object
properties:
  chart_type: {enum: [bar, line, scatter, area, pie, heatmap]}
  x_field: {type: string}
  y_field: {type: string}
  color_field: {type: string, nullable: true}
  size_field: {type: string, nullable: true}
  reason: {type: string}
  priority: {type: number}
```

---

### B. Block I/O 快速参考

| Block | 主要输入 | 主要输出 | 类型注意事项 |
|-------|---------|---------|-------------|
| Data Loader | file_path / db_config | data_table (完整) | ✅ 包含 schema |
| NL-to-SQL | input_table + instruction | result_table | ✅ 保留 schema |
| Chart Recommender | data_table + goal | recommended_charts (array) | ⚠️ 顶层字段冗余 |
| Chart Generator | data_table + config/recommendations | vega_spec + chart_image | ✅ 支持两种模式 |
| Exploration Agent | input_table + goal | chart_images (array) | ✅ 直接兼容 Report |
| Report Generator | charts (array) + goal | markdown_report | ✅ 接受标准 chart_object |

---

**报告生成时间**: 2026-01-22
**分析人**: Claude Code
**版本**: v1.0
**下一步**: 执行 Phase 2 优化任务,完善文档
