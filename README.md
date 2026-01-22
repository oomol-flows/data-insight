# Data Analysis Blocks for OOMOL

This project provides a complete set of OOMOL blocks for AI-powered data analysis, based on Microsoft's Data Formulator project.

## Overview

This package enables users to perform end-to-end data analysis through visual workflows without writing code. It includes blocks for data loading, natural language transformation, and visualization.

## Features

- **Multiple Data Sources**: Load data from CSV, Excel, and JSON files
- **AI-Powered Data Extraction**: Extract tables from images, text, and HTML using vision models
- **Dual Transformation Engines**:
  - SQL-based transformations via DuckDB (fast, efficient for aggregations)
  - Python Pandas transformations (flexible, supports ML operations)
- **Intelligent Chart Recommendations**: AI analyzes data characteristics and suggests optimal visualizations
- **Rich Visualizations**: Generate interactive charts (bar, line, scatter, area, pie, heatmap)
- **Type-Safe Execution**: Automatic schema inference and type detection
- **Safe Code Execution**: Sandboxed Python environment with security restrictions
- **Automatic Error Repair**: Failed code is automatically corrected and re-executed

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

### 2. Data Extractor
**Path**: [tasks/data-extractor](tasks/data-extractor)

Extract structured tabular data from images, text, or HTML using AI.

**Inputs**:
- `source_type`: Type of source (image, text, html)
- `source_content`: Image path/URL, raw text, or HTML content
- `llm`: LLM configuration

**Outputs**:
- `extracted_table`: Extracted structured table data
- `extraction_confidence`: Confidence score (0-1)

**Example Use**:
```yaml
- node_id: extract#1
  task: self::data-extractor
  inputs_from:
    - handle: source_type
      value: text
    - handle: source_content
      value: |
        Product Sales Report
        Product    Region    Sales
        Laptop     North     15000
        Mouse      South     2500
```

**Key Features**:
- Multi-modal extraction from images using vision models
- Intelligent parsing of semi-structured text
- HTML table detection and cleaning
- Confidence scoring for quality assessment

### 3. NL to SQL Transformer
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
- **Enhanced preview**: Shows SQL query, explanation, and results in OOMOL UI

### 4. NL to Pandas Transformer
**Path**: [tasks/nl-to-pandas](tasks/nl-to-pandas)

Transform data using natural language instructions converted to Python Pandas code.

**Inputs**:
- `input_table`: Data table to transform
- `instruction`: Natural language goal (e.g., "Add a column showing percent change")
- `llm`: LLM configuration

**Outputs**:
- `python_code`: Generated Python Pandas code
- `result_table`: Transformation result
- `execution_logs`: Execution logs and messages

**Example Use**:
```yaml
- node_id: transform#1
  task: self::nl-to-pandas
  inputs_from:
    - handle: input_table
      from_node:
        - node_id: load#1
          output_handle: data_table
    - handle: instruction
      value: "Calculate the percentage change between Q1 and Q2 sales"
```

**Key Features**:
- Sandboxed Python code execution with security restrictions
- Automatic code repair on execution errors
- Support for pandas, numpy, and scikit-learn operations
- Function-based code generation (transform_data)
- Rich preview with code display and results

### 5. Chart Recommender
**Path**: [tasks/chart-recommender](tasks/chart-recommender)

Intelligently recommend the best chart types based on data characteristics.

**Inputs**:
- `data_table`: Data table to analyze
- `analysis_goal`: Optional analysis intent or question
- `llm`: LLM configuration

**Outputs**:
- `recommended_charts`: Array of chart recommendations with reasoning

**Example Use**:
```yaml
- node_id: recommend#1
  task: self::chart-recommender
  inputs_from:
    - handle: data_table
      from_node:
        - node_id: transform#1
          output_handle: result_table
    - handle: analysis_goal
      value: "Show sales trends and comparisons"
```

**Key Features**:
- Automatic field type analysis (quantitative, nominal, ordinal, temporal)
- Cardinality-aware recommendations
- Goal-driven chart selection
- Prioritized recommendations (1-3 options)
- Detailed reasoning for each recommendation

### 6. Chart Generator
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

