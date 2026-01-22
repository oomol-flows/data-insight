# region generated meta
import typing


class Inputs(typing.TypedDict):
    chart_image: str


class Outputs(typing.TypedDict):
    charts_array: typing.List[typing.Dict[str, str]]


# endregion

from oocana import Context


async def main(params: Inputs, context: Context) -> Outputs:
    """Convert single chart image to array format for report generator"""

    chart_image = params["chart_image"]

    charts_array = [
        {
            "title": "Sales by Region",
            "image": chart_image,
            "description": "Bar chart showing total sales across different regions, sorted from highest to lowest",
        }
    ]

    return {"charts_array": charts_array}
