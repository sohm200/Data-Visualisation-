"""Data processing and summary (SRS 4.2): FR-06 to FR-10, FR-39 to FR-43, rules 4.2.3 and 4.2.4."""

import statistics

import pandas as pd
import pytest

import profiler
import validator
from profiler import CATEGORY, DATE, EMPTY, ID, NUMERIC, TEXT


def types(result):
    return {c.name: c.type for c in result.columns}


def warning_text(result):
    return " | ".join(w.message for w in result.warnings)


# FR-06, FR-09, FR-10, FR-39, NFR-14: TF-01 compared with an independent calculation
def test_tf01_summary_values(tf):
    name, content = tf("TF-01")
    result = profiler.profile(validator.read_upload(name, content))
    assert (result.row_count, result.column_count) == (20, 4)
    assert types(result) == {"Order Date": DATE, "Region": CATEGORY, "Sales": NUMERIC, "Units": NUMERIC}
    assert result.missing_cells == 0
    assert result.numeric_count == 2

    sales = [1000 + 37 * i + (i % 3) * 55 for i in range(20)]
    column = result.column("Sales")
    assert column.count == 20
    assert column.total == pytest.approx(sum(sales))
    assert round(column.mean, 2) == round(statistics.mean(sales), 2)
    assert round(column.median, 2) == round(statistics.median(sales), 2)
    assert round(column.std, 2) == round(statistics.stdev(sales), 2)      # Excel STDEV.S
    assert (column.minimum, column.maximum) == (min(sales), max(sales))

    dates = result.date_range
    assert dates.name == "Order Date"
    assert (dates.earliest, dates.latest) == (pd.Timestamp("2026-01-01"), pd.Timestamp("2026-01-20"))


# FR-08
def test_missing_value_tokens(profile_csv):
    result = profile_csv("A,B\n1,x\n,y\n   ,z\nNA,w\nn/a,v\nNULL,u\nNone,t\n-,s\n2,r\n3,q\n")
    column = result.column("A")
    assert column.missing_count == 7
    assert result.missing_cells == 7
    assert round(result.missing_percent, 2) == round(100 * 7 / 20, 2)


# FR-40
def test_numbers_stored_as_text_are_cleaned(profile_csv):
    result = profile_csv('Price\n"₹1,200"\n$950\n€ 3 100\n£40.5\n"1,05,000"\n12%\n')
    column = result.column("Price")
    assert column.type == NUMERIC
    assert column.minimum == 12
    assert column.maximum == 105000
    assert column.count == 6


def test_currency_unit_is_remembered(profile_csv):
    result = profile_csv('Fee\n"₹1,200"\n₹950\n₹300\n')
    assert result.column("Fee").unit == "₹"


# FR-41 and 4.2.3 rule 2
def test_text_dates_are_read_day_first(profile_csv):
    result = profile_csv("When\n05-01-2026\n2026-01-06\n07/01/2026\n8 Jan 2026\n09.01.2026\n")
    column = result.column("When")
    assert column.type == DATE
    assert column.earliest == pd.Timestamp("2026-01-05")       # 5 January, not 1 May
    assert column.latest == pd.Timestamp("2026-01-09")


def test_mostly_dates_with_a_few_bad_values_is_still_a_date(profile_csv):
    rows = [f"{d:02d}-03-2026" for d in range(1, 20)] + ["unknown"]
    assert profile_csv("Day\n" + "\n".join(rows)).column("Day").type == DATE


def test_years_alone_are_not_dates(profile_csv):
    result = profile_csv("Year,Value\n" + "\n".join(f"{2000 + i},{i}" for i in range(5)))
    assert result.column("Year").type == NUMERIC


# 4.2.3 rule 1
def test_almost_empty_column_is_flagged(profile_csv):
    rows = ["1,"] * 39 + ["2,x"]
    result = profile_csv("A,Mostly blank\n" + "\n".join(rows))
    assert result.column("Mostly blank").type == EMPTY
    assert "almost empty" in warning_text(result)


