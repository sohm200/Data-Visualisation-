# Simplified Activity and Class Diagrams

## Automated Data Visualization Dashboard System

One activity diagram and one class diagram for the whole system, based on SRS v0.2. For the detailed versions, see `Activity_and_Class_Diagrams.md`.

Image copies are in `docs/diagrams/` (`Simplified_Activity_Diagram.png`, `Simplified_Class_Diagram.png`).

---

## 1. Activity Diagram

```mermaid
flowchart TD
    st((" ")):::startNode --> a1("Open upload screen")
    a1 --> a2("Choose Excel or CSV file")
    a2 --> a3("Click Process Data")
    a3 --> a4("Validate file<br/>type, size, structure")
    a4 --> d1{"File valid?"}
    d1 -->|no| a5("Show error message"):::err
    a5 --> a2
    d1 -->|yes| a6("Read data<br/>sheet or CSV")
    a6 --> a7("Clean data and<br/>detect column types")
    a7 --> a8("Calculate summary<br/>statistics and warnings")
    a8 --> a9("Select charts using rules<br/>up to 10 charts")
    a9 --> a10("Generate charts")
    a10 --> a11("Display dashboard")
    a11 --> d2{"What next?"}
    d2 -->|download chart| a12("Save chart as PNG")
    a12 --> a11
    d2 -->|switch sheet| a6
    d2 -->|analyse another file| a2
    d2 -->|done| en(((" "))):::endNode

    classDef startNode fill:#222,stroke:#222,color:#222
    classDef endNode fill:#fff,stroke:#222,stroke-width:3px,color:#fff
    classDef err fill:#fdecea,stroke:#c62828,color:#000
```

| Step | Requirements |
|---|---|
| Choose file, Process Data | FR-01, US-01 |
| Validate file, show error | FR-02 to FR-05, FR-30, FR-33 |
| Read data | FR-34, FR-35, FR-38 |
| Clean data, detect types | FR-07, FR-08, FR-40 to FR-43 |
| Summary statistics and warnings | FR-06, FR-09, FR-10, FR-23, FR-39 |
| Select and generate charts | FR-12 to FR-17, FR-44 to FR-48 |
| Display dashboard | FR-18 to FR-21, FR-49 to FR-51 |
| Save chart as PNG | FR-24 |

---

## 2. Class Diagram

```mermaid
classDiagram
    direction TB

    class UploadedFile {
        +fileName
        +fileType
        +size
    }
    class FileValidator {
        +validate(file)
        +read(file, sheet) Dataset
    }
    class Dataset {
        +sheetName
        +rowCount
        +columnCount
    }
    class Column {
        +name
        +type
        +missingCount
        +uniqueCount
    }
    class DataProfiler {
        +detectTypes(dataset)
        +calculateStats(dataset) Summary
    }
    class Summary {
        +totalRows
        +totalColumns
        +missingCells
        +numericColumns
        +dateRange
        +warnings
    }
    class ChartSelector {
        +selectCharts(summary) ChartSpec[]
    }
    class ChartSpec {
        +chartType
        +xColumn
        +yColumn
        +title
        +caption
    }
    class ChartRenderer {
        +render(spec) Chart
    }
    class Dashboard {
        +fileName
        +sheetName
        +display()
        +downloadChart()
    }

    FileValidator ..> UploadedFile : checks
    FileValidator ..> Dataset : creates
    Dataset "1" *-- "1..*" Column : contains
    DataProfiler ..> Dataset : analyses
    DataProfiler ..> Summary : creates
    ChartSelector ..> Summary : uses
    ChartSelector ..> ChartSpec : creates
    ChartRenderer ..> ChartSpec : draws
    Dashboard "1" *-- "1" Summary : shows
    Dashboard "1" *-- "0..10" ChartSpec : shows
```

| Class | Role | Module (SRS 6.6) |
|---|---|---|
| UploadedFile | The file the user uploads. Never changed. | — |
| FileValidator | Checks the file and reads it into a table. | validator.py |
| Dataset, Column | The data table and its columns. | — |
| DataProfiler | Detects column types and calculates statistics. | profiler.py |
| Summary | Figures for the summary cards, plus warnings. | — |
| ChartSelector | Picks charts using rules R1 to R6. | chart_rules.py |
| ChartSpec | One chosen chart: type, columns, title, caption. | — |
| ChartRenderer | Draws each chart with Plotly. | renderer.py |
| Dashboard | The page the user sees. | app.py, templates |
