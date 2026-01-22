#region generated meta
import typing


class Inputs(typing.TypedDict):
    chart1_image: str | None
    chart1_title: str | None
    chart1_description: str | None
    chart2_image: str | None
    chart2_title: str | None
    chart2_description: str | None
    chart3_image: str | None
    chart3_title: str | None
    chart3_description: str | None
    chart4_image: str | None
    chart4_title: str | None
    chart4_description: str | None
    chart5_image: str | None
    chart5_title: str | None
    chart5_description: str | None


class Outputs(typing.TypedDict):
    charts_array: typing.List[typing.Dict[str, str]]


#endregion

from oocana import Context


async def main(params: Inputs, context: Context) -> Outputs:
    """
    Build an array of chart objects from individual chart inputs.

    Automatically filters out charts that have no image data.
    Each chart object contains: title, image (base64), and description.
    """
    charts = []

    # Process up to 5 charts
    for i in range(1, 6):
        image_key = f"chart{i}_image"
        title_key = f"chart{i}_title"
        desc_key = f"chart{i}_description"

        image = params.get(image_key)

        # Only include charts that have an image
        if image:
            charts.append({
                "title": params.get(title_key) or f"Chart {i}",
                "image": image,
                "description": params.get(desc_key) or ""
            })

    if not charts:
        raise ValueError("No charts provided. At least one chart image is required.")

    # Preview the chart count
    preview_html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px;">
        <h3>Chart Array Builder</h3>
        <p><strong>Total charts:</strong> {len(charts)}</p>
        <ul>
    """

    for chart in charts:
        preview_html += f"<li><strong>{chart['title']}</strong>"
        if chart['description']:
            preview_html += f" - {chart['description']}"
        preview_html += "</li>"

    preview_html += """
        </ul>
    </div>
    """

    context.preview({"type": "html", "data": preview_html})

    return {"charts_array": charts}
