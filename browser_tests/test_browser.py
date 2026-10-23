"""SRS v0.3: FR-19, FR-49, E-01/E-03, FR-34/US-05, FR-24."""
from pathlib import Path

from PIL import Image
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "outputs/assignment7/inputs"
NO_DATA = "This file has no data. Make sure the first row has column headings and there is at least one row of data below it."
UNSUPPORTED = "This file type isn't supported. Please upload an .xlsx, .xls or .csv file."


def wait(driver):
    return WebDriverWait(driver, 30)


def upload(driver, path):
    wait(driver).until(EC.presence_of_element_located((By.ID, "file"))).send_keys(str(path.resolve()))
    driver.demo()
    wait(driver).until(EC.element_to_be_clickable((By.ID, "process"))).click()
    driver.demo()
    wait(driver).until(EC.invisibility_of_element_located((By.ID, "loading")))


def dashboard(driver):
    wait(driver).until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".dashboard")))
    wait(driver).until(lambda d: d.execute_script("return [...document.querySelectorAll('.chart')].length > 0 && [...document.querySelectorAll('.chart')].every(e => e._fullLayout && e.querySelector('.main-svg') && e.querySelector('.modebar'))"))


def values(driver, rows, total, average, minimum, maximum):
    dashboard(driver)
    cards = {e.find_element(By.CSS_SELECTOR, ".card-label").text:
             e.find_element(By.CSS_SELECTOR, ".card-value").text
             for e in driver.find_elements(By.CSS_SELECTOR, ".cards .card")}
    assert cards["Rows"] == str(rows)
    assert cards["Columns"] == "2"
    assert cards["Missing cells"] == "0"
    assert driver.find_element(By.CSS_SELECTOR, ".card-sub").text == "0.0% of all cells"
    table = driver.find_element(By.CSS_SELECTOR, ".data-table:not(.preview)")
    headers = [e.text for e in table.find_elements(By.CSS_SELECTOR, "thead th")]
    sales = next(e for e in table.find_elements(By.CSS_SELECTOR, "tbody tr")
                 if e.find_element(By.TAG_NAME, "th").text == "Sales")
    actual = dict(zip(headers, [e.text for e in sales.find_elements(By.CSS_SELECTOR, "th, td")]))
    for key, expected in {"Total": total, "Average": average, "Smallest": minimum, "Largest": maximum}.items():
        assert actual[key] == str(expected), actual


def test_01_sales(browser):
    upload(browser, INPUTS / "sales.csv")
    values(browser, 6, 210, 35, 10, 60)
    browser.demo()


def error_case(browser, file, expected):
    upload(browser, INPUTS / file)
    error = wait(browser).until(EC.visibility_of_element_located((By.ID, "error")))
    assert error.text == expected
    assert not browser.find_elements(By.CSS_SELECTOR, ".dashboard")
    assert browser.find_element(By.ID, "upload-form").is_displayed()
    browser.demo()


def test_02_empty(browser):
    error_case(browser, "empty.csv", NO_DATA)


def test_03_headings(browser):
    error_case(browser, "headings.csv", NO_DATA)


def test_04_unsupported(browser):
    error_case(browser, "unsupported.txt", UNSUPPORTED)


def test_05_sheets(browser):
    upload(browser, ROOT / "browser_tests/fixtures/two_sheets.xlsx")
    selector = Select(browser.find_element(By.ID, "sheet-select"))
    assert [e.text for e in selector.options] == ["First", "Second"]
    assert selector.first_selected_option.text == "First"
    values(browser, 4, 40, 10, 4, 16)
    browser.demo()
    old = browser.find_element(By.CSS_SELECTOR, ".dashboard")
    selector.select_by_visible_text("Second")
    browser.demo()
    wait(browser).until(EC.staleness_of(old))
    wait(browser).until(EC.invisibility_of_element_located((By.ID, "loading")))
    assert Select(browser.find_element(By.ID, "sheet-select")).first_selected_option.text == "Second"
    values(browser, 6, 150, 25, 5, 45)
    browser.demo()


def test_06_png(browser):
    upload(browser, INPUTS / "sales.csv")
    values(browser, 6, 210, 35, 10, 60)
    before = set(browser.downloads.iterdir())
    button = wait(browser).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.modebar-btn[data-title="Download plot as a PNG"]')))
    button.click()
    browser.demo()
    def downloaded(_):
        files = set(browser.downloads.iterdir()) - before
        if any(p.suffix in (".crdownload", ".tmp") for p in files):
            return False
        pngs = [p for p in files if p.suffix.lower() == ".png" and p.stat().st_size > 0]
        if len(pngs) != 1:
            return False
        try:
            with Image.open(pngs[0]) as image:
                assert image.format == "PNG"
                image.verify()
            with Image.open(pngs[0]) as image:
                image.load()
                assert image.width > 0 and image.height > 0
            return pngs[0]
        except (OSError, SyntaxError):
            return False
    result = wait(browser).until(downloaded)
    assert result.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    browser.demo()
