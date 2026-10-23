"""Cleaning, column type detection, statistics and warnings (SRS 4.2).

Works on a copy of the values read by validator.py; the original data is never changed.
"""

from __future__ import annotations

import datetime
import logging
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import config
from validator import RawTable, cell_text, missing_mask

log = logging.getLogger("dashboard")

NUMERIC, DATE, CATEGORY, TEXT, ID, EMPTY, FAILED = "numeric", "date", "category", "text", "id", "empty", "failed"
TYPE_LABELS = {
    NUMERIC: "Number", DATE: "Date", CATEGORY: "Category", TEXT: "Text",
    ID: "ID", EMPTY: "Empty", FAILED: "Not analysed",
}
NUMBER_TYPES = (int, float, np.int64, np.int32, np.float64, np.float32)
DATE_TYPES = (datetime.datetime, datetime.date, pd.Timestamp)


@dataclass
class DataWarning:
    # high_missing, empty_column, mixed_type, treated_as_id, ignored, chart_skipped, chart_sampled, item_failed, no_charts
    kind: str
    message: str


@dataclass
class ColumnProfile:
    name: str
    position: int
    type: str
    missing_count: int = 0
    missing_percent: float = 0.0
    unique_count: int = 0
    is_mixed: bool = False
    repeating_id: bool = False            # ID by rule 3b (values repeat), listed in the warnings
    unit: str | None = None               # "₹", "%", ... when the values carried one
    # Numeric columns (FR-09, FR-10, FR-39)
    count: int | None = None
    total: float | None = None
    total_meaningful: bool = False
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    # Date columns
    earliest: pd.Timestamp | None = None
    latest: pd.Timestamp | None = None
    distinct_days: int = 0

    @property
    def type_label(self) -> str:
        return TYPE_LABELS[self.type]


@dataclass
class DatasetProfile:
    file_name: str
    sheet_name: str | None
    sheet_names: list[str]
    row_count: int
    column_count: int
    missing_cells: int
    missing_percent: float
    columns: list[ColumnProfile]
    values: pd.DataFrame                  # cleaned values of numeric (float), date (datetime) and category (str) columns
    correlations: pd.DataFrame | None
    preview_columns: list[str]
    preview_rows: list[list[str]]
    warnings: list[DataWarning] = field(default_factory=list)

    def columns_of(self, column_type: str) -> list[ColumnProfile]:
        """Columns of one type, fewest missing values first (SRS 4.3.3), then file order."""
        chosen = [c for c in self.columns if c.type == column_type]
        return sorted(chosen, key=lambda c: (c.missing_count, c.position))

    def column(self, name: str) -> ColumnProfile:
        return next(c for c in self.columns if c.name == name)

    @property
    def numeric_count(self) -> int:
        return sum(1 for c in self.columns if c.type == NUMERIC)

    @property
    def date_range(self) -> ColumnProfile | None:
        """The date column shown on the summary card: the one with the fewest missing values."""
        dates = self.columns_of(DATE)
        return dates[0] if dates else None


def profile(table: RawTable) -> DatasetProfile:
    data = table.data
    rows = len(data)
    columns: list[ColumnProfile] = []
    values: dict[str, pd.Series] = {}
    warnings: list[DataWarning] = []

    if table.ignored_rows or table.ignored_columns:
        warnings.append(DataWarning("ignored", _ignored_message(table.ignored_rows, table.ignored_columns)))

    for position, name in enumerate(data.columns):
        try:
            column, typed = profile_column(name, position, data[name])
        except Exception:                       # FR-53: one bad column must not stop the dashboard
            log.exception("Column %r in %s could not be analysed", name, table.file_name)
            column, typed = _failed_column(name, position, data[name]), None
            warnings.append(DataWarning("item_failed", f"Column '{name}' could not be analysed and was left out."))
        columns.append(column)
        if typed is not None:
            values[name] = typed
        warnings.extend(_column_warnings(column))

    repeating_ids = [c.name for c in columns if c.repeating_id]
    if repeating_ids:                           # FR-54, FR-23
        warnings.append(DataWarning("treated_as_id", "Treated as IDs, so not added up or charted: "
                                                     f"{', '.join(repeating_ids)}."))

    missing_cells = sum(c.missing_count for c in columns)
    total_cells = rows * len(columns)
    result = DatasetProfile(
        file_name=table.file_name,
        sheet_name=table.sheet_name,
        sheet_names=table.sheet_names,
        row_count=rows,
        column_count=len(columns),
        missing_cells=missing_cells,
        missing_percent=100.0 * missing_cells / total_cells if total_cells else 0.0,
        columns=columns,
        values=pd.DataFrame(values, index=data.index),
        correlations=None,
        preview_columns=list(data.columns),
        preview_rows=data.head(config.PREVIEW_ROWS).map(cell_text).values.tolist(),
        warnings=warnings,
    )
    result.correlations = _correlations(result)
    return result


