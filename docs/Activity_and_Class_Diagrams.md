# Activity and Class Diagrams

## Automated Data Visualization Dashboard System

| | |
|---|---|
| Version | 0.1 |
| Date | 10 October 2026 |
| Based on | SRS v0.2 (`SRS_DataVisualisation_v0.2.md`) and `decisions.md` (entries dated 2026-10-10) |
| Status | Analysis models, drawn before building |

---

## 1. About This Document

The decisions log says to draw activity diagrams and an **analysis class diagram** before building. The **design class diagram** will be generated from the real code after it is built. This document holds the before-building models.

- **Activity diagrams (Section 2)** show the steps the system follows, including every decision and error path in the SRS.
- **Class diagrams (Section 3)** show the main things the system works with (entity classes) and the parts that do the work (boundary and control classes). They describe what the system needs, not the final code. The class names do not have to match the Python code.

Requirement IDs in brackets, such as (FR-34), show where each step comes from.

### 1.1 Notation

Mermaid has no UML activity diagram type, so the activity diagrams are Mermaid flowcharts drawn with UML activity conventions:

| Symbol | Meaning |
|---|---|
| Small filled circle | Start (initial node) |
| Double ring | End (final node) |
| Rounded box | Action |
| Diamond with a question | Decision; the labels on the arrows are the guard conditions |
| Empty diamond | Merge (paths join again) |
| Red box | User-facing error (codes from SRS Section 4.7.3) |
| Yellow box | A warning added to the dashboard's warnings panel |
| Dotted yellow box | Note |
| Labelled outer box | Swimlane: who carries out the actions inside it |

---

## 2. Activity Diagrams

| ID | Activity | Main requirements | Module (SRS 6.6) |
|---|---|---|---|
| AD-1 | Upload to dashboard (overview) | FR-01, FR-24, FR-32, FR-33, FR-51, NFR-04, NFR-07 | app.py, templates |
| AD-2 | Validate and read file | FR-01 to FR-05, FR-34 to FR-38, NFR-08, NFR-09 | validator.py |
| AD-3 | Profile the data | FR-06, FR-08, FR-09, FR-10, FR-23, FR-39, FR-43, FR-50, FR-53 | profiler.py |
| AD-4 | Detect column type | FR-07, FR-40, FR-41, FR-42 (SRS 4.2.3) | profiler.py |
| AD-5 | Select charts | FR-12 to FR-17, FR-44 to FR-48 (SRS 4.3.2, 4.3.3) | chart_rules.py |
| AD-6 | Render charts and build dashboard | FR-15, FR-16, FR-18 to FR-20, FR-23, FR-49, FR-50, FR-53, NFR-10 | renderer.py, app.py |
| AD-7 | Switch sheet | FR-34, US-05, decision of 2026-10-10 | app.py, dashboard.html |

### AD-1 Upload to Dashboard (Overview)

The main flow from choosing a file to using the dashboard. AD-2 to AD-6 expand the server's steps.

