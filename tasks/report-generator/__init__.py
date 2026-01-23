# region generated meta
import typing


class Inputs(typing.TypedDict):
    charts: typing.List[typing.Dict[str, str]]
    analysis_goal: str
    llm: typing.Dict[str, typing.Any]


class Outputs(typing.TypedDict):
    markdown_report: str
    report_file: str


# endregion

from oocana import Context
from openai import OpenAI
import json


REPORT_GEN_SYSTEM_PROMPT = """You are an expert data analyst writing comprehensive reports.

Your task is to generate a professional markdown report based on the provided information and analysis goal.

The report MUST include:
1. **Executive Summary**: High-level overview of key findings (2-3 sentences)
2. **Key Findings**: Bullet points highlighting the most important insights
3. **Detailed Analysis**: In-depth explanation of each finding with supporting evidence
4. **Recommendations**: Actionable suggestions based on the analysis
5. **Conclusion**: Summary and next steps

Guidelines:
- Use professional data analysis language
- If charts are available, reference them using placeholders like {{chart_1}}, {{chart_2}}, etc.
- Be specific and quantitative when possible
- Provide context and interpretation, not just descriptions
- Keep the tone objective and evidence-based

Output pure markdown without code blocks or extra formatting.
"""


def extract_json_from_response(content: str) -> dict:
    """Extract JSON from LLM response that might contain markdown code blocks"""
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
        # If direct parsing fails, try to find JSON object
        import re

        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        raise ValueError(f"Could not extract valid JSON from response: {content[:200]}")


async def main(params: Inputs, context: Context) -> Outputs:
    """
    Generate a comprehensive markdown report with embedded charts.

    Reference: data-formulator/py-src/data_formulator/agents/agent_report_gen.py
    """
    charts = params["charts"]
    analysis_goal = params["analysis_goal"]
    llm = params["llm"]

    context.report_progress(10)

    # 1. Prepare chart summaries for LLM
    chart_summaries = []
    if charts:
        for i, chart in enumerate(charts, 1):
            summary = f"Chart {i}: {chart.get('title', 'Untitled')}"
            if chart.get("description"):
                summary += f" - {chart['description']}"
            chart_summaries.append(summary)
    else:
        # No charts available - will generate text-only report
        chart_summaries.append("No visualizations were generated for this analysis.")

    context.report_progress(20)

    # 2. Construct prompt for report generation
    if charts:
        user_prompt = f"""Analysis Goal: {analysis_goal}

Available Charts:
{chr(10).join(chart_summaries)}

Generate a comprehensive markdown report following the required structure.
Reference charts using placeholders: {{{{chart_1}}}}, {{{{chart_2}}}}, etc.

The report should be insightful, actionable, and well-structured.
"""
    else:
        user_prompt = f"""Analysis Goal: {analysis_goal}

Note: No visualizations were generated for this analysis. Please create a text-based report based on the analysis goal.

Generate a comprehensive markdown report following the required structure.

The report should be insightful, actionable, and well-structured.
"""

    # 3. Call LLM with streaming
    try:
        client = OpenAI(
            base_url=context.oomol_llm_env.get("base_url_v1"),
            api_key=await context.oomol_token(),
        )

        context.report_progress(30)

        # Use streaming for better UX
        stream = client.chat.completions.create(
            model=llm.get("model", "oomol-chat"),
            messages=[
                {"role": "system", "content": REPORT_GEN_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=llm.get("temperature", 0.5),
            max_tokens=llm.get("max_tokens", 128000),
            stream=True,
        )

        # 4. Collect streaming response
        markdown_content = ""
        chunk_count = 0
        for chunk in stream:
            if chunk.choices[0].delta.content:
                markdown_content += chunk.choices[0].delta.content
                chunk_count += 1

                # Update progress during streaming (30% -> 70%)
                if chunk_count % 10 == 0:
                    progress = min(70, 30 + (chunk_count // 10) * 2)
                    context.report_progress(progress)

        context.report_progress(70)

    except Exception as e:
        raise RuntimeError(f"Failed to generate report via LLM: {str(e)}")

    if not markdown_content.strip():
        raise ValueError("LLM returned empty report content")

    # 5. Replace chart placeholders with actual base64 images
    for i, chart in enumerate(charts, 1):
        placeholder = f"{{{{chart_{i}}}}}"
        chart_title = chart.get("title", f"Chart {i}")
        chart_image = chart.get("image", "")

        if chart_image:
            # Embed base64 image in markdown
            image_markdown = f"\n![{chart_title}](data:image/png;base64,{chart_image})\n"
            markdown_content = markdown_content.replace(placeholder, image_markdown)
        else:
            # If no image, just show title
            markdown_content = markdown_content.replace(
                placeholder, f"\n**{chart_title}**\n"
            )

    context.report_progress(80)

    # 6. Save markdown to file
    report_path = f"{context.session_dir}/analysis_report.md"
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
    except Exception as e:
        raise RuntimeError(f"Failed to save report file: {str(e)}")

    context.report_progress(90)

    # 7. Preview the report
    context.preview({"type": "markdown", "data": markdown_content})

    context.report_progress(100)

    return {"markdown_report": markdown_content, "report_file": report_path}
