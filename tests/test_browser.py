"""本机无头 Chrome。只访问临时服务器，不访问外部网站。"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from werkzeug.serving import make_server

from app.paths import ROOT
from tests.helpers import FIXTURE_PASSWORD, OPENING, make_app, opened
from tests.pages import HistoryPage, LoginPage, MoneyPage, OverviewPage

pytestmark = [pytest.mark.integration, pytest.mark.selenium]

SHOTS = ROOT / "docs" / "screenshots"
ARTIFACTS = Path("/opt/cursor/artifacts")


class LiveServer:
    def __init__(self, app) -> None:
        self.app = app
        self._server = make_server("127.0.0.1", 0, app, threaded=True)
        self.base = f"http://127.0.0.1:{self._server.server_port}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def start(self) -> LiveServer:
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


def test_selenium_login_shows_balance(live, driver):
    login = LoginPage(driver, live.base).open()
    driver.set_window_size(1440, 1000)
    assert "Linden Ledger" in login.source()
    assert "Not a bank" in login.source()
    assert "demo_zhang" in login.source()
    assert "Mingyuan Zhang" in login.source()
    assert FIXTURE_PASSWORD not in login.source()
    _no_page_overflow(driver)
    _shot(driver, "ui-login.png")
    login.sign_in("demo_zhang", FIXTURE_PASSWORD)
    overview = OverviewPage(driver, live.base).wait_until_loaded()
    assert overview.balance_fen() == str(OPENING["demo_zhang"])
    assert "10,000.00" in overview.balance_text()
    assert "Not a bank" in overview.source()
    _no_page_overflow(driver)
    _shot(driver, "ui-dashboard.png")
    driver.set_window_size(390, 844)
    overview.open_path("/")
    overview.wait_until_loaded()
    _no_page_overflow(driver)
    _shot(driver, "ui-dashboard-mobile.png")
    MoneyPage(driver, live.base).open("deposit")
    _no_page_overflow(driver)
    _shot(driver, "ui-deposit-mobile.png")


def test_selenium_transactions_and_history(live, driver):
    driver.set_window_size(1440, 1000)
    LoginPage(driver, live.base).open().sign_in("demo_zhang", FIXTURE_PASSWORD)
    overview = OverviewPage(driver, live.base).wait_until_loaded()
    money = MoneyPage(driver, live.base).open("transfer")
    _no_page_overflow(driver)
    _shot(driver, "ui-transfer.png")

    money.open("deposit").submit("10.00", "Browser deposit")
    overview.wait_for_balance_text("10,010.00")

    money.open("withdrawal").submit("3.00", "Browser withdrawal")
    overview.wait_for_balance_text("10,007.00")

    money.open("transfer").submit("7.00", "Browser transfer", "SIM-1002")
    overview.wait_for_balance_text("10,000.00")

    history = HistoryPage(driver, live.base).open()
    page = history.source()
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


def test_selenium_failed_login_stays_on_login_page(live, driver):
    rejected = "wrong-password"
    login = LoginPage(driver, live.base).open()
    driver.set_window_size(1440, 1000)
    login.sign_in("demo_zhang", rejected)
    assert login.still_on_login()
    assert login.error_text() == "The username or passphrase is not correct."
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "login-form")))
    assert driver.find_elements(By.ID, "balance") == []
    source = login.source()
    assert "Sign in" in source
    assert "Not a bank" in source
    assert "does not exist" not in source.lower()
    assert FIXTURE_PASSWORD not in source
    assert rejected not in source
    _no_page_overflow(driver)
    _shot(driver, "ui-login-failed.png")
