"""Page objects for the Linden Ledger browser tests.

These classes own the selectors. The tests describe the journey.
"""

from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class Page:
    def __init__(self, driver: WebDriver, base_url: str) -> None:
        self.driver = driver
        self.base_url = base_url.rstrip("/")
        self.wait = WebDriverWait(driver, 10)

    def open_path(self, path: str) -> None:
        self.driver.get(self.base_url + path)

    def source(self) -> str:
        return self.driver.page_source


class LoginPage(Page):
    def open(self) -> LoginPage:
        self.open_path("/login")
        self.wait.until(EC.presence_of_element_located((By.ID, "login-form")))
        return self

    def sign_in(self, username: str, password: str) -> None:
        username_field = self.driver.find_element(By.ID, "username")
        username_field.clear()
        username_field.send_keys(username)
        password_field = self.driver.find_element(By.ID, "password")
        password_field.clear()
        password_field.send_keys(password)
        self.driver.find_element(By.ID, "login-submit").click()

    def error(self) -> WebElement:
        return self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#login-form .form-error")))

    def error_text(self) -> str:
        return self.error().text

    def still_on_login(self) -> bool:
        current = self.driver.current_url.split("?", 1)[0].rstrip("/")
        return current.endswith("/login") and bool(self.driver.find_elements(By.ID, "login-form"))


class OverviewPage(Page):
    def wait_until_loaded(self) -> OverviewPage:
        self.wait.until(EC.presence_of_element_located((By.ID, "balance")))
        return self

    def balance_text(self) -> str:
        return self.driver.find_element(By.ID, "balance").text

    def balance_fen(self) -> str:
        return self.driver.find_element(By.ID, "balance").get_attribute("data-balance-fen") or ""

    def wait_for_balance_text(self, text: str) -> None:
        self.wait.until(EC.text_to_be_present_in_element((By.ID, "balance"), text))


class MoneyPage(Page):
    _PATHS = {"deposit": "/deposit", "withdrawal": "/withdraw", "transfer": "/transfer"}

    def open(self, kind: str) -> MoneyPage:
        self.open_path(self._PATHS[kind])
        self.wait.until(EC.presence_of_element_located((By.ID, "amount")))
        return self

    def submit(self, amount: str, note: str, to_account_no: str | None = None) -> None:
        if to_account_no is not None:
            recipient = self.driver.find_element(By.ID, "to_account_no")
            recipient.clear()
            recipient.send_keys(to_account_no)
        amount_field = self.driver.find_element(By.ID, "amount")
        amount_field.clear()
        amount_field.send_keys(amount)
        note_field = self.driver.find_element(By.ID, "note")
        note_field.clear()
        note_field.send_keys(note)
        self.driver.find_element(By.CSS_SELECTOR, "main form button.primary").click()


class HistoryPage(Page):
    def open(self) -> HistoryPage:
        self.open_path("/history")
        self.wait.until(EC.presence_of_element_located((By.ID, "history")))
        return self
