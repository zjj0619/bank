"""Independent functional cases for the simulated ledger.

Each test is its own case. These are not slices of the earlier IT assertions.
The temporary database is the only ledger they touch.
"""

from __future__ import annotations

import re
import sqlite3
import threading
from urllib.parse import urlparse

import pytest

from app.db import connect
from app.errors import BusinessError
from app.money import MAX_FEN
from app.services import _update_balance, deposit, transfer
from tests.helpers import (
    OPENING,
    account,
    assert_books,
    assert_safe,
    history,
    login,
    new_key,
    opened,
    post_json,
)

pytestmark = [pytest.mark.integration, pytest.mark.functional]


def _hidden(html: str, name: str) -> str:
    match = re.search(rf'name="{name}" value="([^"]*)"', html)
    assert match, name
    return match.group(1)


def _yuan(fen: int) -> str:
    whole, cents = divmod(fen, 100)
    return f"{whole}.{cents:02d}"


def _user_id(connection, username: str) -> int:
    return int(connection.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()["id"])


def _balance_of(connection, account_no: str) -> int:
    return int(
        connection.execute("SELECT balance_fen FROM accounts WHERE account_no = ?", (account_no,)).fetchone()[
            "balance_fen"
        ]
    )


def _hash_of(connection, username: str) -> str:
    return connection.execute("SELECT password_hash FROM users WHERE username = ?", (username,)).fetchone()[
        "password_hash"
    ]


class _IdempotencyCollision:
    """Force the unique-key handler inside `_apply`.

    BEGIN IMMEDIATE normally lets the second writer see the committed key.
    This proxy raises IntegrityError on the idempotency insert so the
    recovery branches can be executed on purpose.
    """

    def __init__(self, inner, mode: str) -> None:
        self._inner = inner
        self._mode = mode
        self._saved = None

    def execute(self, sql, parameters=()):
        statement = sql if isinstance(sql, str) else str(sql)
        if "INSERT INTO idempotency_keys" in statement:
            self._saved = tuple(parameters)
            raise sqlite3.IntegrityError("UNIQUE constraint failed: idempotency_keys")
        if self._saved is not None and "FROM idempotency_keys" in statement:
            saved = self._saved
            self._saved = None
            if self._mode == "match":
                self._inner.execute(
                    """
                    INSERT INTO idempotency_keys
                        (user_id, idem_key, request_hash, response_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    saved,
                )
            elif self._mode == "mismatch":
                user_id, idem_key, _digest, response_json, created_at = saved
                self._inner.execute(
                    """
                    INSERT INTO idempotency_keys
                        (user_id, idem_key, request_hash, response_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, idem_key, "f" * 64, response_json, created_at),
                )
        return self._inner.execute(statement, parameters)

    def __getattr__(self, name):
        return getattr(self._inner, name)


def _run_pair(app, worker) -> list[str]:
    barrier = threading.Barrier(2)
    results: list[str] = []
    lock = threading.Lock()

    def run(slot: int) -> None:
        try:
            barrier.wait(5)
            outcome = worker(slot)
        except Exception as exc:  # pragma: no cover - kept so a hang is visible
            outcome = "unexpected:" + type(exc).__name__
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=run, args=(slot,)) for slot in (0, 1)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(15)
        assert not thread.is_alive()
    return results


def test_note_of_100_characters_is_stored(client, app):
    headers = login(client)
    note = "N" * 100
    response = post_json(client, "/api/v1/deposits", headers, {"amount": "0.01", "note": note})
    assert response.status_code == 200, response.get_data(as_text=True)
    assert any(item["note"] == note for item in history(client, headers))
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"] + 1
    with opened(app) as connection:
        assert_books(connection)


def test_note_of_101_characters_is_rejected(client, app):
    headers = login(client)
    before = account(client, headers)["balance_fen"]
    response = post_json(client, "/api/v1/deposits", headers, {"amount": "0.01", "note": "N" * 101})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_note"
    assert "100" in response.get_json()["error"]["message"]
    assert account(client, headers)["balance_fen"] == before
    with opened(app) as connection:
        assert_books(connection)
        count = connection.execute("SELECT COUNT(*) AS count FROM transactions WHERE kind = 'deposit'").fetchone()["count"]
        assert count == 0


