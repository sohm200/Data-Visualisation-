import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
from datetime import datetime

import pytest
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parents[1]


def pytest_addoption(parser):
    parser.addoption("--demo-delay", type=float, default=0.7)
    parser.addoption("--browser", choices=["chrome", "edge"], default="chrome")


@pytest.fixture(scope="session")
def evidence():
    path = ROOT / "outputs" / "selenium" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path.mkdir(parents=True)
    return path


@pytest.fixture(scope="session")
def base_url(evidence):
    port_file = evidence / "port.txt"
    env = dict(os.environ, DASHBOARD_LOG_FILE=str(evidence / "app.log"))
    with (evidence / "server.log").open("w") as log:
        process = subprocess.Popen([sys.executable, str(ROOT / "browser_tests/server.py"), str(port_file)],
                                   cwd=ROOT, env=env, stdout=log, stderr=log,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            def ready(_):
                if process.poll() is not None:
                    raise RuntimeError("Dedicated server exited; see server.log")
                if not port_file.exists():
                    return False
                url = "http://127.0.0.1:" + port_file.read_text().strip()
                try:
                    with urllib.request.urlopen(url, timeout=1) as response:
                        return url if response.status == 200 else False
                except OSError:
                    return False
            yield WebDriverWait(None, 30).until(ready)
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


@pytest.fixture
def browser(request, base_url, evidence):
    folder = evidence / request.node.name
    folder.mkdir()
    downloads = folder / "downloads"
    downloads.mkdir()
    name = request.config.getoption("--browser")
    options = webdriver.ChromeOptions() if name == "chrome" else webdriver.EdgeOptions()
    options.add_argument("--window-size=1366,1000")
    options.add_argument("--no-first-run")
    options.add_experimental_option("prefs", {"download.default_directory": str(downloads),
        "download.prompt_for_download": False, "download.directory_upgrade": True})
    driver = (webdriver.Chrome if name == "chrome" else webdriver.Edge)(options=options)
    request.node.driver = driver
    request.node.folder = folder
    driver.downloads = downloads
    driver.demo = lambda: time.sleep(request.config.getoption("--demo-delay"))
    (folder / "browser.json").write_text(json.dumps(driver.capabilities, indent=2))
    try:
        driver.get(base_url)
        WebDriverWait(driver, 30).until(lambda d: d.execute_script("return document.readyState") == "complete")
        driver.demo()
        yield driver
    finally:
        driver.quit()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    driver = getattr(item, "driver", None)
    if driver and (report.when == "call" or report.failed):
        label = "failure" if report.failed else "final"
        if report.failed:
            driver.demo()
        try:
            # Capture the entire page so summary cards and the numeric table are both evidence.
            import base64
            shot = driver.execute_cdp_cmd("Page.captureScreenshot", {"captureBeyondViewport": True,
                "clip": {"x": 0, "y": 0, "width": 1366,
                         "height": driver.execute_script("return document.documentElement.scrollHeight"), "scale": 1}})
            (item.folder / (label + ".png")).write_bytes(base64.b64decode(shot["data"]))
        except Exception:
            driver.save_screenshot(str(item.folder / (label + ".png")))
        (item.folder / "result.json").write_text(json.dumps({"outcome": report.outcome,
            "details": str(report.longrepr) if report.failed else "All assertions passed"}, indent=2))
