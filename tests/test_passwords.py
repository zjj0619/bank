"""Passphrase policy, Argon2id storage, lockout, and session invalidation."""

from __future__ import annotations

import pytest

from app.errors import BusinessError
from app.passwords import POLICY_MESSAGE, validate_password
from app.paths import CREDENTIALS_FILE
from tests.helpers import CHANGED_PASSWORD, FIXTURE_PASSWORDS, WEB_CHANGED_PASSWORD, login, make_app, opened

pytestmark = pytest.mark.security


def test_password_policy_rejects_incomplete_and_weak():
    rejected = (
        "shortA1!",
        "alllowercase1!",
        "ALLUPPERCASE1!",
        "NoDigitsHere!!",
        "NoSymbolHere12",
        "Password123!",
        "Qwertyuiop1!",
        "Abcdwxyz1!mn",
        "Aaaa1!bbbbcc",
        "Xx4!demo_zhang",
        "Hello SIM-1001!",
        "Mingyuan1!pass",
    )
    for candidate in rejected:
        with pytest.raises(BusinessError) as caught:
            validate_password(candidate, "demo_zhang", "Mingyuan Zhang", "SIM-1001")
        assert caught.value.code == "weak_password"
        assert caught.value.message == POLICY_MESSAGE
        assert "denylist" not in caught.value.message.lower()
        assert "deny list" not in caught.value.message.lower()
    accepted = validate_password(
        FIXTURE_PASSWORDS["demo_zhang"],
        "demo_zhang",
        "Mingyuan Zhang",
        "SIM-1001",
    )
    assert accepted == FIXTURE_PASSWORDS["demo_zhang"]


def test_lockout_blocks_correct_passphrase_until_cooldown(tmp_path, monkeypatch):
    for name in (
        "BANK_SEED_PASSWORD",
        "BANK_SEED_PASSWORD_DEMO_ZHANG",
        "BANK_SEED_PASSWORD_DEMO_LI",
        "BANK_SEED_PASSWORD_DEMO_WANG",
    ):
        monkeypatch.delenv(name, raising=False)
    application = make_app(tmp_path, LOCKOUT_THRESHOLD=3, LOCKOUT_SECONDS=900)
    client = application.test_client()

    def attempt(password: str):
        token = client.get("/api/v1/csrf").get_json()["csrf_token"]
        return client.post(
            "/api/v1/auth/login",
            json={"username": "demo_zhang", "password": password},
            headers={"X-CSRF-Token": token},
        )

    for _ in range(3):
        failed = attempt("wrong-password-1!")
        assert failed.status_code == 401
        assert failed.get_json()["error"]["message"] == "The username or passphrase is not correct."
    with opened(application) as connection:
        before = connection.execute(
            "SELECT failed_attempts, locked_until FROM users WHERE username = 'demo_zhang'"
        ).fetchone()
        assert before["failed_attempts"] == 3
        assert before["locked_until"]
        locked_until = before["locked_until"]
    locked = attempt(FIXTURE_PASSWORDS["demo_zhang"])
    assert locked.status_code == 401
    assert locked.get_json()["error"]["message"] == "The username or passphrase is not correct."
    assert "locked" not in locked.get_json()["error"]["message"].lower()
    with opened(application) as connection:
        during = connection.execute(
            "SELECT failed_attempts, locked_until FROM users WHERE username = 'demo_zhang'"
        ).fetchone()
        assert during["failed_attempts"] == 3
        assert during["locked_until"] == locked_until
        connection.execute(
            "UPDATE users SET locked_until = ? WHERE username = 'demo_zhang'",
            ("2000-01-01T00:00:00Z",),
        )
    restored = attempt(FIXTURE_PASSWORDS["demo_zhang"])
    assert restored.status_code == 200
    assert restored.get_json()["ok"] is True


def test_password_hashes_are_argon2_and_distinct(app):
    with opened(app) as connection:
        rows = connection.execute("SELECT username, password_hash FROM users ORDER BY username").fetchall()
    assert len(rows) == 3
    hashes = []
    for row in rows:
        stored = row["password_hash"]
        secret = FIXTURE_PASSWORDS[row["username"]]
        assert stored.startswith("$argon2id$")
        assert stored != secret
        assert secret not in stored
        hashes.append(stored)
    assert len(set(hashes)) == 3


