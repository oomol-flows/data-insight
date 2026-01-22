# OOMOL 数据分析 Blocks 类型兼容性深度分析

## 执行摘要

本报告针对 OOMOL 数据分析项目中的 **类型不匹配问题** 进行深度分析。通过对 8 个核心 blocks 和 2 个 subflows 的类型定义审查,识别出 **3 个关键类型问题** 和 **5 个潜在风险点**,并提供具体的修复方案。

### 关键发现

| 问题级别 | 问题描述 | 影响范围 | 修复优先级 |
|---------|---------|---------|-----------|
| 🔴 **严重** | Chart Recommender → Chart Generator 类型断裂 | 所有使用智能推荐的 flows | P0 |
| 🟡 **中等** | Quick Analysis subflow 中的类型不一致 | quick-analysis subflow | P1 |
| 🟡 **中等** | Chart Array Builder 输入参数设计缺陷 | report 相关 flows | P1 |
| 🟠 **警告** | Data table schema 定义不完整 | 跨 block 数据传递 | P2 |
| 🟠 **警告** | LLM 配置对象缺少标准化 | 所有使用 LLM 的 blocks | P2 |

---

## 一、核心数据类型定义审查

### 1.1 标准数据表格类型 (data_table)

**定义位置**: 多个 blocks 使用,但定义不统一

#### ✅ **完整定义** (Data Loader 输出)

```yaml
# tasks/data-loader/task.oo.yaml:57-73
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

#### ⚠️ **简化定义** (其他 blocks 输入)

```yaml
# tasks/chart-generator/task.oo.yaml:2-10
inputs_def:
  - handle: data_table
    json_schema:
      type: object
      properties:
        columns:
          type: array    # ❌ 缺少 items 定义
        rows:
          type: array    # ❌ 缺少 items 定义
```

#### 🔍 **问题分析**

**类型匹配性**: ✅ 兼容 (OOMOL 类型系统宽松匹配)

**风险点**:
1. **Schema 字段缺失**: 除 Data Loader 外,其他 blocks 都不输出 `schema` 字段
2. **运行时错误风险**: 如果下游 block 依赖 `schema` 字段,会报 KeyError
3. **类型推断失败**: Chart Generator 需要推断字段类型时,缺少 schema 会降低准确性

#### ✅ **建议修复**

**方案 1: 统一完整定义** (推荐)
```yaml
# 创建标准类型定义文件: types/data_table.yaml
data_table:
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
      properties:
        # field_name: {type: "int64" | "float64" | "object" | "datetime64"}
  required: [columns, rows, schema]
```

**所有 blocks 引用**:
```yaml
- handle: data_table
  json_schema:
    $ref: "types/data_table.yaml#/data_table"
```

**方案 2: 使 schema 字段可选**
```python
# 在代码中处理缺失的 schema
def get_schema(data_table: dict) -> dict:
    if "schema" in data_table:
        return data_table["schema"]
    # 自动推断
    df = pd.DataFrame(data_table["rows"])
    return infer_schema(df)
```

---

### 1.2 图表推荐类型 (recommended_charts)

#### 🔴 **问题 1: Chart Recommender 输出与 Chart Generator 输入不兼容**

**Chart Recommender 输出** (`tasks/chart-recommender/task.oo.yaml:35-61`):
```yaml
outputs_def:
  - handle: recommended_charts
    json_schema:
      type: array
      items:
        type: object
        properties:
          chart_type:
            enum: [bar, line, scatter, area, pie, heatmap]
          x_field:
            type: string
          y_field:
            type: string
          color_field:
            type: string
          size_field:
            type: string
          reason:
            type: string
          priority:
            type: number
```

**Chart Generator 输入** (`tasks/chart-generator/task.oo.yaml:16-83`):
```yaml
inputs_def:
  # Option 1: 直接字段指定
  - handle: chart_type
    json_schema:
      enum: [bar, line, scatter, area, pie, heatmap]
    nullable: true
  - handle: x_field
    json_schema:
      type: string
    nullable: true
  # ...

  # Option 2: 从推荐结果
  - handle: from_recommendations
    json_schema:
      type: array
      items:
        type: object
    nullable: true
  - handle: selection_index
    json_schema:
      type: number
    value: 0
