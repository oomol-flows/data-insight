# OOMOL 数据分析 Blocks 组合能力分析报告

## 一、现状概览

### 1.1 已实现的 8 个核心 Blocks

根据代码分析，项目已完成 Data Formulator 指导文档中规划的全部 8 个核心 blocks：

| Block 名称 | 功能定位 | 实现状态 | 关键能力 |
|-----------|---------|---------|----------|
| **Data Loader** | 数据源接入 | ✅ 完成 | CSV/Excel/JSON 加载 + Schema 推断 |
| **Data Extractor** | 非结构化数据提取 | ✅ 完成 | 图像/文本/HTML → 表格数据 |
| **NL-to-SQL** | 自然语言转 SQL | ✅ 完成 | DuckDB + 类型安全 + 预览增强 |
| **NL-to-Pandas** | 自然语言转 Python | ✅ 完成 | 沙盒执行 + 自动修复 |
| **Chart Recommender** | 智能图表推荐 | ✅ 完成 | 数据特征分析 + AI 推荐 |
| **Chart Generator** | 可视化生成 | ✅ 完成 | Vega-Lite + 6 种图表类型 |
| **Report Generator** | 报告生成 | ✅ 完成 | Markdown + 图表嵌入 |
| **Exploration Agent** | 自主探索分析 | ✅ 完成 | 多轮迭代 + 洞察生成 |

### 1.2 当前可用的数据分析能力

基于现有 blocks，用户可以完成的分析任务：

#### ✅ **已支持的典型场景**

1. **基础数据分析流程**
   - 加载数据 → SQL 转换 → 图表展示
   - 示例：销售数据按区域聚合并可视化
   - 参考：`flows/test-data-analysis/`

2. **非结构化数据处理**
   - 图片/文本 → 结构化表格 → 分析
   - 示例：截图中的表格数据提取
   - 参考：`flows/test-data-extractor/`

3. **复杂数据转换**
   - Pandas 代码生成（ML、统计分析）
   - 示例：计算百分比变化、移动平均
   - 参考：`tasks/nl-to-pandas/`

4. **自动化报告生成**
   - 多图表整合 → AI 生成报告
   - 示例：销售绩效分析报告
   - 参考：`flows/test-report-generator/`

5. **自主数据探索**
   - 多轮迭代分析 → 自动发现洞察
   - 示例：客户行为模式探索
   - 参考：`tasks/exploration-agent/`

---

## 二、当前组合能力评估

### 2.1 核心数据流路径分析

通过对现有 flows 的分析，识别出以下 **5 种主要数据流路径**：

#### 路径 1: 快速数据查询与可视化
```
Data Loader → NL-to-SQL → Chart Generator
```
**优势**:
- ✅ 最短路径，适合快速洞察
- ✅ SQL 执行效率高，适合大数据聚合
- ✅ 类型安全，自动转换 Pandas ↔ DuckDB

**局限**:
- ❌ 仅支持 SQL 能力范围内的操作（JOIN、聚合、过滤）
- ❌ 无法进行复杂的机器学习或统计分析

**应用场景**: BI 类分析（销售报表、KPI 仪表盘）

---

#### 路径 2: 复杂数据转换管道
```
Data Loader → NL-to-Pandas → Chart Generator
```
**优势**:
- ✅ 支持复杂 Pandas 操作（merge、pivot、滚动窗口）
- ✅ 可调用 numpy、sklearn 库
- ✅ 沙盒安全执行 + 自动错误修复

**局限**:
- ❌ 执行速度慢于 SQL（特别是大数据集）
- ❌ 需要 LLM 生成正确的 Python 代码（依赖 prompt 质量）

**应用场景**: 数据科学分析（特征工程、趋势预测）

---

#### 路径 3: 非结构化数据分析
```
Data Extractor → NL-to-SQL/Pandas → Chart Generator
```
**优势**:
- ✅ 支持图像、文本、网页等非传统数据源
- ✅ 视觉模型提取 + LLM 理解

**局限**:
- ❌ 提取准确度依赖 LLM 能力（可能出现格式错误）
- ❌ 缺少置信度阈值过滤机制

