"""账户、分录和幂等写操作。余额变更只发生在立即事务里。"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from flask import current_app

from app.db import immediate_transaction
from app.errors import BusinessError
from app.money import MAX_FEN, format_fen
from app.passwords import dummy_hash, hash_password, needs_rehash, validate_password, verify_password
from app.secrets import resolve_seed_passwords
from app.seed_data import DEMO_ACCOUNTS

_NOTE_LIMIT = 100
_IDEMPOTENCY = re.compile(r"^[A-Za-z0-9_-]{8,80}$")
_ACCOUNT_NO = re.compile(r"^SIM-\d{4}$")

KIND_LABELS = {
    ("opening", "credit"): "Opening",
    ("deposit", "credit"): "Deposit",
    ("withdrawal", "debit"): "Withdrawal",
    ("transfer", "debit"): "Transfer out",
    ("transfer", "credit"): "Transfer in",
}


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clean_note(note: object) -> str:
    if note is None:
        return ""
    if not isinstance(note, str):
        raise BusinessError("invalid_note", "The note must be text.")
    cleaned = note.replace("\x00", "").strip()
    if len(cleaned) > _NOTE_LIMIT:
        raise BusinessError("invalid_note", "The note cannot exceed 100 characters.")
    return cleaned


def clean_idempotency_key(value: object) -> str:
    if not isinstance(value, str) or _IDEMPOTENCY.fullmatch(value.strip()) is None:
        raise BusinessError(
            "idempotency_key_required",
            "Provide an Idempotency-Key of 8 to 80 letters, digits, underscores, or hyphens.",
        )
    return value.strip()


def normalize_account_no(value: object) -> str:
    if not isinstance(value, str):
        raise BusinessError("invalid_recipient", "Enter a simulated account such as SIM-1002.")
    text = value.strip().upper()
    if _ACCOUNT_NO.fullmatch(text) is None:
        raise BusinessError("invalid_recipient", "That account number is not in the right form. Simulated accounts look like SIM-1002.")
    return text


def authenticate(connection: sqlite3.Connection, username: object, password: object):
    supplied = password if isinstance(password, str) else ""
    if not isinstance(username, str) or not isinstance(password, str):
        verify_password(dummy_hash(), "invalid-type")
        return None
    username = username.strip()
    if not username or not supplied or len(username) > 64 or len(supplied) > 128:
        verify_password(dummy_hash(), supplied or "empty")
        return None
    with immediate_transaction(connection):
        row = connection.execute(
            """
            SELECT id, username, display_name, password_hash, failed_attempts,
                   locked_until, password_changed_at
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()
        if row is None:
            verify_password(dummy_hash(), supplied)
            return None
        if _is_locked(row["locked_until"]):
            verify_password(row["password_hash"], supplied)
            return None
        if not verify_password(row["password_hash"], supplied):
            _register_failure(connection, row)
            return None
        stored = row["password_hash"]
        if needs_rehash(stored):
            stored = hash_password(supplied)
        connection.execute(
            """
            UPDATE users
            SET failed_attempts = 0, locked_until = NULL, password_hash = ?
            WHERE id = ?
            """,
            (stored, row["id"]),
        )
        return row


