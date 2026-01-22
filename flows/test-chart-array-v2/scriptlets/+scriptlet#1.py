#region generated meta
import typing
class Inputs(typing.TypedDict):
    chart1_image: str
    chart1_title: str
    explanation: str
class Outputs(typing.TypedDict):
    charts_list: typing.NotRequired[list[dict]]
#endregion

from oocana import Context


async def main(params: Inputs, context: Context) -> Outputs:
    """
    Build a chart array from individual chart parameters.
    This scriptlet demonstrates how to prepare data for Chart Array Builder V2.
    """
    charts = [
        {
            "title": params["chart1_title"],
            "image": params["chart1_image"],
            "description": params["explanation"]
        }
    ]

    return {"charts_list": charts}
