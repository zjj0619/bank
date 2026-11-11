"""澄簿模拟银行。课程演示，不连接真实银行，不处理真实资金。"""

from __future__ import annotations

import logging
import os
from datetime import timedelta
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from app.db import init_app
from app.errors import BusinessError
from app.paths import resolve_database_path
from app.secrets import resolve_secret_key

LOGGER = logging.getLogger("chengbu")


def create_app(overrides: dict | None = None) -> Flask:
    overrides = dict(overrides or {})
    testing = bool(overrides.get("TESTING", False))
    database = str(overrides.get("DATABASE") or resolve_database_path())
    Path(database).parent.mkdir(parents=True, exist_ok=True)

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=resolve_secret_key(testing, overrides.get("SECRET_KEY")),
        DATABASE=database,
        TESTING=testing,
        DEBUG=False,
        PROPAGATE_EXCEPTIONS=False,
        SESSION_COOKIE_NAME="chengbu_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("BANK_COOKIE_SECURE") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
        MAX_CONTENT_LENGTH=32 * 1024,
        ALLOW_FAULT_INJECTION=False,
        ARGON2_TIME_COST=int(os.environ.get("BANK_ARGON2_TIME_COST", "2")),
        ARGON2_MEMORY_COST=int(os.environ.get("BANK_ARGON2_MEMORY_COST", "65536")),
        ARGON2_PARALLELISM=int(os.environ.get("BANK_ARGON2_PARALLELISM", "2")),
        LOCKOUT_THRESHOLD=int(os.environ.get("BANK_LOCKOUT_THRESHOLD", "5")),
        LOCKOUT_SECONDS=int(os.environ.get("BANK_LOCKOUT_SECONDS", "900")),
        SEED_PASSWORDS=None,
        SIMULATION=True,
    )
    app.config.update(overrides)
    app.config["DEBUG"] = False
    app.config["PROPAGATE_EXCEPTIONS"] = False
    app.config["SIMULATION"] = True
    app.config["DATABASE"] = database
    app.json.ensure_ascii = False

    init_app(app)
    _register_blueprints(app)
    _register_handlers(app)
    if not LOGGER.handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    return app


def _register_blueprints(app: Flask) -> None:
    from app.routes.api import api_bp
    from app.routes.web import web_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api/v1")


def _wants_json() -> bool:
    return request.path.startswith("/api/")


def _error_body(code: str, message: str, status: int):
    if _wants_json():
        return jsonify(ok=False, simulation=True, error={"code": code, "message": message}), status
    try:
        return render_template("error.html", title="The request could not be completed", message=message), status
    except Exception:
        LOGGER.exception("error page failed")
        return message, status, {"Content-Type": "text/plain; charset=utf-8"}


def _register_handlers(app: Flask) -> None:
    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; "
            "script-src 'self'; form-action 'self'; base-uri 'self'; frame-ancestors 'none'"
        )
        response.headers["X-Simulation"] = "simulated-bank-coursework-not-real-money"
        if not request.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(BusinessError)
    def handle_business(error: BusinessError):
        if error.status >= 500:
            LOGGER.error("business failure %s", error.code)
        return _error_body(error.code, error.message, error.status)

    @app.errorhandler(HTTPException)
    def handle_http(error: HTTPException):
        if error.code == 404:
            message = "That resource does not exist." if _wants_json() else "This page does not exist."
            return _error_body("not_found", message, 404)
        if error.code == 413:
            return _error_body("payload_too_large", "The request is too large.", 413)
        if error.code == 405:
            return _error_body("method_not_allowed", "That method is not accepted.", 405)
        return _error_body("request_failed", "The request could not be processed.", error.code or 400)

    @app.errorhandler(Exception)
    def handle_unexpected(error: Exception):
        if isinstance(error, BusinessError):
            return handle_business(error)
        if isinstance(error, HTTPException):
            return handle_http(error)
        LOGGER.exception("unhandled request failure")
        return _error_body("internal_error", "The operation was cancelled. The account was not changed.", 500)
