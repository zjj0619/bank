"""SQLite 连接、表结构和立即事务。金额列全部是整数分。"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

import click
from flask import current_app, g

SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        display_name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        failed_attempts INTEGER NOT NULL DEFAULT 0,
        locked_until TEXT,
        password_changed_at TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
        account_no TEXT NOT NULL UNIQUE,
        balance_fen INTEGER NOT NULL CHECK (balance_fen >= 0),
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY,
        public_id TEXT NOT NULL UNIQUE,
        kind TEXT NOT NULL CHECK (kind IN ('opening', 'deposit', 'withdrawal', 'transfer')),
        amount_fen INTEGER NOT NULL CHECK (amount_fen > 0),
        actor_user_id INTEGER NOT NULL REFERENCES users(id),
        source_account_id INTEGER REFERENCES accounts(id),
        destination_account_id INTEGER REFERENCES accounts(id),
        note TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ledger_entries (
        id INTEGER PRIMARY KEY,
        transaction_id INTEGER NOT NULL REFERENCES transactions(id),
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        direction TEXT NOT NULL CHECK (direction IN ('credit', 'debit')),
        amount_fen INTEGER NOT NULL CHECK (amount_fen > 0),
        balance_after_fen INTEGER NOT NULL CHECK (balance_after_fen >= 0),
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS idempotency_keys (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        idem_key TEXT NOT NULL,
        request_hash TEXT NOT NULL,
        response_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE (user_id, idem_key)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_ledger_account_id
        ON ledger_entries (account_id, id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_transactions_actor
        ON transactions (actor_user_id, id)
    """,
    """
    CREATE VIEW IF NOT EXISTS account_ledger_totals AS
    SELECT
        a.id AS account_id,
        a.account_no AS account_no,
        a.balance_fen AS balance_fen,
        COALESCE(SUM(
            CASE WHEN l.direction = 'credit' THEN l.amount_fen ELSE -l.amount_fen END
        ), 0) AS ledger_fen
    FROM accounts AS a
    LEFT JOIN ledger_entries AS l ON l.account_id = a.id
    GROUP BY a.id, a.account_no, a.balance_fen
    """,
)


def connect(path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=15, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 8000")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def get_db() -> sqlite3.Connection:
    connection = g.get("db")
    if connection is None:
        connection = connect(current_app.config["DATABASE"])
        g.db = connection
    return connection


def close_db(_error: BaseException | None = None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


@contextmanager
def immediate_transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """BEGIN IMMEDIATE 取得预留锁，写完再提交。任何异常都回滚。"""

    connection.execute("BEGIN IMMEDIATE")
    try:
        yield connection
        connection.execute("COMMIT")
    except Exception:
        try:
            connection.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise


def apply_schema(connection: sqlite3.Connection) -> None:
    for statement in SCHEMA_STATEMENTS:
        connection.execute(statement)
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)")}
    if "failed_attempts" not in columns:
        connection.execute("ALTER TABLE users ADD COLUMN failed_attempts INTEGER NOT NULL DEFAULT 0")
    if "locked_until" not in columns:
        connection.execute("ALTER TABLE users ADD COLUMN locked_until TEXT")
    if "password_changed_at" not in columns:
        connection.execute("ALTER TABLE users ADD COLUMN password_changed_at TEXT")
        connection.execute(
            "UPDATE users SET password_changed_at = created_at WHERE password_changed_at IS NULL"
        )


def init_db(seed: bool = True) -> None:
    connection = get_db()
    apply_schema(connection)
    if seed:
        from app.services import seed_demo_accounts

        seed_demo_accounts(connection)


@click.command("init-db")
def init_db_command() -> None:
    init_db(seed=True)
    click.echo("Initialized the simulated database.")


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
