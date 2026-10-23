# Software Requirements Specification

## Automated Data Visualization Dashboard System

| | |
|---|---|
| **Version** | 0.3 – Agile Draft |
| **Date** | 15 October 2026 |

> This SRS follows the Agile model. Requirements may be added, changed or removed after each sprint review. Requirement IDs are never renumbered or reused, so references stay valid across versions.

---

## Revision History

| Version | Date | Description of Changes |
|---|---|---|
| 0.1 | — | Initial Agile draft. |
| 0.2 | 10 Oct 2026 | Added missing sections, resolved the TBDs (framework, chart library, file size, export), made requirements measurable, and added detection rules, chart thresholds, error catalogue, security requirements, user stories, Definition of Done, test file set and traceability matrix. |
| 0.3 | 15 Oct 2026 | **ID rule:** whole-number columns with an ID heading are IDs even when values repeat (FR-54), and ID headings are judged by their first or last word. **Category rule:** the 20-value cap is removed, so many-value columns get top-15 bar charts (TF-08 now consistent with 4.2.3). **R1:** counts rows over time when there is no number column (FR-55). **Title rows** above the headings are skipped (FR-56). Recorded how ambiguous points were implemented (sheet choice, empty columns, totals, pie values, bins, upload allowance and others). Moved the adopted sheet-switching and Waitress decisions in from the decisions log. TF-05 uses € and £ (₹ cannot be stored in Windows-1252). Added TF-17 and TF-18. Removed the analysis diagrams appendix and trimmed the reading guide and glossary. |

---

## 1. Introduction

### 1.1 Purpose

This document specifies the requirements for the **Automated Data Visualization Dashboard System**. The system lets a user upload a spreadsheet and automatically receive summaries, key values and several suitable charts on one dashboard, without building each graph by hand.

### 1.2 Document Conventions

- **Keywords:** **shall** – mandatory; **should** – strongly desired, may be deferred with a reason; **may** – optional.
- **IDs:** `FR` functional requirement, `NFR` nonfunctional requirement, `BR` business rule, `US` user story, `E` error message, `TF` test file.
- **Priority:** High (needed for the first working version), Medium (can move to a later sprint), Low (nice to have).
- **Status:** Planned, Backlog, Future, Decided, Done.
- **Change column:** **New** = added in v0.3, **Changed** = wording or value changed in v0.3, **—** = unchanged since v0.2.

### 1.3 Product Scope

Many people have large Excel or CSV files but do not know which calculations or charts suit their data. The system reads a file, detects the type of each column, calculates useful values, selects several suitable charts using fixed rules, and shows everything on one simple dashboard.

The first version uses programmed rules to choose charts. An AI feature may be added later, but **the core system must work fully without AI**.

| In scope (first release) | Out of scope (first release) |
|---|---|
| Uploading and validating .xlsx, .xls and .csv files | User accounts and login |
| Column type detection and summary statistics | Saving past reports, or a database |
| Rule-based selection of multiple charts | Editing data inside the app |
| A single-page dashboard | Online hosting |
| PNG export of charts | PDF export, AI recommendations |

### 1.4 References

- Course IEEE-style SRS sample format.
- SRS v0.1 (`docs/SRS_DataVisualisation_v0.1.pdf`) and v0.2 (`docs/SRS_DataVisualisation_v0.2.md`).
- Decisions log (`docs/decisions.md`).

---

## 2. Overall Description

### 2.1 Product Perspective

A small, self-contained web application. The user opens it in a web browser, uploads a spreadsheet and receives a dashboard. The first version runs on the user's own computer (localhost), served by **Waitress**, and needs no internet connection. A future version may be hosted online.

### 2.2 Product Functions

- Upload Excel (.xlsx, .xls) or CSV files up to 25 MB.
- Check that the file and its columns are usable, with clear messages when they are not.
- Handle Excel files with several sheets, title rows above the headings, and CSV files with different separators or encodings.
- Detect numeric, date, category, text and ID columns, including IDs that repeat.
- Clean common formatting problems (currency symbols, thousand separators, mixed date formats).
- Calculate count, total, average, median, minimum, maximum and missing values.
- Choose suitable chart types using documented rules, and create up to 10 charts.
- Show summary cards, charts, warnings, a column information table and a data preview on one HTML dashboard.
- Let the user save any chart as a PNG image.
- Never modify the original uploaded file.

### 2.3 User Classes

| User Type | Description | Main Needs |
|---|---|---|
| General User | Student, teacher, analyst or office user with basic computer knowledge. | Upload a file and understand the results without training. |
| Developer / Admin | Develops and maintains the system. | Test, read error logs, fix errors, update chart rules. |
| Project Guide / Tester | Checks whether the project meets its requirements. | Review features and test outputs; give feedback at sprint reviews. |

### 2.4 Operating Environment

