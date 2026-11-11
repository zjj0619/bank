"""测试夹具。口令只用于临时数据库，不是演示账户或真实用户的口令。"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from app import create_app
from app.db import connect, init_db

# 只写入 pytest 临时库。不要把它当作演示口令，也不要写进报告。
FIXTURE_PASSWORDS = {
    "demo_zhang": "Zx4!ledger-case",
    "demo_li": "Lq8#ledger-case",
    "demo_wang": "Wq2$ledger-case",
}
FIXTURE_PASSWORD = FIXTURE_PASSWORDS["demo_zhang"]
CHANGED_PASSWORD = "Nq6!ledger-case"
WEB_CHANGED_PASSWORD = "Mq3%ledger-case"

OPENING = {
    "demo_zhang": 1_000_000,
    "demo_li": 500_000,
    "demo_wang": 258_025,
}


def make_app(tmp_path, **overrides):
    config = {
        "TESTING": True,
        "DATABASE": str(tmp_path / "bank.sqlite3"),
        "SECRET_KEY": "test-only-secret-not-for-production",
        "SEED_PASSWORDS": dict(FIXTURE_PASSWORDS),
        "ARGON2_TIME_COST": 1,
        "ARGON2_MEMORY_COST": 8192,
        "ARGON2_PARALLELISM": 1,
        "LOCKOUT_THRESHOLD": 5,
        "LOCKOUT_SECONDS": 900,
        "ALLOW_FAULT_INJECTION": False,
        "SESSION_COOKIE_SECURE": False,
    }
    config.update(overrides)
    application = create_app(config)
    with application.app_context():
        init_db(seed=True)
    return application


@contextmanager
def opened(app) -> Iterator:
    connection = connect(app.config["DATABASE"])
    try:
        yield connection
    finally:
        connection.close()


def new_key() -> str:
    return "idem" + uuid.uuid4().hex


def login(client, username: str = "demo_zhang", password: str | None = None) -> dict[str, str]:
    if password is None:
        password = FIXTURE_PASSWORDS[username]
    token = client.get("/api/v1/csrf").get_json()["csrf_token"]
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    body = response.get_json()
    assert body["ok"] is True
    assert "password_hash" not in response.get_data(as_text=True)
    return {"X-CSRF-Token": body["csrf_token"]}


def post_json(client, path: str, headers: dict, payload: dict, extra_headers: dict | None = None):
    merged = dict(headers)
    if extra_headers:
        merged.update(extra_headers)
    if "Idempotency-Key" not in merged and "idempotency_key" not in payload:
        merged["Idempotency-Key"] = new_key()
    return client.post(path, json=payload, headers=merged)


def account(client, headers: dict) -> dict:
    response = client.get("/api/v1/account", headers=headers)
    assert response.status_code == 200, response.get_data(as_text=True)
    return response.get_json()["account"]


def history(client, headers: dict) -> list[dict]:
    response = client.get("/api/v1/transactions", headers=headers)
    assert response.status_code == 200, response.get_data(as_text=True)
    return response.get_json()["transactions"]


def assert_safe(response) -> str:
    text = response.get_data(as_text=True)
    lowered = text.lower()
    assert "traceback" not in lowered
    assert "sqlite3" not in lowered
    assert 'file "' not in lowered
    assert "password_hash" not in lowered
    for secret in (*FIXTURE_PASSWORDS.values(), CHANGED_PASSWORD, WEB_CHANGED_PASSWORD):
        assert secret not in text
    return text


def assert_books(connection) -> None:
    accounts = connection.execute(
        "SELECT id, account_no, balance_fen FROM accounts ORDER BY id"
    ).fetchall()
    assert len(accounts) == 3
    for row in accounts:
        entries = connection.execute(
            """
            SELECT direction, amount_fen, balance_after_fen
            FROM ledger_entries
            WHERE account_id = ?
            ORDER BY id
            """,
            (row["id"],),
        ).fetchall()
        running = 0
        assert entries, row["account_no"]
        for entry in entries:
            delta = entry["amount_fen"] if entry["direction"] == "credit" else -entry["amount_fen"]
            running += delta
            assert entry["balance_after_fen"] == running
            assert running >= 0
        assert running == row["balance_fen"]
        stored_type = connection.execute(
            "SELECT typeof(balance_fen) AS kind FROM accounts WHERE id = ?",
            (row["id"],),
        ).fetchone()["kind"]
        assert stored_type == "integer"
    totals = connection.execute(
        "SELECT account_no, balance_fen, ledger_fen FROM account_ledger_totals ORDER BY account_no"
    ).fetchall()
    assert len(totals) == 3
    for total in totals:
        assert total["balance_fen"] == total["ledger_fen"]


def ledger_rows_for(connection, public_id: str):
    return connection.execute(
        """
        SELECT l.direction, l.amount_fen, l.balance_after_fen, a.account_no
        FROM ledger_entries AS l
        JOIN transactions AS t ON t.id = l.transaction_id
        JOIN accounts AS a ON a.id = l.account_id
        WHERE t.public_id = ?
        ORDER BY l.id
        """,
        (public_id,),
    ).fetchall()