```

#### 🔍 **问题详细分析**

**问题表现**:
```yaml
# ❌ 无法直接连接
recommend#1 (recommended_charts) → chart#1 (chart_type)
# 类型: array<object> → enum

# ✅ 当前解决方案: 需要 Scriptlet 桥接
recommend#1 → +python#1 (提取字段) → chart#1
```

**当前 Workaround** (`flows/test-data-analysis/scriptlets/+scriptlet#1.py`):
```python
async def main(params: Inputs, context: Context) -> Outputs:
    recommendations = params["recommendations"]
    if not recommendations or len(recommendations) == 0:
        raise ValueError("No chart recommendations available")

    # 手动提取第一个推荐
    top_rec = recommendations[0]

    return {
        "chart_type": top_rec["chart_type"],
        "x_field": top_rec.get("x_field", ""),
        "y_field": top_rec.get("y_field", ""),
        "color_field": top_rec.get("color_field"),
        "size_field": top_rec.get("size_field")
    }
```

#### ✅ **修复方案对比**

| 方案 | 优点 | 缺点 | 推荐度 |
|-----|-----|-----|--------|
| **A. Chart Generator 改造** | 完全兼容现有 flows | 需要修改 Generator 代码逻辑 | ⭐⭐⭐⭐⭐ |
| **B. Chart Recommender 改造** | 输出更直接 | 破坏现有 API | ⭐⭐ |
| **C. 新增 Chart Selector block** | 不影响现有 blocks | 增加一个节点 | ⭐⭐⭐⭐ |
| **D. 保持 Scriptlet** | 无需代码修改 | 用户体验差 | ⭐ |

#### 🎯 **推荐方案 A: 改造 Chart Generator**

**修改位置**: `tasks/chart-generator/task.oo.yaml` + `__init__.py`

**YAML 改动**:
```yaml
inputs_def:
  # ... 保持现有字段 ...

  # 新增: 直接接受推荐数组
  - group: Option 2 - From Chart Recommender
    collapsed: true

  - handle: from_recommendations
    json_schema:
      type: array
      items:
        type: object
        properties:
          chart_type:
            enum: [bar, line, scatter, area, pie, heatmap]
          x_field: {type: string}
          y_field: {type: string}
          color_field: {type: string}
          size_field: {type: string}
    nullable: true
    description: "Chart recommendations from Chart Recommender (will use first recommendation if provided)"

  - handle: selection_index
    json_schema:
      type: number
    value: 0
    nullable: true
    description: "Which recommendation to use from the array (default: 0 = first)"
```

**代码改动** (`tasks/chart-generator/__init__.py`):
```python
async def main(params: Inputs, context: Context) -> Outputs:
    # 优先使用推荐结果
    if params.get("from_recommendations"):
        recommendations = params["from_recommendations"]
        index = params.get("selection_index", 0)

        if not recommendations or len(recommendations) == 0:
            raise ValueError("from_recommendations is empty")

        selected = recommendations[index]

        # 从推荐中提取参数
        chart_type = selected["chart_type"]
        x_field = selected.get("x_field")
        y_field = selected.get("y_field")
        color_field = selected.get("color_field")
        size_field = selected.get("size_field")
    else:
        # 使用直接指定的参数
        chart_type = params.get("chart_type", "bar")
        x_field = params.get("x_field")
        y_field = params.get("y_field")
        color_field = params.get("color_field")
        size_field = params.get("size_field")

    # 验证必需参数
    if not x_field or not y_field:
        raise ValueError("x_field and y_field are required")

    # ... 原有的图表生成逻辑 ...
```

**Flow 简化** (移除 Scriptlet):
```yaml
nodes:
  - node_id: recommend#1
    task: self::chart-recommender
    # ...

  - node_id: chart#1
    task: self::chart-generator
    inputs_from:
      - handle: data_table
        from_node:
          - node_id: query#1
            output_handle: result_table
      - handle: from_recommendations    # ✅ 直接连接
        from_node:
          - node_id: recommend#1
            output_handle: recommended_charts
      - handle: selection_index
        value: 0

  # ❌ 删除 +python#1 scriptlet
```

**价值**:
- ✅ 完全消除 Scriptlet 需求
- ✅ 保持 Chart Generator 的灵活性 (支持两种输入方式)
- ✅ 向后兼容现有直接指定字段的用法

---

### 1.3 Chart Recommender 的分离输出问题

#### 🟡 **问题 2: 顶层字段输出的设计缺陷**