- Windows 10/11 or a common Linux distribution.
- A current version of Chrome, Edge or Firefox.
- Python 3.10 or later with the libraries in Section 3.3.
- Runs locally and works without an internet connection.

### 2.5 Design and Implementation Constraints

- Only free and open-source tools are used.
- The core system must not depend on AI or any outside service.
- All chart JavaScript must be served locally (not from a CDN), so the dashboard works offline.
- Chart rules and processing steps must be in separate modules (Section 6.6).
- The user interface must stay simple; technical details are hidden from general users.

### 2.6 User Documentation

- A one-page quick-start guide (`README.md`) explaining installation and use.
- Short instructions on the upload screen (supported types, size limit, first row must be headings).
- Clear error messages (Section 4.7.3) and a short help note on the dashboard explaining each chart type shown.

### 2.7 Assumptions and Dependencies

- The column headings are in the first non-empty row of each sheet, except that a single-cell title row directly above them is skipped (FR-56).
- The file is not badly damaged. Password-protected files are detected and rejected with a message.
- The computer has at least 8 GB of RAM for files near the 25 MB limit.
- The required Python libraries are installed (`requirements.txt` is provided).
- Dates written as text are **day-first** (DD-MM-YYYY), as is common in India.
- Users understand the basic meaning of charts and summary values.

---

## 3. External Interface Requirements

### 3.1 User Interfaces

**Upload screen:**
- Project name and a one-line description.
- A file picker that accepts .xlsx, .xls and .csv, with the note: "Maximum 25 MB. The first row must contain column headings."
- A **Process Data** button, disabled until a file is chosen.
- A loading indicator shown while the file is processed.
- An area for error messages in plain language.
- A one-line privacy note: the file is analysed on this computer only and is never changed.

**Dashboard screen (top to bottom):**
1. **Header:** file name, sheet name (with a sheet selector if the file has several sheets), and an **Analyse another file** button.
2. **Summary cards:** total rows, total columns, missing cells (count and %), number of numeric columns, and date range (if a date column exists).
3. **Warnings panel:** missing or unusual data, columns treated as IDs, skipped charts, sampled charts. Hidden when there are no warnings.
4. **Chart grid:** up to 10 charts. Two per row on screens 1200 px or wider, one per row below that. Each chart has a title, axis labels and a one-line caption.
5. **Column information table:** column name, detected type, missing count and %, unique values, and the statistics of FR-09, FR-10 and FR-39.
6. **Data preview:** the first 10 rows of the data.

All buttons and messages use clear, non-technical words.

### 3.2 Hardware Interfaces

No special hardware. A normal computer, keyboard, mouse or touchpad, display and local storage.

### 3.3 Software Interfaces

| Component | Choice | Purpose |
|---|---|---|
| Language | Python 3.10+ | All processing logic |
| Web framework | Flask | Upload handling, routes and HTML templates |
| Local server | Waitress | Serves the app on the local machine |
| Data processing | pandas 2.2+ | Reading and analysing data |
| .xlsx reading | python-calamine (preferred), openpyxl (fallback) | Calamine is much faster on large files |
| .xls reading | xlrd | Legacy Excel files |
| CSV detection | Python `csv.Sniffer`; encodings tried in a fixed order (FR-35) | Detect separator and encoding |
| Charts | Plotly (Python), with the plotly.js file shipped inside the installed plotly package | Interactive charts with built-in PNG download, served locally |
| Templates | Jinja2 (included with Flask) | Dashboard HTML, with automatic escaping |
| Testing | pytest | Unit and integration tests |
| Front end | HTML, CSS, a small amount of JavaScript | Layout, loading indicator, sheet switching |

### 3.4 Communication Interfaces

- The browser and the application communicate over HTTP on the local machine (`http://127.0.0.1:5000`).
- The server listens on `127.0.0.1` only by default, so other computers cannot reach it.
- No email, cloud storage or outside internet service is used.
- If the system is hosted online later, HTTPS and user access control will be required.

---

## 4. System Features

### 4.1 File Upload and Validation

**Priority: High.** The user uploads a spreadsheet and the system checks it before analysing it.

**User action and system response:**
1. The user chooses an Excel or CSV file and clicks **Process Data**.
2. The system checks the file type, size and basic structure.
3. For a multi-sheet Excel file, the system picks the first sheet that has a heading row and at least one data row.
4. The system continues to the dashboard, or shows a clear error message (Section 4.7.3).

