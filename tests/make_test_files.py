"""Builds the test file set TF-01 to TF-18 (SRS 6.4).

Used by the pytest suite, and runnable on its own to write the files for manual checks:

    python tests/make_test_files.py            # writes into tests/files/
"""

from __future__ import annotations

import datetime as dt
import io
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

REGIONS = ["North", "South", "East", "West"]


def tf01() -> tuple[str, bytes]:
    """Small clean CSV: 20 rows with a date, a category and two numeric columns."""
    lines = ["Order Date,Region,Sales,Units"]
    for i in range(20):
        day = dt.date(2026, 1, 1) + dt.timedelta(days=i)
        lines.append(f"{day:%d-%m-%Y},{REGIONS[i % 4]},{1000 + 37 * i + (i % 3) * 55},{5 + (i * 7) % 23}")
    return "TF-01_small_clean.csv", ("\n".join(lines) + "\n").encode("utf-8")


def tf02() -> tuple[str, bytes]:
    return "TF-02_empty.csv", b""


def tf03() -> tuple[str, bytes]:
    return "TF-03_headings_only.csv", b"Name,Marks,City\n"


def tf04() -> tuple[str, bytes]:
    pdf = b"%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n"
    return "TF-04_pdf_renamed.csv", pdf


def tf05() -> tuple[str, bytes]:
    """Semicolon-separated, Windows-1252, € and £ values with thousand separators.

    ₹ cannot be stored in Windows-1252 (SRS v0.3), so ₹ handling is covered by TF-07 (UTF-8).
    """
    lines = ["Product;Price;Café sales"]
    for i in range(12):
        lines.append(f"Item {i};€{1200 + i * 150:,};£{3000 + i * 410:,}")
    return "TF-05_semicolon_cp1252.csv", ("\r\n".join(lines) + "\r\n").encode("cp1252")


def tf06() -> tuple[str, bytes]:
    """Excel file with 3 sheets, the first one empty."""
    from openpyxl import Workbook
    book = Workbook()
    book.active.title = "Cover"
    marks = book.create_sheet("Marks")
    marks.append(["Student", "Subject", "Marks"])
    for i in range(12):
        marks.append([f"Student {i}", ["Maths", "Physics", "Chemistry"][i % 3], 40 + i * 4])
    staff = book.create_sheet("Staff")
    staff.append(["Name", "Department", "Salary"])
    for i in range(8):
        staff.append([f"Staff {i}", ["Admin", "Teaching"][i % 2], 30000 + i * 2500])
    return "TF-06_three_sheets.xlsx", _save(book)


def tf07() -> tuple[str, bytes]:
    """Messy file: mixed date formats, blanks, N/A, numbers stored as text, an empty row."""
    dates = ["05-01-2026", "2026-01-06", "07/01/2026", "8 Jan 2026", "09-01-2026", "10/01/2026",
             "2026-01-11", "12 Jan 2026", "13-01-2026", "14/01/2026", "15-01-2026", "16-01-2026"]
    amounts = ['"₹1,200"', "₹950", "N/A", '"₹2,450"', " 3100 ", "", "₹780", "n/a", '"₹1,05,000"', "₹640", "₹1500", "-"]
    scores = ["12", "15", "abc", "18", "x", "21", "25", "n.a.", "30", "33", "fail", "40"]
    remarks = ["", "late", "", "", "", "N/A", "", "", "ok", "", "", ""]
    cities = ["Pune", "Mumbai", "Pune", "Delhi", "Mumbai", "Pune", "Delhi", "Pune", "Mumbai", "Delhi", "Pune", "Mumbai"]
    lines = ["Date,City,Amount,Score,Remarks"]
    for i in range(12):
        lines.append(f"{dates[i]},{cities[i]},{amounts[i]},{scores[i]},{remarks[i]}")
        if i == 5:
            lines.append(",,,,")
    return "TF-07_messy.csv", ("\n".join(lines) + "\n").encode("utf-8")


def tf08() -> tuple[str, bytes]:
    """A column with 50 different values (plus a numeric column)."""
    lines = ["Store,Revenue"]
    for i in range(200):
        lines.append(f"Store {i % 50:02d},{1000 + (i * 7919) % 5000}")
    return "TF-08_fifty_categories.csv", ("\n".join(lines) + "\n").encode("utf-8")


def tf09() -> tuple[str, bytes]:
    """Roll No 1 to 200 (shuffled), plus marks and a category."""
    rng = np.random.default_rng(9)
    rolls = rng.permutation(np.arange(1, 201))
    lines = ["Roll No,Division,Marks"]
    for i, roll in enumerate(rolls):
        lines.append(f"{roll},{'ABCD'[i % 4]},{int(rng.integers(20, 100))}")
    return "TF-09_roll_no.csv", ("\n".join(lines) + "\n").encode("utf-8")


@lru_cache(maxsize=1)
def tf10() -> tuple[str, bytes]:
    """Large file: 50,000 rows x 30 columns (about 5 MB)."""
    import pandas as pd
    rows = 50_000
    rng = np.random.default_rng(10)
    base = rng.normal(500, 120, rows)
    frame = pd.DataFrame({"Order Date": pd.Timestamp("2024-01-01") + pd.to_timedelta(rng.integers(0, 730, rows), unit="D")})
    frame["Order Date"] = frame["Order Date"].dt.strftime("%d-%m-%Y")
    for k, values in enumerate([REGIONS, ["Online", "Store"], ["A", "B", "C", "D", "E", "F", "G", "H"],
                                [f"Category {c}" for c in range(12)]]):
        frame[f"Group {k + 1}"] = rng.choice(values, rows)
    for k in range(22):
        noise = rng.normal(0, 60 + 15 * k, rows)
        frame[f"Measure {k + 1}"] = np.round(base * (1 + k / 10) + noise if k < 6 else rng.gamma(2 + k, 30, rows), 2)
    frame["Customer"] = [f"Customer {i}" for i in range(rows)]
    frame["Comment"] = rng.choice(["fine", "late delivery", "great", "damaged box", "ok"], rows) + " #" + \
        pd.Series(range(rows)).astype(str)
    frame["Invoice No"] = rng.permutation(np.arange(100000, 100000 + rows))
    assert frame.shape == (rows, 30)
    return "TF-10_large_50000x30.csv", frame.to_csv(index=False).encode("utf-8")


