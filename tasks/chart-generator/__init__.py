#region generated meta
import typing
class Inputs(typing.TypedDict):
    data_table: dict
    chart_type: typing.Literal["bar", "line", "scatter", "area", "pie", "heatmap"]
    x_field: str
    y_field: str
    color_field: typing.Optional[str]
    size_field: typing.Optional[str]

class Outputs(typing.TypedDict):
    vega_spec: dict
    chart_image: str
#endregion

from oocana import Context
import pandas as pd
import altair as alt
import vl_convert as vlc
import base64

async def main(params: Inputs, context: Context) -> Outputs:
    """
    Generate charts using Vega-Lite.

    Supports multiple chart types (bar, line, scatter, area, pie, heatmap)
    and outputs both Vega-Lite spec and rendered PNG image.
    """
    data_table = params["data_table"]
    chart_type = params["chart_type"]
    x_field = params["x_field"]
    y_field = params["y_field"]
    color_field = params.get("color_field")
    size_field = params.get("size_field")

    # Validate inputs
    if not data_table or not data_table.get("rows"):
        raise ValueError("Data table is empty or invalid")
    if not x_field or not y_field:
        raise ValueError("X and Y fields are required")

    # Convert to DataFrame
    df = pd.DataFrame(data_table["rows"])

    # Validate field names
    if x_field not in df.columns:
        raise ValueError(f"X field '{x_field}' not found in data columns: {df.columns.tolist()}")
    if y_field not in df.columns:
        raise ValueError(f"Y field '{y_field}' not found in data columns: {df.columns.tolist()}")
    if color_field and color_field not in df.columns:
        raise ValueError(f"Color field '{color_field}' not found in data columns: {df.columns.tolist()}")
    if size_field and size_field not in df.columns:
        raise ValueError(f"Size field '{size_field}' not found in data columns: {df.columns.tolist()}")

    # Report progress
    context.report_progress(20)

    # Detect field types
    field_types = detect_field_types(df)

    # Build chart based on type
    context.report_progress(40)

    chart = build_chart(
        df=df,
        chart_type=chart_type,
        x_field=x_field,
        y_field=y_field,
        color_field=color_field,
        size_field=size_field,
        field_types=field_types
    )

    # Convert to Vega-Lite spec
    vega_spec = chart.to_dict()

    context.report_progress(60)

    # Render to PNG
    try:
        png_data = vlc.vegalite_to_png(vega_spec, scale=2)
        base64_image = base64.b64encode(png_data).decode()
    except Exception as e:
        raise RuntimeError(f"Failed to render chart: {str(e)}")

    context.report_progress(80)

    # Preview the chart
    context.preview({
        "type": "image",
        "data": f"data:image/png;base64,{base64_image}"
    })

    context.report_progress(100)

    return {
        "vega_spec": vega_spec,
        "chart_image": base64_image
    }


def detect_field_types(df: pd.DataFrame) -> dict:
    """
    Detect Vega-Lite field types for each column.

    Returns: {"field_name": "quantitative" | "nominal" | "ordinal" | "temporal"}
    """
    types = {}

    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            unique_count = df[col].nunique()
            total_count = len(df)

            # Ordinal if low cardinality
            if unique_count < 20 and unique_count < total_count * 0.5:
                types[col] = "ordinal"
            else:
                types[col] = "quantitative"

        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            types[col] = "temporal"
        else:
            types[col] = "nominal"

    return types


def build_chart(
    df: pd.DataFrame,
    chart_type: str,
    x_field: str,
    y_field: str,
    color_field: str | None,
    size_field: str | None,
    field_types: dict
) -> alt.Chart:
    """
    Build Altair chart based on parameters.
    """
    # Base chart
    base = alt.Chart(df).properties(
        width=600,
        height=400,
        title=f"{chart_type.capitalize()} Chart"
    )

    # Build encoding
    x_encoding = alt.X(
        x_field,
        type=field_types.get(x_field, "nominal"),
        title=x_field
    )
    y_encoding = alt.Y(
        y_field,
        type=field_types.get(y_field, "quantitative"),
        title=y_field
    )

    # Color encoding
    color_encoding = None
    if color_field:
        color_encoding = alt.Color(
            color_field,
            type=field_types.get(color_field, "nominal")
        )

    # Size encoding
    size_encoding = None
    if size_field:
        size_encoding = alt.Size(
            size_field,
            type=field_types.get(size_field, "quantitative")
        )

    # Build chart by type
    if chart_type == "bar":
        chart = base.mark_bar().encode(
            x=x_encoding,
            y=y_encoding,
            color=color_encoding if color_encoding else alt.value("steelblue")
        )

    elif chart_type == "line":
        chart = base.mark_line(point=True).encode(
            x=x_encoding,
            y=y_encoding,
            color=color_encoding if color_encoding else alt.value("steelblue")
        )

    elif chart_type == "scatter":
        encodings = {
            "x": x_encoding,
            "y": y_encoding
        }
        if color_encoding:
            encodings["color"] = color_encoding
        else:
            encodings["color"] = alt.value("steelblue")

        if size_encoding:
            encodings["size"] = size_encoding

        chart = base.mark_circle().encode(**encodings)

    elif chart_type == "area":
        chart = base.mark_area().encode(
            x=x_encoding,
            y=y_encoding,
            color=color_encoding if color_encoding else alt.value("steelblue")
        )

    elif chart_type == "pie":
        # Pie chart uses theta encoding
        chart = base.mark_arc().encode(
            theta=alt.Theta(y_field, type="quantitative"),
            color=alt.Color(x_field, type=field_types.get(x_field, "nominal"))
        )

    elif chart_type == "heatmap":
        chart = base.mark_rect().encode(
            x=x_encoding,
            y=y_encoding,
            color=alt.Color(
                color_field if color_field else y_field,
                type="quantitative",
                scale=alt.Scale(scheme="viridis")
            )
        )

    else:
        raise ValueError(f"Unsupported chart type: {chart_type}")

    return chart
