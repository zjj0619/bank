"""授权、CSRF、回滚、幂等失败和仅针对本机应用的注入回归。"""

from __future__ import annotations

import re

import pytest

from tests.helpers import (
    FIXTURE_PASSWORD,
    OPENING,
    account,
    assert_books,
    assert_safe,
    history,
    login,
    make_app,
    new_key,
    opened,
    post_json,
)

pytestmark = [pytest.mark.integration, pytest.mark.security]


def _hidden(html: str, name: str) -> str:
    match = re.search(rf'name="{name}" value="([^"]*)"', html)
    assert match, name
    return match.group(1)


def test_account_query_ignores_foreign_account_parameters(client):
    headers = login(client, "demo_li")
    response = client.get("/api/v1/account?account_no=SIM-1001&user_id=1", headers=headers)
    assert response.status_code == 200
    body = response.get_json()["account"]
    assert body["username"] == "demo_li"
    assert body["account_no"] == "SIM-1002"
    assert body["balance_fen"] == OPENING["demo_li"]
    assert_safe(response)


def test_history_isolated_between_users(app):
    zhang_client = app.test_client()
    li_client = app.test_client()
    zhang = login(zhang_client)
    posted = post_json(zhang_client, "/api/v1/deposits", zhang, {"amount": "1.00", "note": "仅张可见"})
    assert posted.status_code == 200
    li = login(li_client, "demo_li")
    own = history(li_client, li)
    assert all(item["note"] != "仅张可见" for item in own)
    probed = li_client.get("/api/v1/transactions?account_no=SIM-1001&user_id=1", headers=li)
    assert probed.status_code == 200
    assert all(item["note"] != "仅张可见" for item in probed.get_json()["transactions"])
    assert any(item["note"] == "仅张可见" for item in history(zhang_client, zhang))


def test_unauthorized_reads_require_login(app):
    anon = app.test_client()
    health = anon.get("/api/v1/health")
    assert health.status_code == 200
    assert health.get_json()["simulation"] is True
    for path in ("/api/v1/account", "/api/v1/transactions", "/api/v1/me"):
        response = anon.get(path)
        assert response.status_code == 401, path
        assert response.get_json()["error"]["code"] == "auth_required"
        assert_safe(response)


def test_logout_invalidates_session(client):
    headers = login(client)
    response = client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 200
    account_response = client.get("/api/v1/account", headers=headers)
    assert account_response.status_code == 401
    assert account_response.get_json()["error"]["code"] == "auth_required"


def test_mutation_without_login_is_rejected(app):
    anon = app.test_client()
    token = anon.get("/api/v1/csrf").get_json()["csrf_token"]
    response = anon.post(
        "/api/v1/deposits",
        json={"amount": "10.00"},
        headers={"X-CSRF-Token": token, "Idempotency-Key": new_key()},
    )
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "auth_required"
    with opened(app) as connection:
        assert_books(connection)
        assert connection.execute("SELECT COUNT(*) AS count FROM transactions WHERE kind = 'deposit'").fetchone()["count"] == 0


def test_missing_csrf_rejected_and_balance_unchanged(client, app):
    headers = login(client)
    before = account(client, headers)["balance_fen"]
    api_response = client.post(
        "/api/v1/deposits",
        json={"amount": "1.00"},
        headers={"Idempotency-Key": new_key()},
    )
    assert api_response.status_code == 403
    assert api_response.get_json()["error"]["code"] == "csrf_failed"
    page = client.get("/deposit")
    web_response = client.post(
        "/deposit",
        data={"amount": "1.00", "note": "", "idempotency_key": new_key()},
    )
    assert web_response.status_code == 403
    assert "csrf_token" in page.get_data(as_text=True)
    assert account(client, headers)["balance_fen"] == before
    with opened(app) as connection:
        assert_books(connection)


def test_csrf_rotates_on_login(client, app):
    old = client.get("/api/v1/csrf").get_json()["csrf_token"]
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "demo_zhang", "password": FIXTURE_PASSWORD},
        headers={"X-CSRF-Token": old},
    )
    assert response.status_code == 200
    new = response.get_json()["csrf_token"]
    assert new and new != old
    rejected = post_json(
        client,
        "/api/v1/deposits",
        {"X-CSRF-Token": old},
        {"amount": "1.00"},
    )
    assert rejected.status_code == 403
    accepted = post_json(client, "/api/v1/deposits", {"X-CSRF-Token": new}, {"amount": "1.00"})
    assert accepted.status_code == 200, accepted.get_data(as_text=True)
    assert account(client, {"X-CSRF-Token": new})["balance_fen"] == OPENING["demo_zhang"] + 100
    with opened(app) as connection:
        assert_books(connection)


