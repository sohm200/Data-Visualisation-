"""Flask routes: upload page, process, dashboard (SRS 6.6).

Run with:  python app.py   (serves on http://127.0.0.1:5000 only, NFR-11)
"""

from __future__ import annotations

import io
import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

import plotly
from flask import Flask, Request, render_template, request, send_from_directory
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

import chart_rules
import config
import profiler
import renderer
import validator

log = logging.getLogger("dashboard")
PLOTLY_JS_DIR = Path(plotly.__file__).parent / "package_data"   # plotly.js bundled with the Python package


class InMemoryRequest(Request):
    """Keep uploaded files in memory instead of Werkzeug's spooled temporary files (NFR-07)."""

    def _get_file_stream(self, total_content_length, content_type, filename=None, content_length=None):
        return io.BytesIO()


def create_app(log_file: Path = config.LOG_FILE) -> Flask:
    app = Flask(__name__)
    app.request_class = InMemoryRequest
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_REQUEST_BYTES       # NFR-09: enforced by the server
    app.jinja_env.filters["number"] = renderer.format_number
    app.jinja_env.filters["date"] = renderer.format_date
    _setup_logging(log_file)

    @app.context_processor
    def page_settings():
        return {"messages": config.MESSAGES, "config_max_bytes": config.MAX_FILE_BYTES}

    @app.get("/")
    def upload_page():
        return render_template("upload.html")

    @app.post("/process")
    def process():
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            return _upload_error("E-07", 400)
        file_name = clean_file_name(upload.filename)
        content = upload.read()
        sheet = request.form.get("sheet") or None
        started = time.perf_counter()

        try:
            table = validator.read_upload(file_name, content, sheet)
            data_profile = profiler.profile(table)
            selection = chart_rules.select_charts(data_profile)
            charts, chart_warnings = renderer.render_charts(selection.specs, data_profile)
        except validator.FileError as error:
            if error.cause is not None:
                log.warning("Rejected %s with %s: %s: %s", file_name, error.code,
                            type(error.cause).__name__, error.cause, exc_info=error.cause)
            else:
                log.info("Rejected %s with %s", file_name, error.code)
            return _upload_error(error.code, 413 if error.code == "E-02" else 400)
        except Exception:
            log.exception("Unexpected error while processing %s (sheet %r)", file_name, sheet)    # FR-32
            return _upload_error("E-09", 500)

        log.info("Processed %s, sheet %r: %d rows x %d columns, %d charts in %.2f s", file_name,
                 data_profile.sheet_name, data_profile.row_count, data_profile.column_count, len(charts),
                 time.perf_counter() - started)
        chart_types = list(dict.fromkeys(chart.type for chart in charts))
        return render_template(
            "dashboard.html",
            profile=data_profile,
            date_column=data_profile.date_range,
            warnings=data_profile.warnings + selection.warnings + chart_warnings,
            charts=charts,
            chart_help=[renderer.CHART_HELP[kind] for kind in chart_types],
        )

    @app.get("/vendor/plotly.min.js")
    def plotly_js():
        # Served locally so the dashboard works offline (SRS 2.5).
        return send_from_directory(PLOTLY_JS_DIR, "plotly.min.js", max_age=7 * 24 * 3600)

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_error):
        return _upload_error("E-02", 413)

    return app


def clean_file_name(name: str) -> str:
    """NFR-08: a safe file name for display and logs that keeps the supported extension."""
    extension = Path(name).suffix.lower()
    cleaned = secure_filename(name)
    if extension and not cleaned.lower().endswith(extension):
        cleaned = "uploaded_file" + extension       # e.g. a name written only in non-Latin letters
    return cleaned or "uploaded_file"


def _upload_error(code: str, status: int):
    return render_template("upload.html", error=config.MESSAGES[code]), status


def _setup_logging(log_file: Path) -> None:
    log.setLevel(logging.INFO)
    if any(getattr(h, "baseFilename", None) == str(Path(log_file).resolve()) for h in log.handlers):
        return
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)


app = create_app()

if __name__ == "__main__":
    try:
        from waitress import serve
    except ImportError:
        print(f"Waitress is not installed; using Flask's development server on http://{config.HOST}:{config.PORT}")
        app.run(host=config.HOST, port=config.PORT)
    else:
        print(f"Open http://{config.HOST}:{config.PORT} in your browser. Press Ctrl+C to stop.")
        # Bodies up to twice the limit reach Flask, which answers with the friendly E-02 page. Waitress
        # buffers them in memory rather than in a temporary file (NFR-07).
        limit = config.MAX_REQUEST_BYTES * 2
        serve(app, host=config.HOST, port=config.PORT, max_request_body_size=limit, inbuf_overflow=limit)
