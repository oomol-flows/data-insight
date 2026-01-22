# OOMOL 数据分析 Blocks 开发指导报告

## 项目背景

基于微软开源项目 **Data Formulator** 的代码分析,本报告提供了构建 OOMOL 数据分析能力 blocks 的技术指导。Data Formulator 是一个成熟的 AI 驱动数据可视化工具,具有丰富的数据处理和分析能力。

---

## 一、核心价值提炼

### 1.1 Data Formulator 的核心优势

| 能力维度 | 技术实现 | 可复用性 |
|---------|---------|---------|
| **多数据源接入** | 支持 CSV/Excel/数据库/截图/网页等 10+ 数据源 | ⭐⭐⭐⭐⭐ |
| **AI 驱动转换** | 自然语言 → SQL/Python 代码生成 | ⭐⭐⭐⭐⭐ |
| **智能可视化** | 自动推荐图表类型和编码映射 | ⭐⭐⭐⭐ |
| **安全执行** | Python 沙盒 + 审计钩子防止恶意代码 | ⭐⭐⭐⭐⭐ |
| **多轮探索** | Agent 链式分析,支持分支探索 | ⭐⭐⭐⭐ |
| **报告生成** | Markdown + 图表流式输出 | ⭐⭐⭐⭐ |

### 1.2 OOMOL Blocks 设计原则

根据 CLAUDE.md 规则:
- ✅ **原子化**: 每个 block 专注单一职责
- ✅ **可组合**: 通过 flow 连接多个 blocks 形成复杂分析流程
- ✅ **可视化**: 利用 OOMOL 的预览能力展示中间结果
- ✅ **可复用**: Task blocks 可跨项目使用,Subflow blocks 封装常用分析模式

---

## 二、推荐 Blocks 架构设计

### 2.1 基础能力层 (Foundation Blocks)

#### Block 1: 数据加载器 (Data Loader)
**功能**: 从多种数据源加载表格数据

**输入参数**:
```yaml
inputs_def:
  - handle: source_type
    json_schema:
      type: string
      ui:widget: select
      ui:options:
        options: [csv, excel, json, database, web_table]
    value: csv
    nullable: false

  - handle: file_path
    json_schema:
      type: string
      ui:widget: file
    nullable: true  # CSV/Excel 必需

  - handle: database_config
    json_schema:
      type: object
      properties:
        type: {type: string}
        host: {type: string}
        database: {type: string}
        query: {type: string}
    nullable: true  # 数据库类型必需

  - handle: url
    json_schema:
      type: string
    nullable: true  # Web 表格必需
```

**输出参数**:
```yaml
outputs_def:
  - handle: data_table
    json_schema:
      type: object
      properties:
        columns: {type: array}
        rows: {type: array}
        schema: {type: object}
    description: "Standard table format"

  - handle: preview_html
    json_schema:
      type: string
    description: "HTML table for preview"
```

**核心逻辑** (参考 `data_loader/` 目录):
```python
# 从 data-formulator/py-src/data_formulator/data_loader/ 提取
async def main(params: Inputs, context: Context) -> Outputs:
    source_type = params["source_type"]

    if source_type == "csv":
        df = pd.read_csv(params["file_path"])
    elif source_type == "database":
        # 复用 database_loader.py 的连接逻辑
        conn = create_connection(params["database_config"])
        df = pd.read_sql(params["database_config"]["query"], conn)
    elif source_type == "web_table":
        # 复用 web_scraper.py 逻辑
        tables = extract_tables_from_url(params["url"])
        df = tables[0]

    # 推断 schema
    schema = infer_schema(df)  # 参考 agent_data_load.py

    # 生成预览
    preview = df.head(10).to_html()
    context.preview({"type": "html", "data": preview})

    return {
        "data_table": {
            "columns": df.columns.tolist(),
            "rows": df.to_dict("records"),
            "schema": schema
        },
        "preview_html": preview
    }
```