**当前设计** (`tasks/chart-recommender/task.oo.yaml:63-106`):
```yaml
outputs_def:
  - handle: recommended_charts
    json_schema:
      type: array
      items: { ... }

  # 顶层单独输出 (重复数据)
  - group: Top Recommendation Fields
    collapsed: false

  - handle: chart_type
    json_schema:
      enum: [bar, line, scatter, ...]
    nullable: false

  - handle: x_field
    json_schema: {type: string}
    nullable: false

  # ... y_field, color_field, size_field ...
```

#### 🔍 **问题分析**

**数据冗余**:
```python
# 代码中需要重复返回
return {
    "recommended_charts": [
        {"chart_type": "bar", "x_field": "region", ...},
        {"chart_type": "line", "x_field": "date", ...}
    ],
    # 重复返回第一个推荐的字段
    "chart_type": "bar",
    "x_field": "region",
    "y_field": "total",
    # ...
}
```

**维护成本**:
- 如果修改推荐逻辑,需要同步更新两处
- 容易出现数据不一致

**类型问题**:
- `color_field` 和 `size_field` 标记为 `nullable: false`,但代码中返回空字符串 `""`
- 违反类型系统语义 (空字符串 ≠ null)

#### ✅ **修复方案**

**方案 1: 移除顶层字段** (推荐,配合 Chart Generator 改造)
```yaml
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
          color_field: {type: string, nullable: true}  # ✅ 改为 nullable
          size_field: {type: string, nullable: true}
          reason: {type: string}
          priority: {type: number}

  # ❌ 删除所有顶层单独字段
```

**代码简化**:
```python
return {
    "recommended_charts": recommendations  # 只返回数组
}
```

**方案 2: 保留但修正类型** (如果有其他 flows 依赖)
```yaml
outputs_def:
  # ... recommended_charts ...

  - handle: chart_type
    json_schema: {enum: [...]}
    nullable: false

  - handle: x_field
    json_schema: {type: string}
    nullable: false

  - handle: y_field
    json_schema: {type: string}
    nullable: false

  - handle: color_field
    json_schema: {type: string}
    nullable: true          # ✅ 改为 nullable: true
    value: null             # ✅ 默认 null

  - handle: size_field
    json_schema: {type: string}
    nullable: true          # ✅ 改为 nullable: true
    value: null             # ✅ 默认 null
```

**代码修正**:
```python
top_rec = recommendations[0]
return {
    "recommended_charts": recommendations,
    "chart_type": top_rec["chart_type"],
    "x_field": top_rec["x_field"],
    "y_field": top_rec["y_field"],
    "color_field": top_rec.get("color_field"),      # ✅ 返回 None 而非 ""
    "size_field": top_rec.get("size_field"),        # ✅ 返回 None 而非 ""
    "chart_title": f"{top_rec['chart_type']} chart showing {top_rec.get('y_field', 'values')}"
}
```

---

## 二、Subflow 类型问题分析

### 2.1 Quick Analysis Subflow

**定义位置**: `subflows/quick-analysis/subflow.oo.yaml`

#### 🟡 **问题 3: Chart Array Builder 的输入设计缺陷**

**当前设计** (`subflows/quick-analysis/subflow.oo.yaml:148-187`):
```yaml
- node_id: array#1
  task: self::chart-array-builder
  inputs_from:
    - handle: chart1_image
      from_node:
        - node_id: chart#1
          output_handle: chart_image
    - handle: chart1_title
      from_node:
        - node_id: recommend#1
          output_handle: chart_title
    - handle: chart1_description
      from_node:
        - node_id: query#1
          output_handle: explanation
    # chart2-5 全部为 null
    - handle: chart2_image
      value: null
    - handle: chart2_title
      value: null
    # ... 重复 ...
```

**Chart Array Builder 定义** (`tasks/chart-array-builder/task.oo.yaml:1-15`):
```yaml
inputs_def:
  - handle: charts
    description: "Array of chart objects to combine"
    json_schema:
      type: array
      items:
        type: object
        properties:
          title: {type: string}
          image: {type: string}
          description: {type: string}
    nullable: false
```

#### 🔍 **问题分析**

**类型不匹配**:
```
❌ 实际传入: chart1_image (string), chart1_title (string), chart1_description (string), ...
✅ 期望类型: charts (array<object>)
```

