#region generated meta
import typing
from oocana import LLMModelOptions
class Inputs(typing.TypedDict):
    input_table: dict
    instruction: str
    llm: LLMModelOptions
class Outputs(typing.TypedDict):
    python_code: typing.NotRequired[str]
    result_table: typing.NotRequired[dict]
    execution_logs: typing.NotRequired[str]
#endregion

from oocana import Context
from openai import OpenAI
import json
import re
import pandas as pd
import numpy as np
from sklearn import preprocessing, decomposition, cluster
import sys
import io
from contextlib import redirect_stdout, redirect_stderr


PANDAS_SYSTEM_PROMPT = """You are an expert Python data analyst. Generate Pandas code to transform data according to user instructions.

Code Requirements:
1. Define a function named `transform_data` that takes one DataFrame parameter `df`
2. Return a transformed DataFrame
3. Use only these allowed libraries: pandas (as pd), numpy (as np), sklearn
4. Do NOT use file I/O operations, subprocess, or network requests
5. Handle missing values appropriately
6. Ensure output is always a DataFrame (not Series or other types)

Output Format:
Return valid JSON with this structure:
{
  "python_code": "import pandas as pd\\nimport numpy as np\\n\\ndef transform_data(df):\\n    # transformation logic\\n    return result_df",
  "explanation": "Brief explanation of what the code does"
}

Example 1:
Instruction: "Calculate total sales by product"
Output:
{
  "python_code": "import pandas as pd\\n\\ndef transform_data(df):\\n    result = df.groupby('product')['sales'].sum().reset_index()\\n    result.columns = ['product', 'total_sales']\\n    return result",
  "explanation": "Groups by product and sums the sales column"
}

Example 2:
Instruction: "Add a column showing percent change from Q1 to Q2"
Output:
{
  "python_code": "import pandas as pd\\n\\ndef transform_data(df):\\n    df['percent_change'] = ((df['Q2'] - df['Q1']) / df['Q1'] * 100).round(2)\\n    return df",
  "explanation": "Calculates percentage change between Q1 and Q2 columns"
}

IMPORTANT: Return ONLY the JSON object, no additional text or markdown formatting."""


def extract_json_from_response(text: str) -> dict:
    """Extract JSON from LLM response"""
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from LLM response: {e}\n\nResponse: {text}")


def summarize_table(table: dict) -> str:
    """Create a summary of the table for LLM context"""
    df = pd.DataFrame(table["rows"])
    summary_parts = []

    summary_parts.append(f"Table shape: {len(df)} rows × {len(df.columns)} columns")
    summary_parts.append(f"\nColumns: {', '.join(df.columns.tolist())}")

    # Add schema information
    if "schema" in table:
        summary_parts.append("\nColumn types:")
        for col, info in table["schema"].items():
            col_type = info.get("type", "unknown")
            summary_parts.append(f"  - {col}: {col_type}")

            if "stats" in info:
                stats = info["stats"]
                if "min" in stats and "max" in stats:
                    summary_parts.append(
                        f"    (range: {stats['min']} to {stats['max']})"
                    )

    # Add sample data
    sample_df = df.head(3)
    summary_parts.append("\nSample data:")
    summary_parts.append(sample_df.to_string(index=False))

    return "\n".join(summary_parts)


