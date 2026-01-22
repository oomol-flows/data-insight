#region generated meta
import typing
from oocana import LLMModelOptions


class Inputs(typing.TypedDict):
    data_table: typing.Dict[str, typing.Any]
    auto_clean: bool
    llm: LLMModelOptions


class Outputs(typing.TypedDict):
    quality_report: typing.Dict[str, typing.Any]
    cleaning_suggestions: str
    cleaned_table: typing.Dict[str, typing.Any]
    quality_visualization: str | None


#endregion

from oocana import Context
from openai import OpenAI
import pandas as pd
import numpy as np
import json
import altair as alt
import vl_convert as vlc
import base64


def analyze_missing_values(df: pd.DataFrame) -> dict:
    """Analyze missing values in dataframe"""
    missing = {}
    for col in df.columns:
        null_count = df[col].isnull().sum()
        if null_count > 0:
            missing[col] = {
                "count": int(null_count),
                "percentage": float(null_count / len(df) * 100)
            }
    return missing


def detect_outliers(df: pd.DataFrame) -> dict:
    """Detect outliers using IQR method"""
    outliers = {}
    numeric_cols = df.select_dtypes(include=['number']).columns

    for col in numeric_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1

        # Outliers are values outside [Q1 - 1.5*IQR, Q3 + 1.5*IQR]
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        outlier_mask = (df[col] < lower_bound) | (df[col] > upper_bound)
        outlier_count = outlier_mask.sum()

        if outlier_count > 0:
            outliers[col] = {
                "count": int(outlier_count),
                "percentage": float(outlier_count / len(df) * 100),
                "lower_bound": float(lower_bound),
                "upper_bound": float(upper_bound)
            }

    return outliers


def check_type_consistency(df: pd.DataFrame) -> list:
    """Check for type inconsistency issues"""
    issues = []

    for col in df.columns:
        # Check if numeric column has string values
        if pd.api.types.is_numeric_dtype(df[col]):
            continue

        # Try to convert to numeric
        try:
            pd.to_numeric(df[col], errors='raise')
            issues.append({
                "column": col,
                "issue": "Column appears numeric but stored as string",
                "recommendation": "Convert to numeric type"
            })
        except (ValueError, TypeError):
            pass

    return issues


def calculate_quality_score(missing: dict, outliers: dict, duplicates: int, total_rows: int) -> float:
    """Calculate overall quality score (0-100)"""
    score = 100.0

    # Deduct for missing values (max -30 points)
    if missing:
        avg_missing_pct = sum(v["percentage"] for v in missing.values()) / len(missing)
        score -= min(30, avg_missing_pct * 0.5)

    # Deduct for outliers (max -20 points)
    if outliers:
        avg_outlier_pct = sum(v["percentage"] for v in outliers.values()) / len(outliers)
        score -= min(20, avg_outlier_pct * 0.3)

    # Deduct for duplicates (max -20 points)
    if duplicates > 0:
        dup_pct = (duplicates / total_rows) * 100
        score -= min(20, dup_pct * 0.5)

    return max(0, score)


def create_quality_visualization(df: pd.DataFrame, missing: dict, outliers: dict) -> str:
    """Create a visualization showing data quality issues"""
    if not missing and not outliers:
        return ""

    # Create data for visualization
    viz_data = []

    # Add missing value info
    for col, info in missing.items():
        viz_data.append({
            "column": col,
            "issue_type": "Missing Values",
            "percentage": info["percentage"]
        })

    # Add outlier info
    for col, info in outliers.items():
        viz_data.append({
            "column": col,
            "issue_type": "Outliers",
            "percentage": info["percentage"]
        })

    if not viz_data:
        return ""

    viz_df = pd.DataFrame(viz_data)

    # Create bar chart
    chart = alt.Chart(viz_df).mark_bar().encode(
        x=alt.X("column:N", title="Column", sort="-y"),
        y=alt.Y("percentage:Q", title="Issue Percentage (%)"),
        color=alt.Color("issue_type:N", title="Issue Type"),
        tooltip=["column", "issue_type", alt.Tooltip("percentage:Q", format=".1f")]
    ).properties(
        width=600,
        height=300,
        title="Data Quality Issues by Column"
    )

    try:
        vega_spec = chart.to_dict()
        png_data = vlc.vegalite_to_png(vega_spec, scale=2)
        return base64.b64encode(png_data).decode()
    except Exception:
        return ""


def clean_dataframe(df: pd.DataFrame, missing: dict, outliers: dict) -> pd.DataFrame:
    """Automatically clean dataframe"""
    cleaned_df = df.copy()

    # Remove rows with too many missing values (>50% of columns)
    threshold = len(cleaned_df.columns) * 0.5
    cleaned_df = cleaned_df.dropna(thresh=threshold)

    # Fill remaining missing values
    for col in cleaned_df.columns:
        if cleaned_df[col].isnull().any():
            if pd.api.types.is_numeric_dtype(cleaned_df[col]):
                # Fill numeric with median
                cleaned_df[col].fillna(cleaned_df[col].median(), inplace=True)
            else:
                # Fill categorical with mode
                mode_val = cleaned_df[col].mode()
                if len(mode_val) > 0:
                    cleaned_df[col].fillna(mode_val[0], inplace=True)

    # Cap outliers at bounds (Winsorization)
    for col, info in outliers.items():
        lower = info["lower_bound"]
        upper = info["upper_bound"]
        cleaned_df[col] = cleaned_df[col].clip(lower=lower, upper=upper)

    # Remove duplicate rows
    cleaned_df = cleaned_df.drop_duplicates()

    return cleaned_df


