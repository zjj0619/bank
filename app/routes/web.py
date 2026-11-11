"""服务器渲染的中文页面。"""

from __future__ import annotations

import secrets

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from app.db import get_db
from app.errors import BusinessError, MoneyError
from app.money import format_fen, parse_amount_to_fen
from app.seed_data import DEMO_ACCOUNTS
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
from app.passwords import POLICY_MESSAGE
from app.webutil import ensure_csrf, establish_session, read_idempotency_key, require_csrf, session_user_id

web_bp = Blueprint("web", __name__)


def sparkline_for(entries):
    ordered = list(reversed(entries))
    if not ordered:
        return None
    values = [int(item["balance_after_fen"]) for item in ordered]
    width, height = 320, 72
    low, high = min(values), max(values)
    span = high - low
    if len(values) == 1 or span == 0:
        y = height / 2
        points = f"0,{y:.1f} {width},{y:.1f}"
    else:
        coords = []
        step = width / (len(values) - 1)
        for index, value in enumerate(values):
            x = index * step
            y = 8 + (1 - (value - low) / span) * (height - 16)
            coords.append(f"{x:.1f},{y:.1f}")
        points = " ".join(coords)
    return {
        "points": points,
        "width": width,
        "height": height,
        "low": format_fen(low, grouping=True),
        "high": format_fen(high, grouping=True),
        "count": len(values),
    }


@web_bp.app_template_filter("yuan")
def format_yuan(value: int) -> str:
    return format_fen(int(value), grouping=True)


@web_bp.app_context_processor
def inject_layout():
    user_id = session_user_id()
    token = ensure_csrf()
    nav_user = None
    if user_id is not None:
        nav_user = get_db().execute(
            "SELECT username, display_name FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return {"csrf_token": token, "nav_user": nav_user, "simulation": True}


@web_bp.get("/")
def home():
    user_id = _page_user()
    if user_id is None:
        return redirect(url_for("web.login_form"))
    connection = get_db()
    account = account_payload(get_account_for_user(connection, user_id))
    history = list_history(connection, user_id, limit=5, offset=0)
    return render_template(
        "dashboard.html",
        account=account,
        history=history["transactions"],
        spark=sparkline_for(history["transactions"]),
    )


@web_bp.get("/login")
def login_form():
    if _page_user() is not None:
        return redirect(url_for("web.home"))
    return render_template(
        "login.html",
        error=None,
        username="",
        demo_accounts=DEMO_ACCOUNTS,
    )


@web_bp.post("/login")
def login_submit():
    username = request.form.get("username", "")
    shown = username.strip() if isinstance(username, str) else ""
    try:
        require_csrf()
        user = authenticate(get_db(), username, request.form.get("password"))
    except BusinessError as error:
        return _login_error(error.message, shown, error.status)
    if user is None:
        return _login_error("The username or passphrase is not correct.", shown, 401)
    establish_session(user)
    return redirect(url_for("web.home"))


@web_bp.post("/logout")
def logout():
    try:
        require_csrf()
    except BusinessError as error:
        return render_template("error.html", title="Could not sign out", message=error.message), error.status
    session.clear()
    return redirect(url_for("web.login_form"))


@web_bp.route("/deposit", methods=["GET", "POST"])
def deposit_page():
    return _money_page("deposit")


@web_bp.route("/withdraw", methods=["GET", "POST"])
def withdraw_page():
    return _money_page("withdrawal")


@web_bp.route("/transfer", methods=["GET", "POST"])
def transfer_page():
    return _money_page("transfer")


@web_bp.route("/password", methods=["GET", "POST"])
def password_page():
    user_id = _page_user()
    if user_id is None:
        return redirect(url_for("web.login_form"))
    error = None
    status = 200
    if request.method == "POST":
        new = _form_text("new_password")
        confirm = _form_text("confirm_password")
        try:
            require_csrf()
            if new != confirm:
                raise BusinessError("weak_password", "The two new passphrases do not match.")
            stamp = change_password(get_db(), user_id, _form_text("current_password"), new)
            session["pwd_stamp"] = stamp
            session["csrf_token"] = secrets.token_urlsafe(32)
            flash("Passphrase updated. Other sessions for this account are signed out.", "success")
            return redirect(url_for("web.home"))
        except BusinessError as error_info:
            error = error_info.message
            status = error_info.status
    return render_template("password.html", error=error, policy=POLICY_MESSAGE), status


@web_bp.get("/history")
def history_page():
    user_id = _page_user()
    if user_id is None:
        return redirect(url_for("web.login_form"))
    history = list_history(get_db(), user_id, limit=100, offset=0)
    return render_template("history.html", history=history["transactions"], account_no=history["account_no"])


def _money_page(kind: str):
    user_id = _page_user()
    if user_id is None:
        return redirect(url_for("web.login_form"))
    connection = get_db()
    account = account_payload(get_account_for_user(connection, user_id))
    form = {
        "amount": "",
        "note": "",
        "to_account_no": "",
    }
    idempotency_key = secrets.token_urlsafe(18)
    error = None
    status = 200
    if request.method == "POST":
        form["amount"] = _form_text("amount")
        form["note"] = _form_text("note")
        form["to_account_no"] = _form_text("to_account_no")
        posted_key = _form_text("idempotency_key")
        if posted_key:
            idempotency_key = posted_key
        try:
            require_csrf()
            amount_fen = parse_amount_to_fen(form["amount"])
            note = clean_note(form["note"])
            idem_key = read_idempotency_key()
            if kind == "deposit":
                result = deposit(connection, user_id, amount_fen, note, idem_key)
                verb = "Deposit"
            elif kind == "withdrawal":
                result = withdraw(connection, user_id, amount_fen, note, idem_key)
                verb = "Withdrawal"
            else:
                result = transfer(
                    connection,
                    user_id,
                    amount_fen,
                    note,
                    idem_key,
                    form["to_account_no"],
                )
                verb = "Transfer"
            if result["replayed"]:
                flash("This submission was already posted. Nothing was recorded twice.", "info")
            else:
                target = ""
                if result.get("counterparty_account_no"):
                    target = f"to {result['counterparty_account_no']} "
                flash(
                    f"{verb} recorded {target}{result['amount']} CNY. Balance {result['balance_display']} CNY. Entry {result['transaction_id']}.",
                    "success",
                )
            return redirect(url_for("web.home"))
        except (BusinessError, MoneyError) as error_info:
            error = error_info.message
            status = error_info.status
    return (
        render_template(
            "money_form.html",
            kind=kind,
            account=account,
            form=form,
            error=error,
            idempotency_key=idempotency_key,
        ),
        status,
    )


def _page_user() -> int | None:
    return session_user_id()


def _form_text(name: str) -> str:
    value = request.form.get(name, "")
    if not isinstance(value, str):
        return ""
    return value


def _login_error(message: str, username: str, status: int):
    g.login_error = message
    return (
        render_template(
            "login.html",
            error=message,
            username=username,
            demo_accounts=DEMO_ACCOUNTS,
        ),
        status,
    )