```mermaid
flowchart TD
    subgraph USER ["User"]
        st((" ")):::startNode
        u1("Open upload screen")
        u2("Choose an .xlsx, .xls or .csv file")
        u3("Click Process Data")
        u4("Read the message")
        u5("View dashboard")
        u6{"What next?"}
        u7("Download a chart as PNG<br/>using its Plotly button (FR-24)")
        u8("Pick another sheet<br/>(AD-7)")
        en(((" "))):::endNode
    end

    subgraph BROWSER ["Browser"]
        b1{"File chosen?"}
        b2("Show E-07"):::err
        b3("Show loading indicator<br/>within 1 second (NFR-04)")
        b4("Send the file to the server")
        b5("Show upload screen<br/>with the message")
        b6("Show dashboard")
    end

    subgraph SERVER ["Flask server"]
        s1("Validate and read file<br/>(AD-2)")
        s2{"File valid?"}
        s3("Profile the data<br/>(AD-3, AD-4)")
        s4("Select charts<br/>(AD-5)")
        s5("Render charts and build page<br/>(AD-6)")
        s6{"Unexpected error?"}
        s7("Write details to logs/app.log<br/>(FR-32)")
        s8("Use message E-09"):::err
        s9("Discard the upload, send the<br/>upload page with the message")
        s10("Discard the upload,<br/>send the dashboard (NFR-07)")
        n1["Note: an unexpected error in any<br/>server step takes the yes path here.<br/>A failure in one column or one chart<br/>does not (FR-53, see AD-3 and AD-6)."]:::note
    end

    st --> u1 --> u2 --> u3 --> b1
    b1 -->|no| b2 --> u2
    b1 -->|yes| b3 --> b4 --> s1 --> s2
    s2 -->|"no: E-01 to E-06"| s9
    s2 -->|yes| s3 --> s4 --> s5 --> s6
    s6 -->|yes| s7 --> s8 --> s9
    s6 -->|no| s10 --> b6 --> u5 --> u6
    s9 --> b5 --> u4 -->|"try another file (FR-33)"| u2
    u6 -->|save a chart| u7 --> u6
    u6 -->|switch sheet| u8 --> u5
    u6 -->|"Analyse another file (FR-51)"| u1
    u6 -->|finished| en
    n1 -.- s6

    classDef startNode fill:#222,stroke:#222,color:#222
    classDef endNode fill:#fff,stroke:#222,stroke-width:3px,color:#fff
    classDef err fill:#fdecea,stroke:#c62828,color:#000
    classDef warn fill:#fff4d6,stroke:#c98a00,color:#000
    classDef note fill:#fffbe6,stroke:#bfa500,color:#000,stroke-dasharray:4 3
```

The Process Data button stays disabled until a file is chosen (SRS 3.1), so E-07 is a fallback.

### AD-2 Validate and Read File

What `validator.py` does with one upload. The uploaded file is only read, never changed (FR-11, NFR-05).

```mermaid
flowchart TD
    st((" ")):::startNode --> a1("Receive the upload")
    a1 --> d1{"Larger than 25 MB?"}
    d1 -->|yes| e02("E-02: reject before reading<br/>(MAX_CONTENT_LENGTH, FR-05, NFR-09)"):::err
    d1 -->|no| a2("Clean the file name with<br/>secure_filename (NFR-08)")
    a2 --> d2{"Extension?"}
    d2 -->|"anything else"| e01("E-01: unsupported type"):::err

    d2 -->|".csv"| c1("Detect encoding: UTF-8,<br/>UTF-8 with BOM or Windows-1252")
    c1 --> c2{"Content is readable text?<br/>(FR-02)"}
    c2 -->|no| e04("E-04: damaged or unreadable"):::err
    c2 -->|yes| c3("Detect separator: comma, semicolon,<br/>tab or pipe (FR-35)")
    c3 --> c4("Read the CSV in memory")

    d2 -->|".xlsx or .xls"| x1{"Password-protected?<br/>(FR-37)"}
    x1 -->|yes| e05("E-05: password-protected"):::err
    x1 -->|no| x2{"Opens as that Excel type?<br/>(FR-02)"}
    x2 -->|no| e04
    x2 -->|yes| x3{"Sheet name sent<br/>with the request?"}
    x3 -->|"yes (sheet switch)"| x4("Use the requested sheet")
    x3 -->|no| x5("Use the first non-empty sheet<br/>(FR-34)")
    x4 --> x6("Read the sheet in memory<br/>and list all sheet names")
    x5 --> x6

    c4 --> m1{" "}
    x6 --> m1
    m1 --> d3{"Heading row, at least one data row<br/>and at least one column? (FR-03)"}
    d3 -->|no| e03("E-03: no data"):::err
    d3 -->|yes| d4{"More than 1,000,000<br/>data rows? (FR-36)"}
    d4 -->|yes| e06("E-06: too many rows"):::err
    d4 -->|no| a3("Clean headings: trim spaces, rename blank<br/>ones to Column N, add _2, _3 to duplicates (FR-38)")
    a3 --> a4("Return the table, file name,<br/>sheet name and sheet list")
    a4 --> en1(((" "))):::endNode

    e01 & e02 & e03 & e04 & e05 & e06 --> a5("Return the error code to app.py<br/>(message shown as in AD-1)")
    a5 --> en2(((" "))):::endNode

    classDef startNode fill:#222,stroke:#222,color:#222
    classDef endNode fill:#fff,stroke:#222,stroke-width:3px,color:#fff
    classDef err fill:#fdecea,stroke:#c62828,color:#000
```