def test_injected_fault_rolls_back_all_writes(tmp_path, monkeypatch):
    for name in (
        "BANK_SEED_PASSWORD",
        "BANK_SEED_PASSWORD_DEMO_ZHANG",
        "BANK_SEED_PASSWORD_DEMO_LI",
        "BANK_SEED_PASSWORD_DEMO_WANG",
    ):
        monkeypatch.delenv(name, raising=False)
    application = make_app(tmp_path, ALLOW_FAULT_INJECTION=True)
    client = application.test_client()
    headers = login(client)
    before = account(client, headers)["balance_fen"]
    failed = post_json(
        client,
        "/api/v1/deposits",
        headers,
        {"amount": "19.99", "note": "应当回滚"},
        {"X-Test-Inject-Fault": "after_write"},
    )
    text = assert_safe(failed)
    assert failed.status_code == 500
    assert "The operation was cancelled" in text
    assert "injected" not in text.lower()
    assert account(client, headers)["balance_fen"] == before
    with opened(application) as connection:
        assert_books(connection)
        assert connection.execute("SELECT COUNT(*) AS count FROM transactions").fetchone()["count"] == 3
    retried = post_json(client, "/api/v1/deposits", headers, {"amount": "19.99", "note": "应当回滚"})
    assert retried.status_code == 200, retried.get_data(as_text=True)
    assert account(client, headers)["balance_fen"] == before + 1_999
    with opened(application) as connection:
        assert_books(connection)


def test_fault_header_ignored_when_injection_disabled(client, app):
    headers = login(client)
    response = post_json(
        client,
        "/api/v1/deposits",
        headers,
        {"amount": "1.00"},
        {"X-Test-Inject-Fault": "after_write"},
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"] + 100
    with opened(app) as connection:
        assert_books(connection)


def test_sql_injection_login_does_not_authenticate(client, app):
    payloads = [
        "' OR '1'='1",
        "' OR '1'='1' --",
        "admin'--",
        "demo_zhang' OR '1'='1",
        '" OR "1"="1',
        "demo_zhang'; DROP TABLE users;--",
    ]
    for username in payloads:
        token = client.get("/api/v1/csrf").get_json()["csrf_token"]
        response = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": "' OR '1'='1"},
            headers={"X-CSRF-Token": token},
        )
        assert response.status_code == 401, username
        assert response.get_json()["error"]["code"] == "login_failed"
        assert_safe(response)
        assert client.get("/api/v1/account").status_code == 401
    with opened(app) as connection:
        assert connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"] == 3
        tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        assert {"users", "accounts", "transactions", "ledger_entries"} <= tables
    headers = login(client)
    assert account(client, headers)["account_no"] == "SIM-1001"


def test_sql_injection_in_transaction_form_is_stored_not_executed(client, app):
    headers = login(client)
    note = "'); DROP TABLE accounts;--"
    stored = post_json(client, "/api/v1/deposits", headers, {"amount": "1.00", "note": note})
    assert stored.status_code == 200, stored.get_data(as_text=True)
    assert any(item["note"] == note for item in history(client, headers))
    for amount in ("100; DROP TABLE accounts;--", "1 OR 1=1", "0x10"):
        rejected = post_json(client, "/api/v1/withdrawals", headers, {"amount": amount})
        assert rejected.status_code == 400, amount
    for recipient in ("SIM-1002' OR '1'='1", "SIM-1002; DROP TABLE accounts;--"):
        rejected = post_json(
            client,
            "/api/v1/transfers",
            headers,
            {"amount": "1.00", "to_account_no": recipient, "note": note},
        )
        assert rejected.status_code == 400, recipient
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"] + 100
    with opened(app) as connection:
        assert_books(connection)
        assert connection.execute("SELECT COUNT(*) AS count FROM accounts").fetchone()["count"] == 3
        tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        assert "accounts" in tables and "ledger_entries" in tables


def test_history_escapes_html_in_note(client):
    headers = login(client)
    note = "<script>alert(1)</script>"
    posted = post_json(client, "/api/v1/deposits", headers, {"amount": "0.01", "note": note})
    assert posted.status_code == 200
    page = client.get("/history")
    html = page.get_data(as_text=True)
    assert page.status_code == 200
    assert note not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert any(item["note"] == note for item in history(client, headers))


def test_session_cookie_is_httponly_and_samesite(client):
    token = client.get("/api/v1/csrf").get_json()["csrf_token"]
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "demo_zhang", "password": FIXTURE_PASSWORD},
        headers={"X-CSRF-Token": token},
    )
    cookie = ",".join(response.headers.getlist("Set-Cookie"))
    assert "chengbu_session=" in cookie
    attributes = [part.strip() for part in cookie.split(";")[1:]]
    lowered = [part.lower() for part in attributes]
    assert "httponly" in lowered
    assert "samesite=lax" in lowered
    assert "secure" not in lowered