def infer_schema(df: pd.DataFrame) -> dict:
    """Infer schema from cleaned dataframe"""
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
    """
    Analyze data quality and provide cleaning recommendations.

    Detects:
    - Missing values
    - Outliers (using IQR method)
    - Duplicate rows
    - Type inconsistencies

    Provides AI-powered cleaning suggestions.
    """
    data_table = params["data_table"]
    auto_clean = params["auto_clean"]
    llm = params["llm"]

    context.report_progress(10)

    # Convert to DataFrame
    df = pd.DataFrame(data_table["rows"])

    if df.empty:
        raise ValueError("Input data table is empty")

    # Analyze quality issues
    context.report_progress(20)
    missing = analyze_missing_values(df)

    context.report_progress(35)
    outliers = detect_outliers(df)

    context.report_progress(50)
    type_issues = check_type_consistency(df)

    # Count duplicates
    duplicate_count = int(df.duplicated().sum())

    # Calculate quality score
    quality_score = calculate_quality_score(missing, outliers, duplicate_count, len(df))

    context.report_progress(60)

    # Build quality report
    quality_report = {
        "overall_score": quality_score,
        "missing_values": missing,
        "outliers": outliers,
        "type_issues": type_issues,
        "duplicate_rows": duplicate_count
    }

    # Generate AI cleaning suggestions
    context.report_progress(70)

    summary = f"""Data Quality Analysis:
- Total rows: {len(df)}
- Overall quality score: {quality_score:.1f}/100
- Missing values: {len(missing)} columns affected
- Outliers: {len(outliers)} columns affected
- Duplicate rows: {duplicate_count}
- Type issues: {len(type_issues)}

Details:
{json.dumps(quality_report, indent=2)}
"""

    client = OpenAI(
        base_url=context.oomol_llm_env.get("base_url_v1"),
        api_key=await context.oomol_token(),
    )

    try:
        response = client.chat.completions.create(
            model=llm.get("model", "oomol-chat"),
            messages=[
                {
                    "role": "system",
                    "content": """You are a data quality expert. Analyze the quality report and provide:
1. Top 3 priority issues to fix
2. Specific cleaning recommendations for each issue
3. Potential risks of the issues if not addressed

Be concise and actionable."""
                },
                {"role": "user", "content": summary}
            ],
            temperature=llm.get("temperature", 0.5),
            max_tokens=1000
        )
        cleaning_suggestions = response.choices[0].message.content.strip()
    except Exception as e:
        cleaning_suggestions = f"Failed to generate AI suggestions: {str(e)}\n\nBasic recommendations:\n- Address missing values in {len(missing)} columns\n- Review outliers in {len(outliers)} columns\n- Remove {duplicate_count} duplicate rows"

    context.report_progress(80)

    # Create visualization
    quality_viz = create_quality_visualization(df, missing, outliers)

    # Auto-clean if enabled
    if auto_clean:
        cleaned_df = clean_dataframe(df, missing, outliers)
        cleaned_schema = infer_schema(cleaned_df)

        cleaned_table = {
            "columns": cleaned_df.columns.tolist(),
            "rows": cleaned_df.to_dict("records"),
            "schema": cleaned_schema
        }

        rows_removed = len(df) - len(cleaned_df)
    else:
        # If not cleaning, return original data
        cleaned_table = data_table
        rows_removed = 0

    context.report_progress(90)

    # Generate preview
    score_color = "#22c55e" if quality_score >= 80 else "#eab308" if quality_score >= 60 else "#ef4444"

    preview_html = f"""
<div style="font-family: system-ui, -apple-system, sans-serif; padding: 20px;">
    <div style="margin-bottom: 20px;">
        <h3 style="margin: 0 0 10px 0; color: #1f2937;">Data Quality Report</h3>
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 15px;">
            <div style="font-size: 36px; font-weight: bold; color: {score_color};">
                {quality_score:.1f}
            </div>
            <div style="font-size: 14px; color: #6b7280;">
                <div><strong>Quality Score</strong></div>
                <div>out of 100</div>
            </div>
        </div>
    </div>

    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;">
        <div style="padding: 15px; background: #fef3c7; border-radius: 8px;">
            <div style="font-size: 24px; font-weight: bold; color: #92400e;">{len(missing)}</div>
            <div style="font-size: 13px; color: #78350f;">Columns with Missing Values</div>
        </div>
        <div style="padding: 15px; background: #fed7aa; border-radius: 8px;">
            <div style="font-size: 24px; font-weight: bold; color: #9a3412;">{len(outliers)}</div>
            <div style="font-size: 13px; color: #7c2d12;">Columns with Outliers</div>
        </div>
        <div style="padding: 15px; background: #fecaca; border-radius: 8px;">
            <div style="font-size: 24px; font-weight: bold; color: #991b1b;">{duplicate_count}</div>
            <div style="font-size: 13px; color: #7f1d1d;">Duplicate Rows</div>
        </div>
        {"<div style='padding: 15px; background: #d1fae5; border-radius: 8px;'>" +
         f"<div style='font-size: 24px; font-weight: bold; color: #065f46;'>{rows_removed}</div>" +
         "<div style='font-size: 13px; color: #064e3b;'>Rows Cleaned</div></div>" if auto_clean else ""}
    </div>

    <div style="margin-top: 20px; padding: 15px; background: #eff6ff; border-left: 4px solid #3b82f6; border-radius: 4px;">
        <strong style="color: #1e40af;">AI Recommendations:</strong>
        <div style="color: #1e3a8a; margin-top: 10px; white-space: pre-wrap;">{cleaning_suggestions}</div>
    </div>
</div>
"""

    context.preview({"type": "html", "data": preview_html})

    context.report_progress(100)

    return {
        "quality_report": quality_report,
        "cleaning_suggestions": cleaning_suggestions,
        "cleaned_table": cleaned_table,
        "quality_visualization": quality_viz
    }