### AD-3 Profile the Data

What `profiler.py` does with the table returned by AD-2. Each column is analysed separately, so a problem in one column does not stop the rest.

```mermaid
flowchart TD
    st((" ")):::startNode --> p1("Treat blank cells, spaces only, NA, N/A,<br/>null, none and - as missing (FR-08)")
    p1 --> p2("Ignore fully empty rows<br/>and columns (FR-43)")
    p2 --> d1{"Any rows or<br/>columns ignored?"}
    d1 -->|yes| w1("Warning: rows or<br/>columns ignored"):::warn
    d1 -->|no| p3
    w1 --> p3("Count rows and columns (FR-06)")
    p3 --> p4("Take the next column")
    p4 --> p5("Count missing and unique values")
    p5 --> d2{"More than 20%<br/>missing?"}
    d2 -->|yes| w2("Warning: many<br/>missing values (FR-23)"):::warn
    d2 -->|no| p6
    w2 --> p6("Detect column type<br/>(AD-4)")
    p6 --> d3{"Type?"}
    d3 -->|numeric| p7("Count, average, median, standard deviation,<br/>minimum, maximum (FR-09, FR-39)")
    p7 --> d4{"Total meaningful?<br/>(SRS 4.2.4, FR-10)"}
    d4 -->|yes| p8("Calculate the total")
    d4 -->|no| m1
    p8 --> m1{" "}
    d3 -->|date| p9("Record earliest and latest date")
    p9 --> m1
    d3 -->|"ID, category,<br/>text or empty"| m1
    m1 --> d5{"More columns?"}
    d5 -->|yes| p4
    d5 -->|no| p10("Total missing cells and %, numeric<br/>column count, overall date range (FR-19)")
    p10 --> p11("Keep the first 10 rows<br/>as the preview (FR-50)")
    p11 --> d6{"Any numeric, date or<br/>category column?"}
    d6 -->|no| w3("Warning E-08:<br/>no charts possible"):::warn
    d6 -->|yes| p12("Return the data profile")
    w3 --> p12
    p12 --> en(((" "))):::endNode

    n1["Note: if analysing a column fails, log the<br/>details, add a warning for that column and<br/>continue with the next column (FR-53)."]:::note
    n1 -.- p6

    classDef startNode fill:#222,stroke:#222,color:#222
    classDef endNode fill:#fff,stroke:#222,stroke-width:3px,color:#fff
    classDef warn fill:#fff4d6,stroke:#c98a00,color:#000
    classDef note fill:#fffbe6,stroke:#bfa500,color:#000,stroke-dasharray:4 3
```

### AD-4 Detect Column Type

The rules in SRS Section 4.2.3, applied to the non-missing values of one column in this order. The first rule that matches decides the type.