def test_note_is_trimmed_to_100_characters(client, app):
    headers = login(client)
    note = "  " + ("T" * 100) + "  "
    response = post_json(client, "/api/v1/deposits", headers, {"amount": "0.02", "note": note})
    assert response.status_code == 200, response.get_data(as_text=True)
    assert any(item["note"] == "T" * 100 for item in history(client, headers))
    with opened(app) as connection:
        assert_books(connection)


def test_note_drops_null_bytes(client):
    headers = login(client)
    response = post_json(client, "/api/v1/deposits", headers, {"amount": "0.03", "note": "alpha\x00beta"})
    assert response.status_code == 200, response.get_data(as_text=True)
    assert any(item["note"] == "alphabeta" for item in history(client, headers))


def test_missing_note_is_stored_empty(client):
    headers = login(client)
    response = post_json(client, "/api/v1/deposits", headers, {"amount": "0.04", "note": None})
    assert response.status_code == 200, response.get_data(as_text=True)
    deposits = [item for item in history(client, headers) if item["kind"] == "deposit"]
    assert deposits and deposits[0]["note"] == ""


def test_non_text_note_is_rejected(client):
    headers = login(client)
    before = account(client, headers)["balance_fen"]
    response = post_json(client, "/api/v1/deposits", headers, {"amount": "0.05", "note": 12})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_note"
    assert account(client, headers)["balance_fen"] == before


