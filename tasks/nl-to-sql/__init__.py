#region generated meta
import typing
class Inputs(typing.TypedDict):
    input_table: dict
    instruction: str
    llm: dict

class Outputs(typing.TypedDict):
    sql_query: str
    result_table: dict
    explanation: str
#endregion

from oocana import Context
from openai import OpenAI
import pandas as pd
import duckdb
import json
import re

async def main(params: Inputs, context: Context) -> Outputs:
    """
    Transform natural language instructions into SQL queries.

    Uses LLM to generate DuckDB SQL queries from natural language,
    executes them safely, and returns the results.
    """
    input_table = params["input_table"]
    instruction = params["instruction"]
    llm_config = params["llm"]

    # Validate inputs
    if not instruction:
        raise ValueError("Instruction is required")
    if not input_table or not input_table.get("rows"):
        raise ValueError("Input table is empty or invalid")

    # Report progress
    context.report_progress(10)

    # Prepare table summary for LLM
    table_summary = summarize_table(input_table)

    # Build system prompt
    system_prompt = """You are an expert SQL query generator using DuckDB syntax.

CRITICAL RULES:
1. Output ONLY valid JSON in this exact format:
   {"sql_query": "SELECT ...", "explanation": "This query..."}
2. DO NOT include markdown code blocks or extra text
3. Use DuckDB syntax:
   - Date casting: CAST(column AS DATE)
   - Date arithmetic: date_column + INTERVAL '1 day'
   - String matching: column LIKE '%pattern%'
   - List aggregation: LIST(column) for array results
4. Table name is always 'input_data'
5. Generate safe, read-only SELECT queries only

Examples:
- "Show top 5 by sales" → SELECT * FROM input_data ORDER BY sales DESC LIMIT 5
- "Group by region and sum sales" → SELECT region, SUM(sales) as total FROM input_data GROUP BY region
"""

    # Build user prompt
    user_prompt = f"""Input Table Summary:
{table_summary}

User Goal: {instruction}

Generate a DuckDB SQL query to achieve this goal.
Output JSON format: {{"sql_query": "...", "explanation": "..."}}"""

    # Call LLM
    context.report_progress(30)

    client = OpenAI(
        base_url=context.oomol_llm_env.get("base_url_v1"),
        api_key=await context.oomol_token()
    )

    try:
        # Limit max_tokens to 4096 to avoid streaming requirement
        max_tokens = min(llm_config.get("max_tokens", 4096), 4096)

        response = client.chat.completions.create(
            model=llm_config.get("model", "oomol-chat"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=llm_config.get("temperature", 0),
            max_tokens=max_tokens
        )
    except Exception as e:
        raise RuntimeError(f"LLM API call failed: {str(e)}")

    context.report_progress(60)

    # Parse response
    response_text = response.choices[0].message.content
    result = extract_json_from_response(response_text)

    if not result or "sql_query" not in result:
        raise ValueError(f"Invalid LLM response format: {response_text}")

    sql_query = result["sql_query"]
    explanation = result.get("explanation", "No explanation provided")

    # Execute SQL query
    try:
        # Create DataFrame from input table
        df = pd.DataFrame(input_table["rows"])

        # Convert data types to DuckDB-compatible types
        df = convert_to_duckdb_types(df)

        # Execute query using DuckDB
        conn = duckdb.connect(":memory:")
        conn.register("input_data", df)

        result_df = conn.execute(sql_query).df()
        conn.close()

    except Exception as e:
        raise RuntimeError(f"SQL execution failed: {str(e)}\nQuery: {sql_query}")

    context.report_progress(90)

    # Validate result
    if result_df.empty:
        raise ValueError("Query returned no results")

    # Preview result with SQL query and explanation
    preview_html = f"""
    <div style="font-family: Arial, sans-serif;">
        <h3 style="color: #2c3e50;">📊 SQL Query Result</h3>

        <div style="background: #f8f9fa; padding: 12px; border-radius: 4px; margin: 10px 0;">
            <h4 style="color: #495057; margin: 0 0 8px 0;">Generated SQL:</h4>
            <code style="background: white; padding: 8px; display: block; border-left: 3px solid #4CAF50;">
                {sql_query}
            </code>
        </div>

        <div style="background: #e8f5e9; padding: 12px; border-radius: 4px; margin: 10px 0;">
            <h4 style="color: #2e7d32; margin: 0 0 8px 0;">💡 Explanation:</h4>
            <p style="margin: 0; line-height: 1.6;">{explanation}</p>
        </div>

        <div style="margin-top: 16px;">
            <h4 style="color: #495057;">Results ({len(result_df)} rows):</h4>
            {result_df.head(20).to_html(index=False, classes="result-table")}
        </div>
    </div>

    <style>
        .result-table {{
            border-collapse: collapse;
            width: 100%;
            font-size: 12px;
            margin-top: 8px;
        }}
        .result-table th {{
            background-color: #4CAF50;
            color: white;
            padding: 10px;
            text-align: left;
        }}
        .result-table td {{
            border: 1px solid #ddd;
            padding: 8px;
        }}
        .result-table tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        .result-table tr:hover {{
            background-color: #e8f5e9;
        }}
    </style>
    """

    context.preview({
        "type": "html",
        "data": preview_html
    })

    context.report_progress(100)

    # Return results
    return {
        "sql_query": sql_query,
        "result_table": {
            "columns": result_df.columns.tolist(),
            "rows": result_df.to_dict("records")
        },
        "explanation": explanation
    }


def summarize_table(table: dict) -> str:
    """
    Create a concise summary of the table for LLM context.
    """
    columns = table.get("columns", [])
    schema = table.get("schema", {})
    rows = table.get("rows", [])

    summary_parts = [
        f"Table: input_data ({len(rows)} rows)",
        "Columns:"
    ]

    for col in columns:
        col_info = schema.get(col, {})
        col_type = col_info.get("semantic_type", "unknown")
        col_summary = f"  - {col} ({col_type})"

        if col_type == "quantitative":
            min_val = col_info.get("min")
            max_val = col_info.get("max")
            if min_val is not None and max_val is not None:
                col_summary += f", range: {min_val} to {max_val}"
        elif col_type == "nominal":
            unique_count = col_info.get("unique_count", 0)
            col_summary += f", {unique_count} unique values"

        summary_parts.append(col_summary)

    # Add sample data (first 2 rows)
    if rows:
        summary_parts.append("\nSample data (first 2 rows):")
        for i, row in enumerate(rows[:2]):
            summary_parts.append(f"  Row {i+1}: {json.dumps(row)}")

    return "\n".join(summary_parts)


def extract_json_from_response(response: str) -> dict:
    """
    Extract JSON from LLM response that may contain markdown or extra text.
    """
    # Try to parse as direct JSON
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find JSON object in text
    json_match = re.search(r'\{[^{}]*"sql_query"[^{}]*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from response: {response}")


def convert_to_duckdb_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert DataFrame columns to DuckDB-compatible types.

    DuckDB has issues with Pandas string dtype and some other types.
    """
    df = df.copy()

    for col in df.columns:
        # Convert string dtype to object (standard Python strings)
        if df[col].dtype == 'string':
            df[col] = df[col].astype('object')

        # Convert other problematic types if needed
        elif df[col].dtype == 'Int64':
            df[col] = df[col].astype('float64')  # Use float to handle nulls

    return df