| ID | Requirement | Priority | Status | Change |
|---|---|---|---|---|
| FR-01 | The system shall allow the user to select an .xlsx, .xls or .csv file. | High | Planned | — |
| FR-02 | The system shall reject unsupported file types, checking both the file extension and that the content can be opened as that type. | High | Planned | — |
| FR-03 | The system shall check that the file contains a heading row, at least one data row and at least one column. | High | Planned | — |
| FR-04 | The system shall show a simple message when the file cannot be read. | High | Planned | — |
| FR-05 | The maximum file size shall be **25 MB**. Larger files shall be rejected before they are loaded into memory. The server limit allows 64 KB on top of 25 MB for the upload form itself; the exact 25 MB limit is then applied to the file. | High | Planned | Changed |
| FR-34 | For Excel files with several sheets, the system shall analyse by default the first sheet that has a heading row and at least one data row, show the sheet name, and let the user switch to another sheet. Switching re-submits the same file with the chosen sheet name; the server stores nothing between requests. Choosing a sheet with no data shows E-03. | High | Planned | Changed |
| FR-35 | For CSV files, the system shall detect the separator (comma, semicolon, tab or pipe) and the encoding, trying UTF-8 with BOM, then UTF-8, then Windows-1252. | High | Planned | Changed |
| FR-36 | The system shall reject files with more than 1,000,000 data rows and show a message. | Medium | Planned | — |
| FR-37 | The system shall detect password-protected files and show a specific message. | Medium | Planned | — |
| FR-38 | The system shall trim spaces from headings, rename blank headings to "Column N" (N = the column's position in the file), and add a suffix (_2, _3) to duplicate headings. | Medium | Planned | Changed |
| FR-56 | If the first non-empty row has exactly one filled cell and the next non-empty row has more, the first row shall be treated as a title and skipped, and the next row used as the headings. | Medium | Planned | New |

### 4.2 Data Processing and Summary

**Priority: High.** The system reads the data, cleans common formatting problems, identifies column types and calculates summary values.

| ID | Requirement | Priority | Status | Change |
|---|---|---|---|---|
| FR-06 | The system shall count the number of rows and columns. | High | Planned | — |
| FR-07 | The system shall classify each column as numeric, date, category, text, ID or empty, using the rules in Section 4.2.3. | High | Planned | — |
| FR-08 | The system shall count missing values per column and in total. Empty cells, cells with only spaces, and the values "NA", "N/A", "null", "none" and "-" (any case) shall count as missing. | High | Planned | — |
| FR-09 | For numeric columns, the system shall calculate count, average, minimum and maximum. | High | Planned | — |
| FR-10 | The system shall calculate totals only when a total is meaningful, using the rule in Section 4.2.4. | Medium | Planned | — |
| FR-11 | The system shall not change the original uploaded file. | High | Planned | — |
| FR-39 | For numeric columns, the system should also calculate the median and the sample standard deviation (as Excel `STDEV.S`). | Medium | Planned | Changed |
| FR-40 | The system shall convert numbers stored as text into numbers by removing currency symbols (₹, $, €, £), thousand separators, % signs and spaces. | High | Planned | — |
| FR-41 | The system shall recognise Excel date cells and common text date formats (DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD, "12 Jan 2026"). Text dates shall be read day-first. | Medium | Planned | — |
| FR-42 | The system shall exclude ID columns from statistics and charts, but list them in the column information table. | High | Planned | — |
| FR-43 | The system shall ignore completely empty rows, and columns with no heading and no data, during analysis, and report how many were ignored as a warning. Ignored rows are not counted in the row total or shown in the preview. A column with a heading but no data is kept and classified as Empty. | Medium | Planned | Changed |
| FR-54 | Whole-number columns with an ID heading (rule 3b in 4.2.3) shall be treated as ID columns even when their values repeat. The warnings panel shall list the columns treated as IDs this way. | High | Planned | New |

#### 4.2.3 Column Type Detection Rules

Rules are applied to non-missing values, in this order. The first rule that matches decides the type.

| Order | Type | Rule | Change |
|---|---|---|---|
| 1 | **Empty** | More than 95% of values are missing. The column is flagged in warnings and skipped. | — |
| 2 | **Date** | At least 90% of values are Excel date cells or text that can be read as a date (FR-41). | — |
| 3a | **ID** (unique) | There are at least 20 rows, all non-missing values are unique, **and** either the column has an ID heading or the values are consecutive whole numbers (in any order). | Changed |
| 3b | **ID** (repeating) | The column has an ID heading **and** every value is a whole number. Values may repeat. | New |
| 4 | **Numeric** | At least 90% of values can be read as numbers after the cleaning in FR-40. | — |
| 5 | **Category** | Unique values are fewer than 50% of rows (the values repeat). A column with exactly two values (Yes/No, M/F) is always a category. | Changed |
| 6 | **Text** | Anything else (names, comments, addresses). Counted in the summary but not charted. | — |

**ID heading.** The heading is split into words at spaces, punctuation, underscores and changes of letter case (`WORK_ITEM_ID` → work, item, id; `RollNo` → roll, no; `IDNumber` → id, number). Text in brackets is ignored. The heading is an ID heading when its **last** word is one of `id`, `no`, `number`, `code`, `roll`, `key`, `seq`, or its **first** word is `id`.

| Heading | Values | Type |
|---|---|---|
| Roll No, Order ID, EmployeeID | unique | ID (3a) |
| WORK_ITEM_ID, STATE_SEQ, REVISION_NO, Customer Key | repeating whole numbers | ID (3b) |
| Number of items, No. of students, Quantity (No.) | whole numbers | Numeric (last word is not an ID word) |
| Product Code | repeating text such as "P-01" | Category (3b applies to whole numbers only) |
| Version No | 1.1, 1.2 | Numeric (not whole numbers) |

**Other notes:**
- A column where 50–90% of values are numbers is reported in warnings as "mixed numbers and text".
- Excel TRUE/FALSE cells are treated as the text values TRUE and FALSE.
- "Rows" in rules 3a and 5 means the number of data rows after ignored rows are removed.

#### 4.2.4 Meaningful Total Rule

A total is shown for a numeric column **unless**:
- the values are whole numbers between 1900 and 2100 and the column name contains "year", or
- the column name contains "%" or "percent", or
- the column name has one of the words "rate", "ratio", "avg", "average", "mean" or "age" (as a whole word, so "Wages" still gets a total).

ID columns never have totals (BR-06). **Change:** word matching clarified.

### 4.3 Chart Selection and Generation

**Priority: High.** The system chooses suitable charts using fixed rules and creates a group of charts that describes the whole dataset.

#### 4.3.2 Chart Rules

| Rule | Chart | Used when | Details | Change |
|---|---|---|---|---|
| R1 | **Line chart** | A date column exists. | The numeric value is totalled per date (or averaged, if a total is not meaningful under 4.2.4) and sorted by date. If there is no numeric column, the number of rows per date is shown instead (FR-55). If there are more than 100 distinct calendar days, values are grouped by month. | Changed |
| R2 | **Bar chart** | A category column exists. | Shows the total (or average) of a numeric column per category, sorted from highest to lowest. With no numeric column, it shows the count per category. | — |
| R3 | **Pie chart** | A category column has **2 to 6** categories. | Slices are totals of the main numeric column when that total is meaningful and has no negative values; otherwise row counts. Columns with more categories use rule R2 instead. | Changed |
| R4 | **Histogram** | A numeric column has at least 10 unique values. | Shows how the values are spread. Bin count is the larger of the Sturges and Freedman–Diaconis counts, at most 60. | Changed |
| R5 | **Scatter plot** | Two numeric columns have a correlation of at least 0.5 (positive or negative). | At most the 2 strongest pairs are shown. | — |
| R6 | **Correlation heatmap** | There are 3 or more numeric columns. | Shows how strongly each pair of numeric columns is related. | — |

#### 4.3.3 Chart Priority and Limit

Candidate charts are generated in the order R1 → R2 → R5 → R4 → R3 → R6. The first 10 are shown, with at most 3 of any one chart type.

- When there are several date, category or numeric columns, the ones with the fewest missing values are used first.
- R1 uses only the date column with the fewest missing values.
- R2 pairs every category column with the main numeric column first, then with the next numeric column, and so on.
- The "main numeric column" is the numeric column with the fewest missing values.

#### 4.3.4 Functional Requirements

| ID | Requirement | Priority | Status | Change |
|---|---|---|---|---|
| FR-12 | The system shall select chart types using the rules in Section 4.3.2. | High | Planned | — |
| FR-13 | The system shall generate more than one chart when the data supports it. | High | Planned | — |
| FR-14 | The system shall not use a pie chart for more than 6 categories. | High | Planned | — |
| FR-15 | Every chart shall have a clear title and labelled axes, including units where known. | High | Planned | — |
| FR-16 | Line charts should mark the highest and lowest points, and bar charts should highlight the largest bar. | Medium | Planned | — |
| FR-17 | The system shall skip a chart when the data is not suitable for it, and list skipped charts in the warnings panel. | High | Planned | — |
| FR-44 | The system shall show no more than 10 charts, following the priority in Section 4.3.3. | High | Planned | — |
| FR-45 | Scatter plots with more than 5,000 points shall show a random sample of 5,000 points. Statistics shall still use all rows, and the chart shall say it is a sample. | Medium | Planned | — |
| FR-46 | Bar charts with more than 15 categories shall show the top 15 and note how many categories were left out. | Medium | Planned | — |
| FR-47 | The system should show a correlation heatmap when there are 3 or more numeric columns. | Medium | Planned | — |
| FR-48 | Each chart should have a one-line caption explaining why it was chosen, for example "Compares total Sales across 5 Region values." | Medium | Planned | — |
| FR-55 | When a date column exists but no numeric column does, the system shall show a line chart of the number of rows per date (or per month, under R1). | Medium | Planned | New |

### 4.4 Dashboard Display

**Priority: High.** All results are shown together on one dashboard.

| ID | Requirement | Priority | Status | Change |
|---|---|---|---|---|
| FR-18 | The dashboard shall show the uploaded file name and, for Excel files, the sheet name. | High | Planned | — |
| FR-19 | The dashboard shall show summary cards for total rows, total columns, missing cells (count and %), number of numeric columns, and the date range when a date column exists. The date range is taken from the date column with the fewest missing values, and names that column. | High | Planned | Changed |
| FR-20 | The dashboard shall show charts in a grid: two per row at 1200 px width or more, one per row below that. | High | Planned | — |
| FR-21 | The dashboard shall be readable at 1366 × 768 without horizontal scrolling. Wide tables may scroll inside their own box. | High | Planned | Changed |
| FR-22 | The dashboard should let the user choose a column or chart. | Medium | Backlog | — |
| FR-23 | The dashboard should show warnings for: columns with more than 20% missing values, empty columns, mixed-type columns, columns treated as IDs under rule 3b, ignored rows or columns, skipped charts and sampled charts. | Medium | Planned | Changed |
| FR-49 | The dashboard shall show a column information table with name, detected type, missing count and %, number of unique values, and for numeric columns the total, average, median, minimum, maximum and standard deviation (earliest and latest for date columns). | High | Planned | Changed |
| FR-50 | The dashboard should show a preview of the first 10 rows of the data, as written in the file. | Medium | Planned | Changed |
| FR-51 | The dashboard shall have an "Analyse another file" button that returns to the upload screen. | High | Planned | — |

### 4.5 Export Results

**Priority: Medium.**

| ID | Requirement | Priority | Status | Change |
|---|---|---|---|---|
| FR-24 | The system shall allow each chart to be saved as a PNG image, using the chart's built-in download button. | Medium | Planned | — |
| FR-25 | The system may allow the whole dashboard to be downloaded as a single self-contained HTML file. | Low | Backlog | — |
| FR-26 | PDF export is not included in the first release. It will be reconsidered after user feedback. | Low | Decided | — |

### 4.6 Optional AI Recommendation

**Priority: Low / Future.** An AI feature may later suggest extra charts or explain why a chart was chosen. The project does not depend on it.

| ID | Requirement | Priority | Status | Change |
|---|---|---|---|---|
| FR-27 | The core dashboard shall work fully when the AI feature is unavailable or turned off. | High | Planned | — |
| FR-28 | The AI feature may suggest additional chart types. | Low | Future | — |
| FR-29 | The user should be able to ignore an AI suggestion. AI suggestions shall be labelled and never replace rule-based charts. | Low | Future | — |
| FR-52 | If an AI feature uses an outside service, it shall send only column names, types and summary statistics (never data rows), and only after the user agrees. | Low | Future | — |

### 4.7 Error Handling

**Priority: High.** The system handles common problems without crashing.

| ID | Requirement | Priority | Status | Change |
|---|---|---|---|---|
| FR-30 | The system shall show a useful message for an empty, damaged or unsupported file, using the messages in Section 4.7.3. | High | Planned | — |
| FR-31 | The system shall handle missing values without stopping the whole process. | High | Planned | — |
| FR-32 | The system shall record technical errors (time, file name, error type, full details) in `logs/app.log`. These details shall never be shown to general users. | Medium | Planned | — |
| FR-33 | The system shall allow the user to try another file after an error. | High | Planned | — |
| FR-53 | A failure while analysing one column or drawing one chart shall not stop the rest of the dashboard. The failed item shall be listed in the warnings panel. | High | Planned | — |

#### 4.7.3 Error Message Catalogue

| Code | Condition | Message shown to the user |
|---|---|---|
| E-01 | Unsupported file type | "This file type isn't supported. Please upload an .xlsx, .xls or .csv file." |
| E-02 | File larger than 25 MB | "This file is larger than 25 MB. Please upload a smaller file or split it into parts." |
| E-03 | No data rows or no columns | "This file has no data. Make sure the first row has column headings and there is at least one row of data below it." |
| E-04 | File damaged or unreadable | "We couldn't read this file. It may be damaged. Try opening it in Excel, saving it again, and uploading it." |
| E-05 | Password-protected file | "This file is password-protected. Please remove the password in Excel and upload it again." |
| E-06 | More than 1,000,000 rows | "This file has more than 1,000,000 rows, which is above the current limit." |
| E-07 | Process clicked with no file | "Please choose a file first." |
| E-08 | No chartable columns (warning, not error) | "No charts could be made because no columns contain numbers, dates or categories. The summary and column table are still shown." |
| E-09 | Unexpected error | "Something went wrong while processing this file. Please try again or use a different file." (Details are written to the log.) |

---

## 5. Nonfunctional Requirements

**Reference laptop:** Intel Core i5 / AMD Ryzen 5 (or similar), 8 GB RAM, SSD, Windows 11.

### 5.1 Performance

| ID | Requirement | Change |
|---|---|---|
| NFR-01 | A file of 50,000 rows × 30 columns (about 5–12 MB as CSV, depending on content) shall be processed in 30 seconds or less on the reference laptop. Target: 10 seconds. | Changed |
| NFR-02 | A 25 MB file shall be processed in 60 seconds or less on the reference laptop. | — |
| NFR-03 | The dashboard shall finish displaying within 5 seconds after processing completes. | — |
| NFR-04 | A loading indicator shall appear within 1 second of clicking Process Data. | — |

### 5.2 Safety

| ID | Requirement |
|---|---|
| NFR-05 | The original uploaded file shall never be edited, moved or deleted. The system works only on a copy in memory. |

### 5.3 Security

| ID | Requirement |
|---|---|
| NFR-06 | The local version shall not send uploaded data to any outside service. |
| NFR-07 | Uploaded files shall be processed in memory. If a temporary file is needed, it shall be deleted once processing ends, including when an error occurs. |
| NFR-08 | Uploaded file names shall be cleaned (for example with Flask's `secure_filename`) before use. |
| NFR-09 | The upload size limit shall be enforced by the server (Flask `MAX_CONTENT_LENGTH`), not only by the browser. |
| NFR-10 | Any text from the spreadsheet shown on the dashboard (headings, values, chart labels) shall be HTML-escaped, so that a cell containing HTML or script code cannot run in the browser. |
| NFR-11 | The server shall listen only on `127.0.0.1` by default. |
| NFR-12 | If the system is hosted online later, user access control and HTTPS shall be required. |

### 5.4 Software Quality Attributes

| ID | Quality | Requirement | How it is checked |
|---|---|---|---|
| NFR-13 | Ease of use | A new user can upload a file and view the dashboard without help. | At least 2 sample users complete the task unaided in under 2 minutes. |
| NFR-14 | Correctness | Summary values match the data. | Values for the test files match manual calculations in Excel, rounded to 2 decimal places. |
| NFR-15 | Reliability | A problem in one column does not stop other results (FR-53). | TF-07 produces a dashboard with warnings and no crash. |
| NFR-16 | Maintainability | Validation, profiling, chart rules and rendering are separate modules. Thresholds are kept in one configuration file. | Code review against Section 6.6. |
| NFR-17 | Compatibility | The dashboard works on current Chrome, Edge and Firefox. | Manual check in all three browsers. |
| NFR-18 | Testability | Core functions can be tested with small sample files, without starting the web server. | pytest suite runs in under 60 seconds. |

### 5.5 Business Rules

| ID | Rule |
|---|---|
| BR-01 | Only .xlsx, .xls and .csv files may be processed. |
| BR-02 | The original uploaded file must remain unchanged. |
| BR-03 | A pie chart must not be used for more than 6 categories. |
| BR-04 | Easy-to-read charts are preferred over decorative ones (no 3D charts). |
| BR-05 | The optional AI feature must not block or replace the rule-based system. |
| BR-06 | ID columns are never averaged, totalled or charted. |

---

## 6. Other Requirements

### 6.1 Agile Development Plan

Sprints of about two weeks. Requirements are chosen from the backlog at the start of each sprint; the result is shown at the end and the feedback updates this SRS.

| Sprint | Goal | Main requirements |
|---|---|---|
| 1 | Upload, validation and reading files | FR-01 to FR-05, FR-11, FR-34 (default sheet), FR-35, FR-36, FR-38, FR-56, NFR-08, NFR-09 |
| 2 | Column detection, statistics and chart rules (tested without the UI) | FR-06 to FR-10, FR-12 to FR-17, FR-39 to FR-48, FR-54, FR-55 |
| 3 | Dashboard design and multiple charts | FR-18 to FR-21, FR-23, FR-24, FR-34 (sheet selector), FR-49 to FR-51, NFR-10 |
| 4 | Error handling, testing and improvements | FR-30 to FR-33, FR-37, FR-53, NFR-01 to NFR-04, NFR-13 to NFR-18 |
| Later | Dashboard HTML export, column selection, optional AI | FR-22, FR-25, FR-27 to FR-29, FR-52 |

### 6.2 User Stories and Acceptance Criteria

**US-01 – Upload a file.** _As a general user, I want to upload my spreadsheet so that I can see charts without making them myself._
- Given a valid .csv, .xlsx or .xls file under 25 MB, when I click Process Data, then the dashboard is shown.
- Given a .pdf file, when I click Process Data, then I see message E-01 and stay on the upload screen.

**US-02 – Understand bad files.** _As a general user, I want clear messages when my file has a problem so that I know how to fix it._
- Given an empty, damaged, password-protected or oversized file, I see the matching message from 4.7.3 and no technical error text.
- After any error, I can choose another file without restarting the app.

**US-03 – See key numbers.** _As a general user, I want summary cards so that I can see the size and quality of my data at a glance._
- The dashboard shows rows, columns, missing cells and numeric column count, and these match the file.

**US-04 – Get suitable charts.** _As a general user, I want the system to pick sensible charts so that I don't have to know which chart to use._
- Given a file with a date column and a numeric column, a line chart is shown.
- Given a category column with 4 values, a bar chart is shown and a pie chart may be shown.
- Given a category column with 12 values, no pie chart is shown for it.
- No more than 10 charts are shown.
- ID columns, including repeating ones such as a work item ID, are never added up or charted.

**US-05 – Choose a sheet.** _As a general user with a multi-sheet Excel file, I want to pick which sheet to analyse._
- The first sheet with data is analysed by default, and its name is shown.
- Choosing another sheet from the selector refreshes the dashboard for that sheet.

**US-06 – Save a chart.** _As a general user, I want to save a chart as an image so that I can put it in a report._
- Clicking the chart's download button saves a PNG file that shows the full chart with its title.

**US-07 – Trust the data.** _As a general user, I want to see warnings and a data preview so that I know the file was read correctly._
- Columns with more than 20% missing values appear in the warnings panel.
- The first 10 rows are shown and match the original file.

**US-08 – Fix problems.** _As a developer, I want technical errors logged so that I can fix problems users report._
- When an unexpected error occurs, an entry with time, file name and error details is added to `logs/app.log`.

### 6.3 Definition of Done

A backlog item is **Done** when:
1. The code is written and merged into the main project.
2. The related acceptance criteria (6.2) pass.
3. Automated tests for the item are written and all tests pass.
4. It has been checked manually with at least one file from the test set (6.4).
5. It has been shown at a sprint review.
6. Its status in this SRS is updated.

### 6.4 Testing Requirements

- Unit tests (pytest) for validation, column detection, statistics and chart rules, run without the web server.
- Integration tests that upload each test file to the Flask app and check the response.
- Summary values checked against manual calculations in Excel.
- Chart choices checked against the rules in 4.3.2.
- At least two sample users test the dashboard and give feedback (NFR-13).

The test files are generated by `tests/make_test_files.py`.

| ID | Test file | Expected result | Change |
|---|---|---|---|
| TF-01 | Small clean CSV (20 rows: date, category, two numeric columns) | Dashboard with line, bar, histogram and pie charts; values match Excel | — |
| TF-02 | Empty CSV (0 bytes) | E-03 | — |
| TF-03 | CSV with headings only | E-03 | — |
| TF-04 | A PDF renamed to .csv | E-01 or E-04, no crash | — |
| TF-05 | Semicolon-separated CSV saved in Windows-1252 encoding with € and £ values (₹ cannot be stored in Windows-1252) | Read correctly; currency values detected as numeric | Changed |
| TF-06 | Excel file with 3 sheets, the first one empty | Second sheet analysed by default; selector lists all sheets | — |
| TF-07 | Messy file: mixed date formats, blanks, "N/A", numbers stored as text (including ₹, UTF-8) | Dashboard with warnings, no crash; types detected correctly | — |
| TF-08 | Category column with 50 categories | No pie chart; bar chart shows top 15 with a note | — |
| TF-09 | File with a Roll No column (1 to 200) | Roll No detected as ID; not averaged or charted | — |
| TF-10 | Large file: 50,000 rows × 30 columns | Processed within NFR-01 limits | — |
| TF-11 | File slightly over 25 MB | E-02, rejected before reading | — |
| TF-12 | Legacy .xls file | Read correctly | — |
| TF-13 | Password-protected .xlsx | E-05 | — |
| TF-14 | Blank and duplicate headings | Headings renamed as in FR-38 | — |
| TF-15 | Cell containing `<script>alert(1)</script>` | Shown as plain text; script does not run | — |
| TF-16 | Only text columns (names, comments) | Summary and column table shown; warning E-08 | — |
| TF-17 | Change history: a date column and repeating WORK_ITEM_ID, STATE_SEQ and REVISION_NO columns, plus a state category | The three columns detected as IDs and listed in warnings; none totalled, averaged or charted; a line chart of rows per month | New |
| TF-18 | Excel sheet with a title in A1, a blank row, then the headings | Title skipped; headings read from the correct row | New |

### 6.5 Data Storage Requirements

No database in the first version. Uploaded files are processed in memory and discarded; the server keeps nothing between requests. The only file the system writes is the developer error log (`logs/app.log`).

### 6.6 Proposed Module Structure

Design guidance supporting NFR-16 and NFR-18.

```
app.py            Flask routes only (upload page, process, dashboard)
validator.py      File type, size, structure and password checks; reads the file into a table
profiler.py       Cleaning, column type detection, statistics, warnings
chart_rules.py    Decides WHICH charts to make; returns a list of chart specifications
renderer.py       Turns chart specifications into Plotly charts
config.py         Thresholds (25 MB, 6 pie slices, 10 charts, 5,000 sample points, ...)
templates/        upload.html, dashboard.html
static/           CSS and JavaScript (plotly.js is served from the installed plotly package)
tests/            pytest tests and the test file generator
logs/             app.log
```

`chart_rules.py` returns plain data, not drawings, for example:

```json
[
  {"type": "line", "x": "Order Date", "y": "Sales", "agg": "sum", "rule": "R1"},
  {"type": "bar",  "x": "Region",     "y": "Sales", "agg": "sum", "rule": "R2"}
]
```

This lets the chart rules be tested without rendering anything, and lets a future AI feature add chart specifications without changing the rest of the system.

---

## Appendix A: Glossary

| Term | Meaning |
|---|---|
| Category column | A column with repeated values, such as Region or Gender. |
| Correlation | A number from -1 to 1 showing how strongly two numeric columns move together. |
| ID column | A column that identifies a row or an item, such as Roll No, Order ID or a work item ID. Its values may repeat when the same item appears in several rows. |
| Sampling | Using a random subset of rows to draw a chart faster. |
| Sprint | A short, fixed period (about two weeks) in which a set of backlog items is built. |

---

## Appendix B: Traceability Matrix

| Requirement | Sprint | Verified by |
|---|---|---|
| FR-01, FR-02 | 1 | TF-01, TF-04, TF-12 |
| FR-03 | 1 | TF-02, TF-03 |
| FR-04, FR-30 | 1, 4 | TF-04, TF-13 |
| FR-05, NFR-09 | 1 | TF-11 |
| FR-06, FR-09, FR-10, FR-39 | 2 | TF-01 (manual check in Excel) |
| FR-07, FR-40, FR-41 | 2 | TF-05, TF-07 |
| FR-08, FR-31 | 2 | TF-07 |
| FR-11, NFR-05 | 1 | All test files (file hash unchanged after processing) |
| FR-12, FR-13 | 2 | TF-01, US-04 |
| FR-14, BR-03, FR-46 | 2 | TF-08 |
| FR-15, FR-16, FR-48 | 2, 3 | TF-01 (visual check) |
| FR-17, FR-23 | 2, 3 | TF-07, TF-16, TF-17 |
| FR-18 to FR-21 | 3 | TF-01, check at 1366 × 768 |
| FR-24 | 3 | US-06 |
| FR-32 | 4 | Forced error test, US-08 |
| FR-33, FR-51 | 3, 4 | US-02 |
| FR-34 | 1, 3 | TF-06 |
| FR-35 | 1 | TF-05 |
| FR-36 | 1 | Generated file with over 1,000,000 rows |
| FR-37 | 4 | TF-13 |
| FR-38 | 1 | TF-14 |
| FR-42, BR-06 | 2 | TF-09, TF-17 |
| FR-43 | 2 | TF-07 |
| FR-44, FR-45 | 2 | TF-10 |
| FR-47 | 2 | TF-10 |
| FR-49, FR-50 | 3 | TF-01, US-07 |
| FR-53, NFR-15 | 4 | TF-07 |
| FR-54 | 2 | TF-17 |
| FR-55 | 2 | TF-17 |
| FR-56 | 1 | TF-18 |
| NFR-01, NFR-02 | 4 | TF-10, file of about 25 MB |
| NFR-03, NFR-04 | 4 | Timed manual test |
| NFR-06, NFR-11 | 1 | Code review; run with network disconnected |
| NFR-07, NFR-08 | 1 | Code review |
| NFR-10 | 3 | TF-15 |
| NFR-13 | 4 | Sample user test |
| NFR-14 | 2 | TF-01 compared with Excel |
| NFR-17 | 4 | Manual check in Chrome, Edge and Firefox |
| NFR-18 | All | pytest run time |

---

## Appendix C: Open Items

1. Whether column and chart selection (FR-22) will be in the first release. Decide at the Sprint 3 review.
2. Whether the optional AI recommendation feature (4.6) will be built, and with which service.
3. **Chart variety:** with the 4.3.3 order and the 3-per-type cap, files with many date, category and numeric columns fill all 10 slots with line, bar, scatter and histogram charts, so pie charts and heatmaps rarely appear. To be decided later.
4. Whether the detection thresholds (90% rules, 0.5 correlation, 50% category rule) need adjusting after testing with real user files.
5. Whether the system will be hosted online after the first release (see the decisions log).
