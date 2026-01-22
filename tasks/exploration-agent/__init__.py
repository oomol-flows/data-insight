# region generated meta
import typing


class Inputs(typing.TypedDict):
    input_table: typing.Dict[str, typing.Any]
    exploration_goal: str
    max_iterations: typing.Optional[int]
    llm: typing.Dict[str, typing.Any]


class Outputs(typing.TypedDict):
    exploration_steps: typing.List[typing.Dict[str, typing.Any]]
    final_report: str


# endregion

from oocana import Context
from openai import OpenAI
import pandas as pd
import duckdb
import json


EXPLORATION_SYSTEM_PROMPT = """You are an expert data analyst conducting exploratory data analysis.

Your task is to plan and execute a series of analytical steps to discover insights in the data.

For each step, you must:
1. Analyze the current data state
2. Identify an interesting analytical direction
3. Generate a SQL query to transform the data
4. Explain what insight you expect to find

Output JSON format:
{
  "action": "explore" | "conclude",
  "sql_query": "SQL query for this step (if action is explore)",
  "explanation": "What you're investigating and why",
  "expected_insight": "What pattern you expect to find"
}

Guidelines:
- Start with broad overview (distributions, aggregations)
- Then drill into interesting patterns
- Compare segments or time periods
- Use action "conclude" when you've found sufficient insights
- Keep queries simple and focused
- Each step should build on previous findings
"""

SUMMARIZE_SYSTEM_PROMPT = """You are a data analyst summarizing exploration findings.

Review all exploration steps and generate a concise markdown report with:

1. **Key Findings**: Top 3-5 insights discovered (bullet points)
2. **Data Patterns**: Notable trends or anomalies
3. **Recommendations**: 2-3 actionable suggestions based on findings

Be specific with numbers and clear about patterns.
Output pure markdown without code blocks.
"""


def extract_json_from_response(content: str) -> dict:
    """Extract JSON from LLM response"""
    content = content.strip()

    # Remove markdown code blocks if present
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]

    if content.endswith("```"):
        content = content[:-3]

    content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        import re

        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        raise ValueError(f"Could not extract valid JSON from response: {content[:200]}")


def summarize_table(df: pd.DataFrame) -> str:
    """Create a summary of table structure and sample data"""
    summary_parts = []

    # Schema
    summary_parts.append("Table Schema:")
    for col in df.columns:
        dtype = str(df[col].dtype)
        unique_count = df[col].nunique()
        null_count = df[col].isnull().sum()
        summary_parts.append(
            f"  - {col} ({dtype}): {unique_count} unique values, {null_count} nulls"
        )

    # Sample data
    summary_parts.append("\nSample rows (first 5):")
    summary_parts.append(df.head(5).to_string())

    # Basic stats for numeric columns
    numeric_cols = df.select_dtypes(include=["number"]).columns
    if len(numeric_cols) > 0:
        summary_parts.append("\nNumeric column statistics:")
        summary_parts.append(df[numeric_cols].describe().to_string())

    return "\n".join(summary_parts)


async def execute_sql_query(df: pd.DataFrame, sql_query: str, table_name: str = "data") -> pd.DataFrame:
    """Execute SQL query on dataframe using DuckDB"""
    conn = duckdb.connect(":memory:")
    conn.register(table_name, df)

    try:
        result_df = conn.execute(sql_query).df()
        return result_df
    except Exception as e:
        raise RuntimeError(f"SQL execution failed: {str(e)}\nQuery: {sql_query}")
    finally:
        conn.close()


