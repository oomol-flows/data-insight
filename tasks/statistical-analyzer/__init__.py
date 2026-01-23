#region generated meta
import typing
from oocana import LLMModelOptions
class Inputs(typing.TypedDict):
    data_table: dict
    analysis_type: typing.Literal["correlation", "t_test", "descriptive_stats", "normality_test"]
    variables: str | None
    llm: LLMModelOptions
class Outputs(typing.TypedDict):
    test_result: typing.NotRequired[dict]
    interpretation: typing.NotRequired[str]
    visualization: typing.NotRequired[str | None]
#endregion

from oocana import Context
from openai import OpenAI
import pandas as pd
import numpy as np
from scipy import stats
import json
import matplotlib.pyplot as plt


async def main(params: Inputs, context: Context) -> Outputs:
    """
    Perform statistical analysis on data with AI-powered interpretation.

    Supports:
    - Correlation analysis (Pearson, Spearman)
    - T-test (two sample comparison)
    - Descriptive statistics
    - Normality tests (Shapiro-Wilk)
    """
    context.report_progress(0)

    data_table = params["data_table"]
    analysis_type = params["analysis_type"]
    variables = params.get("variables") or {}
    llm = params["llm"]

    # Build DataFrame
    df = pd.DataFrame(data_table["rows"])

    if df.empty:
        raise ValueError("Data table is empty")

    context.report_progress(20)

    # Perform analysis based on type
    if analysis_type == "descriptive_stats":
        test_result = compute_descriptive_stats(df)
        visualization = None

    elif analysis_type == "correlation":
        independent_vars = variables.get("independent", [])
        if not independent_vars:
            # Auto-select numeric columns
            independent_vars = df.select_dtypes(include=[np.number]).columns.tolist()

        if len(independent_vars) < 2:
            raise ValueError("Correlation analysis requires at least 2 numeric variables")

        test_result = compute_correlation(df, independent_vars)
        visualization = create_correlation_heatmap(df, independent_vars, context)

    elif analysis_type == "t_test":
        dependent_var = variables.get("dependent")
        group_col = variables.get("group_column")

        if not dependent_var or not group_col:
            raise ValueError("T-test requires 'dependent' variable and 'group_column' in variables")

        test_result = compute_t_test(df, dependent_var, group_col)
        visualization = create_box_plot(df, dependent_var, group_col, context)

    elif analysis_type == "normality_test":
        dependent_var = variables.get("dependent")
        if not dependent_var:
            # Auto-select first numeric column
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if not numeric_cols:
                raise ValueError("No numeric columns found for normality test")
            dependent_var = numeric_cols[0]

        test_result = compute_normality_test(df, dependent_var)
        visualization = create_distribution_plot(df, dependent_var, context)

    else:
        raise ValueError(f"Unsupported analysis type: {analysis_type}")

    context.report_progress(60)

    # Generate AI interpretation
    interpretation = await generate_interpretation(
        analysis_type, test_result, llm, context
    )

    context.report_progress(90)

    # No need for separate preview - plt.show() already displayed charts
    context.report_progress(100)

    return {
        "test_result": test_result,
        "interpretation": interpretation,
        "visualization": visualization
    }


def compute_descriptive_stats(df: pd.DataFrame) -> dict:
    """Compute descriptive statistics for all numeric columns"""
    numeric_df = df.select_dtypes(include=[np.number])

    if numeric_df.empty:
        raise ValueError("No numeric columns found in data")

    stats_dict = {
        "summary": numeric_df.describe().to_dict(),
        "columns": numeric_df.columns.tolist(),
        "row_count": len(df)
    }

    return stats_dict


def compute_correlation(df: pd.DataFrame, variables: list) -> dict:
    """Compute correlation matrix (Pearson)"""
    subset = df[variables]

    # Remove non-numeric columns
    subset = subset.select_dtypes(include=[np.number])

    corr_matrix = subset.corr(method="pearson")

    return {
        "method": "Pearson",
        "correlation_matrix": corr_matrix.to_dict(),
        "variables": variables,
        "significant_correlations": find_significant_correlations(corr_matrix)
    }


