#region generated meta
import typing
class Inputs(typing.TypedDict):
    source_type: typing.Literal["csv", "excel", "json", "mysql", "postgresql", "sqlite"]
    file_path: str | None
    database_config: dict | None
class Outputs(typing.TypedDict):
    data_table: typing.NotRequired[dict]
    preview_html: typing.NotRequired[str]
#endregion

from oocana import Context
import pandas as pd
import json


async def main(params: Inputs, context: Context) -> Outputs:
    """
    Load tabular data from various sources.

    Supports:
    - File formats: CSV, Excel, JSON
    - Databases: MySQL, PostgreSQL, SQLite

    Converts data to a standard table format with schema inference.
    """
    source_type = params["source_type"]
    file_path = params.get("file_path")
    database_config = params.get("database_config")

    context.report_progress(0)

    # Load data based on source type
    try:
        if source_type in ["csv", "excel", "json"]:
            # File-based sources
            if not file_path:
                raise ValueError(f"File path is required for {source_type} source")

            context.report_progress(20)

            if source_type == "csv":
                df = pd.read_csv(file_path)
            elif source_type == "excel":
                df = pd.read_excel(file_path)
            elif source_type == "json":
                df = pd.read_json(file_path)

        elif source_type in ["mysql", "postgresql", "sqlite"]:
            # Database sources
            if not database_config:
                raise ValueError(f"Database configuration is required for {source_type} source")

            context.report_progress(20)

            df = await load_from_database(source_type, database_config)

        else:
            raise ValueError(f"Unsupported source type: {source_type}")

    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except Exception as e:
        raise RuntimeError(f"Failed to load data from {source_type}: {str(e)}")

    context.report_progress(60)

    # Validate loaded data
    if df.empty:
        raise ValueError("Loaded data is empty")

    # Infer schema
    schema = infer_schema(df)

    context.report_progress(80)

    # Generate HTML preview (first 10 rows)
    preview_html = df.head(10).to_html(index=False, classes="data-table")

    # Determine source display text
    if source_type in ["csv", "excel", "json"]:
        source_display = f"{source_type.upper()} file: {file_path}"
    else:
        db_config = database_config or {}
        db_name = db_config.get("database", "unknown")
        source_display = f"{source_type.upper()} database: {db_name}"

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
            .info-box {{
                background: #e3f2fd;
                padding: 12px;
                border-radius: 4px;
                margin-bottom: 16px;
                font-family: system-ui;
                font-size: 14px;
            }}
        </style>
        <div class="info-box">
            <strong>Source:</strong> {source_display}<br>
            <strong>Data:</strong> {len(df)} rows × {len(df.columns)} columns
        </div>
        <h3>Data Preview (First 10 rows)</h3>
        {preview_html}
        """
    })

    context.report_progress(100)

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


async def load_from_database(db_type: str, config: dict) -> pd.DataFrame:
    """
    Load data from a database using SQLAlchemy.

    Args:
        db_type: Database type (mysql, postgresql, sqlite)
        config: Database configuration with host, port, database, username, password, query

    Returns:
        DataFrame with query results
    """
    import sqlalchemy

    # Build connection string based on database type
    if db_type == "sqlite":
        # SQLite uses file path
        database_path = config.get("database", ":memory:")
        connection_string = f"sqlite:///{database_path}"
    else:
        # MySQL and PostgreSQL use host/port/credentials
        host = config.get("host", "localhost")
        port = config.get("port")
        database = config.get("database")
        username = config.get("username")
        password = config.get("password")

        # Set default ports
        if not port:
            port = 3306 if db_type == "mysql" else 5432

        # Validate required fields
        if not all([database, username]):
            raise ValueError(f"Database name and username are required for {db_type}")

        # Build connection string
        if db_type == "mysql":
            # Use pymysql driver for MySQL
            connection_string = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
        elif db_type == "postgresql":
            # Use psycopg2 driver for PostgreSQL
            connection_string = f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}"
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    # Get SQL query
    query = config.get("query")
    if not query:
        raise ValueError("SQL query is required in database_config")

    # Create engine and execute query
    try:
        engine = sqlalchemy.create_engine(connection_string)
        df = pd.read_sql(query, engine)
        engine.dispose()
        return df
    except Exception as e:
        raise RuntimeError(f"Database query failed: {str(e)}")


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
