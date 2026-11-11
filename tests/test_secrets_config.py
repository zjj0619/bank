"""Configuration paths for local secrets. Values stay in memory or a temporary file."""

from __future__ import annotations

import os
import stat

import pytest

from app import create_app
from app.secrets import (
    _passwords_from_file,
    load_local_env,
    resolve_secret_key,
    resolve_seed_passwords,
)
from tests.helpers import FIXTURE_PASSWORDS

pytestmark = [pytest.mark.security]

_USERNAMES = ("demo_zhang", "demo_li", "demo_wang")
_ENV_NAMES = {
    "demo_zhang": "BANK_SEED_PASSWORD_DEMO_ZHANG",
    "demo_li": "BANK_SEED_PASSWORD_DEMO_LI",
    "demo_wang": "BANK_SEED_PASSWORD_DEMO_WANG",
}


def _isolate(monkeypatch, tmp_path):
    secret = tmp_path / "session"
    credentials = tmp_path / "credentials"
    env = tmp_path / "env"
    monkeypatch.setattr("app.secrets.SECRET_FILE", secret)
    monkeypatch.setattr("app.secrets.CREDENTIALS_FILE", credentials)
    monkeypatch.setattr("app.secrets.ENV_FILE", env)
    monkeypatch.delenv("BANK_SECRET_KEY", raising=False)
    for name in _ENV_NAMES.values():
        monkeypatch.delenv(name, raising=False)
    return secret, credentials, env


def test_local_env_file_fills_only_missing_names(tmp_path, monkeypatch):
    _secret, _credentials, env = _isolate(monkeypatch, tmp_path)
    env.write_text(
        "# comment\n\nNOEQUALS\nBLANK=\nQUOTED=\"alpha\"\nALREADY=new\nFRESH=from-file\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ALREADY", "keep")
    monkeypatch.delenv("FRESH", raising=False)
    monkeypatch.delenv("QUOTED", raising=False)
    monkeypatch.delenv("BLANK", raising=False)
    load_local_env()
    assert os.environ["ALREADY"] == "keep"
    assert os.environ["FRESH"] == "from-file"
    assert os.environ["QUOTED"] == "alpha"
    assert os.environ.get("BLANK", "") == ""


def test_secret_key_resolution_uses_override_env_file_or_generates(tmp_path, monkeypatch):
    secret, _credentials, _env = _isolate(monkeypatch, tmp_path)
    assert resolve_secret_key(False, "override-marker") == "override-marker"
    monkeypatch.setenv("BANK_SECRET_KEY", "env-session-marker")
    assert resolve_secret_key(False, None) == "env-session-marker"
    monkeypatch.delenv("BANK_SECRET_KEY", raising=False)
    testing_value = resolve_secret_key(True, None)
    assert testing_value
    assert testing_value == resolve_secret_key(True, None)
    assert not secret.exists()
    secret.write_text("file-session-marker\n", encoding="utf-8")
    assert resolve_secret_key(False, None) == "file-session-marker"
    secret.write_text("   \n", encoding="utf-8")
    generated = resolve_secret_key(False, None)
    assert generated
    assert secret.read_text(encoding="utf-8").strip() == generated
    assert generated != "file-session-marker"


def test_private_file_write_ignores_chmod_errors(tmp_path, monkeypatch):
    secret, _credentials, _env = _isolate(monkeypatch, tmp_path)

    def _boom(*_args, **_kwargs):
        raise OSError("chmod is not available")

    monkeypatch.setattr("app.secrets.os.chmod", _boom)
    generated = resolve_secret_key(False, None)
    assert secret.read_text(encoding="utf-8").strip() == generated


def test_seed_passwords_come_from_env_or_file_and_testing_refuses(tmp_path, monkeypatch):
    _secret, credentials, _env = _isolate(monkeypatch, tmp_path)
    assert _passwords_from_file() == {}
    application = create_app(
        {
            "TESTING": False,
            "DATABASE": str(tmp_path / "bank.sqlite3"),
            "SECRET_KEY": "config-override-not-a-user-secret",
            "ARGON2_TIME_COST": 1,
            "ARGON2_MEMORY_COST": 8192,
            "ARGON2_PARALLELISM": 1,
            "SEED_PASSWORDS": None,
        }
    )
    for username, env_name in _ENV_NAMES.items():
        monkeypatch.setenv(env_name, FIXTURE_PASSWORDS[username])
    with application.app_context():
        from_env = resolve_seed_passwords(_USERNAMES)
    assert [from_env[name] for name in _USERNAMES] == [FIXTURE_PASSWORDS[name] for name in _USERNAMES]
    assert not credentials.exists()

    for env_name in _ENV_NAMES.values():
        monkeypatch.delenv(env_name, raising=False)
    credentials.write_text(
        "# comment\nignored=nope\ndemo_wang=\n"
        + "".join(f"{name}={FIXTURE_PASSWORDS[name]}\n" for name in _USERNAMES),
        encoding="utf-8",
    )
    found = _passwords_from_file()
    assert set(found) == set(_USERNAMES)
    with application.app_context():
        from_file = resolve_seed_passwords(_USERNAMES)
    assert [from_file[name] for name in _USERNAMES] == [FIXTURE_PASSWORDS[name] for name in _USERNAMES]

    credentials.unlink()
    with application.app_context():
        application.config["TESTING"] = True
        with pytest.raises(RuntimeError, match="must not create a demo passphrase file"):
            resolve_seed_passwords(_USERNAMES)
    assert not credentials.exists()

    with application.app_context():
        application.config["TESTING"] = False
        generated = resolve_seed_passwords(_USERNAMES)
    text = credentials.read_text(encoding="utf-8")
    assert text.startswith("# Local Linden Ledger")
    assert len(set(generated.values())) == 3
    for name in _USERNAMES:
        assert f"{name}={generated[name]}\n" in text
    assert stat.S_IMODE(credentials.stat().st_mode) == 0o600


def test_configured_seed_map_must_name_every_account(tmp_path, monkeypatch):
    _secret, credentials, _env = _isolate(monkeypatch, tmp_path)
    application = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "bank.sqlite3"),
            "SECRET_KEY": "config-override-not-a-user-secret",
            "SEED_PASSWORDS": {"demo_zhang": FIXTURE_PASSWORDS["demo_zhang"]},
        }
    )
    with application.app_context():
        with pytest.raises(RuntimeError, match="every demo account"):
            resolve_seed_passwords(_USERNAMES)
    assert not credentials.exists()
