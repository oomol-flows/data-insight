# Quick Analysis Subflow - Design Document

## Overview

`quick-analysis` is a new optimized subflow that replaces the problematic `complete-data-analysis` subflow. It provides a streamlined single-round analysis pipeline with proper data flow and intelligent chart recommendations.

## Problem with Previous Design

The old `complete-data-analysis` subflow had several issues:

1. **Broken connections**: chart-generator's inputs (chart_type, x_field, y_field, color_field, size_field) had empty connections `[]`
2. **Unused recommendations**: chart-recommender output wasn't connected to chart-generator
3. **Illogical flow**: Chart recommendation happened BEFORE data transformation, leading to inappropriate suggestions

## New Design: quick-analysis

### Architecture

```
User Question: "What are the top 10 regions by sales?"
    ↓
1. data-loader: Load CSV/Excel/JSON file
    ↓
2. nl-to-sql: Transform with natural language → Get top 10 regions
    ↓
3. chart-recommender: AI analyzes transformed data → Recommends bar chart
    ↓
4. chart-generator: Uses recommended parameters → Generates visualization
    ↓
5. chart-array-builder: Packages chart for report
    ↓
6. report-generator: Creates final markdown report
```

### Key Improvements

1. **Correct data flow**: Recommendation based on TRANSFORMED data, not raw data
2. **Complete connections**: All chart-generator inputs properly connected
3. **Enhanced chart-recommender outputs**:
   - `recommended_charts`: Array of all recommendations (as before)
   - `chart_type`: Top recommendation's chart type (NEW)
   - `x_field`: Top recommendation's X field (NEW)
   - `y_field`: Top recommendation's Y field (NEW)
   - `color_field`: Top recommendation's color field (NEW)
   - `size_field`: Top recommendation's size field (NEW)
   - `chart_title`: Generated chart title (NEW)

4. **Type compatibility**: Fixed schema matching between nl-to-sql and chart-recommender

### Type Schemas

**nl-to-sql → result_table**:
```json
{
  "type": "object",
  "properties": {
    "columns": {"type": "array"},
    "rows": {"type": "array"},
    "schema": {"type": "object"}
  }
}
```

**chart-recommender → data_table** (MATCHES):
```json
{
  "type": "object",
  "properties": {
    "columns": {"type": "array"},
    "rows": {"type": "array"},
    "schema": {"type": "object"}
  }
}
```

### Usage Example

```yaml
nodes:
  - node_id: quick#1
    subflow: self::quick-analysis
    inputs_from:
      - handle: data_file
        value: /oomol-driver/oomol-storage/sales.csv
      - handle: analysis_question
        value: "What are the top 10 regions by total sales?"
      - handle: source_type
        value: csv
      - handle: llm
        value:
          model: oomol-chat
          temperature: 0.5
          max_tokens: 128000
```

### Outputs

- `final_report`: Complete markdown report with analysis
- `chart_image`: Base64 encoded chart visualization
- `query_result`: Transformed data table

### Forward Previews

The subflow exposes three key previews:
1. `load#1`: Data loading preview
2. `chart#1`: Generated chart visualization
3. `report#1`: Final analysis report

## Comparison with smart-data-analysis

| Feature | quick-analysis | smart-data-analysis |
|---------|----------------|---------------------|
| Analysis Type | Single-round direct | Multi-round exploratory |
| Core Components | nl-to-sql + chart-recommender | exploration-agent |
| Speed | Fast (~20-30s) | Slower (multiple iterations) |
| Use Case | Specific questions | Open-ended exploration |
| Output | 1 chart + report | Multiple charts + exploration steps |
| Best For | "Top 10 sales by region" | "Discover sales insights" |

## Files Created/Modified

### Created
- `subflows/quick-analysis/subflow.oo.yaml`
- `subflows/quick-analysis/.subflow.ui.oo.json`
- `flows/test-quick-analysis/flow.oo.yaml`
- `flows/test-quick-analysis/.flow.ui.oo.json`

### Modified
- `tasks/chart-recommender/task.oo.yaml` - Added individual output fields
- `tasks/chart-recommender/__init__.py` - Return top recommendation fields

### Removed
- `subflows/complete-data-analysis/` (deleted)
- `flows/test-complete-analysis/` (deleted)

## Testing

Test flow available at: `flows/test-quick-analysis/flow.oo.yaml`

Run with:
```bash
oomol run flows/test-quick-analysis/flow.oo.yaml
```

## Future Enhancements

1. Support for multiple charts in one analysis
2. Configurable iteration depth
3. Export options (PDF, HTML)
4. Custom chart templates