### 7. Report Generator
**Path**: [tasks/report-generator](tasks/report-generator)

Generate comprehensive markdown reports integrating charts and AI-driven analysis.

**Inputs**:
- `charts`: Array of chart objects with title, base64 image, and description
- `analysis_goal`: High-level goal of the analysis
- `llm`: LLM configuration

**Outputs**:
- `markdown_report`: Complete markdown report with embedded charts
- `report_file`: Path to saved markdown file

**Example Use**:
```yaml
- node_id: report#1
  task: self::report-generator
  inputs_from:
    - handle: charts
      from_node:
        - node_id: prepare_charts#1
          output_handle: charts_array
    - handle: analysis_goal
      value: "Analyze sales performance across different regions"
```

**Key Features**:
- AI-powered report writing with structured sections
- Automatic chart embedding with base64 images
- Professional data analysis language
- Streaming LLM generation for better UX
- Saves report to markdown file for export

### 8. Exploration Agent
**Path**: [tasks/exploration-agent](tasks/exploration-agent)

Autonomous multi-round data exploration agent that discovers insights through iterative analysis.

**Inputs**:
- `input_table`: Data table for exploration
- `exploration_goal`: High-level exploration goal (e.g., "Find insights about sales trends")
- `max_iterations`: Maximum number of exploration iterations (default: 3)
- `llm`: LLM configuration

**Outputs**:
- `exploration_steps`: Array of exploration steps with transformations and insights
- `final_report`: Markdown summary of key findings

**Example Use**:
```yaml
- node_id: explore#1
  task: self::exploration-agent
  inputs_from:
    - handle: input_table
      from_node:
        - node_id: load#1
          output_handle: data_table
    - handle: exploration_goal
      value: "Discover patterns in customer behavior and sales trends"
    - handle: max_iterations
      value: 5
```

**Key Features**:
- Autonomous multi-step analysis planning
- SQL-based data transformations at each step
- Insight extraction from intermediate results
- Adaptive exploration strategy
- Comprehensive markdown report generation
- Progress tracking throughout exploration

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

### Preview System

All blocks include rich preview functionality for the OOMOL visual interface:

**Data Loader**:
- Shows data statistics (rows, columns)
- Displays styled HTML table with first 10 rows

**NL-to-SQL Transformer**:
- Displays generated SQL query with syntax highlighting
- Shows LLM explanation of the query logic
- Presents result table with hover effects

**Chart Generator**:
- Renders chart as high-resolution PNG image
- Shows chart inline in the workflow

Preview content is displayed in the OOMOL UI during flow execution and helps users understand what each block is doing. For detailed information, see [PREVIEW_GUIDE.md](PREVIEW_GUIDE.md).

## Roadmap

Based on the [OOMOL Data Analysis Blocks Guide](OOMOL_DATA_ANALYSIS_BLOCKS_GUIDE.md), the implementation is now complete:

**Phase 1** ✅ (Completed):
- Data Loader block (CSV, Excel, JSON)
- NL-to-SQL transformer
- Chart Generator (bar, line, scatter, area, pie, heatmap)
- Complete test flows

**Phase 2** ✅ (Completed):
- Data Extractor block (extract from images, text, HTML)
- NL-to-Pandas transformer with sandboxed execution
- Chart Recommender block with AI-driven suggestions
- Enhanced previews for all blocks

**Phase 3** ✅ (Completed):
- Exploration Agent (autonomous multi-round analysis)
- Report Generator (comprehensive markdown reports)
- Complete end-to-end analysis pipeline
- All 8 core blocks implemented

**Future Enhancements**:
- Database connections (MySQL, PostgreSQL, etc.)
- Subflow compositions (end-to-end analysis pipeline)
- Error auto-repair mechanisms for failed queries
- Additional chart types and customizations
- Real-time data streaming support

## Contributing

Contributions are welcome! See the implementation guide in [OOMOL_DATA_ANALYSIS_BLOCKS_GUIDE.md](OOMOL_DATA_ANALYSIS_BLOCKS_GUIDE.md) for detailed technical specifications.

## License

MIT License

## Credits

Based on [Data Formulator](https://github.com/microsoft/data-formulator) by Microsoft Research.
