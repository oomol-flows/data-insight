# Data Analysis Blocks for OOMOL

This project provides a complete set of OOMOL blocks for AI-powered data analysis, based on Microsoft's Data Formulator project.

## Overview

This package enables users to perform end-to-end data analysis through visual workflows without writing code. It includes blocks for data loading, natural language transformation, and visualization.

## Features

- **Multiple Data Sources**: Load data from CSV, Excel, and JSON files
- **AI-Powered Transformations**: Convert natural language instructions to SQL queries
- **Rich Visualizations**: Generate interactive charts (bar, line, scatter, area, pie, heatmap)
- **Type-Safe Execution**: Automatic schema inference and type detection
- **Safe SQL Execution**: Uses DuckDB for secure, sandboxed query execution

## Available Blocks

### 1. Data Loader
**Path**: [tasks/data-loader](tasks/data-loader)

Load tabular data from multiple file formats.

**Inputs**:
- `source_type`: File type (csv, excel, json)
- `file_path`: Path to data file

**Outputs**:
- `data_table`: Standardized table with columns, rows, and schema
- `preview_html`: HTML preview of the data

**Example Use**:
```yaml
- node_id: load#1
  task: self::data-loader
  inputs_from:
    - handle: source_type
      value: csv
    - handle: file_path
      value: /oomol-driver/oomol-storage/sample_sales.csv
```

### 2. NL to SQL Transformer
**Path**: [tasks/nl-to-sql](tasks/nl-to-sql)

Transform natural language instructions into SQL queries and execute them.

**Inputs**:
- `input_table`: Data table to query
- `instruction`: Natural language goal (e.g., "Show top 10 sales by region")
- `llm`: LLM configuration

**Outputs**:
- `sql_query`: Generated DuckDB SQL query
- `result_table`: Query execution result
- `explanation`: Human-readable explanation

**Example Use**:
```yaml
- node_id: transform#1
  task: self::nl-to-sql
  inputs_from:
    - handle: input_table
      from_node:
        - node_id: load#1
          output_handle: data_table
    - handle: instruction
      value: "Calculate total sales by region (name the sum as 'total') and sort from highest to lowest"
```

**Key Features**:
- Automatic table schema summarization for LLM context
- Type-safe DataFrame to DuckDB conversion
- Structured JSON output parsing
- Error handling with detailed error messages

### 3. Chart Generator
**Path**: [tasks/chart-generator](tasks/chart-generator)

Generate interactive charts using Vega-Lite from data tables.

**Inputs**:
- `data_table`: Data to visualize
- `chart_type`: Type of chart (bar, line, scatter, area, pie, heatmap)
- `x_field`: Field for X axis
- `y_field`: Field for Y axis
- `color_field`: Optional color encoding field
- `size_field`: Optional size encoding field (scatter plots)

**Outputs**:
- `vega_spec`: Vega-Lite JSON specification
- `chart_image`: Base64 encoded PNG image

**Example Use**:
```yaml
- node_id: chart#1
  task: self::chart-generator
  inputs_from:
    - handle: data_table
      from_node:
        - node_id: transform#1
          output_handle: result_table
    - handle: chart_type
      value: bar
    - handle: x_field
      value: region
    - handle: y_field
      value: total
```

**Key Features**:
- Automatic field type detection (quantitative, nominal, ordinal, temporal)
- Multiple chart types with proper encodings
- High-resolution PNG rendering (2x scale)
- Customizable color and size encodings

## Example Workflow

The [test-data-analysis](flows/test-data-analysis) flow demonstrates a complete pipeline:

1. **Load CSV data** → Load sales data from CSV file
2. **Transform with SQL** → Calculate total sales by region using natural language
3. **Generate chart** → Create a bar chart showing results

**Complete Flow**:
```yaml
nodes:
  - node_id: load#1
    task: self::data-loader
    inputs_from:
      - handle: source_type
        value: csv
      - handle: file_path
        value: /oomol-driver/oomol-storage/sample_sales.csv

  - node_id: transform#1
    task: self::nl-to-sql
    inputs_from:
      - handle: input_table
        from_node:
          - node_id: load#1
            output_handle: data_table
      - handle: instruction
        value: "Calculate total sales by region and sort from highest to lowest"

  - node_id: chart#1
    task: self::chart-generator
    inputs_from:
      - handle: data_table
        from_node:
          - node_id: transform#1
            output_handle: result_table
      - handle: chart_type
        value: bar
      - handle: x_field
        value: region
      - handle: y_field
        value: total
```

## Installation

### Dependencies

This project requires Python 3.11+ and the following packages:

**Python Dependencies** (via Poetry):
- pandas: Data manipulation
- duckdb: SQL query execution
- altair: Chart specification
- vl-convert-python: Chart rendering
- openai: LLM API client
- pillow: Image processing
- openpyxl: Excel support
- sqlalchemy: Database connections
- beautifulsoup4: HTML parsing
- scikit-learn: Machine learning features
- numpy: Numerical computing

### Setup

Run the bootstrap script to install all dependencies:

```bash
npm install
poetry install --no-root
```

## Technical Details

### Data Type Handling

The NL-to-SQL block includes automatic type conversion for DuckDB compatibility:
- Pandas `string` dtype → Python `object` strings
- Nullable integers → Float64 (to preserve nulls)

### Schema Inference

The Data Loader automatically infers schema with:
- **Semantic types**: quantitative, nominal, ordinal, temporal
- **Statistics**: min/max/mean for numeric fields, unique counts
- **Sample values**: For nominal fields

### LLM Integration

Uses OOMOL's built-in LLM API with:
- Structured JSON output format enforcement
- Few-shot prompting for better SQL generation
- DuckDB-specific syntax guidance
- Automatic response parsing with fallback strategies

### Chart Type Detection

The Chart Generator automatically detects appropriate field types:
- **Quantitative**: High cardinality numeric fields
- **Ordinal**: Low cardinality numeric fields (<20 unique values)
- **Nominal**: String/categorical fields
- **Temporal**: Date/datetime fields

## Roadmap

Based on the [OOMOL Data Analysis Blocks Guide](OOMOL_DATA_ANALYSIS_BLOCKS_GUIDE.md), future enhancements include:

**Phase 2** (Weeks 2-3):
- Database connections (MySQL, PostgreSQL)
- Data Extractor block (extract from images, HTML)
- NL-to-Pandas transformer
- Additional chart types
- Chart Recommender block

**Phase 3** (Weeks 4-6):
- Exploration Agent (multi-round analysis)
- Report Generator (Markdown reports)
- End-to-end analysis subflow
- Error auto-repair mechanisms

## Contributing

Contributions are welcome! See the implementation guide in [OOMOL_DATA_ANALYSIS_BLOCKS_GUIDE.md](OOMOL_DATA_ANALYSIS_BLOCKS_GUIDE.md) for detailed technical specifications.

## License

MIT License

## Credits

Based on [Data Formulator](https://github.com/microsoft/data-formulator) by Microsoft Research.