def change_password(connection: sqlite3.Connection, user_id: int, current: object, new: object) -> str:
    if not isinstance(current, str) or not isinstance(new, str):
        verify_password(dummy_hash(), "invalid-type")
        raise BusinessError("login_failed", "The current passphrase is not correct.")
    with immediate_transaction(connection):
        row = connection.execute(
            """
            SELECT id, username, display_name, password_hash, password_changed_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
        account = connection.execute(
            "SELECT account_no FROM accounts WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row is None or not verify_password(row["password_hash"], current):
            verify_password(dummy_hash(), current if isinstance(current, str) else "empty")
            raise BusinessError("login_failed", "The current passphrase is not correct.")
        validate_password(
            new,
            row["username"],
            row["display_name"],
            account["account_no"] if account else "",
        )
        if verify_password(row["password_hash"], new):
            raise BusinessError("weak_password", "Choose a different passphrase.")
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if stamp == row["password_changed_at"]:
            stamp = (datetime.now(timezone.utc) + timedelta(microseconds=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        connection.execute(
            """
            UPDATE users
            SET password_hash = ?, password_changed_at = ?, failed_attempts = 0, locked_until = NULL
            WHERE id = ?
            """,
            (hash_password(new), stamp, user_id),
        )
        return stamp


def _is_locked(locked_until: str | None) -> bool:
    return bool(locked_until) and locked_until > utcnow()


def _register_failure(connection: sqlite3.Connection, row) -> None:
    threshold = int(current_app.config.get("LOCKOUT_THRESHOLD", 5))
    seconds = int(current_app.config.get("LOCKOUT_SECONDS", 900))
    attempts = int(row["failed_attempts"] or 0) + 1
    locked_until = None
    if attempts >= threshold:
        locked_until = (datetime.now(timezone.utc) + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
        attempts = threshold
    connection.execute(
        "UPDATE users SET failed_attempts = ?, locked_until = ? WHERE id = ?",
        (attempts, locked_until, row["id"]),
    )


def seed_demo_accounts(connection: sqlite3.Connection) -> None:
    existing = connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
    if existing:
        return
    passwords = resolve_seed_passwords(tuple(item["username"] for item in DEMO_ACCOUNTS))
    created_at = utcnow()
    hashes = {}
    for item in DEMO_ACCOUNTS:
        secret = validate_password(
            passwords[item["username"]],
            item["username"],
            item["display_name"],
            item["account_no"],
        )
        hashes[item["username"]] = hash_password(secret)
    with immediate_transaction(connection):
        again = connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
        if again:
            return
        for item in DEMO_ACCOUNTS:
            user_cursor = connection.execute(
                """
                INSERT INTO users (
                    username, display_name, password_hash, failed_attempts,
                    locked_until, password_changed_at, created_at
                ) VALUES (?, ?, ?, 0, NULL, ?, ?)
                """,
                (item["username"], item["display_name"], hashes[item["username"]], created_at, created_at),
            )
            user_id = int(user_cursor.lastrowid)
            account_cursor = connection.execute(
                """
                INSERT INTO accounts (user_id, account_no, balance_fen, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, item["account_no"], item["opening_fen"], created_at),
            )
            account_id = int(account_cursor.lastrowid)
            _insert_transaction(
                connection,
                kind="opening",
                amount_fen=int(item["opening_fen"]),
                actor_user_id=user_id,
                source_account_id=None,
                destination_account_id=account_id,
                note="Opening balance for the simulation",
                created_at=created_at,
                entries=(
                    {
                        "account_id": account_id,
                        "direction": "credit",
                        "amount_fen": int(item["opening_fen"]),
                        "balance_after_fen": int(item["opening_fen"]),
                    },
                ),
            )


def get_account_for_user(connection: sqlite3.Connection, user_id: int) -> sqlite3.Row:
    row = connection.execute(
        """
        SELECT a.id, a.user_id, a.account_no, a.balance_fen, u.username, u.display_name
        FROM accounts AS a
        JOIN users AS u ON u.id = a.user_id
        WHERE a.user_id = ?
        """,
        (user_id,),
    ).fetchone()
    if row is None:
        raise BusinessError("account_missing", "The account does not exist.", 404)
    return row


def account_payload(row: sqlite3.Row) -> dict:
    balance = int(row["balance_fen"])
    return {
        "simulation": True,
        "username": row["username"],
        "display_name": row["display_name"],
        "account_no": row["account_no"],
        "currency": "CNY",
        "balance": format_fen(balance),
        "balance_display": format_fen(balance, grouping=True),
        "balance_fen": balance,
        "minor_unit": "fen",
    }