**应用场景**: OCR 数据分析、爬虫数据清洗

---

#### 路径 4: 智能推荐驱动的可视化
```
Data Loader → NL-to-SQL → Chart Recommender → Chart Generator
```
**优势**:
- ✅ 自动选择最佳图表类型
- ✅ 数据特征驱动（字段类型、基数分析）

**局限**:
- ❌ Chart Recommender 输出与 Chart Generator 输入**类型不匹配**
  - Recommender 输出包含 `chart_type`, `x_field`, `y_field` 等字段
  - Generator 需要从推荐结果中手动提取参数
  - **当前需要 Scriptlet 作为桥接层**（见 `flows/test-data-analysis/scriptlets/+scriptlet#1.py`）

**问题**: 这是一个 **架构设计缺陷**，应该优化

---

#### 路径 5: 端到端自动化分析
```
Data Loader → Exploration Agent → Report Generator
```
**优势**:
- ✅ 完全自主，用户只需提供目标
- ✅ 多轮迭代自动调整分析策略

**局限**:
- ❌ 黑盒操作，用户难以干预
- ❌ 执行时间长（多轮 LLM 调用）
- ❌ **Exploration Agent 未实际使用 Chart Generator**
  - 当前实现中，agent 内部自行生成图表
  - 未复用 Chart Generator 的能力（代码重复）

**问题**: 这也是一个 **模块化设计问题**

---

### 2.2 关键架构问题诊断

#### 🚨 **问题 1: Chart Recommender → Chart Generator 连接断裂**

**现状**:
从 `flows/test-data-analysis/flow.oo.yaml` 可以看到，需要一个 Scriptlet (`+python#1`) 来转换数据格式：

```yaml
# 推荐器输出格式
recommended_charts: [
  {
    chart_type: "bar",
    x_field: "region",
    y_field: "total",
    reason: "...",
    priority: 1
  }
]

# 生成器需要的输入格式
# 需要手动拆解为独立参数：
chart_type: "bar"
x_field: "region"
y_field: "total"
```

**根本原因**:
- Chart Recommender 设计为返回**数组**（多个推荐）
- Chart Generator 设计为接受**单个配置**
- 缺少"选择推荐并应用"的中间层

**影响**:
- ❌ 用户体验差：需要手写 Scriptlet 代码
- ❌ 违反 OOMOL 设计理念：blocks 应直接可组合
- ❌ 降低 Chart Recommender 的实用性

---

#### 🚨 **问题 2: Exploration Agent 未模块化调用其他 Blocks**

**现状**:
`tasks/exploration-agent/__init__.py` 中，内部实现包含：
- SQL 代码生成逻辑（重复了 NL-to-SQL 的功能）
- 图表生成逻辑（应该调用 Chart Generator）
- 报告生成逻辑（应该调用 Report Generator）

**根本原因**:
- Agent 设计为"端到端黑盒"
- 没有通过 OOMOL flow 内部调用其他 tasks
- 代码复用性差

**影响**:
- ❌ 功能重复实现，维护成本高
- ❌ 如果修复 NL-to-SQL 的 bug，Exploration Agent 不会受益
- ❌ 用户无法在 UI 中看到 agent 内部的中间步骤

---

#### 🚨 **问题 3: 缺少数据库连接能力**

**现状**:
Data Loader 仅支持文件格式（CSV/Excel/JSON），不支持数据库。

**指导文档提到的能力**（`OOMOL_DATA_ANALYSIS_BLOCKS_GUIDE.md:59-70`）:
```yaml
- handle: database_config
  json_schema:
    type: object
    properties:
      type: {type: string}
      host: {type: string}
      database: {type: string}
      query: {type: string}
  nullable: true
```

**实际代码**（`tasks/data-loader/__init__.py`）:
仅实现了 CSV/Excel/JSON 的解析器，没有数据库连接逻辑。

**影响**:
- ❌ 无法分析生产数据库数据
- ❌ 限制企业场景应用

---

## 三、智能分析能力评估

### 3.1 当前能否帮助用户智能分析数据？

#### ✅ **已经能做到的**

1. **简单 BI 分析（80% 覆盖）**
   - 数据聚合、排序、过滤
   - 多维度对比
   - 基础可视化