def test_change_password_updates_hash_and_ends_other_sessions(client, app):
    first = login(client)
    other = app.test_client()
    other_headers = login(other)
    weak = client.post(
        "/api/v1/auth/password",
        json={"current_password": FIXTURE_PASSWORDS["demo_zhang"], "new_password": "password"},
        headers=first,
    )
    assert weak.status_code == 400
    assert weak.get_json()["error"]["message"] == POLICY_MESSAGE
    reused = client.post(
        "/api/v1/auth/password",
        json={
            "current_password": FIXTURE_PASSWORDS["demo_zhang"],
            "new_password": FIXTURE_PASSWORDS["demo_zhang"],
        },
        headers=first,
    )
    assert reused.status_code == 400
    assert reused.get_json()["error"]["message"] == "Choose a different passphrase."
    changed = client.post(
        "/api/v1/auth/password",
        json={"current_password": FIXTURE_PASSWORDS["demo_zhang"], "new_password": CHANGED_PASSWORD},
        headers=first,
    )
    assert changed.status_code == 200, changed.get_data(as_text=True)
    assert client.get("/api/v1/me").status_code == 200
    assert other.get("/api/v1/me", headers=other_headers).status_code == 401
    token = client.get("/api/v1/csrf").get_json()["csrf_token"]
    old = client.post(
        "/api/v1/auth/login",
        json={"username": "demo_zhang", "password": FIXTURE_PASSWORDS["demo_zhang"]},
        headers={"X-CSRF-Token": token},
    )
    assert old.status_code == 401
    fresh = app.test_client()
    login(fresh, "demo_zhang", CHANGED_PASSWORD)
    with opened(app) as connection:
        stored = connection.execute(
            "SELECT password_hash FROM users WHERE username = 'demo_zhang'"
        ).fetchone()["password_hash"]
    assert stored.startswith("$argon2id$")
    assert CHANGED_PASSWORD not in stored
    assert FIXTURE_PASSWORDS["demo_zhang"] not in stored
    anonymous = app.test_client()
    assert anonymous.get("/password").status_code == 302
    page = fresh.get("/password")
    html = page.get_data(as_text=True)
    token = html.split('name="csrf_token" value="', 1)[1].split('"', 1)[0]
    mismatch = fresh.post(
        "/password",
        data={
            "csrf_token": token,
            "current_password": CHANGED_PASSWORD,
            "new_password": WEB_CHANGED_PASSWORD,
            "confirm_password": "not-the-same-1!",
        },
    )
    assert mismatch.status_code == 400
    assert "do not match" in mismatch.get_data(as_text=True)
    updated = fresh.post(
        "/password",
        data={
            "csrf_token": token,
            "current_password": CHANGED_PASSWORD,
            "new_password": WEB_CHANGED_PASSWORD,
            "confirm_password": WEB_CHANGED_PASSWORD,
        },
        follow_redirects=True,
    )
    assert updated.status_code == 200
    assert "Passphrase updated" in updated.get_data(as_text=True)
    assert client.get("/api/v1/me").status_code == 401


def test_shared_seed_passphrase_is_refused(tmp_path, monkeypatch):
    for name in (
        "BANK_SEED_PASSWORD",
        "BANK_SEED_PASSWORD_DEMO_ZHANG",
        "BANK_SEED_PASSWORD_DEMO_LI",
        "BANK_SEED_PASSWORD_DEMO_WANG",
    ):
        monkeypatch.delenv(name, raising=False)
    existed = CREDENTIALS_FILE.exists()
    passwords = dict(FIXTURE_PASSWORDS)
    passwords["demo_wang"] = passwords["demo_zhang"]
    with pytest.raises(RuntimeError, match="own passphrase"):
        make_app(tmp_path, SEED_PASSWORDS=passwords)
    if not existed:
        assert not CREDENTIALS_FILE.exists()


def test_weak_seed_passphrase_is_refused(tmp_path, monkeypatch):
    for name in (
        "BANK_SEED_PASSWORD",
        "BANK_SEED_PASSWORD_DEMO_ZHANG",
        "BANK_SEED_PASSWORD_DEMO_LI",
        "BANK_SEED_PASSWORD_DEMO_WANG",
    ):
        monkeypatch.delenv(name, raising=False)
    existed = CREDENTIALS_FILE.exists()
    passwords = dict(FIXTURE_PASSWORDS)
    passwords["demo_li"] = "password"
    with pytest.raises(BusinessError) as caught:
        make_app(tmp_path, SEED_PASSWORDS=passwords)
    assert caught.value.message == POLICY_MESSAGE
    assert "password" not in caught.value.message
    if not existed:
        assert not CREDENTIALS_FILE.exists()