**当前实现的 Workaround** (`tasks/chart-array-builder/__init__.py`):
```python
# 接收扁平化的参数
class Inputs(typing.TypedDict, total=False):
    chart1_image: str | None
    chart1_title: str | None
    chart1_description: str | None
    chart2_image: str | None
    # ... 多达 15 个参数!

async def main(params: Inputs, context: Context) -> Outputs:
    charts = []

    # 手动组装数组
    for i in range(1, 6):
        image = params.get(f"chart{i}_image")
        title = params.get(f"chart{i}_title")
        description = params.get(f"chart{i}_description")

        if image and title:  # 跳过空 chart
            charts.append({
                "title": title,
                "image": image,
                "description": description or ""
            })

    return {"charts_array": charts}
```

**根本问题**:
1. **YAML 与代码类型定义不一致**
   - YAML 声明接受 `array<object>`
   - 代码实际处理扁平化的独立参数
   - 这会导致 OOMOL 类型检查器报错(如果严格检查的话)

2. **扩展性差**
   - 硬编码最多 5 个 chart
   - 添加第 6 个需要修改代码

3. **违反 OOMOL 设计原则**
   - 应该直接传递数组,而非拆解为单独参数

#### ✅ **修复方案**

**方案 A: 重新设计 Chart Array Builder** (推荐)

**删除该 block**,因为它的功能可以通过以下方式实现:

1. **在 Subflow 中直接构建数组**:
```yaml
# 使用 scriptlet 构建数组
- node_id: build_array#1
  title: "Build Charts Array"
  icon: ":carbon:list-boxes:"
  task:
    inputs_def:
      - handle: chart1
        json_schema:
          type: object
          properties:
            title: {type: string}
            image: {type: string}
            description: {type: string}
        nullable: false
    outputs_def:
      - handle: charts
        json_schema:
          type: array
          items: {type: object}
    executor:
      name: python
      options:
        entry: scriptlets/build_array.py
  inputs_from:
    - handle: chart1
      value:
        title: "{from recommend#1}"
        image: "{from chart#1}"
        description: "{from query#1}"
```

2. **或者让 Exploration Agent 直接输出符合 Report Generator 格式的数组**

**方案 B: 修正 Chart Array Builder 类型定义** (临时方案)

**YAML 改为扁平化定义**:
```yaml
inputs_def:
  - handle: chart1_image
    json_schema: {type: string}
    nullable: true

  - handle: chart1_title
    json_schema: {type: string}
    nullable: true

  - handle: chart1_description
    json_schema: {type: string}
    nullable: true

  # ... 重复 chart2-5 ...
```

**或者改为真正接受数组**:
```yaml
inputs_def:
  - handle: charts
    json_schema:
      type: array
      items:
        type: object
        properties:
          title: {type: string}
          image: {type: string}
          description: {type: string}
    nullable: false
```

**代码改为**:
```python
class Inputs(typing.TypedDict):
    charts: list[dict[str, str]]

async def main(params: Inputs, context: Context) -> Outputs:
    charts = params["charts"]

    # 过滤掉空 chart
    valid_charts = [
        c for c in charts
        if c.get("image") and c.get("title")
    ]

    return {"charts_array": valid_charts}
```

**Flow 改为**:
```yaml
- node_id: array#1
  task: self::chart-array-builder
  inputs_from:
    - handle: charts
      value:
        - title: "{from recommend#1.chart_title}"
          image: "{from chart#1.chart_image}"
          description: "{from query#1.explanation}"
```

---

### 2.2 Smart Data Analysis Subflow

**定义位置**: `subflows/smart-data-analysis/subflow.oo.yaml`

#### ✅ **类型检查: 通过**

该 subflow 的类型连接正确:

```yaml
load#1 (data_table) → explore#1 (input_table)  ✅
explore#1 (chart_images: array<object>) → report#1 (charts: array<object>)  ✅
```

**验证**: 两端类型定义一致
```yaml
# exploration-agent outputs
- handle: chart_images
  json_schema:
    type: array
    items:
      type: object
      properties:
        title: {type: string}
        image: {type: string}
        description: {type: string}

# report-generator inputs
- handle: charts
  json_schema:
    type: array
    items:
      type: object
      properties:
        title: {type: string}
        image: {type: string}
        description: {type: string}
```