2. **自然语言交互（核心优势）**
   - 用户无需学习 SQL 或 Pandas
   - 即时生成代码和结果
   - 自动错误修复

3. **自动化探索（差异化能力）**
   - Exploration Agent 可自主多轮分析
   - 生成洞察和建议

#### ❌ **无法做到的**

1. **实时数据分析**
   - 缺少数据库连接
   - 无法处理流式数据
   - 无法自动刷新

2. **高级统计分析**
   - 假设检验（t-test、ANOVA）
   - 相关性分析（Pearson、Spearman）
   - 回归分析（线性/逻辑回归）
   - 虽然 NL-to-Pandas 理论上可以调用 sklearn，但**没有专门的统计分析 block**

3. **预测和机器学习**
   - 时间序列预测（ARIMA、Prophet）
   - 分类/聚类（KMeans、Random Forest）
   - 缺少模型训练和评估的 blocks

4. **交互式探索**
   - 用户无法在可视化上点击进行下钻
   - 无法动态调整参数
   - 所有分析都是"一次性执行"

---

### 3.2 与 Data Formulator 原项目的对比

| 能力维度 | Data Formulator | 当前 OOMOL 实现 | 差距分析 |
|---------|----------------|----------------|----------|
| **数据源** | 10+ 种（含数据库） | 3 种（仅文件） | ⚠️ **需补充数据库支持** |
| **转换引擎** | SQL + Python | SQL + Python | ✅ 对齐 |
| **可视化** | 交互式 Vega-Lite | 静态 PNG 导出 | ⚠️ **缺少交互能力** |
| **探索模式** | 分支探索 + 撤销 | 线性多轮迭代 | ⚠️ **无法回溯** |
| **报告生成** | Markdown + 流式 | Markdown + 流式 | ✅ 对齐 |
| **安全沙盒** | 审计钩子 + 白名单 | 审计钩子 + 白名单 | ✅ 对齐 |

---

## 四、升级建议

### 4.1 短期修复（1-2 周）

#### 修复 1: 添加 Chart Selector Block

**目标**: 解决 Chart Recommender → Chart Generator 断裂问题

**设计**:
```yaml
# tasks/chart-selector/task.oo.yaml
inputs_def:
  - handle: recommendations
    json_schema:
      type: array  # 来自 Chart Recommender
  - handle: selection_index
    json_schema:
      type: number
    value: 0  # 默认选第一个推荐

outputs_def:
  - handle: chart_type
    json_schema: {type: string}
  - handle: x_field
    json_schema: {type: string}
  - handle: y_field
    json_schema: {type: string}
  - handle: color_field
    json_schema: {type: string}
  - handle: size_field
    json_schema: {type: string}
```

**代码实现**:
```python
async def main(params: Inputs, context: Context) -> Outputs:
    recommendations = params["recommendations"]
    index = params.get("selection_index", 0)

    selected = recommendations[index]

    return {
        "chart_type": selected["chart_type"],
        "x_field": selected.get("x_field", ""),
        "y_field": selected.get("y_field", ""),
        "color_field": selected.get("color_field"),
        "size_field": selected.get("size_field")
    }
```

**价值**:
- ✅ 消除 Scriptlet 需求
- ✅ 标准化推荐到生成的流程
- ✅ 支持用户选择不同推荐（通过 `selection_index`）

---

#### 修复 2: 重构 Chart Recommender 输出格式

**问题**: 当前输出字段名与 Chart Generator 不一致

**当前**:
```json
{
  "chart_type": "bar",
  "encodings": {"x": "region", "y": "total"}  // 嵌套结构
}
```

**建议改为**:
```json
{
  "chart_type": "bar",
  "x_field": "region",       // 扁平化
  "y_field": "total",
  "color_field": null,
  "size_field": null
}
```

**修改位置**: `tasks/chart-recommender/__init__.py`

---

#### 修复 3: 为 Data Loader 添加数据库支持

**实现步骤**:

