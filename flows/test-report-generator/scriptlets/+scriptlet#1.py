# region generated meta
import typing


class Inputs(typing.TypedDict):
    pass


class Outputs(typing.TypedDict):
    sample_charts: typing.List[typing.Dict[str, str]]


# endregion

from oocana import Context
import base64


async def main(params: Inputs, context: Context) -> Outputs:
    """Generate sample chart data for testing report generator"""

    # Create a simple sample chart (using a tiny 1x1 transparent PNG as placeholder)
    # In real usage, this would come from the chart-generator block
    tiny_png = base64.b64encode(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    ).decode("utf-8")

    sample_charts = [
        {
            "title": "Sales by Region",
            "image": tiny_png,
            "description": "Bar chart showing total sales across North, South, East, and West regions",
        },
        {
            "title": "Monthly Revenue Trend",
            "image": tiny_png,
            "description": "Line chart displaying revenue growth over the past 12 months",
        },
        {
            "title": "Product Category Distribution",
            "image": tiny_png,
            "description": "Pie chart showing the percentage of sales by product category",
        },
    ]

    return {"sample_charts": sample_charts}
