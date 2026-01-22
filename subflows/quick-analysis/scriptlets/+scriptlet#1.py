#region generated meta
import typing
class Inputs(typing.TypedDict):
    chart_image: str
    chart_type: str
    chart_title: str
class Outputs(typing.TypedDict):
    charts: typing.NotRequired[list[dict]]
#endregion

from oocana import Context

async def main(params: Inputs, context: Context) -> Outputs:
    """Build chart array from single chart output"""
    chart = {
        "title": params.get("chart_title", "Chart"),
        "image": params["chart_image"],
        "description": f"{params.get('chart_type', 'chart').title()} visualization"
    }

    return {"charts": [chart]}
