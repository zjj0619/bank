"""会话与 CSRF。状态变更接口在 Cookie 认证下必须校验 CSRF。"""

from __future__ import annotations

import hmac
import secrets

from flask import request, session

from app.errors import BusinessError
from app.services import clean_idempotency_key


def ensure_csrf() -> str:
    token = session.get("csrf_token")
    if not isinstance(token, str) or not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def require_csrf() -> None:
    expected = session.get("csrf_token")
    presented = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token") or ""
    if (
        not isinstance(expected, str)
        or not expected
        or not isinstance(presented, str)
        or not presented
        or not hmac.compare_digest(expected, presented)
    ):
        raise BusinessError("csrf_failed", "The security check failed. Refresh the page and try again.", 403)


def session_user_id() -> int | None:
    user_id = session.get("user_id")
    stamp = session.get("pwd_stamp")
    if not isinstance(user_id, int):
        return None
    if not isinstance(stamp, str) or not stamp:
        session.clear()
        return None
    from app.db import get_db

    row = get_db().execute(
        "SELECT password_changed_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if row is None or row["password_changed_at"] != stamp:
        session.clear()
        return None
    return user_id


def require_user_id() -> int:
    user_id = session_user_id()
    if user_id is None:
        raise BusinessError("auth_required", "Sign in to continue.", 401)
    return user_id


def establish_session(user) -> str:
    stamp = user["password_changed_at"]
    if not isinstance(stamp, str) or not stamp:
        raise BusinessError("auth_required", "Sign in to continue.", 401)
    session.clear()
    session.permanent = True
    session["user_id"] = int(user["id"])
    session["pwd_stamp"] = stamp
    token = secrets.token_urlsafe(32)
    session["csrf_token"] = token
    return token


def read_idempotency_key(data: dict | None = None) -> str:
    if "Idempotency-Key" in request.headers:
        return clean_idempotency_key(request.headers.get("Idempotency-Key"))
    source = data if data is not None else request.form
    return clean_idempotency_key(source.get("idempotency_key"))
