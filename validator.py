"""File checks and reading (SRS 4.1).

Turns the uploaded bytes into a table of original cell values with clean headings.
Works only on the bytes in memory; the uploaded file itself is never touched (FR-11, NFR-05).
"""

from __future__ import annotations

import codecs
import csv
import datetime
import io
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

import config

ZIP_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06")
OLE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"   # legacy .xls, and encrypted .xlsx
ENCRYPTED_OOXML_MARKER = "EncryptionInfo".encode("utf-16-le")
OTHER_BINARY_SIGNATURES = ZIP_SIGNATURES + (
    OLE_SIGNATURE, b"%PDF", b"\x89PNG", b"\xff\xd8\xff", b"GIF8", b"Rar!", b"7z\xbc\xaf",
)


class FileError(Exception):
    """A file problem the user can fix. `code` is a key of config.MESSAGES (SRS 4.7.3)."""

    def __init__(self, code: str, cause: BaseException | None = None):
        super().__init__(code)
        self.code = code
        self.cause = cause

    @property
    def message(self) -> str:
        return config.MESSAGES[self.code]


@dataclass
class RawTable:
    """One sheet (or CSV) after reading: headings plus the original cell values of each data row."""

    file_name: str
    file_kind: str                       # "xlsx", "xls" or "csv"
    data: pd.DataFrame                   # object dtype; columns are the cleaned headings
    sheet_name: str | None = None
    sheet_names: list[str] = field(default_factory=list)
    encoding: str | None = None
    separator: str | None = None
    ignored_rows: int = 0                # completely empty rows dropped (FR-43)
    ignored_columns: int = 0             # columns with no heading and no data dropped (FR-43)


def read_upload(file_name: str, content: bytes, sheet: str | None = None) -> RawTable:
    """Validate the upload and read it. Raises FileError with an E-xx code on any user-fixable problem."""
    extension = Path(file_name).suffix.lower()
    if extension not in config.SUPPORTED_EXTENSIONS:
        raise FileError("E-01")
    if len(content) > config.MAX_FILE_BYTES:
        raise FileError("E-02")
    if not content.strip():
        raise FileError("E-03")

    kind = _detect_kind(extension, content)
    if kind == "csv":
        return _read_csv(file_name, content)
    return _read_excel(file_name, content, kind, sheet)


def missing_mask(column: pd.Series) -> pd.Series:
    """True where a cell counts as missing (FR-08): blank, spaces only, or NA, N/A, null, none, - in any case."""
    normalised = column.map(lambda v: v.strip().lower() if isinstance(v, str) else None)
    return column.isna() | normalised.isin(config.MISSING_TOKENS)


def cell_text(value) -> str:
    """Show a cell value the way a user expects to see it (headings, preview, category labels)."""
    if value is None or (isinstance(value, float) and np.isnan(value)) or value is pd.NaT:
        return ""
    if isinstance(value, (bool, np.bool_)):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))
    if isinstance(value, datetime.time):
        return value.strftime("%H:%M:%S")
    if isinstance(value, datetime.datetime):        # includes pandas Timestamp
        if (value.hour, value.minute, value.second) == (0, 0, 0):
            return value.strftime("%Y-%m-%d")
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, datetime.date):
        return value.strftime("%Y-%m-%d")
    return str(value)


def clean_headings(values) -> list[str]:
    """FR-38: trim headings, name blank ones "Column N", and suffix duplicates with _2, _3."""
    names: list[str] = []
    seen: set[str] = set()
    for position, value in values:
        name = cell_text(value).strip()
        if not name:
            name = f"Column {position + 1}"
        unique, n = name, 2
        while unique in seen:
            unique = f"{name}_{n}"
            n += 1
        seen.add(unique)
        names.append(unique)
    return names


# --- File kind -------------------------------------------------------------------------------

def _detect_kind(extension: str, content: bytes) -> str:
    """FR-02: the content must really be a spreadsheet of a supported kind, not just have the right name."""
    if extension == ".csv":
        if content.startswith(OTHER_BINARY_SIGNATURES) or b"\x00" in content[:8192]:
            raise FileError("E-01")
        return "csv"

    if content.startswith(OLE_SIGNATURE):
        # An encrypted .xlsx is stored inside an OLE container with an EncryptionInfo stream (FR-37).
        if ENCRYPTED_OOXML_MARKER in content:
            raise FileError("E-05")
        return "xls"
    if content.startswith(ZIP_SIGNATURES):
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                names = archive.namelist()
        except (zipfile.BadZipFile, OSError) as exc:
            raise FileError("E-04", exc) from exc
        if not any(name.startswith("xl/") for name in names):
            raise FileError("E-01")       # another Office or zip file renamed to .xlsx
        return "xlsx"
    raise FileError("E-01")


# --- CSV -------------------------------------------------------------------------------------

def _read_csv(file_name: str, content: bytes) -> RawTable:
    text, encoding = _decode(content)
    separator = _detect_separator(text)
    try:
        raw = pd.read_csv(
            io.StringIO(text), sep=separator, header=None, dtype=str, keep_default_na=False,
            skip_blank_lines=False, index_col=False,
        )
    except pd.errors.EmptyDataError as exc:
        raise FileError("E-03", exc) from exc
    except pd.errors.ParserError:
        raw = _read_ragged_csv(text, separator)
    table = _build_table(raw.astype(object), file_name, "csv")
    table.encoding, table.separator = encoding, separator
    return table