def test_login_failure_messages_are_uniform(client):
    def attempt(username: str, password: str):
        token = client.get("/api/v1/csrf").get_json()["csrf_token"]
        return client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
            headers={"X-CSRF-Token": token},
        )

    unknown = attempt("nobody", "wrong-password")
    wrong = attempt("demo_zhang", "wrong-password")
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.get_json()["error"]["message"] == wrong.get_json()["error"]["message"]
    message = unknown.get_json()["error"]["message"].lower()
    assert "不存在" not in message
    assert "does not exist" not in message
    assert "unknown user" not in message
    assert_safe(unknown)
    assert_safe(wrong)


def test_web_login_deposit_and_history_pages(client, app):
    page = client.get("/login")
    html = page.get_data(as_text=True)
    assert page.status_code == 200
    assert 'lang="en"' in html
    assert "Linden Ledger" in html
    assert "Not a bank" in html
    assert "Mingyuan Zhang" in html
    assert "demo_zhang" in html
    assert FIXTURE_PASSWORD not in html
    token = _hidden(html, "csrf_token")
    logged_in = client.post(
        "/login",
        data={"username": "demo_zhang", "password": FIXTURE_PASSWORD, "csrf_token": token},
        follow_redirects=True,
    )
    assert logged_in.status_code == 200
    assert 'data-balance-fen="1000000"' in logged_in.get_data(as_text=True)
    assert "10,000.00" in logged_in.get_data(as_text=True)
    form = client.get("/deposit")
    form_html = form.get_data(as_text=True)
    payload = {
        "csrf_token": _hidden(form_html, "csrf_token"),
        "idempotency_key": _hidden(form_html, "idempotency_key"),
        "amount": "15.00",
        "note": "Page deposit",
    }
    first = client.post("/deposit", data=payload, follow_redirects=True)
    second = client.post("/deposit", data=payload, follow_redirects=True)
    assert "Deposit recorded" in first.get_data(as_text=True)
    assert "already posted" in second.get_data(as_text=True)
    assert 'data-balance-fen="1001500"' in second.get_data(as_text=True)
    withdraw_page = client.get("/withdraw")
    withdraw_html = withdraw_page.get_data(as_text=True)
    withdrawn = client.post(
        "/withdraw",
        data={
            "csrf_token": _hidden(withdraw_html, "csrf_token"),
            "idempotency_key": _hidden(withdraw_html, "idempotency_key"),
            "amount": "5.00",
            "note": "Page withdrawal",
        },
        follow_redirects=True,
    )
    assert "Withdrawal recorded" in withdrawn.get_data(as_text=True)
    assert 'data-balance-fen="1001000"' in withdrawn.get_data(as_text=True)
    transfer_page = client.get("/transfer")
    transfer_html = transfer_page.get_data(as_text=True)
    transferred = client.post(
        "/transfer",
        data={
            "csrf_token": _hidden(transfer_html, "csrf_token"),
            "idempotency_key": _hidden(transfer_html, "idempotency_key"),
            "amount": "10.00",
            "to_account_no": "SIM-1002",
            "note": "Page transfer",
        },
        follow_redirects=True,
    )
    assert "Transfer recorded" in transferred.get_data(as_text=True)
    assert 'data-balance-fen="1000000"' in transferred.get_data(as_text=True)
    history_page = client.get("/history")
    history_html = history_page.get_data(as_text=True)
    assert "Page deposit" in history_html and "Page withdrawal" in history_html and "Page transfer" in history_html
    assert "SIM-1002" in history_html
    with opened(app) as connection:
        assert_books(connection)
        receiver = connection.execute(
            "SELECT balance_fen FROM accounts WHERE account_no = 'SIM-1002'"
        ).fetchone()["balance_fen"]
        assert receiver == OPENING["demo_li"] + 1_000
    home = client.get("/")
    logout = client.post(
        "/logout",
        data={"csrf_token": _hidden(home.get_data(as_text=True), "csrf_token")},
    )
    assert logout.status_code == 302
    assert logout.headers["Location"].endswith("/login")
    assert client.get("/history").status_code == 302


def test_login_does_not_redirect_off_site(client):
    page = client.get("/login")
    response = client.post(
        "/login?next=https://evil.example/phish",
        data={
            "username": "demo_zhang",
            "password": FIXTURE_PASSWORD,
            "csrf_token": _hidden(page.get_data(as_text=True), "csrf_token"),
        },
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    assert "evil.example" not in response.headers["Location"]


def test_api_errors_do_not_leak_tracebacks(client):
    headers = login(client)
    missing = client.get("/api/v1/does-not-exist")
    assert missing.status_code == 404
    assert_safe(missing)
    paging = client.get("/api/v1/transactions?limit=abc", headers=headers)
    assert paging.status_code == 400
    assert paging.get_json()["error"]["code"] == "invalid_paging"
    assert_safe(paging)
    raw = client.post(
        "/api/v1/deposits",
        data="not-json",
        headers={**headers, "Content-Type": "application/json", "Idempotency-Key": new_key()},
    )
    assert raw.status_code == 400
    assert_safe(raw)
    method = client.get("/api/v1/deposits", headers=headers)
    assert method.status_code == 405
    assert_safe(method)