**文件路径参考**:
- [data_loader/csv_loader.py](data-formulator/py-src/data_formulator/data_loader/csv_loader.py)
- [data_loader/database_loader.py](data-formulator/py-src/data_formulator/data_loader/database_loader.py)
- [agents/agent_data_load.py:1-298](data-formulator/py-src/data_formulator/agents/agent_data_load.py#L1-L298)

---

#### Block 2: 图像/文本数据提取器 (Data Extractor)
**功能**: 从图像、混乱文本、网页中提取结构化数据

**输入参数**:
```yaml
inputs_def:
  - handle: source_type
    json_schema:
      type: string
      ui:widget: select
      ui:options:
        options: [image, text, html]
    value: image

  - handle: source_content
    json_schema:
      type: string
    description: "Image path / raw text / HTML content"

  - handle: llm
    json_schema:
      ui:widget: llm::model
    value:
      model: oomol-chat
      temperature: 0
      max_tokens: 128000
    nullable: false
```

**输出参数**:
```yaml
outputs_def:
  - handle: extracted_table
    json_schema:
      type: object

  - handle: extraction_confidence
    json_schema:
      type: number
    description: "0-1 confidence score"
```

**核心逻辑** (参考 `agent_data_clean.py`):
```python
# 从 data-formulator/py-src/data_formulator/agents/agent_data_clean.py 提取
async def main(params: Inputs, context: Context) -> Outputs:
    llm = params["llm"]
    source_type = params["source_type"]

    # 构建提示词 (参考 agent_data_clean.py:40-120)
    if source_type == "image":
        # 使用视觉模型
        messages = [
            {"role": "system", "content": EXTRACT_FROM_IMAGE_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": params["source_content"], "detail": "high"}},
                    {"type": "text", "text": "Extract all tables from this image"}
                ]
            }
        ]
    elif source_type == "text":
        messages = [
            {"role": "system", "content": EXTRACT_FROM_TEXT_PROMPT},
            {"role": "user", "content": params["source_content"]}
        ]
    elif source_type == "html":
        messages = [
            {"role": "system", "content": EXTRACT_FROM_HTML_PROMPT},
            {"role": "user", "content": params["source_content"]}
        ]

    # 调用 LLM (使用 OOMOL token)
    client = OpenAI(
        base_url=context.oomol_llm_env.get("base_url_v1"),
        api_key=await context.oomol_token()
    )
    response = client.chat.completions.create(
        model=llm["model"],
        messages=messages,
        temperature=0
    )

    # 解析 JSON 响应
    result = extract_json_from_response(response.choices[0].message.content)

    return {
        "extracted_table": result["table"],
        "extraction_confidence": result.get("confidence", 0.8)
    }
```

**文件路径参考**:
- [agents/agent_data_clean.py:1-355](data-formulator/py-src/data_formulator/agents/agent_data_clean.py#L1-L355)

---

### 2.2 转换能力层 (Transformation Blocks)

#### Block 3: NL-to-SQL 转换器 (NL to SQL)
**功能**: 自然语言指令 → SQL 查询代码

**输入参数**:
```yaml
inputs_def:
  - handle: input_tables
    json_schema:
      type: array
      items:
        type: object
    description: "Array of table objects"

  - handle: instruction
    json_schema:
      type: string
      ui:widget: text
    description: "Natural language goal (e.g., 'Show top 10 sales by region')"

  - handle: llm
    json_schema:
      ui:widget: llm::model
    value:
      model: oomol-chat
      temperature: 0
      max_tokens: 128000
```

**输出参数**:
```yaml
outputs_def:
  - handle: sql_query
    json_schema:
      type: string
    description: "Generated SQL query"

  - handle: result_table
    json_schema:
      type: object
    description: "Query execution result"

  - handle: explanation
    json_schema:
      type: string
    description: "Code explanation"
```

**核心逻辑** (参考 `agent_sql_data_transform.py`):
```python
# 从 data-formulator/py-src/data_formulator/agents/agent_sql_data_transform.py 提取
import duckdb

async def main(params: Inputs, context: Context) -> Outputs:
    # 1. 准备表格摘要 (参考 agent_sql_data_transform.py:200-250)
    table_summaries = summarize_tables(params["input_tables"])

    # 2. 构建提示词 (参考 agent_sql_data_transform.py:50-150)
    system_prompt = SQL_TRANSFORM_SYSTEM_PROMPT
    user_prompt = f"""
Input Tables:
{table_summaries}

Goal: {params['instruction']}

Generate a DuckDB SQL query to achieve this goal.
Output JSON format: {{"sql_query": "...", "explanation": "..."}}
"""

    # 3. 调用 LLM
    client = OpenAI(
        base_url=context.oomol_llm_env.get("base_url_v1"),
        api_key=await context.oomol_token()
    )
    response = client.chat.completions.create(
        model=params["llm"]["model"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0
    )

    # 4. 解析 SQL
    result = extract_json_from_response(response.choices[0].message.content)
    sql_query = result["sql_query"]

    # 5. 执行 SQL (使用 DuckDB)
    conn = duckdb.connect(":memory:")
    for table in params["input_tables"]:
        df = pd.DataFrame(table["rows"])
        conn.register(table["name"], df)

    result_df = conn.execute(sql_query).df()

    # 6. 预览结果
    context.preview({"type": "table", "data": {
        "headers": result_df.columns.tolist(),
        "rows": result_df.head(20).values.tolist()
    }})

    return {
        "sql_query": sql_query,
        "result_table": {
            "columns": result_df.columns.tolist(),
            "rows": result_df.to_dict("records")
        },
        "explanation": result["explanation"]
    }
```

**文件路径参考**:
- [agents/agent_sql_data_transform.py:1-486](data-formulator/py-src/data_formulator/agents/agent_sql_data_transform.py#L1-L486)

---

#### Block 4: NL-to-Pandas 转换器 (NL to Pandas)
**功能**: 自然语言指令 → Python Pandas 代码

**输入参数**: 与 Block 3 类似

**输出参数**:
```yaml
outputs_def:
  - handle: python_code
    json_schema:
      type: string

  - handle: result_table
    json_schema:
      type: object

  - handle: execution_logs
    json_schema:
      type: string
```

**核心逻辑** (参考 `agent_py_data_transform.py` + `py_sandbox.py`):
```python
# 从 data-formulator/py-src/data_formulator/agents/agent_py_data_transform.py 提取
async def main(params: Inputs, context: Context) -> Outputs:
    # 1. LLM 生成代码 (类似 Block 3)
    python_code = generate_pandas_code_via_llm(params)

    # 2. 安全执行 (参考 py_sandbox.py:30-120)
    result_df, logs = execute_in_sandbox(
        code=python_code,
        input_tables=params["input_tables"],
        allowed_modules=["pandas", "numpy", "sklearn"]
    )

    # 3. 错误自动修复 (参考 agent_py_data_transform.py:300-400)
    if "error" in logs:
        repaired_code = repair_code_via_llm(python_code, logs["error"])
        result_df, logs = execute_in_sandbox(repaired_code, params["input_tables"])

    return {
        "python_code": python_code,
        "result_table": {
            "columns": result_df.columns.tolist(),
            "rows": result_df.to_dict("records")
        },
        "execution_logs": logs
    }

# 沙盒执行函数 (参考 py_sandbox.py)
def execute_in_sandbox(code, input_tables, allowed_modules):
    """
    使用审计钩子防止文件写入和危险操作
    """
    # 构建受限全局环境
    restricted_globals = {
        "__builtins__": {
            "print": print,
            "len": len,
            "range": range,
            # ... 白名单函数
        },
        "pd": pandas,
        "np": numpy
    }

    # 注册审计钩子
    sys.addaudithook(audit_hook)  # 阻止 open(), subprocess 等

    # 执行代码
    exec(code, restricted_globals)
    result = restricted_globals["transform_data"](*[pd.DataFrame(t["rows"]) for t in input_tables])

    return result, {"status": "success"}
```

**文件路径参考**:
- [agents/agent_py_data_transform.py:1-531](data-formulator/py-src/data_formulator/agents/agent_py_data_transform.py#L1-L531)
- [py_sandbox.py:1-150](data-formulator/py-src/data_formulator/py_sandbox.py#L1-L150)

---

### 2.3 可视化能力层 (Visualization Blocks)

#### Block 5: 智能图表推荐器 (Chart Recommender)
**功能**: 根据数据特征自动推荐最佳图表类型

**输入参数**:
```yaml
inputs_def:
  - handle: data_table
    json_schema:
      type: object

  - handle: analysis_goal
    json_schema:
      type: string
      ui:widget: text
    description: "Optional: User's analysis intent"
    nullable: true

  - handle: llm
    json_schema:
      ui:widget: llm::model
```

**输出参数**:
```yaml
outputs_def:
  - handle: recommended_charts
    json_schema:
      type: array
      items:
        type: object
        properties:
          chart_type: {type: string}
          encodings: {type: object}
          reason: {type: string}
          priority: {type: number}
```

**核心逻辑** (参考 `agent_sql_data_rec.py` / `agent_py_data_rec.py`):
```python
# 从 data-formulator/py-src/data_formulator/agents/agent_sql_data_rec.py 提取
async def main(params: Inputs, context: Context) -> Outputs:
    data_table = params["data_table"]

    # 1. 数据统计分析
    df = pd.DataFrame(data_table["rows"])
    field_stats = analyze_field_statistics(df)

    # 2. 构建推荐提示词 (参考 agent_sql_data_rec.py:50-200)
    prompt = f"""
Data fields: {field_stats}
Goal: {params.get('analysis_goal', 'Explore the data')}

Recommend 3 most effective visualizations.
Output JSON: [{{"chart_type": "...", "encodings": {{"x": "...", "y": "..."}}, "reason": "...", "priority": 1-3}}]
"""

    # 3. 调用 LLM
    client = OpenAI(
        base_url=context.oomol_llm_env.get("base_url_v1"),
        api_key=await context.oomol_token()
    )
    response = client.chat.completions.create(
        model=params["llm"]["model"],
        messages=[
            {"role": "system", "content": CHART_RECOMMENDATION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    # 4. 解析推荐结果
    recommendations = extract_json_from_response(response.choices[0].message.content)

    return {"recommended_charts": recommendations}
```

**文件路径参考**:
- [agents/agent_sql_data_rec.py:1-520](data-formulator/py-src/data_formulator/agents/agent_sql_data_rec.py#L1-L520)
- [agents/agent_py_data_rec.py:1-487](data-formulator/py-src/data_formulator/agents/agent_py_data_rec.py#L1-L487)

---

#### Block 6: Vega-Lite 图表生成器 (Chart Generator)
**功能**: 根据编码配置生成 Vega-Lite 图表

**输入参数**:
```yaml
inputs_def:
  - handle: data_table
    json_schema:
      type: object

  - handle: chart_type
    json_schema:
      type: string
      ui:widget: select
      ui:options:
        options: [bar, line, scatter, heatmap, pie, area, boxplot]
    value: bar

  - handle: encodings
    json_schema:
      type: object
      properties:
        x: {type: string}
        y: {type: string}
        color: {type: string}
        size: {type: string}
    description: "Field assignments to visual channels"
```

**输出参数**:
```yaml
outputs_def:
  - handle: vega_spec
    json_schema:
      type: object
    description: "Vega-Lite JSON specification"

  - handle: chart_image
    json_schema:
      type: string
    description: "Base64 PNG image"
```

**核心逻辑** (参考 `create_vl_plots.py`):
```python
# 从 data-formulator/py-src/data_formulator/workflows/create_vl_plots.py 提取
import altair as alt
import vl_convert as vlc

async def main(params: Inputs, context: Context) -> Outputs:
    df = pd.DataFrame(params["data_table"]["rows"])
    chart_type = params["chart_type"]
    encodings = params["encodings"]

    # 1. 检测字段类型 (参考 create_vl_plots.py:50-150)
    field_types = detect_field_types(df)

    # 2. 构建 Vega-Lite spec (参考 create_vl_plots.py:200-400)
    if chart_type == "bar":
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X(encodings["x"], type=field_types[encodings["x"]]),
            y=alt.Y(encodings["y"], type=field_types[encodings["y"]]),
            color=alt.Color(encodings.get("color")) if "color" in encodings else alt.value("steelblue")
        )
    elif chart_type == "line":
        chart = alt.Chart(df).mark_line().encode(
            x=alt.X(encodings["x"], type=field_types[encodings["x"]]),
            y=alt.Y(encodings["y"], type=field_types[encodings["y"]])
        )
    # ... 其他图表类型

    vega_spec = chart.to_dict()

    # 3. 渲染为 PNG (使用 vl-convert)
    png_data = vlc.vegalite_to_png(vega_spec, scale=2)
    import base64
    base64_image = base64.b64encode(png_data).decode()

    # 4. 预览
    context.preview({"type": "image", "data": f"data:image/png;base64,{base64_image}"})

    return {
        "vega_spec": vega_spec,
        "chart_image": base64_image
    }

# 字段类型检测函数
def detect_field_types(df):
    """
    返回: {"field1": "quantitative", "field2": "nominal", ...}
    """
    types = {}
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            unique_count = df[col].nunique()
            if unique_count < 20 and unique_count < len(df) * 0.5:
                types[col] = "ordinal"
            else:
                types[col] = "quantitative"
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            types[col] = "temporal"
        else:
            types[col] = "nominal"
    return types
```

**文件路径参考**:
- [workflows/create_vl_plots.py:1-580](data-formulator/py-src/data_formulator/workflows/create_vl_plots.py#L1-L580)

---

### 2.4 高级分析层 (Advanced Analysis Blocks)

#### Block 7: 多轮探索 Agent (Exploration Agent)
**功能**: 自主进行多轮数据探索和分析

**输入参数**:
```yaml
inputs_def:
  - handle: input_tables
    json_schema:
      type: array

  - handle: exploration_goal
    json_schema:
      type: string
      ui:widget: text
    description: "High-level goal (e.g., 'Find insights about sales trends')"

  - handle: max_iterations
    json_schema:
      type: number
    value: 5
    nullable: true

  - handle: llm
    json_schema:
      ui:widget: llm::model
```

**输出参数**:
```yaml
outputs_def:
  - handle: exploration_steps
    json_schema:
      type: array
      items:
        type: object
        properties:
          step_number: {type: number}
          transformation: {type: string}
          chart_type: {type: string}
          insight: {type: string}

  - handle: final_report
    json_schema:
      type: string
    description: "Markdown report with findings"
```

**核心逻辑** (参考 `exploration_flow.py` + `agent_exploration.py`):
```python
# 从 data-formulator/py-src/data_formulator/workflows/exploration_flow.py 提取
async def main(params: Inputs, context: Context) -> Outputs:
    exploration_steps = []
    current_tables = params["input_tables"]

    # 1. 生成探索计划 (参考 agent_exploration.py:50-200)
    plan = await generate_exploration_plan(
        params["exploration_goal"],
        current_tables,
        params["llm"]
    )

    # 2. 迭代执行探索步骤
    for i in range(params.get("max_iterations", 5)):
        context.report_progress(int((i + 1) / params["max_iterations"] * 80))

        # 2.1 获取当前步骤
        current_step = plan["steps"][i] if i < len(plan["steps"]) else None
        if not current_step:
            break

        # 2.2 数据转换 (调用 NL-to-SQL 或 NL-to-Pandas block)
        transformed_table = await transform_data(
            current_tables,
            current_step["transformation_goal"],
            params["llm"]
        )

        # 2.3 生成可视化
        chart = await create_chart(
            transformed_table,
            current_step["chart_type"],
            current_step["encodings"]
        )

        # 2.4 分析结果并决定下一步 (参考 agent_exploration.py:300-450)
        analysis = await analyze_and_decide_next(
            transformed_table,
            chart,
            plan["steps"][i+1:],
            params["llm"]
        )

        exploration_steps.append({
            "step_number": i + 1,
            "transformation": current_step["transformation_goal"],
            "chart_type": current_step["chart_type"],
            "insight": analysis["insight"]
        })

        # 2.5 更新计划 (如果需要)
        if analysis["action"] == "revise_plan":
            plan["steps"] = plan["steps"][:i+1] + analysis["revised_steps"]
        elif analysis["action"] == "conclude":
            break

        current_tables = [transformed_table]

    # 3. 生成最终报告
    context.report_progress(90)
    final_report = await generate_report(exploration_steps, params["llm"])

    context.report_progress(100)
    context.preview({"type": "markdown", "data": final_report})

    return {
        "exploration_steps": exploration_steps,
        "final_report": final_report
    }
```

**文件路径参考**:
- [workflows/exploration_flow.py:1-450](data-formulator/py-src/data_formulator/workflows/exploration_flow.py#L1-L450)
- [agents/agent_exploration.py:1-532](data-formulator/py-src/data_formulator/agents/agent_exploration.py#L1-L532)

---

#### Block 8: Markdown 报告生成器 (Report Generator)
**功能**: 将图表和洞察整合成 Markdown 报告

**输入参数**:
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

  - handle: analysis_goal
    json_schema:
      type: string

  - handle: llm
    json_schema:
      ui:widget: llm::model
```

**输出参数**:
```yaml
outputs_def:
  - handle: markdown_report
    json_schema:
      type: string

  - handle: report_file
    json_schema:
      type: string
    description: "Path to saved .md file"
```

**核心逻辑** (参考 `agent_report_gen.py`):
```python
# 从 data-formulator/py-src/data_formulator/agents/agent_report_gen.py 提取
async def main(params: Inputs, context: Context) -> Outputs:
    charts = params["charts"]

    # 1. 准备图表摘要
    chart_summaries = [
        f"Chart {i+1}: {c['title']} - {c['description']}"
        for i, c in enumerate(charts)
    ]

    # 2. 流式生成报告 (参考 agent_report_gen.py:100-250)
    prompt = f"""
Analysis goal: {params['analysis_goal']}

Available charts:
{chr(10).join(chart_summaries)}

Generate a comprehensive markdown report with:
1. Executive summary
2. Key findings (reference charts as {{{{chart_1}}}}, {{{{chart_2}}}}, etc.)
3. Detailed analysis
4. Recommendations

Use professional data analysis language.
"""

    client = OpenAI(
        base_url=context.oomol_llm_env.get("base_url_v1"),
        api_key=await context.oomol_token()
    )

    # 流式调用
    stream = client.chat.completions.create(
        model=params["llm"]["model"],
        messages=[
            {"role": "system", "content": REPORT_GEN_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        stream=True
    )

    markdown_content = ""
    for chunk in stream:
        if chunk.choices[0].delta.content:
            markdown_content += chunk.choices[0].delta.content

    # 3. 替换图表占位符
    for i, chart in enumerate(charts):
        placeholder = f"{{{{chart_{i+1}}}}}"
        markdown_content = markdown_content.replace(
            placeholder,
            f"\n![{chart['title']}](data:image/png;base64,{chart['image']})\n"
        )

    # 4. 保存文件
    report_path = f"{context.session_dir}/analysis_report.md"
    with open(report_path, "w") as f:
        f.write(markdown_content)

    # 5. 预览
    context.preview({"type": "markdown", "data": markdown_content})

    return {
        "markdown_report": markdown_content,
        "report_file": report_path
    }
```

**文件路径参考**:
- [agents/agent_report_gen.py:1-380](data-formulator/py-src/data_formulator/agents/agent_report_gen.py#L1-L380)

---

## 三、Subflow 组合示例

### Subflow 1: 端到端数据分析流水线
**组合 Blocks**: Data Loader → NL-to-SQL → Chart Generator → Report Generator

```yaml
# subflows/end-to-end-analysis/subflow.oo.yaml
title: "End-to-End Data Analysis Pipeline"
description: "Load data → Transform → Visualize → Report"

inputs_def:
  - handle: data_source
    json_schema:
      type: string
      ui:widget: file

  - handle: analysis_question
    json_schema:
      type: string
      ui:widget: text

outputs_def:
  - handle: final_report
    json_schema:
      type: string

nodes:
  - node_id: load#1
    task: self::data-loader
    inputs_from:
      - handle: source_type
        value: csv
      - handle: file_path
        from_flow:
          - input_handle: data_source

  - node_id: transform#1
    task: self::nl-to-sql
    inputs_from:
      - handle: input_tables
        from_node:
          - node_id: load#1
            output_handle: data_table
      - handle: instruction
        from_flow:
          - input_handle: analysis_question

  - node_id: recommend#1
    task: self::chart-recommender
    inputs_from:
      - handle: data_table
        from_node:
          - node_id: transform#1
            output_handle: result_table
      - handle: analysis_goal
        from_flow:
          - input_handle: analysis_question

  - node_id: chart#1
    task: self::chart-generator
    inputs_from:
      - handle: data_table
        from_node:
          - node_id: transform#1
            output_handle: result_table
      - handle: chart_type
        from_node:
          - node_id: recommend#1
            output_handle: recommended_charts
            # 取第一个推荐

  - node_id: report#1
    task: self::report-generator
    inputs_from:
      - handle: charts
        from_node:
          - node_id: chart#1
            output_handle: chart_image
      - handle: analysis_goal
        from_flow:
          - input_handle: analysis_question

outputs_from:
  - handle: final_report
    from_node:
      - node_id: report#1
        output_handle: markdown_report

forward_previews:
  - chart#1  # 转发图表预览
  - report#1  # 转发报告预览
```

---

## 四、实施路线图

### 阶段 1: 基础能力 (1-2 周)
**目标**: 构建最小可用的数据分析流程

**任务**:
1. ✅ 创建项目结构 (`tasks/`, `flows/`, `subflows/`)
2. ✅ 实现 Block 1 (Data Loader) - 支持 CSV/Excel
3. ✅ 实现 Block 3 (NL-to-SQL) - 基础版本
4. ✅ 实现 Block 6 (Chart Generator) - 支持 bar/line 图
5. ✅ 创建测试 flow 验证完整流程

**验收标准**:
- 能加载 CSV 文件
- 能用自然语言查询数据 (如 "按类别汇总销售额")
- 能生成柱状图和折线图
- 所有 blocks 通过 `runFlow` 测试

---

### 阶段 2: 扩展能力 (2-3 周)
**目标**: 增强数据源和转换能力

**任务**:
1. ✅ 扩展 Block 1 - 支持数据库连接 (MySQL/PostgreSQL)
2. ✅ 实现 Block 2 (Data Extractor) - 图像/文本提取
3. ✅ 实现 Block 4 (NL-to-Pandas) - Python 转换
4. ✅ 增强 Block 6 - 支持更多图表类型 (scatter/heatmap/pie)
5. ✅ 实现 Block 5 (Chart Recommender)

**验收标准**:
- 支持 3+ 种数据源
- 能处理非结构化数据 (截图/网页表格)
- 图表推荐准确率 >80%

---

### 阶段 3: 高级分析 (2-3 周)
**目标**: AI 驱动的自动化分析

**任务**:
1. ✅ 实现 Block 7 (Exploration Agent)
2. ✅ 实现 Block 8 (Report Generator)
3. ✅ 创建 Subflow 1 (End-to-End Pipeline)
4. ✅ 优化 LLM 提示词 (提高代码生成质量)
5. ✅ 实现错误自动修复机制

**验收标准**:
- 探索 Agent 能自主完成 3+ 轮分析
- 生成的报告包含洞察和建议
- 代码执行成功率 >90%

---

### 阶段 4: 优化和文档 (1 周)
**目标**: 生产就绪

**任务**:
1. ✅ 性能优化 (缓存、并行处理)
2. ✅ 错误处理完善 (所有 blocks 都要 raise exception)
3. ✅ 使用 `/oo_update_description` 添加英文描述
4. ✅ 使用 `/oo_update_readme` 生成 README
5. ✅ 创建示例 flows (销售分析、用户行为分析等)

**验收标准**:
- 所有 blocks 有完整文档
- README 包含使用示例
- 至少 3 个真实场景的示例 flow

---

## 五、关键技术决策

### 5.1 SQL vs Python 转换路径

**推荐策略**: 优先使用 SQL,必要时使用 Python

| 场景 | 推荐路径 | 原因 |
|-----|---------|------|
| 聚合、过滤、JOIN | SQL | 性能更好,语法简洁 |
| 机器学习、复杂计算 | Python | sklearn/numpy 支持 |
| 日期处理 | SQL | DuckDB 日期函数强大 |
| 文本处理 | Python | 正则表达式更灵活 |

**实现**: 在 NL-to-SQL block 中添加能力检测,超出 SQL 范围时自动降级到 Python

---

### 5.2 沙盒安全策略

**必须实现的安全措施** (参考 `py_sandbox.py`):

1. **审计钩子**: 阻止 `open()`, `subprocess.Popen()`, `os.system()`
2. **受限 builtins**: 只允许白名单函数 (len, range, print 等)
3. **模块白名单**: pandas, numpy, sklearn, datetime (禁止 requests, socket)
4. **执行超时**: 单个转换最多 30 秒
5. **内存限制**: 最多使用 2GB RAM

**代码示例**:
```python
# 核心安全函数
def audit_hook(event, args):
    """阻止危险操作"""
    dangerous_events = {
        "open": ["w", "a", "x"],  # 禁止写文件
        "subprocess.Popen": True,
        "os.system": True
    }
    if event in dangerous_events:
        raise RuntimeError(f"Operation {event} is not allowed")

sys.addaudithook(audit_hook)
```

---

### 5.3 LLM 提示词优化建议

基于 Data Formulator 的最佳实践:

**结构化输出强制**:
```python
system_prompt = """
You MUST output valid JSON in this exact format:
{
  "sql_query": "SELECT ...",
  "explanation": "This query..."
}

Do NOT include markdown code blocks or extra text.
"""
```

**Few-shot 示例** (参考 `agent_sql_data_transform.py:100-180`):
```python
examples = [
    {
        "input": "Show top 5 products by sales",
        "output": {
            "sql_query": "SELECT product, SUM(sales) as total FROM table1 GROUP BY product ORDER BY total DESC LIMIT 5",
            "explanation": "Groups by product and sums sales"
        }
    },
    # 2-3 more examples
]
```

**DuckDB 特定提示** (关键!):
```python
notes = """
IMPORTANT DuckDB syntax rules:
1. Date casting: CAST(column AS DATE), NOT CAST(column AS DATETIME)
2. Date arithmetic: date_column + INTERVAL '1 day'
3. String matching: column LIKE '%pattern%', NOT column.contains()
4. List aggregation: LIST(column) for array results
"""
```

---

### 5.4 进度报告策略

**何时报告进度**:
- 数据加载: 0% → 20% (读取文件)
- 数据转换: 20% → 60% (LLM 生成 + 执行)
- 可视化: 60% → 80% (渲染图表)
- 报告生成: 80% → 100% (流式输出)

**代码模板**:
```python
async def main(params: Inputs, context: Context) -> Outputs:
    context.report_progress(0)

    # Step 1
    data = load_data(params["file_path"])
    context.report_progress(20)

    # Step 2
    result = transform_data(data)
    context.report_progress(60)

    # Step 3
    chart = create_chart(result)
    context.report_progress(80)

    # Final
    context.report_progress(100)
    return {"output": chart}
```

---

## 六、常见问题和解决方案

### Q1: DuckDB 日期类型错误
**问题**: `CAST(column AS DATETIME)` 失败
**解决**: 使用 `CAST(column AS DATE)` 或 `strptime(column, '%Y-%m-%d')`
**参考**: [agent_sql_data_transform.py:60-80](data-formulator/py-src/data_formulator/agents/agent_sql_data_transform.py#L60-L80)

### Q2: Pandas 代码执行超时
**问题**: 大数据集导致转换超时
**解决**: 添加采样逻辑,对 >10MB 数据先采样 10k 行测试
**参考**: [py_sandbox.py:120-150](data-formulator/py-src/data_formulator/py_sandbox.py#L120-L150)

### Q3: LLM 输出格式不一致
**问题**: 有时返回 JSON,有时返回 markdown
**解决**: 使用 `extract_json_from_response()` 函数提取
**参考**: [client_utils.py:200-250](data-formulator/py-src/data_formulator/client_utils.py#L200-L250)

### Q4: 图表预览不显示
**问题**: Vega-Lite spec 无法渲染
**解决**: 检查字段类型是否正确,日期字段必须转换为 ISO 格式
**参考**: [create_vl_plots.py:400-450](data-formulator/py-src/data_formulator/workflows/create_vl_plots.py#L400-L450)

---

## 七、依赖管理清单

### Python 依赖 (pyproject.toml)
```toml
[tool.poetry.dependencies]
python = "^3.11"
pandas = "^2.1.0"
duckdb = "^0.9.0"
altair = "^5.1.0"
vl-convert-python = "^1.0.0"
openai = "^1.3.0"  # OOMOL LLM API
Pillow = "^10.0.0"  # 图像处理
openpyxl = "^3.1.0"  # Excel 支持
sqlalchemy = "^2.0.0"  # 数据库连接
beautifulsoup4 = "^4.12.0"  # HTML 解析
scikit-learn = "^1.3.0"  # ML 功能
numpy = "^1.25.0"
```

### Node.js 依赖 (package.json)
```json
{
  "dependencies": {}
}
```

### 系统依赖 (package.oo.yaml)
```yaml
scripts:
  bootstrap: |
    npm install
    poetry install --no-root
```

---

## 八、测试用例设计

### 测试 Flow 1: CSV 数据基础分析
```yaml
# flows/test-csv-analysis/flow.oo.yaml
nodes:
  - node_id: load#1
    task: self::data-loader
    inputs_from:
      - handle: source_type
        value: csv
      - handle: file_path
        value: /oomol-driver/oomol-storage/sample_sales.csv

  - node_id: transform#1
    task: self::nl-to-sql
    inputs_from:
      - handle: input_tables
        from_node: [{node_id: load#1, output_handle: data_table}]
      - handle: instruction
        value: "Show total sales by region, sorted descending"

  - node_id: chart#1
    task: self::chart-generator
    inputs_from:
      - handle: data_table
        from_node: [{node_id: transform#1, output_handle: result_table}]
      - handle: chart_type
        value: bar
      - handle: encodings
        value: {x: region, y: total_sales}
```

**预期结果**:
- `load#1` 输出包含 `columns` 和 `rows`
- `transform#1` 生成有效 SQL 查询
- `chart#1` 生成 Vega-Lite spec 和 PNG 图像

---

### 测试 Flow 2: 多轮探索
```yaml
# flows/test-exploration/flow.oo.yaml
nodes:
  - node_id: explore#1
    task: self::exploration-agent
    inputs_from:
      - handle: input_tables
        from_node: [{node_id: load#1, output_handle: data_table}]
      - handle: exploration_goal
        value: "Find insights about customer behavior patterns"
      - handle: max_iterations
        value: 3
```

**预期结果**:
- 至少执行 3 轮分析
- 每轮包含转换 + 可视化 + 洞察
- 最终报告包含 3+ 个发现

---

## 九、总结和建议

### 核心价值主张
通过将 Data Formulator 的能力模块化为 OOMOL blocks,我们能够:
1. **降低门槛**: 用户无需编程即可完成复杂数据分析
2. **提高效率**: AI 驱动的自动化减少手动操作
3. **保证安全**: 沙盒执行防止恶意代码
4. **促进复用**: Blocks 可组合成不同分析场景

### 差异化优势
相比原始 Data Formulator:
- ✅ **可视化工作流**: OOMOL 提供拖拽式界面
- ✅ **模块化**: 每个能力独立封装,易于维护
- ✅ **跨项目复用**: Blocks 可在多个项目间共享
- ✅ **实时预览**: 每个节点的输出立即可见

### 下一步行动
1. **立即开始**: 按阶段 1 路线图创建基础 blocks
2. **迭代优化**: 每个 block 完成后立即测试
3. **收集反馈**: 在真实数据集上验证效果
4. **扩展生态**: 鼓励社区贡献新的分析 blocks

---

**报告生成时间**: 2026-01-22
**参考代码库**: [data-formulator/](data-formulator/)
**联系方式**: 如有疑问,请参考 OOMOL 文档或提交 issue

---

## 附录: 快速参考表

| Block 名称 | 核心功能 | 参考文件 | 优先级 |
|----------|---------|---------|--------|
| Data Loader | 多源数据加载 | data_loader/*.py | P0 |
| Data Extractor | 非结构化数据提取 | agent_data_clean.py | P1 |
| NL-to-SQL | 自然语言转 SQL | agent_sql_data_transform.py | P0 |
| NL-to-Pandas | 自然语言转 Python | agent_py_data_transform.py | P1 |
| Chart Recommender | 智能图表推荐 | agent_sql_data_rec.py | P1 |
| Chart Generator | Vega-Lite 渲染 | create_vl_plots.py | P0 |
| Exploration Agent | 多轮自动分析 | exploration_flow.py | P2 |
| Report Generator | Markdown 报告 | agent_report_gen.py | P1 |

**优先级说明**:
- P0: 阶段 1 必须实现 (MVP)
- P1: 阶段 2 扩展功能
- P2: 阶段 3 高级特性