def execute_in_sandbox(code: str, df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Execute Python code in a restricted environment"""

    # Capture stdout/stderr
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    # Build restricted globals
    restricted_globals = {
        "__builtins__": {
            "print": print,
            "len": len,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "sum": sum,
            "min": min,
            "max": max,
            "abs": abs,
            "round": round,
            "sorted": sorted,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "type": type,
            "isinstance": isinstance,
            "ValueError": ValueError,
            "TypeError": TypeError,
            "KeyError": KeyError,
        },
        "pd": pd,
        "np": np,
        "preprocessing": preprocessing,
        "decomposition": decomposition,
        "cluster": cluster,
    }

    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            # Execute code to define the function
            exec(code, restricted_globals)

            # Call the transform_data function
            if "transform_data" not in restricted_globals:
                raise ValueError("Code must define a 'transform_data' function")

            result = restricted_globals["transform_data"](df)

            # Ensure result is a DataFrame
            if not isinstance(result, pd.DataFrame):
                raise ValueError(
                    f"Function must return a DataFrame, got {type(result).__name__}"
                )

        logs = stdout_capture.getvalue()
        if stderr_capture.getvalue():
            logs += "\n" + stderr_capture.getvalue()

        return result, logs or "Execution successful"

    except Exception as e:
        error_msg = f"Execution error: {type(e).__name__}: {str(e)}"
        if stderr_capture.getvalue():
            error_msg += f"\n{stderr_capture.getvalue()}"
        raise RuntimeError(error_msg)


def repair_code_via_llm(
    original_code: str, error: str, instruction: str, llm: dict, context: Context
) -> str:
    """Attempt to repair failed code using LLM"""

    repair_prompt = f"""The following Python code failed to execute:

```python
{original_code}
```

Error:
{error}

Original instruction: {instruction}

Please fix the code to handle this error. Return the corrected code in the same JSON format:
{{
  "python_code": "corrected code here",
  "explanation": "what was fixed"
}}"""

    client = OpenAI(
        base_url=context.oomol_llm_env.get("base_url_v1"),
        api_key=context.oomol_token(),
    )

    response = client.chat.completions.create(
        model=llm.get("model", "oomol-chat"),
        messages=[
            {"role": "system", "content": PANDAS_SYSTEM_PROMPT},
            {"role": "user", "content": repair_prompt},
        ],
        temperature=0,
    )

    result = extract_json_from_response(response.choices[0].message.content)
    return result["python_code"]


def infer_schema(df: pd.DataFrame) -> dict:
    """Infer schema from DataFrame"""
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
        else:
            col_info["type"] = "nominal"
            unique_count = df[col].nunique()
            if unique_count <= 10:
                col_info["unique_values"] = df[col].unique().tolist()
            col_info["unique_count"] = unique_count

        schema[col] = col_info

    return schema


async def main(params: Inputs, context: Context) -> Outputs:
    """Transform data using natural language instructions converted to Pandas code"""

    context.report_progress(0)

    input_table = params["input_table"]
    instruction = params["instruction"]
    llm = params["llm"]

    # Prepare input DataFrame
    df = pd.DataFrame(input_table["rows"])

    context.report_progress(10)

    # Generate table summary for LLM
    table_summary = summarize_table(input_table)

    # Build prompt
    user_prompt = f"""Input Table:
{table_summary}

Instruction: {instruction}

Generate Pandas code to accomplish this transformation."""

    context.report_progress(20)

    # Call LLM to generate code
    client = OpenAI(
        base_url=context.oomol_llm_env.get("base_url_v1"),
        api_key=await context.oomol_token(),
    )

    response = client.chat.completions.create(
        model=llm.get("model", "oomol-chat"),
        messages=[
            {"role": "system", "content": PANDAS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=llm.get("temperature", 0),
        max_tokens=llm.get("max_tokens", 128000),
    )

    context.report_progress(50)

    # Parse response
    result = extract_json_from_response(response.choices[0].message.content)
    python_code = result["python_code"]
    explanation = result.get("explanation", "")

    context.report_progress(60)

    # Execute code in sandbox
    try:
        result_df, logs = execute_in_sandbox(python_code, df)
    except Exception as e:
        # Attempt to repair code
        try:
            repaired_code = repair_code_via_llm(
                python_code, str(e), instruction, llm, context
            )
            result_df, logs = execute_in_sandbox(repaired_code, df)
            python_code = repaired_code
            logs = f"Code repaired and executed successfully\n{logs}"
        except Exception as repair_error:
            raise RuntimeError(
                f"Code execution failed even after repair attempt:\n"
                f"Original error: {e}\n"
                f"Repair error: {repair_error}"
            )

    context.report_progress(80)

    # Build output
    schema = infer_schema(result_df)
    result_table = {
        "columns": result_df.columns.tolist(),
        "rows": result_df.to_dict("records"),
        "schema": schema,
    }

    # Generate preview
    preview_df = result_df.head(20)
    preview_html = f"""
<div style="font-family: system-ui, -apple-system, sans-serif; padding: 20px;">
    <div style="margin-bottom: 20px;">
        <h3 style="margin: 0 0 10px 0; color: #1f2937;">Transformation Result</h3>
        <div style="display: flex; gap: 20px; font-size: 14px; color: #6b7280; margin-bottom: 15px;">
            <span><strong>Rows:</strong> {len(result_df)}</span>
            <span><strong>Columns:</strong> {len(result_df.columns)}</span>
        </div>
        <div style="background: #f0fdf4; border-left: 4px solid #22c55e; padding: 12px; margin-bottom: 15px; border-radius: 4px;">
            <strong style="color: #15803d;">Explanation:</strong>
            <div style="color: #166534; margin-top: 5px;">{explanation}</div>
        </div>
    </div>

    <details style="margin-bottom: 20px;">
        <summary style="cursor: pointer; padding: 10px; background: #f3f4f6; border-radius: 4px; font-weight: 600; color: #374151;">
            🐍 View Python Code
        </summary>
        <pre style="background: #1f2937; color: #e5e7eb; padding: 15px; border-radius: 4px; overflow-x: auto; margin-top: 10px; font-size: 13px; line-height: 1.5;"><code>{python_code}</code></pre>
    </details>

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

    context.preview({"type": "html", "data": preview_html})

    context.report_progress(100)

    return {
        "python_code": python_code,
        "result_table": result_table,
        "execution_logs": logs,
    }
