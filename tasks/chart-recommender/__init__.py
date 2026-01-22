#region generated meta
import typing
from oocana import LLMModelOptions
class Inputs(typing.TypedDict):
    data_table: dict
    analysis_goal: str | None
    llm: LLMModelOptions
class Outputs(typing.TypedDict):
    recommended_charts: typing.NotRequired[list[dict]]
#endregion

from oocana import Context
from openai import OpenAI
import json
import re
import pandas as pd


CHART_RECOMMENDATION_SYSTEM_PROMPT = """You are an expert data visualization consultant. Recommend the most effective chart types for the given data.

Available Chart Types:
- bar: Compare categorical values (good for rankings, comparisons across categories)
- line: Show trends over time or continuous data
- scatter: Show correlation between two quantitative variables
- area: Show cumulative totals or trends with emphasis on magnitude
- pie: Show parts of a whole (use sparingly, max 6-7 categories)
- heatmap: Show patterns in 2D categorical or temporal data

Encoding Guidelines:
- x_field: Usually categorical or temporal (for line/area charts)
- y_field: Usually quantitative (measurements, counts, values)
- color_field: Add another dimension (categorical grouping)
- size_field: Add magnitude dimension (for scatter plots)

Analysis Strategy:
1. Examine field types (quantitative, nominal, ordinal, temporal)
2. Consider cardinality (number of unique values)
3. Match analysis goal to appropriate visualization
4. Prioritize clarity over complexity

Output Format (JSON):
[
  {
    "chart_type": "bar",
    "x_field": "category_column",
    "y_field": "value_column",
    "color_field": "group_column",
    "size_field": null,
    "reason": "Best for comparing values across categories. Shows clear ranking.",
    "priority": 1
  },
  {
    "chart_type": "line",
    "x_field": "date_column",
    "y_field": "value_column",
    "color_field": null,
    "size_field": null,
    "reason": "If data has temporal component, line chart reveals trends over time.",
    "priority": 2
  }
]

Important Rules:
- Recommend 2-3 charts maximum
- Set priority (1 = highest, 3 = lowest)
- Provide clear reasoning for each recommendation
- Choose fields that exist in the data
- Return ONLY valid JSON, no markdown formatting"""