1. **更新 `task.oo.yaml`**:
```yaml
inputs_def:
  - handle: source_type
    json_schema:
      enum: [csv, excel, json, mysql, postgresql, sqlite]

  - handle: database_config
    json_schema:
      type: object
      properties:
        host: {type: string}
        port: {type: number}
        database: {type: string}
        username: {type: string}
        password: {type: string, contentMediaType: oomol/secret}
        query: {type: string, ui:widget: text}
    nullable: true
```

2. **代码实现** (`tasks/data-loader/__init__.py`):
```python
import sqlalchemy

async def load_from_database(config: dict) -> pd.DataFrame:
    db_type = config["type"]
    connection_string = f"{db_type}://{config['username']}:{config['password']}@{config['host']}:{config.get('port', 3306)}/{config['database']}"

    engine = sqlalchemy.create_engine(connection_string)
    df = pd.read_sql(config["query"], engine)

    return df
```

3. **依赖添加** (`pyproject.toml`):
```toml
sqlalchemy = "^2.0.0"
pymysql = "^1.1.0"       # MySQL 驱动
psycopg2-binary = "^2.9.0"  # PostgreSQL 驱动
```

**价值**:
- ✅ 支持企业数据库分析
- ✅ 实时数据访问
- ✅ 对齐 Data Formulator 能力

---

### 4.2 中期优化（3-4 周）

#### 优化 1: 模块化 Exploration Agent

**目标**: 让 Exploration Agent 通过 flow 调用其他 blocks，而非内部重复实现

**技术方案**: 使用 **Dynamic Flow Execution**

**伪代码**:
```python
async def main(params: Inputs, context: Context) -> Outputs:
    exploration_steps = []

    for step in range(params["max_iterations"]):
        # 动态构建 sub-flow
        sub_flow = {
            "nodes": [
                {
                    "node_id": "transform#1",
                    "task": "self::nl-to-sql",
                    "inputs_from": [
                        {"handle": "input_table", "value": current_table},
                        {"handle": "instruction", "value": current_goal}
                    ]
                },
                {
                    "node_id": "chart#1",
                    "task": "self::chart-generator",
                    "inputs_from": [
                        {"handle": "data_table", "from_node": [{"node_id": "transform#1", "output_handle": "result_table"}]},
                        {"handle": "chart_type", "value": recommended_chart_type}
                    ]
                }
            ]
        }

        # 执行 sub-flow（假设有这个 API）
        result = await context.run_flow(sub_flow)

        # 分析结果并决定下一步
        insight = await analyze_result(result, params["llm"])
        exploration_steps.append(insight)

    return {"exploration_steps": exploration_steps}
```

**挑战**:
- ❓ OOMOL 是否支持从 task 内部动态执行 flow？
- ❓ 如果不支持，可能需要修改 OOMOL 核心框架

**价值**:
- ✅ 消除代码重复
- ✅ 自动继承其他 blocks 的改进
- ✅ 用户可在 UI 中看到 agent 内部步骤

---

#### 优化 2: 添加统计分析 Block

**新增 Block**: Statistical Analyzer

**功能定位**: 专门处理统计检验和相关性分析

**输入参数**:
```yaml
inputs_def:
  - handle: data_table
    json_schema: {type: object}

  - handle: analysis_type
    json_schema:
      type: string
      enum: [correlation, t_test, anova, chi_square, regression]

  - handle: variables
    json_schema:
      type: object
      properties:
        independent: {type: array}  # 自变量
        dependent: {type: string}   # 因变量
```

**输出参数**:
```yaml
outputs_def:
  - handle: test_result
    json_schema:
      type: object
      properties:
        statistic: {type: number}
        p_value: {type: number}
        confidence_interval: {type: array}

  - handle: interpretation
    json_schema: {type: string}  # LLM 生成的解释
```

**核心逻辑**:
```python
from scipy import stats
import statsmodels.api as sm

async def main(params: Inputs, context: Context) -> Outputs:
    df = pd.DataFrame(params["data_table"]["rows"])
    analysis_type = params["analysis_type"]

    if analysis_type == "correlation":
        result = df[params["variables"]["independent"]].corr(method="pearson")
    elif analysis_type == "t_test":
        group1 = df[df["group"] == "A"][params["variables"]["dependent"]]
        group2 = df[df["group"] == "B"][params["variables"]["dependent"]]
        statistic, p_value = stats.ttest_ind(group1, group2)
    elif analysis_type == "regression":
        X = df[params["variables"]["independent"]]
        y = df[params["variables"]["dependent"]]
        model = sm.OLS(y, sm.add_constant(X)).fit()
        result = model.summary()

    # 使用 LLM 生成解释
    interpretation = await generate_interpretation(result, params["llm"])

    return {
        "test_result": result.to_dict(),
        "interpretation": interpretation
    }
```