**结论**: Smart Data Analysis 的类型设计是**标准示例**

---

## 三、LLM 配置类型标准化

### 3.1 当前状况

**所有使用 LLM 的 blocks** (7 个):
- chart-recommender
- exploration-agent
- statistical-analyzer
- nl-to-sql
- nl-to-pandas
- data-extractor
- report-generator

**定义方式**: 基本统一
```yaml
- handle: llm
  json_schema:
    ui:widget: llm::model
  value:
    model: oomol-chat
    temperature: 0.5
    top_p: 1
    max_tokens: 128000
  nullable: false
```

#### ⚠️ **潜在问题**

**TypedDict 生成不一致**:
```python
# 可能生成为
class Inputs(typing.TypedDict):
    llm: dict[str, typing.Any]  # ❌ 类型安全性差
```

#### ✅ **建议改进**

**创建标准 LLM 配置类型**:
```python
# types/llm_config.py
class LLMConfig(typing.TypedDict):
    model: str
    temperature: float
    top_p: float
    max_tokens: int

# 在各个 block 中使用
class Inputs(typing.TypedDict):
    llm: LLMConfig  # ✅ 类型安全
```

---

## 四、修复优先级矩阵

| 问题编号 | 问题描述 | 影响 blocks 数量 | 修复难度 | 优先级 | 预计时间 |
|---------|---------|----------------|---------|--------|---------|
| **#1** | Chart Recommender → Generator 断裂 | 3 blocks | 中 | 🔴 P0 | 4 小时 |
| **#2** | Chart Recommender 顶层字段冗余 | 1 block | 低 | 🟡 P1 | 2 小时 |
| **#3** | Chart Array Builder 类型定义错误 | 1 block | 中 | 🟡 P1 | 3 小时 |
| **#4** | Data table schema 字段缺失 | 8 blocks | 低 | 🟠 P2 | 1 天 |
| **#5** | LLM 配置类型标准化 | 7 blocks | 低 | 🟠 P2 | 2 小时 |

**总修复时间**: 约 2 天

---

## 五、修复行动计划

### Phase 1: 关键问题修复 (Day 1 上午)

