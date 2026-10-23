"""File upload and validation (SRS 4.1): FR-01 to FR-05, FR-11, FR-34 to FR-38."""

import hashlib

import pytest

import config
from validator import FileError, read_upload


def error_code(name, content, sheet=None):
    with pytest.raises(FileError) as caught:
        read_upload(name, content, sheet)
    return caught.value.code


# FR-01, FR-02, BR-01
@pytest.mark.parametrize("name", ["report.pdf", "data.txt", "data.json", "noextension", "sheet.xlsm"])
def test_unsupported_extension_is_rejected(name):
    assert error_code(name, b"a,b\n1,2\n") == "E-01"


def test_extension_is_case_insensitive():
    assert read_upload("DATA.CSV", b"a,b\n1,2\n").data.shape == (1, 2)


def test_tf04_pdf_renamed_to_csv_is_rejected(tf):
    assert error_code(*tf("TF-04")) in ("E-01", "E-04")


@pytest.mark.parametrize("name", ["fake.xlsx", "fake.xls"])
def test_text_renamed_to_excel_is_rejected(name):
    assert error_code(name, b"a,b\n1,2\n") == "E-01"


def test_xlsx_renamed_to_csv_is_rejected(tf):
    _, content = tf("TF-06")
    assert error_code("book.csv", content) == "E-01"


def test_damaged_xlsx_is_reported_as_unreadable(tf):
    _, content = tf("TF-06")
    assert error_code("broken.xlsx", content[: len(content) // 2]) == "E-04"


# FR-03
def test_tf02_empty_file(tf):
    assert error_code(*tf("TF-02")) == "E-03"


def test_tf03_headings_only(tf):
    assert error_code(*tf("TF-03")) == "E-03"


def test_blank_lines_only_is_no_data():
    assert error_code("blank.csv", b"\n\n,,,\n") == "E-03"


def test_headings_followed_by_empty_rows_is_no_data():
    assert error_code("x.csv", b"a,b\n,\nN/A,-\n") == "E-03"


# FR-05, NFR-09
def test_tf11_file_over_25_mb_is_rejected(tf):
    name, content = tf("TF-11")
    assert len(content) > config.MAX_FILE_BYTES
    assert error_code(name, content) == "E-02"


# FR-36
def test_more_than_a_million_rows_is_rejected():
    content = b"n\n" + b"1\n" * (config.MAX_DATA_ROWS + 1)
    assert error_code("big.csv", content) == "E-06"


def test_exactly_a_million_rows_is_accepted():
    content = b"n\n" + b"1\n" * config.MAX_DATA_ROWS
    assert len(read_upload("big.csv", content).data) == config.MAX_DATA_ROWS


# FR-37
def test_tf13_password_protected_xlsx(tf):
    assert error_code(*tf("TF-13")) == "E-05"


# FR-35
def test_tf05_semicolon_windows_1252(tf):
    table = read_upload(*tf("TF-05"))
    assert table.separator == ";"
    assert table.encoding == "Windows-1252"
    assert list(table.data.columns) == ["Product", "Price", "Café sales"]
    assert table.data.iloc[0, 1] == "€1,200"


@pytest.mark.parametrize("separator", [",", ";", "\t", "|"])
def test_separators_are_detected(separator):
    text = separator.join(["Name", "City", "Marks"]) + "\n"
    text += "\n".join(separator.join([f"P{i}", "Pune", str(i)]) for i in range(5))
    table = read_upload("x.csv", text.encode())
    assert table.separator == separator
    assert table.data.shape == (5, 3)


def test_quoted_values_containing_the_separator():
    table = read_upload("x.csv", b'Name,Amount\n"Shah, R","1,200"\n"Rao, K","950"\n')
    assert table.data.iloc[0].tolist() == ["Shah, R", "1,200"]


def test_utf8_with_bom():
    table = read_upload("x.csv", "﻿Naam,Rakam\nअ,₹10\n".encode("utf-8"))
    assert table.encoding == "UTF-8 with BOM"
    assert list(table.data.columns) == ["Naam", "Rakam"]
    assert table.data.iloc[0].tolist() == ["अ", "₹10"]


def test_rows_with_extra_fields_are_kept():
    table = read_upload("x.csv", b"a,b\n1,2\n3,4,5\n")
    assert list(table.data.columns) == ["a", "b", "Column 3"]
    assert table.data.iloc[1].tolist() == ["3", "4", "5"]


# FR-34
def test_tf06_first_non_empty_sheet_is_the_default(tf):
    table = read_upload(*tf("TF-06"))
    assert table.sheet_name == "Marks"
    assert table.sheet_names == ["Cover", "Marks", "Staff"]


def test_tf06_another_sheet_can_be_chosen(tf):
    table = read_upload(*tf("TF-06"), sheet="Staff")
    assert table.sheet_name == "Staff"
    assert list(table.data.columns) == ["Name", "Department", "Salary"]


def test_choosing_an_empty_sheet_reports_no_data(tf):
    assert error_code(*tf("TF-06"), sheet="Cover") == "E-03"


def test_unknown_sheet_falls_back_to_the_default(tf):
    assert read_upload(*tf("TF-06"), sheet="Nope").sheet_name == "Marks"


# FR-01: legacy .xls (TF-12)
def test_tf12_legacy_xls(tf):
    table = read_upload(*tf("TF-12"))
    assert table.file_kind == "xls"
    assert table.sheet_name == "Results"
    assert table.data.shape == (15, 3)


# FR-38
def test_tf14_headings_are_trimmed_named_and_deduplicated(tf):
    table = read_upload(*tf("TF-14"))
    assert list(table.data.columns) == ["Name", "Marks", "Column 3", "Marks_2", "Marks_3", "Column 6"]


def test_headings_can_start_below_empty_rows():
    table = read_upload("x.csv", b",,\n,,\nA,B,C\n1,2,3\n")
    assert list(table.data.columns) == ["A", "B", "C"]
    assert len(table.data) == 1


# FR-56
def test_tf18_title_row_is_skipped(tf):
    table = read_upload(*tf("TF-18"))
    assert list(table.data.columns) == ["Month", "Region", "Sales"]
    assert len(table.data) == 12


def test_title_row_in_a_csv_is_skipped():
    table = read_upload("x.csv", b"Marks list,,\nName,Class,Marks\nAsha,A,10\n")
    assert list(table.data.columns) == ["Name", "Class", "Marks"]


def test_single_column_file_keeps_its_heading():
    table = read_upload("x.csv", b"Name\nAsha\nRavi\n")
    assert list(table.data.columns) == ["Name"]
    assert len(table.data) == 2


# FR-43 (counted while reading)
def test_completely_empty_rows_and_columns_are_counted():
    table = read_upload("x.csv", b"A,,B\n1,,2\n,,\n3,,4\n")
    assert list(table.data.columns) == ["A", "B"]
    assert (table.ignored_rows, table.ignored_columns) == (1, 1)


# FR-11, NFR-05
@pytest.mark.parametrize("test_file", ["TF-01", "TF-05", "TF-06", "TF-07", "TF-12"])
def test_original_content_is_unchanged(tf, test_file):
    name, content = tf(test_file)
    before = hashlib.sha256(content).hexdigest()
    read_upload(name, content)
    assert hashlib.sha256(content).hexdigest() == before