def profile_column(name: str, position: int, series: pd.Series) -> tuple[ColumnProfile, pd.Series | None]:
    """Classify one column with the SRS 4.2.3 rules and calculate its statistics.

    Returns the profile and the cleaned values used for charts (None for ID, text and empty columns).
    """
    rows = len(series)
    missing = missing_mask(series)
    present = series[~missing].map(lambda v: v.strip() if isinstance(v, str) else v)
    kinds = present.map(type)
    labels = present.astype(object)
    not_text = kinds != str
    if not_text.any():
        labels[not_text] = present[not_text].map(cell_text)
    column = ColumnProfile(
        name=name,
        position=position,
        type=TEXT,
        missing_count=int(missing.sum()),
        missing_percent=100.0 * missing.sum() / rows if rows else 0.0,
        unique_count=int(labels.nunique()),
    )

    # Rule 1: Empty
    if not len(present) or column.missing_count / rows > config.EMPTY_COLUMN_MISSING_RATIO:
        column.type = EMPTY
        return column, None

    # Rule 2: Date
    dates = to_dates(present, kinds)
    if dates.notna().mean() >= config.DATE_MIN_RATIO:
        column.type = DATE
        valid = dates.dropna()
        column.earliest, column.latest = valid.min(), valid.max()
        column.distinct_days = int(valid.dt.normalize().nunique())
        return column, dates.reindex(series.index)

    numbers = to_numbers(present, kinds)
    number_ratio = numbers.notna().mean()

    # Rule 3a: ID with unique values
    id_heading = has_id_heading(name)
    if rows >= config.ID_MIN_ROWS and column.unique_count == len(present) and (
        id_heading or _is_consecutive(numbers)
    ):
        column.type = ID
        return column, None

    # Rule 3b: ID whose values repeat, such as a work item ID in a change history (FR-54)
    if id_heading and numbers.notna().all() and (numbers % 1 == 0).all():
        column.type = ID
        column.repeating_id = True
        return column, None

    # Rule 4: Numeric
    if number_ratio >= config.NUMERIC_MIN_RATIO:
        column.type = NUMERIC
        column.unit = _unit(present, kinds)
        column.unique_count = int(numbers.nunique())
        _numeric_stats(column, numbers.dropna())
        return column, numbers.reindex(series.index)

    column.is_mixed = number_ratio >= config.MIXED_MIN_RATIO

    # Rule 5: Category (values repeat, or exactly two values)
    if column.unique_count == 2 or column.unique_count < config.CATEGORY_MAX_UNIQUE_RATIO * rows:
        column.type = CATEGORY
        return column, labels.reindex(series.index)

    # Rule 6: Text
    return column, None


def to_numbers(present: pd.Series, kinds: pd.Series) -> pd.Series:
    """FR-40: numbers, and text numbers with ₹ $ € £, thousand separators, % and spaces removed. NaN otherwise."""
    result = pd.Series(np.nan, index=present.index, dtype=float)
    native = kinds.isin(NUMBER_TYPES)
    if native.any():
        result[native] = present[native].astype(float)
    text = kinds == str
    if text.any():
        cleaned = present[text].astype(str).str.replace(config.NUMBER_STRIP_PATTERN, "", regex=True)
        result[text] = pd.to_numeric(cleaned, errors="coerce").astype(float)
    result[~np.isfinite(result)] = np.nan
    return result


def to_dates(present: pd.Series, kinds: pd.Series) -> pd.Series:
    """FR-41: Excel date cells, plus text dates in the formats of config.DATE_FORMATS (day-first)."""
    pieces = []
    native = kinds.isin(DATE_TYPES)
    if native.any():
        pieces.append(pd.to_datetime(present[native], errors="coerce"))
    text = present[kinds == str]
    if len(text):
        sample = _parse_text_dates(text.iloc[:config.DATE_SAMPLE_SIZE])
        if sample.notna().mean() >= config.DATE_SAMPLE_MIN_RATIO:
            pieces.append(_parse_text_dates(text))
    if not pieces:
        return pd.Series(pd.NaT, index=present.index, dtype="datetime64[ns]")
    combined = pd.concat(pieces) if len(pieces) > 1 else pieces[0]
    return pd.to_datetime(combined.reindex(present.index))


def _parse_text_dates(text: pd.Series) -> pd.Series:
    found = []
    remaining = text
    for date_format in config.DATE_FORMATS:
        if remaining.empty:
            break
        parsed = pd.to_datetime(remaining, format=date_format, errors="coerce")
        matched = parsed.notna()
        if matched.any():
            found.append(parsed[matched])
            remaining = remaining[~matched]
    if not found:
        return pd.Series(pd.NaT, index=text.index, dtype="datetime64[ns]")
    return pd.to_datetime(pd.concat(found)).reindex(text.index)