def extract_json_from_response(text: str) -> list:
    """Extract JSON array from LLM response"""
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    # Try to find JSON array
    json_match = re.search(r"\[.*\]", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # Fallback: try parsing entire text
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            return [result]
        else:
            raise ValueError("Expected JSON array or object")
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from LLM response: {e}\n\nResponse: {text}")


def analyze_field_statistics(df: pd.DataFrame, schema: dict) -> dict:
    """Generate field statistics for LLM context"""
    stats = {}

    for col in df.columns:
        col_stats = {"name": col}

        # Get type from schema
        if col in schema:
            col_stats["semantic_type"] = schema[col].get("type", "unknown")

            if "stats" in schema[col]:
                col_stats["statistics"] = schema[col]["stats"]

            if "unique_count" in schema[col]:
                col_stats["unique_count"] = schema[col]["unique_count"]
            else:
                col_stats["unique_count"] = df[col].nunique()

            if "unique_values" in schema[col]:
                col_stats["sample_values"] = schema[col]["unique_values"]
        else:
            # Fallback: analyze directly
            col_stats["unique_count"] = df[col].nunique()

            if pd.api.types.is_numeric_dtype(df[col]):
                col_stats["semantic_type"] = "quantitative"
                col_stats["statistics"] = {
                    "min": float(df[col].min()),
                    "max": float(df[col].max()),
                    "mean": float(df[col].mean()),
                }
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                col_stats["semantic_type"] = "temporal"
            else:
                col_stats["semantic_type"] = "nominal"
                if col_stats["unique_count"] <= 10:
                    col_stats["sample_values"] = df[col].unique().tolist()

        stats[col] = col_stats

    return stats


def format_field_stats_for_prompt(field_stats: dict) -> str:
    """Format field statistics into human-readable text for LLM"""
    lines = []

    for col, stats in field_stats.items():
        line_parts = [f"- **{col}**"]
        line_parts.append(f"({stats.get('semantic_type', 'unknown')})")

        if "unique_count" in stats:
            line_parts.append(f"[{stats['unique_count']} unique values]")

        if "statistics" in stats:
            st = stats["statistics"]
            if "min" in st and "max" in st:
                line_parts.append(f"Range: {st['min']} to {st['max']}")
            if "mean" in st:
                line_parts.append(f"Mean: {st['mean']:.2f}")

        if "sample_values" in stats:
            samples = stats["sample_values"]
            if len(samples) <= 5:
                line_parts.append(f"Values: {', '.join(map(str, samples))}")
            else:
                line_parts.append(f"Sample values: {', '.join(map(str, samples[:5]))}, ...")

        lines.append(" ".join(line_parts))

    return "\n".join(lines)


async def main(params: Inputs, context: Context) -> Outputs:
    """Recommend optimal chart types based on data characteristics"""

    context.report_progress(0)

    data_table = params["data_table"]
    analysis_goal = params.get("analysis_goal") or "Explore the data and find insights"
    llm = params["llm"]

    # Build DataFrame
    df = pd.DataFrame(data_table["rows"])
    schema = data_table.get("schema", {})

    context.report_progress(20)

    # Analyze field statistics
    field_stats = analyze_field_statistics(df, schema)
    field_stats_text = format_field_stats_for_prompt(field_stats)

    context.report_progress(40)

    # Build prompt
    user_prompt = f"""Data Overview:
- Rows: {len(df)}
- Columns: {len(df.columns)}

Field Details:
{field_stats_text}

Analysis Goal: {analysis_goal}

Recommend 2-3 most effective visualizations for this data and goal."""

    context.report_progress(50)

    # Call LLM
    client = OpenAI(
        base_url=context.oomol_llm_env.get("base_url_v1"),
        api_key=await context.oomol_token(),
    )

    response = client.chat.completions.create(
        model=llm.get("model", "oomol-chat"),
        messages=[
            {"role": "system", "content": CHART_RECOMMENDATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=llm.get("temperature", 0.3),
        max_tokens=llm.get("max_tokens", 128000),
    )

    context.report_progress(80)

    # Parse recommendations
    recommendations = extract_json_from_response(response.choices[0].message.content)

    # Validate recommendations
    for rec in recommendations:
        # Validate required fields (chart_type, x_field, y_field must be present and non-empty)
        required_fields = ["chart_type", "x_field", "y_field"]
        missing_fields = [f for f in required_fields if not rec.get(f)]
        if missing_fields:
            raise ValueError(f"Recommendation missing required fields {missing_fields}: {rec}")

        # Ensure optional fields exist (use empty string instead of None for string fields)
        rec.setdefault("color_field", "")
        rec.setdefault("size_field", "")
        rec.setdefault("reason", "")
        rec.setdefault("priority", 1)

    # Sort by priority
    recommendations.sort(key=lambda x: x["priority"])

    # Generate preview
    preview_html = f"""
<div style="font-family: system-ui, -apple-system, sans-serif; padding: 20px;">
    <div style="margin-bottom: 20px;">
        <h3 style="margin: 0 0 10px 0; color: #1f2937;">Chart Recommendations</h3>
        <div style="font-size: 14px; color: #6b7280; margin-bottom: 5px;">
            <strong>Analysis Goal:</strong> {analysis_goal}
        </div>
        <div style="font-size: 14px; color: #6b7280;">
            <strong>Data:</strong> {len(df)} rows × {len(df.columns)} columns
        </div>
    </div>
"""

    for i, rec in enumerate(recommendations):
        priority_color = {1: "#10b981", 2: "#3b82f6", 3: "#6366f1"}.get(rec["priority"], "#6b7280")
        priority_label = {1: "Best Choice", 2: "Alternative", 3: "Option"}.get(rec["priority"], "")

        encodings = []
        if rec["x_field"]:
            encodings.append(f"X: {rec['x_field']}")
        if rec["y_field"]:
            encodings.append(f"Y: {rec['y_field']}")
        if rec["color_field"]:
            encodings.append(f"Color: {rec['color_field']}")
        if rec["size_field"]:
            encodings.append(f"Size: {rec['size_field']}")

        encodings_text = " | ".join(encodings) if encodings else "No specific fields"

        preview_html += f"""
    <div style="border: 2px solid {priority_color}; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
            <span style="background: {priority_color}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;">
                #{rec['priority']} {priority_label}
            </span>
            <span style="font-size: 18px; font-weight: 600; color: #1f2937; text-transform: capitalize;">
                {rec['chart_type']} Chart
            </span>
        </div>
        <div style="font-size: 13px; color: #6b7280; margin-bottom: 8px;">
            <strong>Encodings:</strong> {encodings_text}
        </div>
        <div style="background: #f9fafb; padding: 12px; border-radius: 4px; font-size: 14px; color: #374151;">
            {rec['reason']}
        </div>
    </div>
"""

    preview_html += """
</div>
"""

    context.preview({"type": "html", "data": preview_html})

    context.report_progress(100)

    return {"recommended_charts": recommendations}
