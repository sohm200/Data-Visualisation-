"""Integration tests: upload each test file to the Flask app and check the response (SRS 6.4)."""

import io
import re
import time

import pytest

import app as app_module
import config
import profiler
from conftest import TEST_LOG_FILE


@pytest.fixture(scope="module")
def client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def upload(client, name, content, sheet=None):
    data = {"file": (io.BytesIO(content), name)}
    if sheet:
        data["sheet"] = sheet
    return client.post("/process", data=data, content_type="multipart/form-data")


def text(response):
    return response.get_data(as_text=True)


def chart_count(response):
    return len(re.findall(r'class="chart" id="chart-\d+"', text(response)))


def test_upload_page(client):
    page = text(client.get("/"))
    assert "Process Data" in page
    assert 'accept=".xlsx,.xls,.csv"' in page
    assert "Maximum 25 MB. The first row must contain column headings." in page


def test_plotly_is_served_locally(client):
    response = client.get("/vendor/plotly.min.js")
    assert response.status_code == 200
    assert "javascript" in response.content_type
    response.close()


# US-01, US-03, US-04, FR-18 to FR-20, FR-49 to FR-51
def test_tf01_dashboard(client, tf):
    response = upload(client, *tf("TF-01"))
    page = text(response)
    assert response.status_code == 200
    assert "TF-01_small_clean.csv" in page
    assert re.search(r'Rows</span>\s*<span class="card-value">20<', page)
    assert re.search(r'Columns</span>\s*<span class="card-value">4<', page)
    assert re.search(r'Number columns</span>\s*<span class="card-value">2<', page)
    assert "01 Jan 2026 &ndash; 20 Jan 2026" in page
    assert 2 <= chart_count(response) <= 10
    assert "Things to check" not in page                     # hidden when there are no warnings
    assert 'href="/">Analyse another file' in page
    assert "Data preview" in page and "01-01-2026" in page


# US-01, US-02, FR-30
@pytest.mark.parametrize("test_file, code, status", [
    ("TF-02", "E-03", 400), ("TF-03", "E-03", 400), ("TF-13", "E-05", 400), ("TF-11", "E-02", 413),
])
def test_bad_files_show_the_catalogue_message(client, tf, test_file, code, status):
    response = upload(client, *tf(test_file))
    page = text(response)
    assert response.status_code == status
    assert config.MESSAGES[code].replace("'", "&#39;") in page
    assert 'id="upload-form"' in page                       # FR-33: can try another file
    assert "Traceback" not in page


def test_tf04_pdf_renamed_to_csv(client, tf):
    page = text(upload(client, *tf("TF-04")))
    assert "isn&#39;t supported" in page or "couldn&#39;t read" in page


def test_unsupported_type(client):
    page = text(upload(client, "report.pdf", b"%PDF-1.4"))
    assert config.MESSAGES["E-01"].replace("'", "&#39;") in page


# E-07
def test_process_without_a_file(client):
    response = client.post("/process", data={}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert config.MESSAGES["E-07"] in text(response)


# FR-34, US-05, TF-06
def test_tf06_sheet_selector_and_switching(client, tf):
    page = text(upload(client, *tf("TF-06")))
    assert re.findall(r'<option value="([^"]+)"', page) == ["Cover", "Marks", "Staff"]
    assert '<option value="Marks" selected>' in page
    page = text(upload(client, *tf("TF-06"), sheet="Staff"))
    assert '<option value="Staff" selected>' in page
    assert "Salary" in page


# US-07, FR-23, NFR-15
def test_tf07_messy_file_shows_warnings(client, tf):
    response = upload(client, *tf("TF-07"))
    page = text(response)
    assert response.status_code == 200
    assert "Things to check" in page
    assert "&#39;Amount&#39; has 33% missing values" in page


@pytest.mark.parametrize("test_file", ["TF-05", "TF-08", "TF-09", "TF-12", "TF-14", "TF-18"])
def test_other_files_produce_a_dashboard(client, tf, test_file):
    response = upload(client, *tf(test_file))
    assert response.status_code == 200
    assert 'class="page dashboard"' in text(response)


# FR-54, FR-55, TF-17
def test_tf17_change_history(client, tf):
    response = upload(client, *tf("TF-17"))
    page = text(response)
    assert response.status_code == 200
    assert "Treated as IDs, so not added up or charted: WORK_ITEM_ID, STATE_SEQ, REVISION_NO." in page
    assert re.search(r'Number columns</span>\s*<span class="card-value">0<', page)
    assert "Shows how many rows there are for each month of CHANGED_DATE." in page


# NFR-10, TF-15
def test_tf15_script_is_shown_as_text(client, tf):
    page = text(upload(client, *tf("TF-15")))
    body = page.split("<body", 1)[1]
    assert "<script>alert(1)</script>" not in body
    assert "<img src=x" not in body
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body
    assert "&lt;b&gt;Group&lt;/b&gt;" in body


# E-08, TF-16
def test_tf16_text_only(client, tf):
    response = upload(client, *tf("TF-16"))
    page = text(response)
    assert response.status_code == 200
    assert chart_count(response) == 0
    assert config.MESSAGES["E-08"] in page
    assert 'class="data-table"' in page


# NFR-01, TF-10
def test_tf10_is_processed_within_30_seconds(client, tf):
    name, content = tf("TF-10")
    started = time.perf_counter()
    response = upload(client, name, content)
    elapsed = time.perf_counter() - started
    assert response.status_code == 200
    assert chart_count(response) == config.MAX_CHARTS
    assert elapsed < 30, f"took {elapsed:.1f} s"


# FR-32, US-08, E-09
def test_unexpected_error_is_logged_not_shown(client, tf, monkeypatch):
    def broken(table):
        raise RuntimeError("internal detail 12345")

    monkeypatch.setattr(profiler, "profile", broken)
    response = upload(client, *tf("TF-01"))
    page = text(response)
    assert response.status_code == 500
    assert config.MESSAGES["E-09"] in page
    assert "internal detail" not in page and "RuntimeError" not in page

    log = TEST_LOG_FILE.read_text(encoding="utf-8")
    assert "Unexpected error while processing TF-01_small_clean.csv" in log
    assert "RuntimeError: internal detail 12345" in log
    assert re.search(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", log, re.M)


# NFR-08
@pytest.mark.parametrize("raw, cleaned", [
    ("../../secret/report.csv", "secret_report.csv"),
    ("my data (final).csv", "my_data_final.csv"),
    ("बिक्री.csv", "uploaded_file.csv"),
])
def test_file_names_are_cleaned(raw, cleaned):
    assert app_module.clean_file_name(raw) == cleaned


# NFR-07
def test_uploads_are_kept_in_memory():
    stream = app_module.InMemoryRequest._get_file_stream(None, 10 ** 8, "text/csv", "x.csv")
    assert isinstance(stream, io.BytesIO)
