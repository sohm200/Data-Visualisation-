"""All thresholds and fixed settings in one place (SRS NFR-16).

Change values here to adjust how files are checked, how columns are typed and
which charts are chosen. Nothing else in the code should hard-code these numbers.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = Path(os.environ.get("DASHBOARD_LOG_FILE", BASE_DIR / "logs" / "app.log"))   # FR-32

# --- Server (SRS 3.4, NFR-11) ---
HOST = os.environ.get("DASHBOARD_HOST", "127.0.0.1")   # container sets 0.0.0.0
PORT = 5000

# --- File upload and validation (SRS 4.1) ---
SUPPORTED_EXTENSIONS = (".xlsx", ".xls", ".csv")           # FR-01, BR-01
MAX_FILE_BYTES = 25 * 1024 * 1024                           # FR-05: 25 MB
# Flask rejects the whole request above this size before reading it (NFR-09).
# The small allowance covers the multipart form overhead around the file itself.
MAX_REQUEST_BYTES = MAX_FILE_BYTES + 64 * 1024
MAX_DATA_ROWS = 1_000_000                                   # FR-36
CSV_SEPARATORS = (",", ";", "\t", "|")                     # FR-35
CSV_SNIFF_CHARS = 64 * 1024

# --- Data cleaning and column types (SRS 4.2) ---
MISSING_TOKENS = frozenset({"", "na", "n/a", "null", "none", "-"})   # FR-08 (compared lower-case, trimmed)
NUMBER_STRIP_PATTERN = r"[₹$€£%,\s ]"                  # FR-40: removed before reading a number
CURRENCY_SYMBOLS = ("₹", "$", "€", "£")

# FR-41: text date formats, tried in this order. Day-first (SRS 2.7).
DATE_FORMATS = (
    "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y",
    "%Y-%m-%d", "%Y/%m/%d",
    "%d %b %Y", "%d %B %Y", "%d-%b-%Y", "%d-%B-%Y", "%d %b, %Y",
    "%b %d, %Y", "%B %d, %Y",
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M",
    "%d-%m-%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M",
    "%d-%m-%y", "%d/%m/%y",
)
DATE_SAMPLE_SIZE = 200          # values tried before parsing a whole text column as dates
DATE_SAMPLE_MIN_RATIO = 0.5     # skip the full parse if fewer than this share of the sample are dates

EMPTY_COLUMN_MISSING_RATIO = 0.95   # 4.2.3 rule 1: more than this share missing -> Empty
DATE_MIN_RATIO = 0.90               # 4.2.3 rule 2
ID_MIN_ROWS = 20                    # 4.2.3 rule 3a
# 4.2.3 "ID heading": the heading's last word is one of these, or its first word is one of ID_FIRST_WORDS.
ID_LAST_WORDS = ("id", "no", "number", "code", "roll", "key", "seq")
ID_FIRST_WORDS = ("id",)
NUMERIC_MIN_RATIO = 0.90            # 4.2.3 rule 4
MIXED_MIN_RATIO = 0.50              # 50-90% numbers -> "mixed numbers and text" warning
CATEGORY_MAX_UNIQUE_RATIO = 0.50    # 4.2.3 rule 5: unique values fewer than this share of rows
HIGH_MISSING_RATIO = 0.20           # FR-23: warn above 20% missing

# 4.2.4 Meaningful total rule
NO_TOTAL_YEAR_RANGE = (1900, 2100)
NO_TOTAL_NAME_WORDS = ("rate", "ratio", "avg", "average", "mean", "age")
NO_TOTAL_NAME_SUBSTRINGS = ("%", "percent")

# --- Chart selection (SRS 4.3) ---
MAX_CHARTS = 10                     # FR-44
MAX_CHARTS_PER_TYPE = 3             # 4.3.3
LINE_MONTHLY_AFTER_DATES = 100      # R1: group by month above this many distinct dates
LINE_MIN_POINTS = 2
BAR_TOP_N = 15                      # FR-46
PIE_MIN_SLICES = 2                  # R3
PIE_MAX_SLICES = 6                  # R3, FR-14, BR-03
HISTOGRAM_MIN_UNIQUE = 10           # R4
HISTOGRAM_MAX_BINS = 60
SCATTER_MIN_CORRELATION = 0.5       # R5
SCATTER_MAX_PAIRS = 2
SCATTER_MAX_POINTS = 5000           # FR-45
SCATTER_SAMPLE_SEED = 42
HEATMAP_MIN_NUMERIC = 3             # R6, FR-47

# --- Dashboard (SRS 3.1) ---
PREVIEW_ROWS = 10                   # FR-50

# --- Messages shown to the user (SRS 4.7.3) ---
MESSAGES = {
    "E-01": "This file type isn't supported. Please upload an .xlsx, .xls or .csv file.",
    "E-02": "This file is larger than 25 MB. Please upload a smaller file or split it into parts.",
    "E-03": "This file has no data. Make sure the first row has column headings and there is at least one row of data below it.",
    "E-04": "We couldn't read this file. It may be damaged. Try opening it in Excel, saving it again, and uploading it.",
    "E-05": "This file is password-protected. Please remove the password in Excel and upload it again.",
    "E-06": "This file has more than 1,000,000 rows, which is above the current limit.",
    "E-07": "Please choose a file first.",
    "E-08": "No charts could be made because no columns contain numbers, dates or categories. The summary and column table are still shown.",
    "E-09": "Something went wrong while processing this file. Please try again or use a different file.",
}
