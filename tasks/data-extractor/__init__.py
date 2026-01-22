#region generated meta
import typing
from oocana import LLMModelOptions
class Inputs(typing.TypedDict):
    source_type: typing.Literal["image", "text", "html"]
    source_content: str
    llm: LLMModelOptions
class Outputs(typing.TypedDict):
    extracted_table: typing.NotRequired[dict]
    extraction_confidence: typing.NotRequired[float]
#endregion

from oocana import Context
from openai import OpenAI
import json
import re
import pandas as pd


# Prompt templates for different source types
EXTRACT_FROM_IMAGE_PROMPT = """You are a data extraction expert. Extract structured tabular data from the provided image.

Instructions:
1. Identify all tables in the image
2. Extract column headers and all data rows
3. Preserve data types (numbers, text, dates)
4. If multiple tables exist, extract the largest/most significant one
5. Return your analysis as valid JSON

Output format:
{
  "columns": ["column1", "column2", ...],
  "rows": [
    {"column1": value1, "column2": value2, ...},
    ...
  ],
  "confidence": 0.95,
  "notes": "Any observations about data quality or structure"
}

IMPORTANT: Return ONLY the JSON object, no additional text or markdown formatting."""


EXTRACT_FROM_TEXT_PROMPT = """You are a data extraction expert. Extract structured tabular data from the provided text.

The text may contain:
- Tables in plain text format
- Lists that can be converted to tables
- Semi-structured data that needs parsing

Instructions:
1. Identify the tabular structure in the text
2. Extract column headers (infer if not explicit)
3. Parse all data rows
4. Clean and normalize values
5. Return your analysis as valid JSON

Output format:
{
  "columns": ["column1", "column2", ...],
  "rows": [
    {"column1": value1, "column2": value2, ...},
    ...
  ],
  "confidence": 0.90,
  "notes": "Any observations about data quality or structure"
}

IMPORTANT: Return ONLY the JSON object, no additional text or markdown formatting."""


EXTRACT_FROM_HTML_PROMPT = """You are a data extraction expert. Extract structured tabular data from the provided HTML content.

Instructions:
1. Locate <table> tags or structured data in the HTML
2. Extract headers from <th> or first row
3. Parse data from <td> elements
4. Clean HTML entities and formatting
5. If multiple tables exist, extract the largest/most significant one
6. Return your analysis as valid JSON

Output format:
{
  "columns": ["column1", "column2", ...],
  "rows": [
    {"column1": value1, "column2": value2, ...},
    ...
  ],
  "confidence": 0.95,
  "notes": "Any observations about data quality or structure"
}

IMPORTANT: Return ONLY the JSON object, no additional text or markdown formatting."""


def extract_json_from_response(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks"""
    # Remove markdown code blocks if present
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    # Try to find JSON object
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # Fallback: try parsing the entire text
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from LLM response: {e}\n\nResponse text: {text}")


def infer_schema(df: pd.DataFrame) -> dict:
    """Infer schema information from DataFrame"""
    schema = {}

    for col in df.columns:
        dtype = df[col].dtype
        col_info = {"name": col}

        if pd.api.types.is_numeric_dtype(dtype):
            unique_count = df[col].nunique()
            if unique_count < 20 and unique_count < len(df) * 0.5:
                col_info["type"] = "ordinal"
            else:
                col_info["type"] = "quantitative"

            col_info["stats"] = {
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "mean": float(df[col].mean()),
            }

        elif pd.api.types.is_datetime64_any_dtype(dtype):
            col_info["type"] = "temporal"
            col_info["stats"] = {
                "min": str(df[col].min()),
                "max": str(df[col].max()),
            }

        else:
            col_info["type"] = "nominal"
            unique_vals = df[col].unique()
            if len(unique_vals) <= 10:
                col_info["unique_values"] = unique_vals.tolist()
            col_info["unique_count"] = len(unique_vals)

        schema[col] = col_info

    return schema


async def main(params: Inputs, context: Context) -> Outputs:
    """Extract structured table data from images, text, or HTML using LLM"""

    context.report_progress(0)

    source_type = params["source_type"]
    source_content = params["source_content"]
    llm = params["llm"]

    # Select appropriate prompt based on source type
    if source_type == "image":
        system_prompt = EXTRACT_FROM_IMAGE_PROMPT
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": source_content, "detail": "high"},
                    },
                    {"type": "text", "text": "Extract all tabular data from this image"},
                ],
            },
        ]
    elif source_type == "text":
        system_prompt = EXTRACT_FROM_TEXT_PROMPT
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": source_content},
        ]
    elif source_type == "html":
        system_prompt = EXTRACT_FROM_HTML_PROMPT
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": source_content},
        ]
    else:
        raise ValueError(f"Unsupported source_type: {source_type}")

    context.report_progress(20)

    # Call LLM using OOMOL token
    client = OpenAI(
        base_url=context.oomol_llm_env.get("base_url_v1"),
        api_key=await context.oomol_token(),
    )

    response = client.chat.completions.create(
        model=llm.get("model", "oomol-chat"),
        messages=messages,
        temperature=llm.get("temperature", 0),
        max_tokens=llm.get("max_tokens", 128000),
    )

    context.report_progress(60)

    # Parse JSON response
    result = extract_json_from_response(response.choices[0].message.content)

    if "columns" not in result or "rows" not in result:
        raise ValueError(
            "LLM response missing required fields 'columns' or 'rows'\n\n"
            f"Response: {response.choices[0].message.content}"
        )

    # Build DataFrame for schema inference
    df = pd.DataFrame(result["rows"])
    schema = infer_schema(df)

    context.report_progress(80)

    # Build standardized output
    extracted_table = {
        "columns": result["columns"],
        "rows": result["rows"],
        "schema": schema,
    }

    confidence = result.get("confidence", 0.8)

    # Generate preview
    preview_df = df.head(10)
    preview_html = f"""
<div style="font-family: system-ui, -apple-system, sans-serif; padding: 20px;">
    <div style="margin-bottom: 20px;">
        <h3 style="margin: 0 0 10px 0; color: #1f2937;">Extracted Data</h3>
        <div style="display: flex; gap: 20px; font-size: 14px; color: #6b7280;">
            <span><strong>Source:</strong> {source_type}</span>
            <span><strong>Rows:</strong> {len(result['rows'])}</span>
            <span><strong>Columns:</strong> {len(result['columns'])}</span>
            <span><strong>Confidence:</strong> {confidence:.1%}</span>
        </div>
    </div>
    {preview_df.to_html(index=False, classes='data-table', border=0)}
</div>
<style>
    .data-table {{
        border-collapse: collapse;
        width: 100%;
        font-size: 13px;
    }}
    .data-table th {{
        background: #f3f4f6;
        padding: 10px;
        text-align: left;
        font-weight: 600;
        color: #374151;
        border-bottom: 2px solid #e5e7eb;
    }}
    .data-table td {{
        padding: 10px;
        border-bottom: 1px solid #e5e7eb;
        color: #1f2937;
    }}
    .data-table tr:hover {{
        background: #f9fafb;
    }}
</style>
"""

    if result.get("notes"):
        preview_html += f"""
<div style="margin-top: 20px; padding: 15px; background: #eff6ff; border-left: 4px solid #3b82f6; border-radius: 4px;">
    <strong style="color: #1e40af;">Notes:</strong>
    <div style="color: #1e3a8a; margin-top: 5px;">{result['notes']}</div>
</div>
"""

    context.preview({"type": "html", "data": preview_html})

    context.report_progress(100)

    return {
        "extracted_table": extracted_table,
        "extraction_confidence": confidence,
    }