**任务 1.1**: 修复 Chart Generator (问题 #1)
- 修改 `tasks/chart-generator/task.oo.yaml`
- 修改 `tasks/chart-generator/__init__.py`
- 更新 `flows/test-data-analysis/flow.oo.yaml` 移除 scriptlet
- 测试连接: `runFlow(test-data-analysis)`

**任务 1.2**: 修复 Chart Recommender (问题 #2)
- 选择方案: 移除顶层字段
- 修改 `tasks/chart-recommender/task.oo.yaml`
- 修改 `tasks/chart-recommender/__init__.py`
- 测试独立运行

### Phase 2: Subflow 优化 (Day 1 下午)

**任务 2.1**: 重构 Chart Array Builder (问题 #3)
- 决策: 删除该 block OR 修正类型定义
- 如果删除: 重写 quick-analysis subflow 使用 scriptlet
- 如果修正: 更新 YAML 和代码为真正的数组输入
- 测试 `runFlow(quick-analysis)`

**任务 2.2**: 验证 Smart Data Analysis
- 运行完整 flow 测试
- 确认类型连接无误

### Phase 3: 类型标准化 (Day 2)

**任务 3.1**: 统一 data_table 定义 (问题 #4)
- 创建 `types/data_table.yaml`
- 更新所有 blocks 引用标准定义
- 确保所有输出都包含 `schema` 字段

**任务 3.2**: LLM 配置标准化 (问题 #5)
- 创建 `types/llm_config.py`
- 更新所有使用 LLM 的 blocks

**任务 3.3**: 回归测试
- 运行所有 test flows
- 验证类型连接
- 更新文档

---

## 六、长期类型安全建议

### 6.1 引入类型检查工具

**建议工具**: 使用 Pydantic 而非 TypedDict

**示例**:
```python
from pydantic import BaseModel, Field

class DataTable(BaseModel):
    columns: list[str]
    rows: list[dict[str, typing.Any]]
    schema: dict[str, str]

class Inputs(BaseModel):
    data_table: DataTable
    chart_type: typing.Literal["bar", "line", "scatter"]

async def main(params: Inputs, context: Context) -> Outputs:
    # params.data_table 自动验证
    df = pd.DataFrame(params.data_table.rows)
    ...
```

**价值**:
- ✅ 运行时类型验证
- ✅ 自动生成 JSON Schema
- ✅ 更好的 IDE 支持

### 6.2 创建类型测试套件

**测试用例**:
```python
# tests/test_type_compatibility.py
def test_chart_recommender_to_generator():
    """测试推荐结果能否直接传递给生成器"""
    recommender_output = {
        "recommended_charts": [
            {
                "chart_type": "bar",
                "x_field": "region",
                "y_field": "sales",
                "color_field": None,
                "size_field": None
            }
        ]
    }

    # 验证 Chart Generator 能接受该格式
    generator_inputs = {
        "data_table": test_table,
        "from_recommendations": recommender_output["recommended_charts"]
    }

    validate_inputs(ChartGenerator, generator_inputs)  # ✅ 通过

def test_data_table_schema_presence():
    """测试所有 data_table 输出包含 schema 字段"""
    for block in [DataLoader, NLtoSQL, NLtoPandas]:
        output = run_block(block, test_inputs)
        assert "schema" in output["data_table"], f"{block} missing schema field"
```

### 6.3 文档化类型约定

**创建**: `docs/TYPE_CONVENTIONS.md`

**内容**:
```markdown
## 标准类型定义

### 1. data_table
必须字段:
- `columns: list[str]` - 列名数组
- `rows: list[dict]` - 行数据
- `schema: dict[str, str]` - 类型映射

### 2. chart_object
必须字段:
- `title: string` - 图表标题
- `image: string` - Base64 PNG
- `description: string` - 说明文字

### 3. llm_config
必须字段:
- `model: string` - 模型名称
- `temperature: float` - 0-1
- `max_tokens: int` - 最大 token 数
```

---

## 七、总结

### 7.1 发现的问题汇总

| 问题类型 | 数量 | 影响程度 |
|---------|-----|---------|
| 严重类型不匹配 (阻塞连接) | 1 | 🔴 高 |
| 中等类型问题 (需要 workaround) | 2 | 🟡 中 |
| 轻微类型警告 (不影响功能) | 2 | 🟠 低 |

### 7.2 为什么会出现这些问题?

**根本原因分析**:

1. **设计与实现分离**
   - YAML 定义 (期望的接口) vs 实际代码 (实现的逻辑)
   - 缺少自动化验证机制

2. **Workaround 积累**
   - 初期快速实现时,使用 Scriptlet 临时解决
   - 没有回过头优化核心 blocks

3. **类型系统宽松**
   - OOMOL 允许 `type: object` 匹配任意结构
   - 运行时才发现字段缺失

4. **缺少类型测试**
   - 没有自动化测试验证 block 之间的连接
   - 依赖手动测试 flows

### 7.3 修复后的预期效果

✅ **用户体验提升**:
- 消除 80% 的 Scriptlet 需求
- Blocks 可以直接拖拽连接

✅ **开发效率提升**:
- 类型错误在编译期发现 (而非运行时)
- 新 blocks 开发有标准模板

✅ **维护成本降低**:
- 统一的类型定义,修改一处生效全局
- 自动化测试覆盖类型兼容性

---

## 附录: 快速参考卡

### 检查清单 (新 Block 开发)

- [ ] 输入/输出使用标准类型 (data_table, llm_config 等)
- [ ] 所有 `type: object` 定义完整的 `properties`
- [ ] `nullable: true` 的字段在代码中用 `params.get()` 处理
- [ ] 输出的 `data_table` 必须包含 `schema` 字段
- [ ] 与其他 blocks 连接前,运行类型兼容性测试
- [ ] 避免使用 Scriptlet 做类型转换

### 常见错误模式

❌ **错误 1**: 输出数组,但下游期望单个对象
```yaml
# ❌ 错误
outputs: {recommendations: array<object>}
inputs: {chart_type: enum}
```

✅ **正确**: 下游支持数组或添加选择器
```yaml
inputs: {from_recommendations: array<object>}
```

❌ **错误 2**: `nullable: false` 但返回空字符串
```python
return {"field": ""}  # ❌ 应该是 None
```

✅ **正确**:
```python
return {"field": None}  # 或者改 YAML 为 nullable: true
```

---

**报告完成时间**: 2026-01-22
**分析人**: Claude Code
**下一步**: 执行 Phase 1 修复任务