```mermaid
flowchart TD
    st((" ")):::startNode --> t1{"More than 95%<br/>missing?"}
    t1 -->|yes| r1("Empty: skip the column")
    r1 --> w1("Warning: empty column"):::warn
    t1 -->|no| t2{"Excel date cells, or at least 90%<br/>read as dates, day-first? (FR-41)"}
    t2 -->|yes| r2("Date: convert values to dates")
    t2 -->|no| t3{"All values unique, at least 20 rows, and<br/>name contains id, no, number, code or roll,<br/>or values are consecutive whole numbers?"}
    t3 -->|yes| r3("ID: list in the column table only,<br/>no statistics or charts (FR-42, BR-06)")
    t3 -->|no| c1("Try reading values as numbers after removing<br/>₹ $ € £, thousand separators, % and spaces (FR-40)")
    c1 --> t4{"At least 90%<br/>read as numbers?"}
    t4 -->|yes| r4("Numeric: convert values to numbers")
    t4 -->|no| t5{"50% to 90%<br/>read as numbers?"}
    t5 -->|yes| w2("Warning: mixed<br/>numbers and text"):::warn
    t5 -->|no| t6
    w2 --> t6{"Exactly 2 distinct values, or 20 or fewer<br/>distinct values that are under 50% of rows?"}
    t6 -->|yes| r5("Category")
    t6 -->|no| r6("Text: counted in the<br/>summary, not charted")
    w1 & r2 & r3 & r4 & r5 & r6 --> m1{" "}
    m1 --> en(((" "))):::endNode

    classDef startNode fill:#222,stroke:#222,color:#222
    classDef endNode fill:#fff,stroke:#222,stroke-width:3px,color:#fff
    classDef warn fill:#fff4d6,stroke:#c98a00,color:#000
```

### AD-5 Select Charts

What `chart_rules.py` does with the data profile. It produces chart specifications (plain data), not drawings (SRS 6.6). Rules run in the priority order from SRS 4.3.3: R1, R2, R5, R4, R3, R6.

```mermaid
flowchart TD
    st((" ")):::startNode --> s0("Order category and numeric columns<br/>by fewest missing values (SRS 4.3.3)")
    s0 --> r1{"R1: a date column and<br/>a numeric column?"}
    r1 -->|yes| a1("Line spec: numeric total per date (average if a<br/>total is not meaningful), sorted by date.<br/>Group by month if more than 100 dates.")
    r1 -->|no| r2
    a1 --> r2{"R2: a category<br/>column?"}
    r2 -->|yes| a2("Bar spec per category column: total or average of a<br/>numeric column, or count if there is none. Highest first.<br/>More than 15 categories: top 15 plus a note (FR-46).")
    r2 -->|no| r5
    a2 --> r5{"R5: numeric pairs with correlation<br/>of 0.5 or more, either sign?"}
    r5 -->|yes| a5("Scatter spec for the 2 strongest pairs. More than<br/>5,000 rows: mark as a 5,000-point sample (FR-45).")
    r5 -->|no| r4
    a5 --> d5{"Sampled?"}
    d5 -->|yes| w5("Warning: sampled chart"):::warn
    d5 -->|no| r4
    w5 --> r4{"R4: a numeric column with<br/>at least 10 unique values?"}
    r4 -->|yes| a4("Histogram spec per such column,<br/>bins chosen automatically")
    r4 -->|no| r3
    a4 --> r3{"R3: a category column with 2 to 6 categories,<br/>counts or meaningful totals, no negative values?"}
    r3 -->|yes| a3("Pie spec (never more than<br/>6 slices: FR-14, BR-03)")
    r3 -->|no| r6
    a3 --> r6{"R6: 3 or more<br/>numeric columns?"}
    r6 -->|yes| a6("Correlation heatmap spec (FR-47)")
    r6 -->|no| l1
    a6 --> l1("Keep the first 10 candidates, at most<br/>3 of any one chart type (FR-44)")
    l1 --> d1{"Any candidates<br/>left out?"}
    d1 -->|yes| w1("Warning: skipped charts (FR-17)"):::warn
    d1 -->|no| l2
    w1 --> l2("Add a title, axis labels and a one-line<br/>caption to each spec (FR-15, FR-48)")
    l2 --> l3("Return the list of chart specifications")
    l3 --> en(((" "))):::endNode

    classDef startNode fill:#222,stroke:#222,color:#222
    classDef endNode fill:#fff,stroke:#222,stroke-width:3px,color:#fff
    classDef warn fill:#fff4d6,stroke:#c98a00,color:#000
```