def tf11() -> tuple[str, bytes]:
    """A file slightly over 25 MB."""
    header = b"Name,Value\n"
    row = b"Some person name,12345\n"
    count = (25 * 1024 * 1024) // len(row) + 1000
    return "TF-11_over_25mb.csv", header + row * count


def tf12() -> tuple[str, bytes]:
    """Legacy .xls file."""
    import xlwt
    book = xlwt.Workbook()
    sheet = book.add_sheet("Results")
    date_style = xlwt.easyxf(num_format_str="DD-MM-YYYY")
    for col, heading in enumerate(["Exam Date", "Branch", "Score"]):
        sheet.write(0, col, heading)
    for i in range(15):
        sheet.write(i + 1, 0, dt.datetime(2026, 3, 1) + dt.timedelta(days=i), date_style)
        sheet.write(i + 1, 1, ["Computer", "IT", "Mechanical"][i % 3])
        sheet.write(i + 1, 2, 55 + (i * 13) % 40)
    buffer = io.BytesIO()
    book.save(buffer)
    return "TF-12_legacy.xls", buffer.getvalue()


def tf13() -> tuple[str, bytes]:
    """Password-protected .xlsx (password: secret)."""
    from msoffcrypto.format.ooxml import OOXMLFile
    from openpyxl import Workbook
    book = Workbook()
    book.active.append(["Name", "Value"])
    book.active.append(["A", 1])
    encrypted = io.BytesIO()
    OOXMLFile(io.BytesIO(_save(book))).encrypt("secret", encrypted)
    return "TF-13_password.xlsx", encrypted.getvalue()


def tf14() -> tuple[str, bytes]:
    """Blank and duplicate headings, with spaces around some headings."""
    lines = [" Name ,Marks,,Marks, Marks ,", "Asha,10,x,11,12,y", "Ravi,20,y,21,22,z"]
    return "TF-14_headings.csv", ("\n".join(lines) + "\n").encode("utf-8")


def tf15() -> tuple[str, bytes]:
    """Script code in a heading and in cells."""
    lines = ["Name,<b>Group</b>,Score",
             '<script>alert(1)</script>,<img src=x onerror=alert(2)>,10',
             "Normal,A,20",
             "Other,<img src=x onerror=alert(2)>,30"]
    return "TF-15_script.csv", ("\n".join(lines) + "\n").encode("utf-8")


def tf16() -> tuple[str, bytes]:
    """Only text columns (names and comments)."""
    lines = ["Name,Comment"] + [f"Person {i},Comment number {i} about something" for i in range(30)]
    return "TF-16_text_only.csv", ("\n".join(lines) + "\n").encode("utf-8")


def tf17() -> tuple[str, bytes]:
    """Change history: one row per change, so WORK_ITEM_ID, STATE_SEQ and REVISION_NO repeat (FR-54, FR-55)."""
    rng = np.random.default_rng(17)
    states = ["New", "Active", "Resolved", "Closed"]
    lines = ["WORK_ITEM_ID,STATE_SEQ,REVISION_NO,WORK_ITEM_STATE,CHANGED_DATE"]
    start = dt.date(2025, 1, 1)
    for item in rng.choice(np.arange(10_000, 99_999), 300, replace=False):
        created = start + dt.timedelta(days=int(rng.integers(0, 450)))
        for revision in range(1, int(rng.integers(2, 9))):
            changed = created + dt.timedelta(days=int(rng.integers(0, 30)) * revision)
            lines.append(f"{item},{min(revision, 4)},{revision},{states[min(revision, 4) - 1]},{changed:%Y-%m-%d}")
    return "TF-17_change_history.csv", ("\n".join(lines) + "\n").encode("utf-8")


def tf18() -> tuple[str, bytes]:
    """Excel sheet with a title in A1, a blank row, then the headings (FR-56)."""
    from openpyxl import Workbook
    book = Workbook()
    sheet = book.active
    sheet.title = "Report"
    sheet["A1"] = "Quarterly Sales Report 2026"
    sheet.append([])
    sheet.append(["Month", "Region", "Sales"])
    for i in range(12):
        sheet.append([dt.datetime(2026, i % 12 + 1, 1), REGIONS[i % 4], 5000 + i * 375])
    return "TF-18_title_row.xlsx", _save(book)


def _save(book) -> bytes:
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


BUILDERS = {
    "TF-01": tf01, "TF-02": tf02, "TF-03": tf03, "TF-04": tf04, "TF-05": tf05, "TF-06": tf06,
    "TF-07": tf07, "TF-08": tf08, "TF-09": tf09, "TF-10": tf10, "TF-11": tf11, "TF-12": tf12,
    "TF-13": tf13, "TF-14": tf14, "TF-15": tf15, "TF-16": tf16, "TF-17": tf17, "TF-18": tf18,
}


def build(test_file_id: str) -> tuple[str, bytes]:
    return BUILDERS[test_file_id]()


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "files"
    target.mkdir(parents=True, exist_ok=True)
    for test_file_id in BUILDERS:
        name, content = build(test_file_id)
        (target / name).write_bytes(content)
        print(f"{test_file_id}: {name} ({len(content):,} bytes)")