# 4.2.3 rule 3, FR-42, BR-06
def test_tf09_roll_no_is_an_id(tf):
    result = profiler.profile(validator.read_upload(*tf("TF-09")))
    roll = result.column("Roll No")
    assert roll.type == ID
    assert roll.mean is None and roll.total is None
    assert "Roll No" not in result.values.columns
    assert result.numeric_count == 1


@pytest.mark.parametrize("heading", ["Order ID", "EmployeeID", "emp_code", "Phone Number", "S.No"])
def test_unique_values_with_an_id_heading_are_ids(profile_csv, heading):
    rows = [f"{1000 + i * 7},{i % 3}" for i in range(25)]
    assert profile_csv(f"{heading},X\n" + "\n".join(rows)).column(heading).type == ID


def test_consecutive_whole_numbers_are_an_id_without_a_hint(profile_csv):
    rows = [f"{i},{i % 4}" for i in range(101, 131)]
    assert profile_csv("Serial,X\n" + "\n".join(rows)).column("Serial").type == ID


def test_unique_id_without_a_heading_needs_at_least_20_rows(profile_csv):
    rows = [f"{i},{i % 4}" for i in range(1, 20)]
    assert profile_csv("Serial,X\n" + "\n".join(rows)).column("Serial").type == NUMERIC


# 4.2.3 rule 3b, FR-54: the examples table in SRS v0.3
@pytest.mark.parametrize("heading, values, expected", [
    ("WORK_ITEM_ID", [101, 101, 102, 102, 103, 101], ID),
    ("STATE_SEQ", [1, 2, 1, 2, 3, 1], ID),
    ("REVISION_NO", [1, 2, 3, 1, 2, 1], ID),
    ("Customer Key", [7, 7, 9, 12, 9, 7], ID),
    ("id_customer", [7, 7, 9, 12, 9, 7], ID),
    ("Roll No", [3, 1, 2, 3, 1, 2], ID),
    ("Number of items", [3, 5, 2, 3, 5, 4], NUMERIC),
    ("No. of students", [30, 32, 30, 28, 30, 31], NUMERIC),
    ("Quantity (No.)", [3, 5, 2, 3, 5, 4], NUMERIC),
    ("Version No", [1.1, 1.2, 1.1, 2.0, 1.2, 1.1], NUMERIC),
    ("Key Revenue", [100, 200, 100, 300, 200, 100], NUMERIC),
])
def test_id_headings(profile_csv, heading, values, expected):
    rows = "\n".join(f'"{v}"' for v in values)
    assert profile_csv(f'"{heading}"\n{rows}').column(heading).type == expected


def test_repeating_text_codes_stay_categories(profile_csv):
    rows = [f"P-0{i % 3}" for i in range(30)]
    assert profile_csv("Product Code\n" + "\n".join(rows)).column("Product Code").type == CATEGORY


@pytest.mark.parametrize("heading, expected", [
    ("WORK_ITEM_ID", True), ("OrderID", True), ("Roll_No.", True), ("ID Number", True), ("STATE_SEQ", True),
    ("Paid Amount", False), ("Width", False), ("Number of items", False), ("Quantity (No.)", False),
    ("Key Revenue", False), ("Notes", False),
])
def test_has_id_heading(heading, expected):
    assert profiler.has_id_heading(heading) is expected


# TF-17, FR-54, FR-23
def test_tf17_repeating_ids(tf):
    result = profiler.profile(validator.read_upload(*tf("TF-17")))
    assert types(result) == {"WORK_ITEM_ID": ID, "STATE_SEQ": ID, "REVISION_NO": ID,
                             "WORK_ITEM_STATE": CATEGORY, "CHANGED_DATE": DATE}
    assert result.numeric_count == 0
    assert all(c.total is None and c.mean is None for c in result.columns)
    assert "Treated as IDs, so not added up or charted: WORK_ITEM_ID, STATE_SEQ, REVISION_NO." in warning_text(result)


def test_unique_ids_are_not_listed_as_repeating(tf):
    result = profiler.profile(validator.read_upload(*tf("TF-09")))
    assert "Treated as IDs" not in warning_text(result)


def test_unique_amounts_are_not_ids(profile_csv):
    rows = [f"{1000 + i * 13.5}" for i in range(30)]
    assert profile_csv("Paid Amount\n" + "\n".join(rows)).column("Paid Amount").type == NUMERIC