def list_history(connection: sqlite3.Connection, user_id: int, limit: int, offset: int) -> dict:
    account = get_account_for_user(connection, user_id)
    rows = connection.execute(
        """
        SELECT
            t.public_id,
            t.kind,
            t.note,
            t.created_at,
            l.direction,
            l.amount_fen AS entry_amount,
            l.balance_after_fen,
            src.account_no AS source_no,
            dst.account_no AS dest_no,
            su.display_name AS source_name,
            du.display_name AS dest_name
        FROM ledger_entries AS l
        JOIN transactions AS t ON t.id = l.transaction_id
        LEFT JOIN accounts AS src ON src.id = t.source_account_id
        LEFT JOIN accounts AS dst ON dst.id = t.destination_account_id
        LEFT JOIN users AS su ON su.id = src.user_id
        LEFT JOIN users AS du ON du.id = dst.user_id
        WHERE l.account_id = ?
        ORDER BY l.id DESC
        LIMIT ? OFFSET ?
        """,
        (account["id"], limit, offset),
    ).fetchall()
    items = [_history_item(row) for row in rows]
    return {
        "simulation": True,
        "account_no": account["account_no"],
        "limit": limit,
        "offset": offset,
        "count": len(items),
        "transactions": items,
    }


def deposit(connection, user_id, amount_fen, note, idem_key, fault_point=None) -> dict:
    return _apply(
        connection,
        user_id=user_id,
        kind="deposit",
        amount_fen=amount_fen,
        note=note,
        idem_key=idem_key,
        to_account_no=None,
        fault_point=fault_point,
    )


def withdraw(connection, user_id, amount_fen, note, idem_key, fault_point=None) -> dict:
    return _apply(
        connection,
        user_id=user_id,
        kind="withdrawal",
        amount_fen=amount_fen,
        note=note,
        idem_key=idem_key,
        to_account_no=None,
        fault_point=fault_point,
    )


def transfer(connection, user_id, amount_fen, note, idem_key, to_account_no, fault_point=None) -> dict:
    return _apply(
        connection,
        user_id=user_id,
        kind="transfer",
        amount_fen=amount_fen,
        note=note,
        idem_key=idem_key,
        to_account_no=to_account_no,
        fault_point=fault_point,
    )


def _apply(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    kind: str,
    amount_fen: int,
    note: str,
    idem_key: str,
    to_account_no: str | None,
    fault_point: str | None,
) -> dict:
    if isinstance(amount_fen, bool) or not isinstance(amount_fen, int) or amount_fen <= 0:
        raise BusinessError("non_positive_amount", "The amount must be greater than 0.")
    if amount_fen > MAX_FEN:
        raise BusinessError("amount_overflow", "The amount is outside the allowed range.")
    note = clean_note(note)
    idem_key = clean_idempotency_key(idem_key)
    destination = normalize_account_no(to_account_no) if kind == "transfer" else ""
    fingerprint = _fingerprint(kind, amount_fen, destination, note)
    try:
        with immediate_transaction(connection):
            existing = connection.execute(
                """
                SELECT request_hash, response_json
                FROM idempotency_keys
                WHERE user_id = ? AND idem_key = ?
                """,
                (user_id, idem_key),
            ).fetchone()
            if existing is not None:
                if existing["request_hash"] != fingerprint:
                    raise BusinessError("idempotency_conflict", "That idempotency key was already used for a different request.", 409)
                payload = json.loads(existing["response_json"])
                payload["replayed"] = True
                return payload

            account = connection.execute(
                """
                SELECT id, user_id, account_no, balance_fen
                FROM accounts
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            if account is None:
                raise BusinessError("account_missing", "The account does not exist.", 404)

            created_at = utcnow()
            if kind == "deposit":
                result, entries, source_id, dest_id = _plan_deposit(connection, account, amount_fen)
            elif kind == "withdrawal":
                result, entries, source_id, dest_id = _plan_withdrawal(connection, account, amount_fen)
            elif kind == "transfer":
                result, entries, source_id, dest_id = _plan_transfer(
                    connection, account, amount_fen, destination
                )
            else:
                raise BusinessError("invalid_amount", "That transaction type is not supported.")

            public_id = _insert_transaction(
                connection,
                kind=kind,
                amount_fen=amount_fen,
                actor_user_id=user_id,
                source_account_id=source_id,
                destination_account_id=dest_id,
                note=note,
                created_at=created_at,
                entries=entries,
            )
            if fault_point == "after_write":
                raise RuntimeError("injected fault")
            result["transaction_id"] = public_id
            result["replayed"] = False
            result["created_at"] = created_at
            connection.execute(
                """
                INSERT INTO idempotency_keys
                    (user_id, idem_key, request_hash, response_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, idem_key, fingerprint, json.dumps(result, ensure_ascii=False), created_at),
            )
            return result
    except sqlite3.IntegrityError:
        existing = connection.execute(
            """
            SELECT request_hash, response_json
            FROM idempotency_keys
            WHERE user_id = ? AND idem_key = ?
            """,
            (user_id, idem_key),
        ).fetchone()
        if existing is None:
            raise BusinessError("conflict", "The account is busy with another update. Try again.", 409) from None
        if existing["request_hash"] != fingerprint:
            raise BusinessError("idempotency_conflict", "That idempotency key was already used for a different request.", 409) from None
        payload = json.loads(existing["response_json"])
        payload["replayed"] = True
        return payload