def _decode(content: bytes) -> tuple[str, str]:
    """FR-35: UTF-8 with BOM, UTF-8, then Windows-1252."""
    if content.startswith(codecs.BOM_UTF8):
        try:
            return content[len(codecs.BOM_UTF8):].decode("utf-8"), "UTF-8 with BOM"
        except UnicodeDecodeError as exc:
            raise FileError("E-04", exc) from exc
    try:
        return content.decode("utf-8"), "UTF-8"
    except UnicodeDecodeError:
        pass
    try:
        return content.decode("cp1252"), "Windows-1252"
    except UnicodeDecodeError as exc:
        raise FileError("E-04", exc) from exc


def _detect_separator(text: str) -> str:
    """FR-35: comma, semicolon, tab or pipe. csv.Sniffer first, then the most consistent candidate."""
    sample = text[:config.CSV_SNIFF_CHARS]
    if len(text) > len(sample) and "\n" in sample:
        sample = sample[:sample.rindex("\n")]        # do not judge a half-read last line
    try:
        found = csv.Sniffer().sniff(sample, delimiters="".join(config.CSV_SEPARATORS)).delimiter
        if found in config.CSV_SEPARATORS:
            return found
    except csv.Error:
        pass

    lines = [line for line in sample.splitlines() if line.strip()][:50]
    best, best_score = ",", (0, 0)
    for separator in config.CSV_SEPARATORS:
        counts = [len(row) for row in csv.reader(lines, delimiter=separator)]
        if not counts or counts[0] < 2:
            continue
        score = (sum(1 for c in counts if c == counts[0]), counts[0])   # consistent rows first, then width
        if score > best_score:
            best, best_score = separator, score
    return best


def _read_ragged_csv(text: str, separator: str) -> pd.DataFrame:
    """Slower path for CSV files whose rows have different numbers of fields."""
    rows = list(csv.reader(io.StringIO(text), delimiter=separator))
    width = max((len(row) for row in rows), default=0)
    return pd.DataFrame([row + [""] * (width - len(row)) for row in rows], dtype=object)


# --- Excel -----------------------------------------------------------------------------------

def _read_excel(file_name: str, content: bytes, kind: str, sheet: str | None) -> RawTable:
    book = _open_workbook(content, kind)
    sheet_names = [str(name) for name in book.sheet_names]

    if sheet in sheet_names:
        candidates = [sheet]                       # the user picked a sheet (FR-34)
    else:
        candidates = sheet_names                   # default: first sheet with usable data
    last_error: FileError | None = None
    for name in candidates:
        try:
            raw = book.parse(name, header=None)
        except Exception as exc:                   # a damaged sheet
            last_error = FileError("E-04", exc)
            continue
        try:
            table = _build_table(raw.astype(object), file_name, kind)
        except FileError as exc:
            if exc.code != "E-03":
                raise
            last_error = exc
            continue
        table.sheet_name, table.sheet_names = name, sheet_names
        return table
    raise last_error or FileError("E-03")


def _open_workbook(content: bytes, kind: str) -> pd.ExcelFile:
    """.xlsx with python-calamine, falling back to openpyxl; .xls with xlrd (SRS 3.3)."""
    engines = ("calamine", "openpyxl") if kind == "xlsx" else ("xlrd",)
    error: BaseException | None = None
    for engine in engines:
        try:
            return pd.ExcelFile(io.BytesIO(content), engine=engine)
        except ImportError as exc:
            error = exc
        except Exception as exc:
            if "encrypt" in str(exc).lower() or "password" in str(exc).lower():
                raise FileError("E-05", exc) from exc
            error = exc
    raise FileError("E-04", error)


# --- Headings and empty rows/columns ---------------------------------------------------------

def _build_table(raw: pd.DataFrame, file_name: str, kind: str) -> RawTable:
    """Find the heading row (skipping a title row, FR-56), drop completely empty rows and columns,
    and apply the FR-03/FR-36 checks."""
    if raw.empty:
        raise FileError("E-03")
    raw.columns = range(raw.shape[1])
    missing = raw.apply(missing_mask)

    filled_counts = (~missing).sum(axis=1).to_numpy()
    filled_rows = np.flatnonzero(filled_counts)
    if not len(filled_rows):
        raise FileError("E-03")
    header_at = int(filled_rows[0])               # first non-empty row holds the headings (SRS 2.7)
    # FR-56: a single-cell title such as "Sales Report 2026" above wider headings is skipped.
    if len(filled_rows) > 1 and filled_counts[header_at] == 1 and filled_counts[filled_rows[1]] > 1:
        header_at = int(filled_rows[1])

    header = raw.iloc[header_at]
    data = raw.iloc[header_at + 1:]
    data_missing = missing.iloc[header_at + 1:]
    empty_rows = data_missing.all(axis=1)
    empty_columns = missing.iloc[header_at] & data_missing.all(axis=0)

    data = data.loc[~empty_rows, ~empty_columns]
    if data.shape[0] == 0 or data.shape[1] == 0:
        raise FileError("E-03")
    if data.shape[0] > config.MAX_DATA_ROWS:
        raise FileError("E-06")

    data.columns = clean_headings(header[~empty_columns].items())
    return RawTable(
        file_name=file_name,
        file_kind=kind,
        data=data.reset_index(drop=True),
        ignored_rows=int(empty_rows.sum()),
        ignored_columns=int(empty_columns.sum()),
    )
