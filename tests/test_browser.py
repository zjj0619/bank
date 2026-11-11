"""本机无头 Chrome。只访问临时服务器，不访问外部网站。"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest
from werkzeug.serving import make_server

from app.paths import ROOT
from tests.helpers import FIXTURE_PASSWORD, OPENING, make_app, opened

pytestmark = [pytest.mark.integration, pytest.mark.selenium]

SHOTS = ROOT / "docs" / "screenshots"
ARTIFACTS = Path("/opt/cursor/artifacts")


class LiveServer:
    def __init__(self, app) -> None:
        self.app = app
        self._server = make_server("127.0.0.1", 0, app, threaded=True)
        self.base = f"http://127.0.0.1:{self._server.server_port}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def start(self) -> "LiveServer":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()


@pytest.fixture
def live(tmp_path, monkeypatch):
    for name in (
        "BANK_SEED_PASSWORD",
        "BANK_SEED_PASSWORD_DEMO_ZHANG",
        "BANK_SEED_PASSWORD_DEMO_LI",
        "BANK_SEED_PASSWORD_DEMO_WANG",
        "BANK_DATABASE",
    ):
        monkeypatch.delenv(name, raising=False)
    server = LiveServer(make_app(tmp_path)).start()
    yield server
    server.stop()


def _skip_reason(prefix: str, exc: BaseException) -> str:
    detail = f"{type(exc).__name__}: {exc}".splitlines()[0][:500]
    return (
        f"{prefix} No browser path is hard-coded. CHROME_BIN or BANK_CHROME_BIN selects the executable when set; "
        "otherwise Selenium Manager looks for Chrome or Chromium on PATH. "
        "CHROMEDRIVER or BANK_CHROMEDRIVER can override the driver. "
        f"Skip reason: {detail}"
    )


@pytest.fixture
def driver():
    import os

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
    except Exception as exc:  # pragma: no cover
        pytest.skip(_skip_reason("Selenium could not be imported.", exc))
    options = Options()
    binary = os.environ.get("CHROME_BIN") or os.environ.get("BANK_CHROME_BIN")
    if binary:
        options.binary_location = binary
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--lang=zh-CN")
    options.add_argument("--window-size=1440,1000")
    driver_path = os.environ.get("CHROMEDRIVER") or os.environ.get("BANK_CHROMEDRIVER")
    service = Service(executable_path=driver_path) if driver_path else Service()
    try:
        browser = webdriver.Chrome(service=service, options=options)
    except Exception as exc:  # pragma: no cover
        pytest.skip(_skip_reason("The browser did not start.", exc))
    browser.set_page_load_timeout(20)
    yield browser
    browser.quit()


def _shot(browser, name: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    browser.save_screenshot(str(SHOTS / name))
    browser.save_screenshot(str(ARTIFACTS / name))


def _no_page_overflow(browser) -> None:
    metrics = browser.execute_script(
        """
        const root = document.documentElement;
        return {
          scroll: Math.max(root.scrollWidth, document.body ? document.body.scrollWidth : 0),
          client: root.clientWidth
        };
        """
    )
    assert metrics["scroll"] <= metrics["client"] + 1, metrics


def _login(browser, base: str, username: str = "demo_zhang") -> None:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    browser.get(base + "/login")
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.ID, "username")))
    browser.find_element(By.ID, "username").send_keys(username)
    browser.find_element(By.ID, "password").send_keys(FIXTURE_PASSWORD)
    browser.find_element(By.ID, "login-submit").click()
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.ID, "balance")))


def test_selenium_login_shows_balance(live, driver):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    driver.get(live.base + "/login")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "login-form")))
    driver.set_window_size(1440, 1000)
    assert "Linden Ledger" in driver.page_source
    assert "Not a bank" in driver.page_source
    assert "demo_zhang" in driver.page_source
    assert "Mingyuan Zhang" in driver.page_source
    assert FIXTURE_PASSWORD not in driver.page_source
    _no_page_overflow(driver)
    _shot(driver, "ui-login.png")
    _login(driver, live.base)
    balance = driver.find_element(By.ID, "balance")
    assert balance.get_attribute("data-balance-fen") == str(OPENING["demo_zhang"])
    assert "10,000.00" in balance.text
    assert "Not a bank" in driver.page_source
    _no_page_overflow(driver)
    _shot(driver, "ui-dashboard.png")
    driver.set_window_size(390, 844)
    driver.get(live.base + "/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "balance")))
    _no_page_overflow(driver)
    _shot(driver, "ui-dashboard-mobile.png")
    driver.get(live.base + "/deposit")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "amount")))
    _no_page_overflow(driver)
    _shot(driver, "ui-deposit-mobile.png")


def test_selenium_transactions_and_history(live, driver):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    wait = WebDriverWait(driver, 10)
    driver.set_window_size(1440, 1000)
    _login(driver, live.base)
    driver.get(live.base + "/transfer")
    wait.until(EC.presence_of_element_located((By.ID, "to_account_no")))
    _no_page_overflow(driver)
    _shot(driver, "ui-transfer.png")

    driver.get(live.base + "/deposit")
    wait.until(EC.presence_of_element_located((By.ID, "amount")))
    driver.find_element(By.ID, "amount").send_keys("10.00")
    driver.find_element(By.ID, "note").send_keys("Browser deposit")
    driver.find_element(By.CSS_SELECTOR, "main form button.primary").click()
    wait.until(EC.text_to_be_present_in_element((By.ID, "balance"), "10,010.00"))

    driver.get(live.base + "/withdraw")
    wait.until(EC.presence_of_element_located((By.ID, "amount")))
    driver.find_element(By.ID, "amount").send_keys("3.00")
    driver.find_element(By.ID, "note").send_keys("Browser withdrawal")
    driver.find_element(By.CSS_SELECTOR, "main form button.primary").click()
    wait.until(EC.text_to_be_present_in_element((By.ID, "balance"), "10,007.00"))

    driver.get(live.base + "/transfer")
    wait.until(EC.presence_of_element_located((By.ID, "to_account_no")))
    driver.find_element(By.ID, "to_account_no").send_keys("SIM-1002")
    driver.find_element(By.ID, "amount").send_keys("7.00")
    driver.find_element(By.ID, "note").send_keys("Browser transfer")
    driver.find_element(By.CSS_SELECTOR, "main form button.primary").click()
    wait.until(EC.text_to_be_present_in_element((By.ID, "balance"), "10,000.00"))

    driver.get(live.base + "/history")
    wait.until(EC.presence_of_element_located((By.ID, "history")))
    page = driver.page_source
    assert "Browser deposit" in page
    assert "Browser withdrawal" in page
    assert "Browser transfer" in page
    _no_page_overflow(driver)
    assert "SIM-1002" in page
    _shot(driver, "ui-history.png")
    with opened(live.app) as connection:
        receiver = connection.execute(
            "SELECT balance_fen FROM accounts WHERE account_no = 'SIM-1002'"
        ).fetchone()["balance_fen"]
        assert receiver == OPENING["demo_li"] + 700