def _plan_deposit(connection, account, amount_fen: int):
    new_balance = int(account["balance_fen"]) + amount_fen
    if new_balance > MAX_FEN:
        raise BusinessError("amount_overflow", "The balance after this deposit would exceed the allowed range.")
    _update_balance(connection, int(account["id"]), int(account["balance_fen"]), new_balance)
    result = _movement_result("deposit", amount_fen, new_balance, None)
    entries = (
        {
            "account_id": int(account["id"]),
            "direction": "credit",
            "amount_fen": amount_fen,
            "balance_after_fen": new_balance,
        },
    )
    return result, entries, None, int(account["id"])


def _plan_withdrawal(connection, account, amount_fen: int):
    if int(account["balance_fen"]) < amount_fen:
        raise BusinessError("insufficient_funds", "The balance is not sufficient.")
    new_balance = int(account["balance_fen"]) - amount_fen
    _update_balance(connection, int(account["id"]), int(account["balance_fen"]), new_balance)
    result = _movement_result("withdrawal", amount_fen, new_balance, None)
    entries = (
        {
            "account_id": int(account["id"]),
            "direction": "debit",
            "amount_fen": amount_fen,
            "balance_after_fen": new_balance,
        },
    )
    return result, entries, int(account["id"]), None


def _plan_transfer(connection, account, amount_fen: int, destination_no: str):
    dest = connection.execute(
        """
        SELECT id, user_id, account_no, balance_fen
        FROM accounts
        WHERE account_no = ?
        """,
        (destination_no,),
    ).fetchone()
    if dest is None:
        raise BusinessError("recipient_not_found", "That simulated account does not exist.", 404)
    if int(dest["id"]) == int(account["id"]):
        raise BusinessError("self_transfer", "You cannot transfer to your own simulated account.")
    if int(account["balance_fen"]) < amount_fen:
        raise BusinessError("insufficient_funds", "The balance is not sufficient.")
    dest_balance = int(dest["balance_fen"]) + amount_fen
    if dest_balance > MAX_FEN:
        raise BusinessError("amount_overflow", "The receiving balance would exceed the allowed range.")
    sender_balance = int(account["balance_fen"]) - amount_fen
    first, second = sorted((account, dest), key=lambda row: int(row["id"]))
    for row, new_balance in (
        (first, sender_balance if int(first["id"]) == int(account["id"]) else dest_balance),
        (second, sender_balance if int(second["id"]) == int(account["id"]) else dest_balance),
    ):
        _update_balance(connection, int(row["id"]), int(row["balance_fen"]), new_balance)
    result = _movement_result("transfer", amount_fen, sender_balance, dest["account_no"])
    entries = (
        {
            "account_id": int(account["id"]),
            "direction": "debit",
            "amount_fen": amount_fen,
            "balance_after_fen": sender_balance,
        },
        {
            "account_id": int(dest["id"]),
            "direction": "credit",
            "amount_fen": amount_fen,
            "balance_after_fen": dest_balance,
        },
    )
    return result, entries, int(account["id"]), int(dest["id"])