async def main(params: Inputs, context: Context) -> Outputs:
    """
    Multi-round exploration agent that autonomously discovers insights.

    Reference: data-formulator/py-src/data_formulator/workflows/exploration_flow.py
    """
    input_table = params["input_table"]
    exploration_goal = params["exploration_goal"]
    max_iterations = params.get("max_iterations") or 3
    llm = params["llm"]

    if not input_table.get("rows"):
        raise ValueError("Input table has no data rows")

    context.report_progress(5)

    # Initialize
    df = pd.DataFrame(input_table["rows"])
    exploration_steps = []
    current_df = df

    # Setup OpenAI client
    client = OpenAI(
        base_url=context.oomol_llm_env.get("base_url_v1"),
        api_key=await context.oomol_token(),
    )

    context.report_progress(10)

    # Initial data summary
    initial_summary = summarize_table(df)

    # Exploration loop
    for step_num in range(1, max_iterations + 1):
        progress = 10 + (step_num / max_iterations) * 60
        context.report_progress(int(progress))

        # Generate exploration plan for this step
        current_summary = summarize_table(current_df)

        prompt = f"""Exploration Goal: {exploration_goal}

Current data state:
{current_summary}

This is step {step_num} of {max_iterations}.

Previous steps:
{json.dumps([{"step": s["step_number"], "finding": s["insight"]} for s in exploration_steps], indent=2)}

Plan the next analytical step to discover insights.
"""

        try:
            response = client.chat.completions.create(
                model=llm.get("model", "oomol-chat"),
                messages=[
                    {"role": "system", "content": EXPLORATION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=llm.get("temperature", 0.3),
                max_tokens=llm.get("max_tokens", 128000),
            )

            step_plan = extract_json_from_response(response.choices[0].message.content)

        except Exception as e:
            raise RuntimeError(f"Failed to generate exploration plan: {str(e)}")

        # Check if agent wants to conclude
        if step_plan.get("action") == "conclude":
            break

        # Execute transformation
        sql_query = step_plan.get("sql_query", "")
        if not sql_query:
            # If no query provided, skip this step
            continue

        try:
            transformed_df = await execute_sql_query(current_df, sql_query, "data")
        except Exception as e:
            # If query fails, record error and continue
            exploration_steps.append(
                {
                    "step_number": step_num,
                    "transformation": step_plan.get("explanation", ""),
                    "sql_query": sql_query,
                    "insight": f"Query failed: {str(e)}",
                }
            )
            continue

        # Analyze results to generate insight
        insight_prompt = f"""You executed this SQL query:
{sql_query}

Expected to find: {step_plan.get('expected_insight', '')}

Result data:
{transformed_df.head(10).to_string()}

Result shape: {transformed_df.shape[0]} rows, {transformed_df.shape[1]} columns

What insight does this reveal? Provide a concise 1-2 sentence finding with specific numbers.
"""

        try:
            insight_response = client.chat.completions.create(
                model=llm.get("model", "oomol-chat"),
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data analyst extracting insights. Be specific and quantitative.",
                    },
                    {"role": "user", "content": insight_prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )

            insight = insight_response.choices[0].message.content.strip()

        except Exception as e:
            insight = step_plan.get("expected_insight", "Analysis completed")

        # Record step
        exploration_steps.append(
            {
                "step_number": step_num,
                "transformation": step_plan.get("explanation", ""),
                "sql_query": sql_query,
                "insight": insight,
            }
        )

        # Update current dataframe for next iteration
        current_df = transformed_df

    context.report_progress(70)

    # Generate final report
    if not exploration_steps:
        final_report = f"# Exploration Report\n\nGoal: {exploration_goal}\n\nNo exploration steps were completed."
    else:
        # Prepare summary of all findings
        findings_summary = "\n\n".join(
            [
                f"**Step {s['step_number']}**: {s['transformation']}\n- Finding: {s['insight']}"
                for s in exploration_steps
            ]
        )

        summary_prompt = f"""Exploration Goal: {exploration_goal}

Exploration Steps:
{findings_summary}

Generate a comprehensive markdown report summarizing the key findings.
"""

        try:
            summary_response = client.chat.completions.create(
                model=llm.get("model", "oomol-chat"),
                messages=[
                    {"role": "system", "content": SUMMARIZE_SYSTEM_PROMPT},
                    {"role": "user", "content": summary_prompt},
                ],
                temperature=0.5,
                max_tokens=2000,
            )

            final_report = summary_response.choices[0].message.content.strip()

        except Exception as e:
            # Fallback to basic report
            final_report = f"""# Data Exploration Report

## Goal
{exploration_goal}

## Findings

{findings_summary}

## Conclusion
Completed {len(exploration_steps)} exploration steps.
"""

    context.report_progress(90)

    # Preview the report
    context.preview({"type": "markdown", "data": final_report})

    context.report_progress(100)

    return {"exploration_steps": exploration_steps, "final_report": final_report}