**价值**:
- ✅ 支持科研和数据科学场景
- ✅ 自动生成统计学解释（降低专业门槛）

---

#### 优化 3: 添加时间序列分析 Block

**新增 Block**: Time Series Analyzer

**功能定位**: 处理时间序列预测和趋势分析

**输入参数**:
```yaml
inputs_def:
  - handle: data_table
    json_schema: {type: object}

  - handle: time_column
    json_schema: {type: string}

  - handle: value_column
    json_schema: {type: string}

  - handle: analysis_type
    json_schema:
      enum: [trend, seasonality, forecast, anomaly_detection]

  - handle: forecast_periods
    json_schema: {type: number}
    value: 12
    nullable: true
```

**核心逻辑**:
```python
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.arima.model import ARIMA

async def main(params: Inputs, context: Context) -> Outputs:
    df = pd.DataFrame(params["data_table"]["rows"])
    df[params["time_column"]] = pd.to_datetime(df[params["time_column"]])
    df = df.set_index(params["time_column"])

    series = df[params["value_column"]]

    if params["analysis_type"] == "trend":
        decomposition = seasonal_decompose(series, model="additive")
        trend = decomposition.trend.dropna()
    elif params["analysis_type"] == "forecast":
        model = ARIMA(series, order=(1, 1, 1))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=params["forecast_periods"])

    # 可视化
    fig = plot_forecast(series, forecast)
    context.preview({"type": "image", "data": fig_to_base64(fig)})

    return {"forecast_data": forecast.to_dict()}
```

**价值**:
- ✅ 支持销售预测、趋势分析
- ✅ 企业 BI 核心需求

---

### 4.3 长期演进（2-3 个月）

#### 演进 1: 创建端到端 Subflow

**目标**: 将常用分析模式封装为 subflow，降低用户门槛

**示例 Subflow 1**: Quick Insight Generator

**组合 Blocks**:
```
Data Loader → NL-to-SQL → Chart Recommender → Chart Selector → Chart Generator
```

**Subflow 输入**:
```yaml
inputs_def:
  - handle: data_file
    json_schema: {type: string, ui:widget: file}
  - handle: analysis_question
    json_schema: {type: string, ui:widget: text}
```

**Subflow 输出**:
```yaml
outputs_def:
  - handle: chart_image
    json_schema: {type: string}
  - handle: insight
    json_schema: {type: string}
```

**价值**:
- ✅ 一键完成"数据 → 洞察"
- ✅ 适合非技术用户

---

**示例 Subflow 2**: Full Report Pipeline

**组合 Blocks**:
```
Data Loader → [NL-to-SQL → Chart Generator] × 3 → Report Generator
```

**价值**:
- ✅ 自动生成多图表报告
- ✅ 企业汇报场景

---

#### 演进 2: 添加交互式仪表盘 Block

**新增 Block**: Dashboard Builder

**功能定位**: 生成可交互的 Web 仪表盘（而非静态图表）

**技术方案**: 使用 **Plotly Dash** 或 **Streamlit**

**输出**:
- 生成一个独立的 HTML 文件
- 包含 JavaScript 交互逻辑
- 支持下钻、筛选、时间范围调整

**价值**:
- ✅ 实时监控和探索
- ✅ 对标商业 BI 工具（Tableau、Power BI）

---

#### 演进 3: 添加机器学习 Blocks

**新增 3 个 Blocks**:

1. **Feature Engineer**
   - 自动特征工程（编码、缩放、多项式特征）

2. **Model Trainer**
   - 分类/回归/聚类模型训练
   - 超参数自动调优

3. **Model Evaluator**
   - 混淆矩阵、ROC 曲线
   - 特征重要性分析