def test_idempotency_key_of_8_characters_is_accepted(client):
    headers = login(client)
    response = post_json(
        client, "/api/v1/deposits", headers, {"amount": "0.06"}, {"Idempotency-Key": "abcd1234"}
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.get_json()["replayed"] is False
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"] + 6


def test_idempotency_key_of_80_characters_is_accepted(client):
    headers = login(client)
    response = post_json(client, "/api/v1/deposits", headers, {"amount": "0.07"}, {"Idempotency-Key": "k" * 80})
    assert response.status_code == 200, response.get_data(as_text=True)
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"] + 7


def test_idempotency_key_of_7_characters_is_rejected(client):
    headers = login(client)
    before = account(client, headers)["balance_fen"]
    response = post_json(client, "/api/v1/deposits", headers, {"amount": "1.00"}, {"Idempotency-Key": "abc1234"})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "idempotency_key_required"
    assert account(client, headers)["balance_fen"] == before


def test_idempotency_key_of_81_characters_is_rejected(client):
    headers = login(client)
    response = post_json(client, "/api/v1/withdrawals", headers, {"amount": "1.00"}, {"Idempotency-Key": "k" * 81})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "idempotency_key_required"
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"]


def test_idempotency_key_with_a_space_is_rejected(client):
    headers = login(client)
    response = post_json(
        client, "/api/v1/transfers", headers, {"amount": "1.00", "to_account_no": "SIM-1002"}, {"Idempotency-Key": "bad key!"}
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "idempotency_key_required"
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"]


def test_missing_idempotency_key_is_rejected(client):
    headers = login(client)
    response = client.post("/api/v1/deposits", json={"amount": "1.00"}, headers=headers)
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "idempotency_key_required"
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"]


def test_idempotency_key_in_json_body_posts_a_withdrawal(client, app):
    headers = login(client)
    key = new_key()
    response = client.post(
        "/api/v1/withdrawals",
        json={"amount": "1.25", "idempotency_key": key, "note": "body key"},
        headers=headers,
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.get_json()["replayed"] is False
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"] - 125
    with opened(app) as connection:
        assert_books(connection)


def test_replayed_withdrawal_does_not_debit_twice(client, app):
    headers = login(client)
    key = new_key()
    payload = {"amount": "2.00", "note": "once"}
    first = post_json(client, "/api/v1/withdrawals", headers, payload, {"Idempotency-Key": key})
    second = post_json(client, "/api/v1/withdrawals", headers, dict(payload), {"Idempotency-Key": key})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.get_json()["replayed"] is False
    assert second.get_json()["replayed"] is True
    assert first.get_json()["transaction"]["transaction_id"] == second.get_json()["transaction"]["transaction_id"]
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"] - 200
    with opened(app) as connection:
        assert_books(connection)
        count = connection.execute("SELECT COUNT(*) AS count FROM transactions WHERE kind = 'withdrawal'").fetchone()["count"]
        assert count == 1


def test_failed_transfer_does_not_consume_idempotency_key(client, app):
    headers = login(client)
    key = new_key()
    failed = post_json(
        client,
        "/api/v1/transfers",
        headers,
        {"amount": "1.00", "to_account_no": "SIM-9999"},
        {"Idempotency-Key": key},
    )
    assert failed.status_code == 404
    assert failed.get_json()["error"]["code"] == "recipient_not_found"
    posted = post_json(
        client,
        "/api/v1/transfers",
        headers,
        {"amount": "1.00", "to_account_no": "SIM-1002"},
        {"Idempotency-Key": key},
    )
    assert posted.status_code == 200, posted.get_data(as_text=True)
    assert posted.get_json()["replayed"] is False
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"] - 100
    with opened(app) as connection:
        assert_books(connection)


def test_transfer_rejected_when_receiver_balance_would_exceed_cap(app):
    li_client = app.test_client()
    zhang_client = app.test_client()
    li = login(li_client, "demo_li")
    zhang = login(zhang_client, "demo_zhang")
    gap = MAX_FEN - OPENING["demo_li"]
    filled = post_json(li_client, "/api/v1/deposits", li, {"amount": _yuan(gap)})
    assert filled.status_code == 200, filled.get_data(as_text=True)
    assert account(li_client, li)["balance_fen"] == MAX_FEN
    rejected = post_json(zhang_client, "/api/v1/transfers", zhang, {"amount": "0.01", "to_account_no": "SIM-1002"})
    assert rejected.status_code == 400
    assert rejected.get_json()["error"]["code"] == "amount_overflow"
    assert "receiving balance" in rejected.get_json()["error"]["message"]
    assert account(zhang_client, zhang)["balance_fen"] == OPENING["demo_zhang"]
    assert account(li_client, li)["balance_fen"] == MAX_FEN
    with opened(app) as connection:
        assert_books(connection)


def test_transfer_that_lands_receiver_on_cap_succeeds(app):
    li_client = app.test_client()
    zhang_client = app.test_client()
    li = login(li_client, "demo_li")
    zhang = login(zhang_client, "demo_zhang")
    gap = MAX_FEN - OPENING["demo_li"] - 100
    filled = post_json(li_client, "/api/v1/deposits", li, {"amount": _yuan(gap)})
    assert filled.status_code == 200, filled.get_data(as_text=True)
    posted = post_json(zhang_client, "/api/v1/transfers", zhang, {"amount": "1.00", "to_account_no": "SIM-1002"})
    assert posted.status_code == 200, posted.get_data(as_text=True)
    assert account(li_client, li)["balance_fen"] == MAX_FEN
    assert account(zhang_client, zhang)["balance_fen"] == OPENING["demo_zhang"] - 100
    overflow = post_json(zhang_client, "/api/v1/transfers", zhang, {"amount": "0.01", "to_account_no": "SIM-1002"})
    assert overflow.status_code == 400
    assert overflow.get_json()["error"]["code"] == "amount_overflow"
    assert account(li_client, li)["balance_fen"] == MAX_FEN
    with opened(app) as connection:
        assert_books(connection)


def test_concurrent_transfers_of_full_balance_do_not_overspend(app):
    with opened(app) as connection:
        user_id = _user_id(connection, "demo_zhang")
    destinations = ("SIM-1002", "SIM-1003")
    keys = (new_key(), new_key())

    def worker(slot: int) -> str:
        local = connect(app.config["DATABASE"])
        try:
            transfer(local, user_id, OPENING["demo_zhang"], "full", keys[slot], destinations[slot])
            return "ok"
        except BusinessError as exc:
            return exc.code
        finally:
            local.close()

    assert sorted(_run_pair(app, worker)) == ["insufficient_funds", "ok"]
    with opened(app) as connection:
        assert_books(connection)
        balances = {
            "SIM-1001": _balance_of(connection, "SIM-1001"),
            "SIM-1002": _balance_of(connection, "SIM-1002"),
            "SIM-1003": _balance_of(connection, "SIM-1003"),
        }
        assert balances["SIM-1001"] == 0
        moved = [name for name in destinations if balances[name] != OPENING[{"SIM-1002": "demo_li", "SIM-1003": "demo_wang"}[name]]]
        assert len(moved) == 1
        assert sum(balances.values()) == sum(OPENING.values())
        count = connection.execute("SELECT COUNT(*) AS count FROM transactions WHERE kind = 'transfer'").fetchone()["count"]
        assert count == 1


def test_concurrent_transfers_from_two_senders_both_post(app):
    with opened(app) as connection:
        zhang_id = _user_id(connection, "demo_zhang")
        wang_id = _user_id(connection, "demo_wang")
    actors = ((zhang_id, 10_000, new_key()), (wang_id, 5_000, new_key()))

    def worker(slot: int) -> str:
        user_id, amount_fen, key = actors[slot]
        local = connect(app.config["DATABASE"])
        try:
            transfer(local, user_id, amount_fen, "together", key, "SIM-1002")
            return "ok"
        except BusinessError as exc:
            return exc.code
        finally:
            local.close()

    assert sorted(_run_pair(app, worker)) == ["ok", "ok"]
    with opened(app) as connection:
        assert_books(connection)
        assert _balance_of(connection, "SIM-1002") == OPENING["demo_li"] + 15_000
        assert _balance_of(connection, "SIM-1001") == OPENING["demo_zhang"] - 10_000
        assert _balance_of(connection, "SIM-1003") == OPENING["demo_wang"] - 5_000


def test_concurrent_same_key_deposits_post_once(app):
    with opened(app) as connection:
        user_id = _user_id(connection, "demo_zhang")
    shared = new_key()

    def worker(_slot: int) -> str:
        local = connect(app.config["DATABASE"])
        try:
            result = deposit(local, user_id, 100, "same key", shared)
            return "replayed" if result["replayed"] else "ok"
        except BusinessError as exc:
            return exc.code
        finally:
            local.close()

    assert sorted(_run_pair(app, worker)) == ["ok", "replayed"]
    with opened(app) as connection:
        assert_books(connection)
        assert _balance_of(connection, "SIM-1001") == OPENING["demo_zhang"] + 100
        count = connection.execute("SELECT COUNT(*) AS count FROM transactions WHERE kind = 'deposit'").fetchone()["count"]
        assert count == 1


def test_integrity_error_without_stored_key_returns_conflict(app):
    with opened(app) as connection:
        user_id = _user_id(connection, "demo_zhang")
        before = _balance_of(connection, "SIM-1001")
        proxy = _IdempotencyCollision(connection, "none")
        with pytest.raises(BusinessError) as caught:
            deposit(proxy, user_id, 100, "collision", new_key())
        assert caught.value.code == "conflict"
        assert caught.value.status == 409
        assert _balance_of(connection, "SIM-1001") == before
        assert_books(connection)


def test_integrity_error_with_matching_key_returns_replay(app):
    with opened(app) as connection:
        user_id = _user_id(connection, "demo_zhang")
        before = _balance_of(connection, "SIM-1001")
        proxy = _IdempotencyCollision(connection, "match")
        result = deposit(proxy, user_id, 250, "stored", new_key())
        assert result["replayed"] is True
        assert result["kind"] == "deposit"
        assert result["amount_fen"] == 250
        assert _balance_of(connection, "SIM-1001") == before
        stored = connection.execute("SELECT COUNT(*) AS count FROM idempotency_keys").fetchone()["count"]
        assert stored == 1
        assert_books(connection)


def test_integrity_error_with_different_fingerprint_conflicts(app):
    with opened(app) as connection:
        user_id = _user_id(connection, "demo_zhang")
        before = _balance_of(connection, "SIM-1001")
        proxy = _IdempotencyCollision(connection, "mismatch")
        with pytest.raises(BusinessError) as caught:
            deposit(proxy, user_id, 250, "other", new_key())
        assert caught.value.code == "idempotency_conflict"
        assert caught.value.status == 409
        assert _balance_of(connection, "SIM-1001") == before
        assert_books(connection)


def test_history_limit_one_returns_newest_entry(client):
    headers = login(client)
    assert post_json(client, "/api/v1/deposits", headers, {"amount": "0.08", "note": "newest"}).status_code == 200
    response = client.get("/api/v1/transactions?limit=1", headers=headers)
    body = response.get_json()
    assert response.status_code == 200
    assert body["count"] == 1
    assert body["transactions"][0]["note"] == "newest"
    assert body["transactions"][0]["kind"] == "deposit"


def test_history_offset_skips_newest_entry(client):
    headers = login(client)
    assert post_json(client, "/api/v1/deposits", headers, {"amount": "0.09", "note": "skip-me"}).status_code == 200
    response = client.get("/api/v1/transactions?limit=1&offset=1", headers=headers)
    body = response.get_json()
    assert response.status_code == 200
    assert body["count"] == 1
    assert body["transactions"][0]["kind"] == "opening"
    assert body["transactions"][0]["note"] != "skip-me"


def test_history_limit_above_100_is_rejected(client):
    headers = login(client)
    response = client.get("/api/v1/transactions?limit=101", headers=headers)
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_paging"


def test_history_offset_above_100000_is_rejected(client):
    headers = login(client)
    response = client.get("/api/v1/transactions?offset=100001", headers=headers)
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_paging"


def test_profile_returns_signed_in_user_only(app):
    client = app.test_client()
    headers = login(client, "demo_li")
    response = client.get("/api/v1/me?user_id=1&username=demo_zhang", headers=headers)
    body = response.get_json()
    assert response.status_code == 200
    assert body["user"] == {
        "username": "demo_li",
        "display_name": "Wanqing Li",
        "account_no": "SIM-1002",
    }
    assert "balance" not in body["user"]


def test_opening_activity_is_labeled_opening(client):
    headers = login(client)
    opening = next(item for item in history(client, headers) if item["kind"] == "opening")
    assert opening["kind_label"] == "Opening"
    assert opening["direction_label"] == "In"
    assert opening["amount"] == "10000.00"
    assert opening["counterparty_account_no"] is None


def test_transfer_activity_labels_direction(app):
    zhang_client = app.test_client()
    li_client = app.test_client()
    zhang = login(zhang_client, "demo_zhang")
    li = login(li_client, "demo_li")
    posted = post_json(
        zhang_client,
        "/api/v1/transfers",
        zhang,
        {"amount": "1.50", "to_account_no": "SIM-1002", "note": "labels"},
    )
    assert posted.status_code == 200, posted.get_data(as_text=True)
    outgoing = next(item for item in history(zhang_client, zhang) if item["kind"] == "transfer")
    incoming = next(item for item in history(li_client, li) if item["kind"] == "transfer")
    assert outgoing["kind_label"] == "Transfer out"
    assert outgoing["direction_label"] == "Out"
    assert outgoing["counterparty_account_no"] == "SIM-1002"
    assert incoming["kind_label"] == "Transfer in"
    assert incoming["direction_label"] == "In"
    assert incoming["counterparty_account_no"] == "SIM-1001"
    assert outgoing["note"] == incoming["note"] == "labels"


def test_one_decimal_amount_posts_whole_fen(client, app):
    headers = login(client)
    response = post_json(client, "/api/v1/deposits", headers, {"amount": "1.5"})
    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.get_json()["transaction"]["amount_fen"] == 150
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"] + 150
    with opened(app) as connection:
        assert_books(connection)


def test_leading_zero_amount_is_rejected(client):
    headers = login(client)
    response = post_json(client, "/api/v1/deposits", headers, {"amount": "01.00"})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_amount"
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"]


def test_amount_with_surrounding_spaces_is_accepted(client):
    headers = login(client)
    response = post_json(client, "/api/v1/withdrawals", headers, {"amount": " 2.50 "})
    assert response.status_code == 200, response.get_data(as_text=True)
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"] - 250


def test_account_number_with_surrounding_spaces_transfers(client, app):
    headers = login(client)
    response = post_json(client, "/api/v1/transfers", headers, {"amount": "0.02", "to_account_no": "  sim-1002  "})
    assert response.status_code == 200, response.get_data(as_text=True)
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"] - 2
    with opened(app) as connection:
        assert _balance_of(connection, "SIM-1002") == OPENING["demo_li"] + 2
        assert_books(connection)


def test_non_string_recipient_is_rejected(client):
    headers = login(client)
    response = post_json(client, "/api/v1/transfers", headers, {"amount": "1.00", "to_account_no": 1002})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_recipient"
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"]


def test_signed_out_deposit_page_redirects_to_sign_in(client):
    response = client.get("/deposit")
    assert response.status_code == 302
    assert urlparse(response.headers["Location"]).path == "/login"


def test_signed_out_activity_page_redirects_to_sign_in(client):
    response = client.get("/history")
    assert response.status_code == 302
    assert urlparse(response.headers["Location"]).path == "/login"


def test_signed_in_user_is_sent_from_sign_in_to_overview(client):
    login(client)
    response = client.get("/login")
    assert response.status_code == 302
    assert urlparse(response.headers["Location"]).path == "/"


def test_web_withdrawal_over_balance_stays_on_the_form(client):
    login(client)
    page = client.get("/withdraw")
    html = page.get_data(as_text=True)
    response = client.post(
        "/withdraw",
        data={
            "csrf_token": _hidden(html, "csrf_token"),
            "idempotency_key": _hidden(html, "idempotency_key"),
            "amount": "10000.01",
            "note": "too much",
        },
    )
    body = response.get_data(as_text=True)
    assert response.status_code == 400
    assert "not sufficient" in body.lower()
    assert "Withdraw" in body
    assert client.get("/api/v1/account").get_json()["account"]["balance_fen"] == OPENING["demo_zhang"]


def test_web_transfer_to_unknown_account_stays_on_the_form(client):
    login(client)
    page = client.get("/transfer")
    html = page.get_data(as_text=True)
    response = client.post(
        "/transfer",
        data={
            "csrf_token": _hidden(html, "csrf_token"),
            "idempotency_key": _hidden(html, "idempotency_key"),
            "amount": "1.00",
            "to_account_no": "SIM-9999",
            "note": "missing",
        },
    )
    body = response.get_data(as_text=True)
    assert response.status_code == 404
    assert "does not exist" in body
    assert "Transfer" in body
    assert client.get("/api/v1/account").get_json()["account"]["balance_fen"] == OPENING["demo_zhang"]


def test_web_passphrase_mismatch_does_not_change_the_hash(client, app):
    login(client)
    with opened(app) as connection:
        before = _hash_of(connection, "demo_zhang")
    page = client.get("/password")
    html = page.get_data(as_text=True)
    response = client.post(
        "/password",
        data={
            "csrf_token": _hidden(html, "csrf_token"),
            "current_password": "Not-Used-Because-Mismatch-9!",
            "new_password": "First-Choice-Value-9!",
            "confirm_password": "Second-Choice-Value-9!",
        },
    )
    assert response.status_code == 400
    assert "do not match" in response.get_data(as_text=True)
    with opened(app) as connection:
        assert _hash_of(connection, "demo_zhang") == before


def test_sign_out_without_csrf_keeps_the_session(client):
    login(client)
    response = client.post("/logout", data={})
    assert response.status_code == 403
    assert "security check failed" in response.get_data(as_text=True).lower()
    home = client.get("/")
    assert home.status_code == 200
    assert 'data-balance-fen="1000000"' in home.get_data(as_text=True)


def test_dashboard_shows_posted_balance_line_after_a_second_entry(client):
    login(client)
    before = client.get("/")
    assert before.status_code == 200
    assert 'id="spark-title"' not in before.get_data(as_text=True)
    page = client.get("/deposit")
    html = page.get_data(as_text=True)
    posted = client.post(
        "/deposit",
        data={
            "csrf_token": _hidden(html, "csrf_token"),
            "idempotency_key": _hidden(html, "idempotency_key"),
            "amount": "1.00",
            "note": "second point",
        },
        follow_redirects=True,
    )
    overview = posted.get_data(as_text=True)
    assert "Deposit recorded" in overview
    assert 'id="spark-title"' in overview
    assert "<polyline" in overview


def test_wrong_csrf_token_rejects_a_deposit(client):
    headers = login(client)
    response = post_json(
        client,
        "/api/v1/deposits",
        headers,
        {"amount": "1.00"},
        {"X-CSRF-Token": "not-the-token"},
    )
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "csrf_failed"
    assert account(client, headers)["balance_fen"] == OPENING["demo_zhang"]


def test_username_longer_than_64_characters_does_not_sign_in(client):
    token = client.get("/api/v1/csrf").get_json()["csrf_token"]
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "u" * 65, "password": "Not-A-Session-9!"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "login_failed"
    assert_safe(response)
    assert client.get("/api/v1/account").status_code == 401


def test_non_string_password_does_not_sign_in(client):
    token = client.get("/api/v1/csrf").get_json()["csrf_token"]
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "demo_zhang", "password": 12345},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "login_failed"
    assert_safe(response)
    assert client.get("/api/v1/account").status_code == 401


def test_wrong_current_passphrase_keeps_the_hash(client, app):
    headers = login(client)
    with opened(app) as connection:
        before = _hash_of(connection, "demo_zhang")
    response = client.post(
        "/api/v1/auth/password",
        json={"current_password": "Not-The-Current-9!", "new_password": "Replacement-Value-9!"},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "login_failed"
    assert_safe(response)
    with opened(app) as connection:
        assert _hash_of(connection, "demo_zhang") == before


def test_security_headers_are_present_on_a_page(client):
    response = client.get("/login")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "same-origin"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Simulation"] == "simulated-bank-coursework-not-real-money"
    assert response.headers["Cache-Control"] == "no-store"


def test_transfer_chain_conserves_the_three_balances(app):
    zhang_client = app.test_client()
    li_client = app.test_client()
    wang_client = app.test_client()
    zhang = login(zhang_client, "demo_zhang")
    li = login(li_client, "demo_li")
    wang = login(wang_client, "demo_wang")
    assert post_json(zhang_client, "/api/v1/transfers", zhang, {"amount": "10.00", "to_account_no": "SIM-1002"}).status_code == 200
    assert post_json(li_client, "/api/v1/transfers", li, {"amount": "4.00", "to_account_no": "SIM-1003"}).status_code == 200
    assert post_json(wang_client, "/api/v1/transfers", wang, {"amount": "1.00", "to_account_no": "SIM-1001"}).status_code == 200
    assert account(zhang_client, zhang)["balance_fen"] == OPENING["demo_zhang"] - 1_000 + 100
    assert account(li_client, li)["balance_fen"] == OPENING["demo_li"] + 1_000 - 400
    assert account(wang_client, wang)["balance_fen"] == OPENING["demo_wang"] + 400 - 100
    assert (
        account(zhang_client, zhang)["balance_fen"]
        + account(li_client, li)["balance_fen"]
        + account(wang_client, wang)["balance_fen"]
        == sum(OPENING.values())
    )
    with opened(app) as connection:
        assert_books(connection)


def test_unicode_note_respects_the_100_character_limit(client):
    headers = login(client)
    accepted = post_json(client, "/api/v1/deposits", headers, {"amount": "0.11", "note": "字" * 100})
    assert accepted.status_code == 200, accepted.get_data(as_text=True)
    assert any(item["note"] == "字" * 100 for item in history(client, headers))
    rejected = post_json(client, "/api/v1/deposits", headers, {"amount": "0.11", "note": "字" * 101})
    assert rejected.status_code == 400
    assert rejected.get_json()["error"]["code"] == "invalid_note"
    deposits = [item for item in history(client, headers) if item["kind"] == "deposit"]
    assert len(deposits) == 1


def test_stale_balance_guard_rejects_the_update(app):
    with opened(app) as connection:
        row = connection.execute("SELECT id, balance_fen FROM accounts WHERE account_no = 'SIM-1001'").fetchone()
        before = int(row["balance_fen"])
        with pytest.raises(BusinessError) as caught:
            _update_balance(connection, int(row["id"]), before + 5, before - 1)
        assert caught.value.code == "conflict"
        assert caught.value.status == 409
        assert _balance_of(connection, "SIM-1001") == before
        assert_books(connection)


def test_balance_guard_rejects_an_out_of_range_result(app):
    with opened(app) as connection:
        row = connection.execute("SELECT id, balance_fen FROM accounts WHERE account_no = 'SIM-1001'").fetchone()
        before = int(row["balance_fen"])
        with pytest.raises(BusinessError) as high:
            _update_balance(connection, int(row["id"]), before, MAX_FEN + 1)
        assert high.value.code == "amount_overflow"
        with pytest.raises(BusinessError) as low:
            _update_balance(connection, int(row["id"]), before, -1)
        assert low.value.code == "amount_overflow"
        assert _balance_of(connection, "SIM-1001") == before
        assert_books(connection)
