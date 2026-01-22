# Preview 功能说明

## nl-to-sql Block 预览增强

### 功能描述

nl-to-sql block 现在提供了增强的预览功能,在 OOMOL 可视化界面中显示:

1. **生成的 SQL 查询** - 高亮显示的 SQL 代码
2. **查询解释** - LLM 生成的易懂说明
3. **查询结果表格** - 前 20 行数据的格式化表格

### 预览内容示例

当你在 OOMOL UI 中运行包含 nl-to-sql block 的 flow 时,会看到:

```
📊 SQL Query Result

Generated SQL:
    SELECT region, SUM(sales) AS total
    FROM input_data
    GROUP BY region
    ORDER BY total DESC

💡 Explanation:
This query groups the data by region, calculates the sum of sales
for each region, and orders the results from highest to lowest total sales.

Results (4 rows):
┌────────┬───────┐
│ region │ total │
├────────┼───────┤
│ East   │ 42000 │
│ North  │ 37000 │
│ South  │ 34400 │
│ West   │ 35100 │
└────────┴───────┘
```

### 技术实现

预览使用 `context.preview()` API:

```python
context.preview({
    "type": "html",
    "data": preview_html  # 包含 SQL、解释和结果表格的 HTML
})
```

### 注意事项

1. **预览 vs 输出**:
   - `context.preview()` 在 OOMOL UI 中显示,不影响 block 的输出数据
   - Block 的返回值 (`sql_query`, `result_table`, `explanation`) 可以传递给下游 blocks

2. **何时显示预览**:
   - 在 OOMOL 可视化工作流编辑器中运行时
   - 在 flow 执行过程中,每个 block 完成时显示

3. **预览内容不在 API 返回中**:
   - 使用 `runFlow` API 执行时,预览内容不会包含在返回结果中
   - 预览专门用于 UI 交互,API 只返回实际的输出数据

## 其他 Blocks 的预览

### data-loader Block
显示:
- 数据统计(行数、列数)
- 前 10 行数据的 HTML 表格

### chart-generator Block
显示:
- 生成的图表 PNG 图像(base64 编码)

## 测试预览功能

运行 [test-preview](../flows/test-preview) flow 在 OOMOL UI 中查看预览效果:

```bash
# 在 OOMOL UI 中打开 flows/test-preview/flow.oo.yaml
# 点击运行按钮
# 查看 transform#1 节点的预览面板
```

## 自定义预览

如果你创建自己的 blocks,可以使用以下预览类型:

- `"type": "html"` - HTML 内容
- `"type": "markdown"` - Markdown 文本
- `"type": "image"` - 图像(base64 或路径)
- `"type": "table"` - 表格数据
- `"type": "json"` - JSON 对象
- `"type": "text"` - 纯文本

示例:

```python
# HTML 预览
context.preview({
    "type": "html",
    "data": "<h1>Result</h1><p>Content here</p>"
})

# 表格预览
context.preview({
    "type": "table",
    "data": {
        "headers": ["Name", "Value"],
        "rows": [["A", 1], ["B", 2]]
    }
})

# 图像预览
context.preview({
    "type": "image",
    "data": "data:image/png;base64,iVBORw0KG..."
})
```
