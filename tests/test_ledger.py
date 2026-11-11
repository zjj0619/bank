"""余额、分录、转账双方和金额边界。每个用例使用独立的临时数据库。"""

from __future__ import annotations

import threading

import pytest

from app.db import connect
from app.errors import BusinessError
from app.money import MAX_FEN
from app.services import withdraw
from tests.helpers import (
    FIXTURE_PASSWORD,
    OPENING,
    account,
    assert_books,
    history,
    ledger_rows_for,
    login,
    new_key,
    opened,
    post_json,
)

pytestmark = pytest.mark.integration

ENDPOINTS = ("/api/v1/deposits", "/api/v1/withdrawals", "/api/v1/transfers")


def _reject_amount(client, headers, amount, code):
    before = account(client, headers)["balance_fen"]
    for path in ENDPOINTS:
        payload = {"amount": amount}
        if path.endswith("/transfers"):
            payload["to_account_no"] = "SIM-1002"
        response = post_json(client, path, headers, payload)
        body = response.get_json()
        assert response.status_code == 400, (path, response.get_data(as_text=True))
        assert body["ok"] is False
        assert body["error"]["code"] == code
        assert account(client, headers)["balance_fen"] == before


def test_seed_balances_match_opening_ledger(client, app):
    headers = login(client)
    body = account(client, headers)
    assert body["balance"] == "10000.00"
    assert body["balance_fen"] == OPENING["demo_zhang"]
    assert body["account_no"] == "SIM-1001"
    assert body["simulation"] is True
    with opened(app) as connection:
        assert_books(connection)
        stored = connection.execute(
            "SELECT password_hash FROM users WHERE username = 'demo_zhang'"
        ).fetchone()["password_hash"]
        assert stored.startswith("$argon2id$")
        assert FIXTURE_PASSWORD not in stored
        opening = history(client, headers)
        assert opening[0]["kind"] == "opening"
        assert opening[0]["balance_after_fen"] == OPENING["demo_zhang"]