A category column with 7 or more categories gets no pie chart. It is already covered by its bar chart from R2.

### AD-6 Render Charts and Build Dashboard

What `renderer.py` and `app.py` do with the chart specifications. A chart that fails to draw is listed in the warnings panel. It does not stop the dashboard.

```mermaid
flowchart TD
    st((" ")):::startNode --> d0{"Any chart<br/>specifications?"}
    d0 -->|no| f1
    d0 -->|yes| g1("Take the next specification")
    g1 --> g2("Prepare the data: total, average or count,<br/>month grouping, top 15, 5,000-point sample")
    g2 --> g3("Build the Plotly chart with title,<br/>axis labels and caption (FR-15)")
    g3 --> d1{"Chart type?"}
    d1 -->|line| g4("Mark the highest and<br/>lowest points (FR-16)")
    d1 -->|bar| g5("Highlight the largest bar (FR-16)")
    d1 -->|other| m1{" "}
    g4 --> m1
    g5 --> m1
    m1 --> d2{"Drawn<br/>successfully?"}
    d2 -->|yes| g6("Add the chart to the grid")
    d2 -->|no| g7("Log the details. Warning:<br/>chart could not be drawn (FR-53)"):::warn
    g6 --> d3{"More<br/>specifications?"}
    g7 --> d3
    d3 -->|yes| g1
    d3 -->|no| f1("Fill dashboard.html: header, summary cards, warnings,<br/>chart grid, column table, preview (FR-18 to FR-20, FR-49, FR-50).<br/>Jinja2 escapes all spreadsheet text (NFR-10).")
    f1 --> d4{"Any warnings?"}
    d4 -->|yes| f2("Show the warnings panel")
    d4 -->|no| f3("Hide the warnings panel")
    f2 & f3 --> en(((" "))):::endNode

    classDef startNode fill:#222,stroke:#222,color:#222
    classDef endNode fill:#fff,stroke:#222,stroke-width:3px,color:#fff
    classDef warn fill:#fff4d6,stroke:#c98a00,color:#000
```

### AD-7 Switch Sheet

From the decisions log (2026-10-10): the browser sends the same file again with the chosen sheet name. The server keeps nothing between requests.

```mermaid
flowchart TD
    subgraph USER ["User"]
        st((" ")):::startNode
        u1("Pick a sheet from the selector")
        u2("View the dashboard<br/>for that sheet")
        u3("Read the message")
        en(((" "))):::endNode
    end

    subgraph BROWSER ["Browser"]
        b1("Show loading indicator")
        b2("Send the same file again<br/>with the chosen sheet name")
        b3("Replace the dashboard")
        b4("Show upload screen<br/>with the message")
    end

    subgraph SERVER ["Flask server (stores nothing between requests)"]
        s1("Validate and read the file<br/>using the requested sheet (AD-2)")
        s2{"Sheet usable?"}
        s3("Profile, select and render<br/>(AD-3 to AD-6)")
        s4("Send the dashboard<br/>for that sheet")
        s5("Send the message,<br/>for example E-03 for an empty sheet"):::err
    end

    st --> u1 --> b1 --> b2 --> s1 --> s2
    s2 -->|yes| s3 --> s4 --> b3 --> u2 --> en
    s2 -->|no| s5 --> b4 --> u3 --> en

    classDef startNode fill:#222,stroke:#222,color:#222
    classDef endNode fill:#fff,stroke:#222,stroke-width:3px,color:#fff
    classDef err fill:#fdecea,stroke:#c62828,color:#000
```

---

## 3. Analysis Class Diagrams

Two views:

- **CD-1 Entity classes:** the information the system creates and passes along. All of it lives in memory for one request only (SRS 6.5).
- **CD-2 Boundary and control classes:** the screens (boundary) and the parts that do the work (control), and how they depend on each other.

### CD-1 Entity Classes