def find_significant_correlations(corr_matrix: pd.DataFrame, threshold: float = 0.5) -> list:
    """Find variable pairs with correlation > threshold"""
    significant = []

    for i in range(len(corr_matrix.columns)):
        for j in range(i + 1, len(corr_matrix.columns)):
            var1 = corr_matrix.columns[i]
            var2 = corr_matrix.columns[j]
            corr_value = corr_matrix.iloc[i, j]

            if abs(corr_value) >= threshold:
                significant.append({
                    "var1": var1,
                    "var2": var2,
                    "correlation": float(corr_value),
                    "strength": "strong" if abs(corr_value) >= 0.7 else "moderate"
                })

    return significant


def compute_t_test(df: pd.DataFrame, dependent_var: str, group_col: str) -> dict:
    """Perform independent t-test between two groups"""
    groups = df[group_col].unique()

    if len(groups) != 2:
        raise ValueError(f"T-test requires exactly 2 groups, found {len(groups)}")

    group1_data = df[df[group_col] == groups[0]][dependent_var].dropna()
    group2_data = df[df[group_col] == groups[1]][dependent_var].dropna()

    # Perform t-test
    statistic, p_value = stats.ttest_ind(group1_data, group2_data)

    # Compute effect size (Cohen's d)
    mean_diff = group1_data.mean() - group2_data.mean()
    pooled_std = np.sqrt(((len(group1_data) - 1) * group1_data.std() ** 2 +
                           (len(group2_data) - 1) * group2_data.std() ** 2) /
                          (len(group1_data) + len(group2_data) - 2))
    cohens_d = mean_diff / pooled_std if pooled_std != 0 else 0

    return {
        "test": "Independent T-Test",
        "dependent_variable": dependent_var,
        "group_variable": group_col,
        "groups": {
            str(groups[0]): {
                "mean": float(group1_data.mean()),
                "std": float(group1_data.std()),
                "n": int(len(group1_data))
            },
            str(groups[1]): {
                "mean": float(group2_data.mean()),
                "std": float(group2_data.std()),
                "n": int(len(group2_data))
            }
        },
        "t_statistic": float(statistic),
        "p_value": float(p_value),
        "cohens_d": float(cohens_d),
        "significant": p_value < 0.05
    }


def compute_normality_test(df: pd.DataFrame, variable: str) -> dict:
    """Perform Shapiro-Wilk normality test"""
    data = df[variable].dropna()

    if len(data) < 3:
        raise ValueError("Normality test requires at least 3 data points")

    statistic, p_value = stats.shapiro(data)

    return {
        "test": "Shapiro-Wilk Normality Test",
        "variable": variable,
        "statistic": float(statistic),
        "p_value": float(p_value),
        "is_normal": p_value >= 0.05,
        "sample_size": int(len(data)),
        "mean": float(data.mean()),
        "std": float(data.std())
    }