def _update_balance(connection, account_id: int, expected: int, new_balance: int) -> None:
    if new_balance < 0 or new_balance > MAX_FEN:
        raise BusinessError("amount_overflow", "The balance would fall outside the allowed range.")
    cursor = connection.execute(
        """
        UPDATE accounts
        SET balance_fen = ?
        WHERE id = ? AND balance_fen = ?
        """,
        (new_balance, account_id, expected),
    )
    if cursor.rowcount != 1:
        raise BusinessError("conflict", "The account is busy with another update. Try again.", 409)


def _movement_result(kind: str, amount_fen: int, balance_fen: int, counterparty: str | None) -> dict:
    return {
        "simulation": True,
        "kind": kind,
        "amount": format_fen(amount_fen),
        "amount_fen": amount_fen,
        "balance": format_fen(balance_fen),
        "balance_display": format_fen(balance_fen, grouping=True),
        "balance_fen": balance_fen,
        "counterparty_account_no": counterparty,
    }


def _insert_transaction(
    connection,
    *,
    kind: str,
    amount_fen: int,
    actor_user_id: int,
    source_account_id: int | None,
    destination_account_id: int | None,
    note: str,
    created_at: str,
    entries: tuple[dict, ...],
) -> str:
    placeholder = "P" + secrets.token_hex(16)
    cursor = connection.execute(
        """
        INSERT INTO transactions (
            public_id, kind, amount_fen, actor_user_id,
            source_account_id, destination_account_id, note, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            placeholder,
            kind,
            amount_fen,
            actor_user_id,
            source_account_id,
            destination_account_id,
            note,
            created_at,
        ),
    )
    transaction_id = int(cursor.lastrowid)
    public_id = f"TXN{transaction_id:08d}"
    connection.execute(
        "UPDATE transactions SET public_id = ? WHERE id = ?",
        (public_id, transaction_id),
    )
    for entry in entries:
        connection.execute(
            """
            INSERT INTO ledger_entries (
                transaction_id, account_id, direction, amount_fen, balance_after_fen, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                transaction_id,
                entry["account_id"],
                entry["direction"],
                entry["amount_fen"],
                entry["balance_after_fen"],
                created_at,
            ),
        )
    return public_id


def _history_item(row: sqlite3.Row) -> dict:
    kind = row["kind"]
    direction = row["direction"]
    amount = int(row["entry_amount"])
    balance_after = int(row["balance_after_fen"])
    if kind == "transfer" and direction == "debit":
        counterparty_no = row["dest_no"]
        counterparty_name = row["dest_name"]
    elif kind == "transfer" and direction == "credit":
        counterparty_no = row["source_no"]
        counterparty_name = row["source_name"]
    else:
        counterparty_no = None
        counterparty_name = None
    return {
        "transaction_id": row["public_id"],
        "kind": kind,
        "kind_label": KIND_LABELS.get((kind, direction), kind),
        "direction": direction,
        "direction_label": "In" if direction == "credit" else "Out",
        "amount": format_fen(amount),
        "amount_display": format_fen(amount, grouping=True),
        "amount_fen": amount,
        "balance_after": format_fen(balance_after),
        "balance_after_display": format_fen(balance_after, grouping=True),
        "balance_after_fen": balance_after,
        "counterparty_account_no": counterparty_no,
        "counterparty_name": counterparty_name,
        "note": row["note"],
        "created_at": row["created_at"],
    }


def _fingerprint(kind: str, amount_fen: int, destination: str, note: str) -> str:
    raw = json.dumps(
        {
            "kind": kind,
            "amount_fen": amount_fen,
            "destination": destination,
            "note": note,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