```mermaid
classDiagram
    direction TB

    class UploadedFile {
        +String fileName
        +FileType fileType
        +int sizeBytes
        +bytes content
    }
    class FileType {
        <<enumeration>>
        XLSX
        XLS
        CSV
    }
    class Dataset {
        +String fileName
        +String sheetName
        +List~String~ sheetNames
        +String encoding
        +String separator
        +int rowCount
        +int columnCount
        +int ignoredRowCount
        +int ignoredColumnCount
        +Table rows
    }
    class Column {
        +String name
        +String originalHeading
        +ColumnType type
        +int missingCount
        +float missingPercent
        +int uniqueCount
        +bool isMixed
        +bool analysisFailed
    }
    class ColumnType {
        <<enumeration>>
        EMPTY
        DATE
        ID
        NUMERIC
        CATEGORY
        TEXT
    }
    class NumericSummary {
        +int count
        +float average
        +float median
        +float stdDev
        +float minimum
        +float maximum
        +bool totalIsMeaningful
        +float total
    }
    class DateSummary {
        +Date earliest
        +Date latest
    }
    class DatasetProfile {
        +int totalMissingCells
        +float missingPercent
        +int numericColumnCount
        +Date dateRangeStart
        +Date dateRangeEnd
        +Table preview
    }
    class Warning {
        +WarningKind kind
        +String message
    }
    class WarningKind {
        <<enumeration>>
        HIGH_MISSING
        EMPTY_COLUMN
        MIXED_TYPE
        IGNORED_ROWS_COLUMNS
        CHART_SKIPPED
        CHART_SAMPLED
        ITEM_FAILED
        NO_CHARTABLE_COLUMNS
    }
    class ChartSpec {
        +ChartType type
        +String rule
        +Aggregation aggregation
        +String title
        +String xLabel
        +String yLabel
        +String caption
        +bool groupByMonth
        +bool isSampled
        +int omittedCategoryCount
    }
    class ChartType {
        <<enumeration>>
        LINE
        BAR
        PIE
        HISTOGRAM
        SCATTER
        HEATMAP
    }
    class Aggregation {
        <<enumeration>>
        SUM
        AVERAGE
        COUNT
        NONE
    }
    class RenderedChart {
        +String html
    }
    class Dashboard {
        +String fileName
        +String sheetName
        +List~String~ sheetNames
    }
    class ErrorMessage {
        +String code
        +String text
    }
    class ErrorLogEntry {
        +DateTime time
        +String fileName
        +String errorType
        +String details
    }

    UploadedFile --> FileType
    UploadedFile "1" --> "0..1" Dataset : is read into
    UploadedFile "1" --> "0..1" ErrorMessage : is rejected with
    Dataset "1" *-- "1..*" Column : contains
    Column --> ColumnType
    Column "1" *-- "0..1" NumericSummary : numeric only
    Column "1" *-- "0..1" DateSummary : date only
    DatasetProfile "1" --> "1" Dataset : describes
    ChartSpec "0..*" --> "1..*" Column : plots
    ChartSpec --> ChartType
    ChartSpec --> Aggregation
    RenderedChart "1" --> "1" ChartSpec : draws
    Dashboard "1" *-- "1" DatasetProfile
    Dashboard "1" *-- "0..10" RenderedChart
    Dashboard "1" *-- "0..*" Warning
    Warning --> WarningKind
    Warning "0..*" --> "0..1" Column : about
    ErrorLogEntry "0..1" --> "1" ErrorMessage : logged with E-09
```