def test_deposit_success_updates_balance_and_ledger(client, app):
    headers = login(client)
    response = post_json(
        client,
        "/api/v1/deposits",
        headers,
        {"amount": "100.50", "note": "模拟工资"},
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    body = response.get_json()
    assert body["replayed"] is False
    txn = body["transaction"]
    assert txn["kind"] == "deposit"
    assert txn["amount"] == "100.50"
    assert txn["amount_fen"] == 10_050
    assert txn["balance_fen"] == OPENING["demo_zhang"] + 10_050
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"] + 10_050
    with opened(app) as connection:
        assert_books(connection)
        rows = ledger_rows_for(connection, txn["transaction_id"])
        assert len(rows) == 1
        assert rows[0]["direction"] == "credit"
        assert rows[0]["amount_fen"] == 10_050
        assert rows[0]["account_no"] == "SIM-1001"


def test_withdrawal_success_updates_balance_and_ledger(client, app):
    headers = login(client)
    response = post_json(client, "/api/v1/withdrawals", headers, {"amount": "20.00", "note": "模拟取现"})
    assert response.status_code == 200, response.get_data(as_text=True)
    txn = response.get_json()["transaction"]
    assert txn["kind"] == "withdrawal"
    assert txn["balance_fen"] == OPENING["demo_zhang"] - 2_000
    with opened(app) as connection:
        assert_books(connection)
        rows = ledger_rows_for(connection, txn["transaction_id"])
        assert len(rows) == 1
        assert rows[0]["direction"] == "debit"
        assert rows[0]["amount_fen"] == 2_000


def test_transfer_syncs_both_balances_and_ledgers(client, app):
    sender = login(client)
    response = post_json(
        client,
        "/api/v1/transfers",
        sender,
        {"amount": "88.80", "to_account_no": "SIM-1002", "note": "模拟转账"},
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    txn = response.get_json()["transaction"]
    assert txn["balance_fen"] == OPENING["demo_zhang"] - 8_880
    assert txn["counterparty_account_no"] == "SIM-1002"
    assert "receiver_balance" not in txn
    receiver_client = app.test_client()
    receiver = login(receiver_client, "demo_li")
    assert account(receiver_client, receiver)["balance_fen"] == OPENING["demo_li"] + 8_880
    with opened(app) as connection:
        assert_books(connection)
        rows = ledger_rows_for(connection, txn["transaction_id"])
        assert [row["account_no"] for row in rows] == ["SIM-1001", "SIM-1002"]
        assert [row["direction"] for row in rows] == ["debit", "credit"]
        assert {row["amount_fen"] for row in rows} == {8_880}
        supply = connection.execute("SELECT SUM(balance_fen) AS total FROM accounts").fetchone()["total"]
        assert supply == sum(OPENING.values())


def test_transfer_visible_in_both_histories(client):
    sender = login(client)
    response = post_json(
        client,
        "/api/v1/transfers",
        sender,
        {"amount": "3.25", "to_account_no": "SIM-1003", "note": "双方可见"},
    )
    public_id = response.get_json()["transaction"]["transaction_id"]
    outgoing = history(client, sender)
    matched = [item for item in outgoing if item["transaction_id"] == public_id]
    assert len(matched) == 1
    assert matched[0]["direction"] == "debit"
    assert matched[0]["kind_label"] == "Transfer out"
    assert matched[0]["counterparty_account_no"] == "SIM-1003"
    assert matched[0]["counterparty_name"] == "Qinian Wang"
    receiver = login(client, "demo_wang")
    incoming = [item for item in history(client, receiver) if item["transaction_id"] == public_id]
    assert len(incoming) == 1
    assert incoming[0]["direction"] == "credit"
    assert incoming[0]["kind_label"] == "Transfer in"
    assert incoming[0]["counterparty_account_no"] == "SIM-1001"
    assert incoming[0]["amount_fen"] == 325
    assert incoming[0]["balance_after_fen"] == OPENING["demo_wang"] + 325


def test_transfer_entire_balance_conserves_money(client, app):
    sender = login(client, "demo_wang")
    amount = f"{OPENING['demo_wang'] // 100}.{OPENING['demo_wang'] % 100:02d}"
    response = post_json(
        client,
        "/api/v1/transfers",
        sender,
        {"amount": amount, "to_account_no": "SIM-1001"},
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    assert account(client, sender)["balance_fen"] == 0
    receiver = login(client)
    assert account(client, receiver)["balance_fen"] == OPENING["demo_zhang"] + OPENING["demo_wang"]
    with opened(app) as connection:
        assert_books(connection)
        supply = connection.execute("SELECT SUM(balance_fen) AS total FROM accounts").fetchone()["total"]
        assert supply == sum(OPENING.values())


def test_transfer_account_number_is_case_insensitive(client):
    headers = login(client)
    response = post_json(
        client,
        "/api/v1/transfers",
        headers,
        {"amount": "0.01", "to_account_no": "sim-1002"},
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.get_json()["transaction"]["counterparty_account_no"] == "SIM-1002"
    receiver = login(client, "demo_li")
    assert account(client, receiver)["balance_fen"] == OPENING["demo_li"] + 1


def test_withdrawal_insufficient_funds(client, app):
    headers = login(client)
    before = account(client, headers)["balance_fen"]
    response = post_json(client, "/api/v1/withdrawals", headers, {"amount": "10000.01"})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "insufficient_funds"
    assert account(client, headers)["balance_fen"] == before
    with opened(app) as connection:
        assert_books(connection)
        debits = connection.execute(
            "SELECT COUNT(*) AS count FROM ledger_entries WHERE direction = 'debit'"
        ).fetchone()["count"]
        assert debits == 0


def test_transfer_insufficient_funds(client, app):
    headers = login(client, "demo_li")
    response = post_json(
        client,
        "/api/v1/transfers",
        headers,
        {"amount": "5000.01", "to_account_no": "SIM-1001"},
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "insufficient_funds"
    assert account(client, headers)["balance_fen"] == OPENING["demo_li"]
    other = login(client)
    assert account(client, other)["balance_fen"] == OPENING["demo_zhang"]
    with opened(app) as connection:
        assert_books(connection)


def test_transfer_invalid_recipient_format(client, app):
    headers = login(client)
    before = account(client, headers)["balance_fen"]
    for recipient in ("", "1002", "SIM-10", "SIM-1002' OR '1'='1", "SIM-1002; DROP TABLE accounts;--"):
        response = post_json(
            client,
            "/api/v1/transfers",
            headers,
            {"amount": "1.00", "to_account_no": recipient},
        )
        assert response.status_code == 400, recipient
        assert response.get_json()["error"]["code"] == "invalid_recipient"
    assert account(client, headers)["balance_fen"] == before
    with opened(app) as connection:
        assert_books(connection)
        assert connection.execute("SELECT COUNT(*) AS count FROM accounts").fetchone()["count"] == 3


def test_transfer_nonexistent_recipient(client, app):
    headers = login(client)
    response = post_json(
        client,
        "/api/v1/transfers",
        headers,
        {"amount": "1.00", "to_account_no": "SIM-9999"},
    )
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "recipient_not_found"
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"]
    with opened(app) as connection:
        assert_books(connection)


def test_transfer_to_self_rejected(client, app):
    headers = login(client)
    response = post_json(
        client,
        "/api/v1/transfers",
        headers,
        {"amount": "1.00", "to_account_no": "SIM-1001"},
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "self_transfer"
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"]
    with opened(app) as connection:
        assert_books(connection)


def test_minimum_fen_deposit_boundary(client, app):
    headers = login(client)
    response = post_json(client, "/api/v1/deposits", headers, {"amount": "0.01"})
    assert response.status_code == 200, response.get_data(as_text=True)
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"] + 1
    assert account(client, headers)["balance"] == "10000.01"
    with opened(app) as connection:
        assert_books(connection)


def test_zero_amount_rejected(client, app):
    headers = login(client)
    _reject_amount(client, headers, "0", "non_positive_amount")
    _reject_amount(client, headers, "0.00", "non_positive_amount")
    _reject_amount(client, headers, 0, "non_positive_amount")
    with opened(app) as connection:
        assert_books(connection)


def test_negative_amount_rejected(client, app):
    headers = login(client)
    _reject_amount(client, headers, "-1", "non_positive_amount")
    _reject_amount(client, headers, "-0.01", "non_positive_amount")
    _reject_amount(client, headers, -5, "non_positive_amount")
    with opened(app) as connection:
        assert_books(connection)


def test_overprecision_rejected(client, app):
    headers = login(client)
    _reject_amount(client, headers, "1.001", "overprecision")
    _reject_amount(client, headers, "0.001", "overprecision")
    _reject_amount(client, headers, "10.999", "overprecision")
    with opened(app) as connection:
        assert_books(connection)


def test_nonfinite_amount_rejected(client, app):
    headers = login(client)
    before = account(client, headers)["balance_fen"]
    for raw in ('{"amount": NaN}', '{"amount": Infinity}', '{"amount": -Infinity}'):
        response = client.post(
            "/api/v1/deposits",
            data=raw,
            headers={**headers, "Content-Type": "application/json", "Idempotency-Key": new_key()},
        )
        assert response.status_code == 400, raw
        assert response.get_json()["error"]["code"] == "nonfinite_amount"
    for token in ("NaN", "inf", "+Infinity", "-nan"):
        response = post_json(client, "/api/v1/withdrawals", headers, {"amount": token})
        assert response.status_code == 400
        assert response.get_json()["error"]["code"] == "nonfinite_amount"
    assert account(client, headers)["balance_fen"] == before
    with opened(app) as connection:
        assert_books(connection)


def test_invalid_amount_strings_rejected(client, app):
    headers = login(client)
    before = account(client, headers)["balance_fen"]
    samples = ["1e2", "1,000.00", "+10", "abc", "", "10.00.1", "1.", "00.50", "  ", True, None, []]
    for sample in samples:
        response = post_json(client, "/api/v1/deposits", headers, {"amount": sample})
        assert response.status_code == 400, sample
        assert response.get_json()["error"]["code"] == "invalid_amount"
    assert account(client, headers)["balance_fen"] == before
    with opened(app) as connection:
        assert_books(connection)


def test_json_float_amount_rejected(client, app):
    headers = login(client)
    response = post_json(client, "/api/v1/deposits", headers, {"amount": 10.5})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "amount_must_be_string"
    whole = post_json(client, "/api/v1/deposits", headers, {"amount": 2})
    assert whole.status_code == 200, whole.get_data(as_text=True)
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"] + 200
    with opened(app) as connection:
        assert_books(connection)


def test_overflow_amount_rejected(client, app):
    headers = login(client)
    _reject_amount(client, headers, "10000000000001.00", "amount_overflow")
    _reject_amount(client, headers, "1" + "0" * 20, "amount_overflow")
    with opened(app) as connection:
        assert_books(connection)


def test_deposit_rejected_when_balance_would_overflow(client, app):
    headers = login(client)
    gap = MAX_FEN - OPENING["demo_zhang"]
    amount = f"{gap // 100}.{gap % 100:02d}"
    first = post_json(client, "/api/v1/deposits", headers, {"amount": amount})
    assert first.status_code == 200, first.get_data(as_text=True)
    assert account(client, headers)["balance_fen"] == MAX_FEN
    second = post_json(client, "/api/v1/deposits", headers, {"amount": "0.01"})
    assert second.status_code == 400
    assert second.get_json()["error"]["code"] == "amount_overflow"
    assert account(client, headers)["balance_fen"] == MAX_FEN
    with opened(app) as connection:
        assert_books(connection)


def test_balance_matches_ledger_after_mixed_operations(app):
    zhang_client = app.test_client()
    li_client = app.test_client()
    zhang = login(zhang_client, "demo_zhang")
    li = login(li_client, "demo_li")
    assert post_json(zhang_client, "/api/v1/deposits", zhang, {"amount": "10.00"}).status_code == 200
    assert post_json(zhang_client, "/api/v1/withdrawals", zhang, {"amount": "3.40"}).status_code == 200
    assert post_json(
        zhang_client,
        "/api/v1/transfers",
        zhang,
        {"amount": "6.60", "to_account_no": "SIM-1002"},
    ).status_code == 200
    assert post_json(li_client, "/api/v1/withdrawals", li, {"amount": "1.10"}).status_code == 200
    assert account(zhang_client, zhang)["balance_fen"] == OPENING["demo_zhang"] + 1_000 - 340 - 660
    assert account(li_client, li)["balance_fen"] == OPENING["demo_li"] + 660 - 110
    entries = history(zhang_client, zhang)
    running_seen = [item["balance_after_fen"] for item in entries]
    assert running_seen[0] == account(zhang_client, zhang)["balance_fen"]
    with opened(app) as connection:
        assert_books(connection)


def test_withdraw_exact_balance_boundary(client, app):
    headers = login(client, "demo_li")
    response = post_json(client, "/api/v1/withdrawals", headers, {"amount": "5000.00"})
    assert response.status_code == 200, response.get_data(as_text=True)
    assert account(client, headers)["balance"] == "0.00"
    assert account(client, headers)["balance_fen"] == 0
    follow = post_json(client, "/api/v1/withdrawals", headers, {"amount": "0.01"})
    assert follow.status_code == 400
    assert follow.get_json()["error"]["code"] == "insufficient_funds"
    with opened(app) as connection:
        assert_books(connection)


def test_duplicate_deposit_is_idempotent(client, app):
    headers = login(client)
    key = new_key()
    first = post_json(client, "/api/v1/deposits", headers, {"amount": "12.34"}, {"Idempotency-Key": key})
    second = post_json(client, "/api/v1/deposits", headers, {"amount": "12.34"}, {"Idempotency-Key": key})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.get_json()["replayed"] is False
    assert second.get_json()["replayed"] is True
    assert first.get_json()["transaction"]["transaction_id"] == second.get_json()["transaction"]["transaction_id"]
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"] + 1_234
    with opened(app) as connection:
        assert_books(connection)
        count = connection.execute(
            "SELECT COUNT(*) AS count FROM transactions WHERE kind = 'deposit'"
        ).fetchone()["count"]
        assert count == 1


def test_duplicate_transfer_is_idempotent(client, app):
    headers = login(client)
    key = new_key()
    payload = {"amount": "4.00", "to_account_no": "SIM-1003", "idempotency_key": key}
    first = post_json(client, "/api/v1/transfers", headers, payload)
    second = post_json(client, "/api/v1/transfers", headers, dict(payload))
    assert first.get_json()["replayed"] is False
    assert second.get_json()["replayed"] is True
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"] - 400
    receiver = login(client, "demo_wang")
    assert account(client, receiver)["balance_fen"] == OPENING["demo_wang"] + 400
    with opened(app) as connection:
        assert_books(connection)
        count = connection.execute(
            "SELECT COUNT(*) AS count FROM transactions WHERE kind = 'transfer'"
        ).fetchone()["count"]
        assert count == 1


def test_idempotency_conflict_does_not_apply_second_amount(client, app):
    headers = login(client)
    key = new_key()
    first = post_json(client, "/api/v1/deposits", headers, {"amount": "1.00"}, {"Idempotency-Key": key})
    second = post_json(client, "/api/v1/deposits", headers, {"amount": "2.00"}, {"Idempotency-Key": key})
    assert first.status_code == 200
    assert second.status_code == 409
    assert second.get_json()["error"]["code"] == "idempotency_conflict"
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"] + 100
    with opened(app) as connection:
        assert_books(connection)


def test_failed_withdrawal_does_not_consume_idempotency_key(client, app):
    headers = login(client)
    key = new_key()
    failed = post_json(client, "/api/v1/withdrawals", headers, {"amount": "99999.00"}, {"Idempotency-Key": key})
    assert failed.status_code == 400
    retried = post_json(client, "/api/v1/withdrawals", headers, {"amount": "1.00"}, {"Idempotency-Key": key})
    assert retried.status_code == 200, retried.get_data(as_text=True)
    assert retried.get_json()["replayed"] is False
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"] - 100
    with opened(app) as connection:
        assert_books(connection)


def test_idempotency_keys_are_isolated_per_user(app):
    key = new_key()
    zhang_client = app.test_client()
    li_client = app.test_client()
    zhang = login(zhang_client, "demo_zhang")
    li = login(li_client, "demo_li")
    first = post_json(zhang_client, "/api/v1/deposits", zhang, {"amount": "1.00"}, {"Idempotency-Key": key})
    second = post_json(li_client, "/api/v1/deposits", li, {"amount": "1.00"}, {"Idempotency-Key": key})
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.get_json()["replayed"] is False
    assert first.get_json()["transaction"]["transaction_id"] != second.get_json()["transaction"]["transaction_id"]
    assert account(zhang_client, zhang)["balance_fen"] == OPENING["demo_zhang"] + 100
    assert account(li_client, li)["balance_fen"] == OPENING["demo_li"] + 100
    with opened(app) as connection:
        assert_books(connection)


def test_concurrent_withdrawals_do_not_overdraft(app):
    with opened(app) as connection:
        user_id = connection.execute(
            "SELECT id FROM users WHERE username = 'demo_zhang'"
        ).fetchone()["id"]
    barrier = threading.Barrier(2)
    results = []
    lock = threading.Lock()

    def worker(key: str) -> None:
        local = connect(app.config["DATABASE"])
        try:
            barrier.wait(5)
            try:
                withdraw(local, user_id, OPENING["demo_zhang"], "", key, None)
                outcome = "ok"
            except BusinessError as exc:
                outcome = exc.code
        except Exception as exc:  # pragma: no cover - 失败时保留类型
            outcome = "unexpected:" + type(exc).__name__
        finally:
            local.close()
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=worker, args=(new_key(),)) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(10)
    assert sorted(results) == ["insufficient_funds", "ok"]
    with opened(app) as connection:
        assert_books(connection)
        balance = connection.execute(
            "SELECT balance_fen FROM accounts WHERE account_no = 'SIM-1001'"
        ).fetchone()["balance_fen"]
        assert balance == 0
        debits = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM ledger_entries AS l
            JOIN accounts AS a ON a.id = l.account_id
            WHERE a.account_no = 'SIM-1001' AND l.direction = 'debit'
            """
        ).fetchone()["count"]
        assert debits == 1
