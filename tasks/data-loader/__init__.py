#region generated meta
import typing
class Inputs(typing.TypedDict):
    source_type: typing.Literal["csv", "excel", "json"]
    file_path: str

class Outputs(typing.TypedDict):
    data_table: dict
    preview_html: str
#endregion

from oocana import Context
import pandas as pd
import json

async def main(params: Inputs, context: Context) -> Outputs:
    """
    Load tabular data from various file formats.

    Supports CSV, Excel, and JSON files and converts them to a standard
    table format with schema inference.
    """
    source_type = params["source_type"]
    file_path = params["file_path"]

    # Validate file path
    if not file_path:
        raise ValueError("File path is required")

    # Load data based on source type
    try:
        if source_type == "csv":
            df = pd.read_csv(file_path)
        elif source_type == "excel":
            df = pd.read_excel(file_path)
        elif source_type == "json":
            df = pd.read_json(file_path)
        else:
            raise ValueError(f"Unsupported source type: {source_type}")
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except Exception as e:
        raise RuntimeError(f"Failed to load {source_type} file: {str(e)}")

    # Validate loaded data
    if df.empty:
        raise ValueError("Loaded data is empty")

    # Infer schema
    schema = infer_schema(df)

    # Generate HTML preview (first 10 rows)
    preview_html = df.head(10).to_html(index=False, classes="data-table")

    # Preview the data
    context.preview({
        "type": "html",
        "data": f"""
        <style>
            .data-table {{
                border-collapse: collapse;
                width: 100%;
                font-family: Arial, sans-serif;
                font-size: 12px;
            }}
            .data-table th {{
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                text-align: left;
            }}
            .data-table td {{
                border: 1px solid #ddd;
                padding: 8px;
            }}
            .data-table tr:nth-child(even) {{
                background-color: #f2f2f2;
            }}
        </style>
        <h3>Data Preview ({len(df)} rows × {len(df.columns)} columns)</h3>
        {preview_html}
        """
    })

    # Convert to standard format
    data_table = {
        "columns": df.columns.tolist(),
        "rows": df.to_dict("records"),
        "schema": schema
    }

    return {
        "data_table": data_table,
        "preview_html": preview_html
    }


def infer_schema(df: pd.DataFrame) -> dict:
    """
    Infer schema from DataFrame.

    Returns a dictionary mapping column names to their types and statistics.
    """
    schema = {}

    for col in df.columns:
        col_info = {
            "name": col,
            "type": str(df[col].dtype),
            "nullable": bool(df[col].isnull().any()),
            "unique_count": int(df[col].nunique())
        }

        # Add type-specific info
        if pd.api.types.is_numeric_dtype(df[col]):
            col_info["semantic_type"] = "quantitative"
            col_info["min"] = float(df[col].min()) if not df[col].isnull().all() else None
            col_info["max"] = float(df[col].max()) if not df[col].isnull().all() else None
            col_info["mean"] = float(df[col].mean()) if not df[col].isnull().all() else None
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            col_info["semantic_type"] = "temporal"
        else:
            col_info["semantic_type"] = "nominal"
            col_info["sample_values"] = df[col].dropna().head(3).tolist()

        schema[col] = col_info

    return schema