| Class | What it is | Requirements |
|---|---|---|
| UploadedFile | The file as received. Read only; never changed or saved. | FR-01, FR-05, FR-11, NFR-05, NFR-07 |
| Dataset | The table read from one sheet (or the CSV), with cleaned headings. | FR-06, FR-34, FR-35, FR-38, FR-43 |
| Column | One column with its detected type and quality counts. | FR-07, FR-08, FR-49 |
| NumericSummary | Statistics for a numeric column. `total` is only filled when `totalIsMeaningful` is true. | FR-09, FR-10, FR-39 |
| DateSummary | Earliest and latest date in a date column. | FR-19, FR-41 |
| DatasetProfile | Whole-file figures for the summary cards, plus the 10-row preview. | FR-19, FR-50 |
| Warning | One line in the warnings panel. | FR-17, FR-23, FR-45, FR-53, E-08 |
| ChartSpec | A decision to draw one chart: which rule, columns and aggregation. Plain data, no drawing. | FR-12 to FR-17, FR-44 to FR-48 |
| RenderedChart | The Plotly HTML for one chart, with its built-in PNG download. | FR-15, FR-16, FR-24 |
| Dashboard | Everything shown on the dashboard screen. | FR-18 to FR-21, FR-49 to FR-51 |
| ErrorMessage | A friendly message from the catalogue, E-01 to E-09. | FR-04, FR-30, SRS 4.7.3 |
| ErrorLogEntry | One technical entry in `logs/app.log`. Never shown to users. | FR-32 |

ID columns are `Column` objects with type `ID`. They have no `NumericSummary` and no `ChartSpec` ever refers to them (FR-42, BR-06).

### CD-2 Boundary and Control Classes

```mermaid
classDiagram
    direction LR

    class UploadPage {
        <<boundary>>
        +chooseFile()
        +processData()
        +showMessage(ErrorMessage)
    }
    class DashboardPage {
        <<boundary>>
        +show(Dashboard)
        +selectSheet(String sheetName)
        +downloadChartPng(RenderedChart)
        +analyseAnotherFile()
    }
    class RequestController {
        <<control>>
        +showUploadPage()
        +process(UploadedFile, String sheetName) Dashboard
    }
    class FileValidator {
        <<control>>
        +validateAndRead(UploadedFile, String sheetName) Dataset
    }
    class DataProfiler {
        <<control>>
        +profile(Dataset) DatasetProfile
        -detectType(Column) ColumnType
        -isTotalMeaningful(Column) bool
    }
    class ChartSpecSource {
        <<interface>>
        +suggest(DatasetProfile) List~ChartSpec~
    }
    class ChartSelector {
        <<control>>
        +suggest(DatasetProfile) List~ChartSpec~
        -applyLimits(List~ChartSpec~) List~ChartSpec~
    }
    class AiSuggester {
        <<future>>
        +suggest(DatasetProfile) List~ChartSpec~
    }
    class ChartRule {
        <<interface>>
        +String ruleId
        +ChartType chartType
        +candidates(DatasetProfile) List~ChartSpec~
    }
    class LineRule {
        R1 line chart
    }
    class BarRule {
        R2 bar chart
    }
    class PieRule {
        R3 pie chart
    }
    class HistogramRule {
        R4 histogram
    }
    class ScatterRule {
        R5 scatter plot
    }
    class HeatmapRule {
        R6 correlation heatmap
    }
    class ChartRenderer {
        <<control>>
        +render(Dataset, ChartSpec) RenderedChart
    }
    class ErrorLogger {
        <<control>>
        +log(ErrorLogEntry)
    }
    class Settings {
        <<config>>
        +maxFileSizeMB = 25
        +maxDataRows = 1000000
        +emptyColumnMissingShare = 0.95
        +typeMatchShare = 0.9
        +mixedTypeLowerShare = 0.5
        +idMinRows = 20
        +categoryMaxUnique = 20
        +categoryMaxUniqueShare = 0.5
        +highMissingWarnShare = 0.2
        +maxCharts = 10
        +maxChartsPerType = 3
        +lineMonthGroupingDates = 100
        +pieMinSlices = 2
        +pieMaxSlices = 6
        +histogramMinUnique = 10
        +scatterMinCorrelation = 0.5
        +scatterMaxPairs = 2
        +scatterSampleSize = 5000
        +heatmapMinColumns = 3
        +barMaxCategories = 15
        +previewRows = 10
    }

    UploadPage ..> RequestController : submits file
    DashboardPage ..> RequestController : re-submits file with sheet name
    RequestController ..> UploadPage : returns with message
    RequestController ..> DashboardPage : returns
    RequestController --> FileValidator
    RequestController --> DataProfiler
    RequestController --> "1..*" ChartSpecSource
    RequestController --> ChartRenderer
    RequestController --> ErrorLogger
    ChartSelector ..|> ChartSpecSource
    AiSuggester ..|> ChartSpecSource
    ChartSelector "1" o-- "6" ChartRule : runs in order R1 R2 R5 R4 R3 R6
    LineRule ..|> ChartRule
    BarRule ..|> ChartRule
    PieRule ..|> ChartRule
    HistogramRule ..|> ChartRule
    ScatterRule ..|> ChartRule
    HeatmapRule ..|> ChartRule
    FileValidator ..> Settings
    DataProfiler ..> Settings
    ChartSelector ..> Settings
    ChartRule ..> Settings
```