def create_correlation_heatmap(df: pd.DataFrame, variables: list, context: Context) -> str:
    """Create correlation heatmap visualization"""
    subset = df[variables].select_dtypes(include=[np.number])
    corr_matrix = subset.corr()

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(corr_matrix, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')

    # Set ticks
    ax.set_xticks(range(len(corr_matrix.columns)))
    ax.set_yticks(range(len(corr_matrix.columns)))
    ax.set_xticklabels(corr_matrix.columns, rotation=45, ha='right')
    ax.set_yticklabels(corr_matrix.columns)

    # Add colorbar
    plt.colorbar(im, ax=ax)

    # Add correlation values
    for i in range(len(corr_matrix.columns)):
        for j in range(len(corr_matrix.columns)):
            text = ax.text(j, i, f'{corr_matrix.iloc[i, j]:.2f}',
                          ha="center", va="center", color="black", fontsize=9)

    ax.set_title("Correlation Matrix")
    plt.tight_layout()

    # Save to PNG file
    output_path = f"{context.session_dir}/correlation_heatmap.png"
    plt.savefig(output_path, format='png', dpi=150, bbox_inches='tight')

    # Show for preview
    plt.show()
    plt.close()

    return output_path


def create_box_plot(df: pd.DataFrame, dependent_var: str, group_col: str, context: Context) -> str:
    """Create box plot for group comparison"""
    fig, ax = plt.subplots(figsize=(8, 6))

    groups = df[group_col].unique()
    data_by_group = [df[df[group_col] == g][dependent_var].dropna() for g in groups]

    ax.boxplot(data_by_group, labels=groups)
    ax.set_xlabel(group_col)
    ax.set_ylabel(dependent_var)
    ax.set_title(f'{dependent_var} by {group_col}')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save to PNG file
    output_path = f"{context.session_dir}/box_plot.png"
    plt.savefig(output_path, format='png', dpi=150, bbox_inches='tight')

    # Show for preview
    plt.show()
    plt.close()

    return output_path


def create_distribution_plot(df: pd.DataFrame, variable: str, context: Context) -> str:
    """Create histogram with normal distribution overlay"""
    data = df[variable].dropna()

    fig, ax = plt.subplots(figsize=(8, 6))

    # Histogram
    ax.hist(data, bins=30, density=True, alpha=0.7, color='steelblue', edgecolor='black')

    # Overlay normal distribution
    mu, sigma = data.mean(), data.std()
    x = np.linspace(data.min(), data.max(), 100)
    ax.plot(x, stats.norm.pdf(x, mu, sigma), 'r-', linewidth=2, label='Normal Distribution')

    ax.set_xlabel(variable)
    ax.set_ylabel('Density')
    ax.set_title(f'Distribution of {variable}')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save to PNG file
    output_path = f"{context.session_dir}/distribution_plot.png"
    plt.savefig(output_path, format='png', dpi=150, bbox_inches='tight')

    # Show for preview
    plt.show()
    plt.close()

    return output_path


async def generate_interpretation(
    analysis_type: str,
    test_result: dict,
    llm: dict,
    context: Context
) -> str:
    """Generate AI interpretation of statistical results"""

    # Build prompt based on analysis type
    if analysis_type == "descriptive_stats":
        prompt = f"""Interpret these descriptive statistics:

{json.dumps(test_result, indent=2)}

Provide a concise summary (2-3 sentences) highlighting:
1. Key measures of central tendency (mean, median)
2. Variability (standard deviation, range)
3. Any notable patterns or outliers"""

    elif analysis_type == "correlation":
        prompt = f"""Interpret this correlation analysis:

{json.dumps(test_result, indent=2)}

Provide a concise interpretation (2-3 sentences) including:
1. Strength and direction of significant correlations
2. What these relationships might indicate
3. Any notable patterns"""

    elif analysis_type == "t_test":
        prompt = f"""Interpret this t-test result:

{json.dumps(test_result, indent=2)}

Provide a concise interpretation (2-3 sentences) including:
1. Whether groups differ significantly (p-value < 0.05)
2. Magnitude of the difference (effect size)
3. Practical significance of the finding"""

    elif analysis_type == "normality_test":
        prompt = f"""Interpret this normality test:

{json.dumps(test_result, indent=2)}

Provide a concise interpretation (2-3 sentences) including:
1. Whether data is normally distributed (p-value >= 0.05)
2. Implications for further analysis
3. Recommendations if non-normal"""

    else:
        prompt = f"Interpret these statistical results:\n\n{json.dumps(test_result, indent=2)}"

    # Call LLM
    client = OpenAI(
        base_url=context.oomol_llm_env.get("base_url_v1"),
        api_key=await context.oomol_token(),
    )

    max_tokens = llm.get("max_tokens", 128000)

    # Use streaming if max_tokens > 4096 (API requirement)
    if max_tokens > 4096:
        stream = client.chat.completions.create(
            model=llm.get("model", "oomol-chat"),
            messages=[
                {
                    "role": "system",
                    "content": "You are a statistical expert. Provide clear, concise interpretations of statistical results for a general audience. Use plain language and avoid jargon."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=llm.get("temperature", 0.3),
            max_tokens=max_tokens,
            stream=True,
        )

        # Collect streamed response
        content = ""
        for chunk in stream:
            if chunk.choices[0].delta.content:
                content += chunk.choices[0].delta.content

        return content.strip()
    else:
        response = client.chat.completions.create(
            model=llm.get("model", "oomol-chat"),
            messages=[
                {
                    "role": "system",
                    "content": "You are a statistical expert. Provide clear, concise interpretations of statistical results for a general audience. Use plain language and avoid jargon."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=llm.get("temperature", 0.3),
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content.strip()
