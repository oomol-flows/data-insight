#region generated meta
import typing
class Inputs(typing.TypedDict):
    charts: list[dict]
class Outputs(typing.TypedDict):
    charts_array: typing.NotRequired[list[dict]]
#endregion

from oocana import Context


async def main(params: Inputs, context: Context) -> Outputs:
    """
    Build an array of chart objects from a list input.

    Automatically filters out charts that have no image data.
    Each chart object should contain: title, image (base64), and description.
    """
    input_charts = params.get("charts", [])

    if not input_charts:
        raise ValueError("No charts provided. The 'charts' parameter is required and must be a non-empty array.")

    # Filter out invalid charts (those without images)
    valid_charts = []
    for i, chart in enumerate(input_charts):
        if not isinstance(chart, dict):
            raise ValueError(f"Chart at index {i} is not a valid object: {chart}")

        image = chart.get("image")
        if image:  # Only include charts with image data
            valid_charts.append({
                "title": chart.get("title") or f"Chart {i + 1}",
                "image": image,
                "description": chart.get("description") or ""
            })

    if not valid_charts:
        raise ValueError("No valid charts found. All provided charts are missing image data.")

    # Preview the chart count
    preview_html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px;">
        <h3>📊 Chart Array Builder</h3>
        <p><strong>Input charts:</strong> {len(input_charts)}</p>
        <p><strong>Valid charts:</strong> {len(valid_charts)}</p>
        <ul style="line-height: 1.8;">
    """

    for chart in valid_charts:
        preview_html += f"<li><strong>{chart['title']}</strong>"
        if chart['description']:
            preview_html += f" - {chart['description'][:100]}"
            if len(chart['description']) > 100:
                preview_html += "..."
        preview_html += "</li>"

    preview_html += """
        </ul>
    </div>
    """

    context.preview({"type": "html", "data": preview_html})

    return {"charts_array": valid_charts}