# 4.2.3 rules 5 and 6
def test_category_and_text(profile_csv):
    rows = [f"{['M', 'F'][i % 2]},{['Pune', 'Delhi', 'Goa'][i % 3]},Person {i}" for i in range(30)]
    result = profile_csv("Gender,City,Name\n" + "\n".join(rows))
    assert types(result) == {"Gender": CATEGORY, "City": CATEGORY, "Name": TEXT}


def test_two_values_are_always_a_category(profile_csv):
    assert profile_csv("Paid\nYes\nNo\nYes\n").column("Paid").type == CATEGORY


def test_repeating_values_are_a_category_even_above_20(profile_csv):
    rows = [f"Shop {i % 25}" for i in range(100)]
    assert profile_csv("Shop\n" + "\n".join(rows)).column("Shop").type == CATEGORY


def test_mostly_different_values_are_text(profile_csv):
    rows = [f"Shop {i % 60}" for i in range(100)]          # 60 values in 100 rows: not under 50%
    assert profile_csv("Shop\n" + "\n".join(rows)).column("Shop").type == TEXT


def test_mixed_numbers_and_text_warning(profile_csv):
    rows = ["1", "2", "3", "abc", "5", "6", "x", "8", "9", "y"]
    result = profile_csv("Score\n" + "\n".join(rows))
    column = result.column("Score")
    assert column.type in (CATEGORY, TEXT)
    assert column.is_mixed
    assert "mixed numbers and text" in warning_text(result)


# 4.2.4 meaningful total rule
@pytest.mark.parametrize("heading, values, expected", [
    ("Sales", [10, 20, 30], True),
    ("Year", [2019, 2020, 2021], False),
    ("Year of joining", [2019, 2020, 2021], False),
    ("Discount %", [5, 10, 15], False),
    ("Interest Rate", [5, 6, 7], False),
    ("Avg Score", [5, 6, 7], False),
    ("Age", [21, 34, 45], False),
    ("Wages", [100, 200, 300], True),          # "age" inside a word does not count
    ("Percentage", [50, 60, 70], False),
])
def test_meaningful_total(heading, values, expected):
    assert profiler.total_is_meaningful(heading, pd.Series(values, dtype=float)) is expected


# FR-23 and FR-43 warnings
def test_tf07_messy_file(tf):
    result = profiler.profile(validator.read_upload(*tf("TF-07")))
    assert types(result) == {"Date": DATE, "City": CATEGORY, "Amount": NUMERIC, "Score": TEXT, "Remarks": CATEGORY}
    assert result.row_count == 12
    amount = result.column("Amount")
    assert amount.missing_count == 4
    assert amount.maximum == 105000
    text = warning_text(result)
    assert "1 completely empty row was ignored" in text
    assert "'Amount' has 33% missing values" in text
    assert "'Score' has mixed numbers and text" in text


# FR-50
def test_preview_shows_the_first_10_rows_as_written(tf):
    result = profiler.profile(validator.read_upload(*tf("TF-07")))
    assert len(result.preview_rows) == 10
    assert result.preview_rows[0] == ["05-01-2026", "Pune", "₹1,200", "12", ""]
    assert result.preview_rows[2][2] == "N/A"


# FR-53, NFR-15
def test_a_failing_column_does_not_stop_the_others(profile_csv, monkeypatch):
    real = profiler.profile_column

    def flaky(name, position, series):
        if name == "B":
            raise ValueError("boom")
        return real(name, position, series)

    monkeypatch.setattr(profiler, "profile_column", flaky)
    result = profile_csv("A,B,C\n1,x,p\n2,y,q\n3,z,r\n")
    assert types(result) == {"A": NUMERIC, "B": "failed", "C": TEXT}
    assert "'B' could not be analysed" in warning_text(result)


def test_correlations_between_numeric_columns(profile_csv):
    rows = [f"{i * 3},{6 * i + 1},{(i * 7) % 5}" for i in range(20)]
    result = profile_csv("X,Y,Z\n" + "\n".join(rows))
    assert result.correlations.loc["X", "Y"] == pytest.approx(1.0)