def total_is_meaningful(name: str, numbers: pd.Series) -> bool:
    """SRS 4.2.4: no totals for years, percentages, rates, ratios, averages or ages."""
    lower = name.lower()
    if any(part in lower for part in config.NO_TOTAL_NAME_SUBSTRINGS):
        return False
    if set(heading_words(name)) & set(config.NO_TOTAL_NAME_WORDS):
        return False
    low, high = config.NO_TOTAL_YEAR_RANGE
    if "year" in lower and len(numbers) and (numbers % 1 == 0).all() and numbers.between(low, high).all():
        return False
    return True


def _numeric_stats(column: ColumnProfile, numbers: pd.Series) -> None:
    column.count = int(len(numbers))
    if not column.count:
        return
    column.mean = float(numbers.mean())
    column.median = float(numbers.median())
    column.std = float(numbers.std()) if column.count > 1 else None     # sample std dev, like Excel STDEV.S
    column.minimum = float(numbers.min())
    column.maximum = float(numbers.max())
    column.total_meaningful = total_is_meaningful(column.name, numbers)
    if column.total_meaningful:
        column.total = float(numbers.sum())


def has_id_heading(name: str) -> bool:
    """SRS 4.2.3 "ID heading": the last word is an ID word, or the first word is "id". Text in brackets is ignored,
    so "Number of items" and "Quantity (No.)" are not ID headings but "WORK_ITEM_ID" and "Roll No" are."""
    words = heading_words(re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", name))
    return bool(words) and (words[-1] in config.ID_LAST_WORDS or words[0] in config.ID_FIRST_WORDS)


def heading_words(name: str) -> list[str]:
    """Words in a heading, in order: "OrderID" -> order, id; "Roll_No." -> roll, no; "IDNumber" -> id, number."""
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", name)
    spaced = re.sub(r"(?<=[A-Za-z])(?=[0-9])|(?<=[0-9])(?=[A-Za-z])", " ", spaced)
    return re.findall(r"[a-z0-9]+", spaced.lower())


def _is_consecutive(numbers: pd.Series) -> bool:
    """All values are whole numbers forming an unbroken run, such as 1..200 (rows may be in any order)."""
    if numbers.isna().any() or not len(numbers) or not (numbers % 1 == 0).all():
        return False
    return numbers.max() - numbers.min() == len(numbers) - 1 and numbers.nunique() == len(numbers)


def _unit(present: pd.Series, kinds: pd.Series) -> str | None:
    """The symbol most text values carried (FR-15 "units where known"), judged on the first 1,000."""
    text = present[kinds == str].iloc[:1000].astype(str)
    if text.empty:
        return None
    for symbol in ("%",) + config.CURRENCY_SYMBOLS:
        if text.str.contains(symbol, regex=False).mean() > 0.5:
            return symbol
    return None


def _correlations(result: DatasetProfile) -> pd.DataFrame | None:
    numeric = [c.name for c in result.columns_of(NUMERIC)]
    if len(numeric) < 2:
        return None
    try:
        return result.values[numeric].corr(method="pearson", min_periods=3)
    except Exception:
        log.exception("Correlations could not be calculated for %s", result.file_name)
        result.warnings.append(DataWarning("item_failed", "Relationships between number columns could not be calculated."))
        return None


def _failed_column(name: str, position: int, series: pd.Series) -> ColumnProfile:
    column = ColumnProfile(name=name, position=position, type=FAILED)
    try:
        column.missing_count = int(missing_mask(series).sum())
        column.missing_percent = 100.0 * column.missing_count / len(series) if len(series) else 0.0
    except Exception:
        pass
    return column


def _column_warnings(column: ColumnProfile) -> list[DataWarning]:
    """FR-23 warnings about a single column."""
    if column.type == EMPTY:
        return [DataWarning("empty_column", f"Column '{column.name}' is almost empty "
                                            f"({column.missing_percent:.0f}% missing) and was skipped.")]
    found = []
    if column.missing_percent > 100 * config.HIGH_MISSING_RATIO:
        found.append(DataWarning("high_missing", f"Column '{column.name}' has {column.missing_percent:.0f}% missing values."))
    if column.is_mixed:
        found.append(DataWarning("mixed_type", f"Column '{column.name}' has mixed numbers and text, "
                                               f"so it was treated as {column.type_label.lower()}."))
    return found


def _ignored_message(rows: int, columns: int) -> str:
    parts = []
    if rows:
        parts.append(f"{rows:,} completely empty row{'s' if rows != 1 else ''}")
    if columns:
        parts.append(f"{columns:,} empty column{'s' if columns != 1 else ''}")
    return " and ".join(parts) + " were ignored." if rows + columns > 1 else " and ".join(parts) + " was ignored."