**价值**:
- ✅ 支持预测分析
- ✅ 数据科学完整闭环

---

## 五、总结与优先级

### 5.1 当前 Blocks 能力评分

| 评估维度 | 得分 | 说明 |
|---------|-----|------|
| **基础分析能力** | ⭐⭐⭐⭐⭐ (5/5) | SQL + Pandas 覆盖 90% 常见需求 |
| **模块化设计** | ⭐⭐⭐ (3/5) | 存在架构问题（Recommender-Generator 断裂） |
| **智能化程度** | ⭐⭐⭐⭐ (4/5) | AI 驱动的转换和推荐 |
| **企业就绪度** | ⭐⭐ (2/5) | 缺少数据库连接和实时能力 |
| **高级分析** | ⭐⭐ (2/5) | 无统计检验、预测、ML 能力 |

**综合评分: 3.2/5 分**

---

### 5.2 升级建议优先级排序

| 优先级 | 任务 | 预期时间 | 影响力 | 难度 |
|-------|-----|---------|-------|------|
| **P0** | 修复 Chart Recommender → Generator 连接 | 3 天 | ⭐⭐⭐⭐⭐ | 低 |
| **P0** | 添加数据库支持到 Data Loader | 5 天 | ⭐⭐⭐⭐⭐ | 中 |
| **P1** | 添加统计分析 Block | 1 周 | ⭐⭐⭐⭐ | 中 |
| **P1** | 模块化 Exploration Agent | 2 周 | ⭐⭐⭐ | 高 |
| **P2** | 添加时间序列分析 Block | 1 周 | ⭐⭐⭐⭐ | 中 |
| **P2** | 创建端到端 Subflows | 1 周 | ⭐⭐⭐ | 低 |
| **P3** | 添加交互式仪表盘 Block | 3 周 | ⭐⭐⭐⭐ | 高 |
| **P3** | 添加机器学习 Blocks | 4 周 | ⭐⭐⭐⭐ | 高 |

---

### 5.3 关键结论

#### ✅ **当前系统能做到的**

1. **基础数据分析（90% 覆盖）**
   - BI 报表、趋势分析、对比分析
   - 适合小型企业和个人用户

2. **低代码数据科学**
   - 用户无需编程即可完成复杂转换
   - Pandas 代码自动生成

3. **自动化洞察生成**
   - Exploration Agent 可自主发现模式
   - 报告自动撰写

#### ❌ **需要补充的核心能力**

1. **企业级数据接入**（P0）
   - 数据库连接是**刚需**
   - 目前只支持文件上传，无法用于生产环境

2. **高级统计分析**（P1）
   - 科研和数据科学场景必需
   - 竞品（如 SPSS、R）的核心能力

3. **预测和机器学习**（P2）
   - 时间序列预测（销售、库存）
   - 企业 BI 的高价值场景

4. **交互式探索**（P3）
   - 实时筛选、下钻
   - 对标 Tableau、Power BI

---

### 5.4 最终建议

**立即执行（1 周内）**:
1. 修复 Chart Recommender → Generator 连接问题
2. 开始数据库支持开发

**短期规划（1 个月内）**:
1. 完成数据库支持
2. 添加统计分析 Block
3. 创建 2-3 个实用 Subflows

**中期规划（3 个月内）**:
1. 添加时间序列分析
2. 重构 Exploration Agent
3. 发布 v1.0 稳定版

**长期愿景（6 个月内）**:
1. 交互式仪表盘
2. 机器学习完整工具链
3. 对标商业 BI 工具的核心能力

---

## 附录：参考资料

- **指导文档**: [OOMOL_DATA_ANALYSIS_BLOCKS_GUIDE.md](OOMOL_DATA_ANALYSIS_BLOCKS_GUIDE.md)
- **项目 README**: [README.md](README.md)
- **测试 Flows**: `flows/test-*`
- **Data Formulator 原项目**: https://github.com/microsoft/data-formulator

---

**报告生成时间**: 2026-01-22
**分析范围**: 全部 8 个核心 blocks + 4 个测试 flows
**评估方法**: 代码审查 + 架构分析 + 与原项目对比
