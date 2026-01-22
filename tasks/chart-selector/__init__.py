#region generated meta
import typing
class Inputs(typing.TypedDict):
    recommendations: list[dict]
    selection_index: float | None
class Outputs(typing.TypedDict):
    chart_type: typing.NotRequired[typing.Literal["bar", "line", "scatter", "area", "pie", "heatmap"]]
    x_field: typing.NotRequired[str]
    y_field: typing.NotRequired[str]
    color_field: typing.NotRequired[str | None]
    size_field: typing.NotRequired[str | None]
    selected_recommendation: typing.NotRequired[dict]
#endregion

from oocana import Context


async def main(params: Inputs, context: Context) -> Outputs:
    """
    Select a chart recommendation and extract its configuration.

    This block bridges Chart Recommender and Chart Generator by:
    1. Picking one recommendation from the array (by index)
    2. Extracting individual field parameters
    3. Making them compatible with Chart Generator inputs
    """
    recommendations = params["recommendations"]

    if not recommendations:
        raise ValueError("No recommendations provided. The recommendations array is empty.")

    # Get selection index (default to 0 = highest priority)
    index = params.get("selection_index", 0)

    # Validate index
    if index < 0 or index >= len(recommendations):
        raise ValueError(
            f"Invalid selection_index {index}. Must be between 0 and {len(recommendations) - 1}."
        )

    # Select the recommendation
    selected = recommendations[index]

    # Extract fields (use empty string for None values to match Chart Generator expectations)
    chart_type = selected.get("chart_type", "")
    x_field = selected.get("x_field", "")
    y_field = selected.get("y_field", "")
    color_field = selected.get("color_field") or None
    size_field = selected.get("size_field") or None

    # Validate required fields
    if not chart_type:
        raise ValueError(f"Selected recommendation (index {index}) is missing 'chart_type'.")
    if not x_field:
        raise ValueError(f"Selected recommendation (index {index}) is missing 'x_field'.")
    if not y_field:
        raise ValueError(f"Selected recommendation (index {index}) is missing 'y_field'.")

    # Preview the selection
    preview_html = f"""
    <div style="font-family: system-ui; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px;">
        <h2 style="margin: 0 0 16px 0; font-size: 20px;">✨ Selected Chart Configuration</h2>

        <div style="background: rgba(255,255,255,0.1); padding: 16px; border-radius: 6px; margin-bottom: 12px;">
            <div style="font-size: 14px; opacity: 0.9; margin-bottom: 8px;">
                <strong>Selection:</strong> Recommendation #{index + 1} (Priority {selected.get('priority', 'N/A')})
            </div>
            <div style="font-size: 24px; font-weight: bold;">{chart_type.upper()}</div>
        </div>

        <div style="background: rgba(255,255,255,0.1); padding: 16px; border-radius: 6px;">
            <div style="margin-bottom: 8px;"><strong>X Axis:</strong> {x_field}</div>
            <div style="margin-bottom: 8px;"><strong>Y Axis:</strong> {y_field}</div>
            {f'<div style="margin-bottom: 8px;"><strong>Color:</strong> {color_field}</div>' if color_field else ''}
            {f'<div style="margin-bottom: 8px;"><strong>Size:</strong> {size_field}</div>' if size_field else ''}
        </div>

        {f'''
        <div style="background: rgba(255,255,255,0.1); padding: 16px; border-radius: 6px; margin-top: 12px;">
            <div style="font-size: 13px; opacity: 0.9;"><strong>Reason:</strong></div>
            <div style="margin-top: 6px; font-size: 14px;">{selected.get('reason', 'No reason provided')}</div>
        </div>
        ''' if selected.get('reason') else ''}
    </div>
    """

    context.preview({"type": "html", "data": preview_html})

    return {
        "chart_type": chart_type,
        "x_field": x_field,
        "y_field": y_field,
        "color_field": color_field,
        "size_field": size_field,
        "selected_recommendation": selected
    }