| Class | Stereotype | Module (SRS 6.6) | Requirements |
|---|---|---|---|
| UploadPage | boundary | templates/upload.html | SRS 3.1, FR-01, NFR-04 |
| DashboardPage | boundary | templates/dashboard.html, static/ | FR-18 to FR-24, FR-34, FR-49 to FR-51 |
| RequestController | control | app.py | FR-30, FR-33, NFR-07, NFR-09, NFR-11 |
| FileValidator | control | validator.py | FR-01 to FR-05, FR-34 to FR-38 |
| DataProfiler | control | profiler.py | FR-06 to FR-10, FR-39 to FR-43 |
| ChartSpecSource | interface | chart_rules.py | SRS 6.6 (a second source can be added later) |
| ChartSelector, ChartRule and R1 to R6 | control | chart_rules.py | FR-12 to FR-17, FR-44 to FR-48 |
| AiSuggester | future | not built yet | FR-27 to FR-29, FR-52, BR-05 |
| ChartRenderer | control | renderer.py | FR-15, FR-16, FR-24, FR-53 |
| ErrorLogger | control | app.py (Python logging) | FR-32 |
| Settings | config | config.py | NFR-16 (all thresholds in one place) |

Design notes:

- **ChartSpecSource** comes from SRS 6.6: chart rules return plain specifications, so a future AI feature can be a second source without changing the rest. `AiSuggester` is marked `<<future>>`. The core works without it (FR-27), and its suggestions are labelled and never replace rule-based charts (FR-29, BR-05).
- **One class per chart rule** keeps each rule testable on its own, without the web server (NFR-18). The real code may use plain functions. The design class diagram drawn after building will show what was actually built.
- **Settings** lists every threshold from SRS 4.2.3, 4.2.4, 4.3.2 and 4.3.3, so they can be adjusted after testing (Appendix D, open item 3) by changing one file.
- **RequestController** has no saved state. Each request carries the file, and the optional sheet name, from start to finish (decisions log, 2026-10-10).

---

## 4. Points to Confirm

The diagrams make the following choices where the SRS leaves room. Confirm or change them, then record the outcome in `decisions.md`.

1. **Wrong content for the extension** (for example, a PDF renamed to .csv). AD-2 shows E-04. FR-02 could also justify E-01, and TF-04 accepts either.
2. **Charts left out by the 10-chart limit.** AD-5 lists them as "skipped charts" in the warnings panel (FR-17). The other option is to list only charts that failed or did not suit the data.
3. **Errors while switching sheets** (for example, the chosen sheet is empty). AD-7 returns to the upload screen with the message, like any other error. The other option is to keep the current dashboard and show the message on it.
4. **Keeping the file for a sheet switch.** The browser can only send the file again if the page still holds it. That means the upload screen sends the file with JavaScript and swaps in the dashboard, instead of a normal form post that loads a new page. This affects Sprint 3 (FR-34 sheet selector).
