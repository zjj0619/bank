"""文档化的 JSON API。浏览器会话同样使用 CSRF。"""

from __future__ import annotations

import re
import secrets

from flask import Blueprint, current_app, jsonify, request, session

from app.db import get_db
from app.errors import BusinessError
from app.money import parse_amount_to_fen
from app.services import (
    account_payload,
    authenticate,
    change_password,
    clean_note,
    deposit,
    get_account_for_user,
    list_history,
    transfer,
    withdraw,
)
from app.webutil import establish_session, read_idempotency_key, require_csrf, require_user_id

api_bp = Blueprint("api", __name__)
_NONFINITE_BODY = re.compile(r"\b(?:NaN|Infinity|-Infinity)\b")


@api_bp.get("/health")
def health():
    return jsonify(ok=True, simulation=True, service="chengbu-sim-bank", version="1.0.0")


@api_bp.get("/csrf")
def csrf():
    from app.webutil import ensure_csrf

    return jsonify(ok=True, simulation=True, csrf_token=ensure_csrf())


@api_bp.post("/auth/login")
def login():
    require_csrf()
    data = _read_json_object()
    user = authenticate(get_db(), data.get("username"), data.get("password"))
    if user is None:
        raise BusinessError("login_failed", "The username or passphrase is not correct.", 401)
    token = establish_session(user)
    account = get_account_for_user(get_db(), int(user["id"]))
    return jsonify(
        ok=True,
        simulation=True,
        csrf_token=token,
        user={
            "username": account["username"],
            "display_name": account["display_name"],
            "account_no": account["account_no"],
        },
    )


@api_bp.post("/auth/password")
def password():
    require_csrf()
    user_id = require_user_id()
    data = _read_json_object()
    stamp = change_password(get_db(), user_id, data.get("current_password"), data.get("new_password"))
    session["pwd_stamp"] = stamp
    token = secrets.token_urlsafe(32)
    session["csrf_token"] = token
    return jsonify(ok=True, simulation=True, csrf_token=token)


@api_bp.post("/auth/logout")
def logout():
    require_csrf()
    require_user_id()
    session.clear()
    return jsonify(ok=True, simulation=True)


@api_bp.get("/me")
def me():
    user_id = require_user_id()
    account = get_account_for_user(get_db(), user_id)
    return jsonify(
        ok=True,
        simulation=True,
        user={
            "username": account["username"],
            "display_name": account["display_name"],
            "account_no": account["account_no"],
        },
    )


@api_bp.get("/account")
def account():
    user_id = require_user_id()
    row = get_account_for_user(get_db(), user_id)
    return jsonify(ok=True, account=account_payload(row))


@api_bp.get("/transactions")
def transactions():
    user_id = require_user_id()
    limit, offset = _paging()
    payload = list_history(get_db(), user_id, limit, offset)
    return jsonify(ok=True, **payload)


@api_bp.post("/deposits")
def deposits():
    return _movement("deposit")


@api_bp.post("/withdrawals")
def withdrawals():
    return _movement("withdrawal")


@api_bp.post("/transfers")
def transfers():
    return _movement("transfer")


def _movement(kind: str):
    require_csrf()
    user_id = require_user_id()
    data = _read_json_object()
    amount_fen = parse_amount_to_fen(data.get("amount"))
    note = clean_note(data.get("note", ""))
    idem_key = read_idempotency_key(data)
    fault_point = _fault_point()
    connection = get_db()
    if kind == "deposit":
        result = deposit(connection, user_id, amount_fen, note, idem_key, fault_point)
    elif kind == "withdrawal":
        result = withdraw(connection, user_id, amount_fen, note, idem_key, fault_point)
    else:
        result = transfer(
            connection,
            user_id,
            amount_fen,
            note,
            idem_key,
            data.get("to_account_no"),
            fault_point,
        )
    return jsonify(ok=True, replayed=result["replayed"], transaction=result)


def _fault_point() -> str | None:
    if not current_app.config.get("ALLOW_FAULT_INJECTION"):
        return None
    if request.headers.get("X-Test-Inject-Fault") == "after_write":
        return "after_write"
    return None


def _paging() -> tuple[int, int]:
    raw_limit = request.args.get("limit", "50")
    raw_offset = request.args.get("offset", "0")
    if not str(raw_limit).isdigit() or not str(raw_offset).isdigit():
        raise BusinessError("invalid_paging", "The paging values are not valid.")
    limit = int(raw_limit)
    offset = int(raw_offset)
    if limit < 1 or limit > 100 or offset < 0 or offset > 100_000:
        raise BusinessError("invalid_paging", "The paging values are out of range.")
    return limit, offset


def _read_json_object() -> dict:
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        return data
    raw = request.get_data(as_text=True) or ""
    if _NONFINITE_BODY.search(raw):
        raise BusinessError("nonfinite_amount", "The amount must be a finite number.")
    raise BusinessError("invalid_json", "The request body must be a JSON object.")
