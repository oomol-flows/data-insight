#region generated meta
import typing
class Inputs(typing.TypedDict):
    chart_image: str
    explanation: str
class Outputs(typing.TypedDict):
    charts_list: typing.NotRequired[list[dict]]
#endregion

from oocana import Context


async def main(params: Inputs, context: Context) -> Outputs:
    """Build a chart array from individual chart parameters."""
    charts = [
        {
            "title": "Analysis Visualization",
            "image": params["chart_image"],
            "description": params["explanation"]
        }
    ]
    
    return {"charts_list": charts}
