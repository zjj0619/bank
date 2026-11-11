"""演示口令和会话密钥只从环境或被忽略的本地文件读取，日志和页面都不打印口令。"""

from __future__ import annotations

import os
import secrets

from flask import current_app

from app.paths import CREDENTIALS_FILE, ENV_FILE, SECRET_FILE


def load_local_env() -> None:
    """读取项目根目录的 .env。已存在的环境变量优先，空值忽略。"""

    if not ENV_FILE.exists():
        return
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


def _write_private(path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def resolve_secret_key(testing: bool, override: str | None) -> str:
    if override:
        return override
    env = os.environ.get("BANK_SECRET_KEY", "").strip()
    if env:
        return env
    if testing:
        return "test-only-secret-not-for-production"
    if SECRET_FILE.exists():
        existing = SECRET_FILE.read_text(encoding="utf-8").strip()
        if existing:
            return existing
    generated = secrets.token_hex(32)
    _write_private(SECRET_FILE, generated + "\n")
    return generated


_ENV_BY_USERNAME = {
    "demo_zhang": "BANK_SEED_PASSWORD_DEMO_ZHANG",
    "demo_li": "BANK_SEED_PASSWORD_DEMO_LI",
    "demo_wang": "BANK_SEED_PASSWORD_DEMO_WANG",
}


def _passwords_from_file() -> dict[str, str]:
    found: dict[str, str] = {}
    if not CREDENTIALS_FILE.exists():
        return found
    for raw_line in CREDENTIALS_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in _ENV_BY_USERNAME and value:
            found[key] = value
    return found


def resolve_seed_passwords(usernames: tuple[str, ...]) -> dict[str, str]:
    """One passphrase per demo account. Never log or return these to a page."""

    configured = current_app.config.get("SEED_PASSWORDS")
    if isinstance(configured, dict) and configured:
        missing = [name for name in usernames if not configured.get(name)]
        if missing:
            raise RuntimeError("Tests must set a passphrase for every demo account.")
        _reject_shared(configured, usernames)
        return {name: configured[name] for name in usernames}

    from_file = _passwords_from_file()
    resolved: dict[str, str] = {}
    generated: dict[str, str] = {}
    for name in usernames:
        env_name = _ENV_BY_USERNAME.get(name, "")
        env_value = os.environ.get(env_name, "").strip() if env_name else ""
        if env_value:
            resolved[name] = env_value
        elif from_file.get(name):
            resolved[name] = from_file[name]
        elif current_app.config.get("TESTING"):
            raise RuntimeError("Tests must set SEED_PASSWORDS and must not create a demo passphrase file.")
        else:
            from app.passwords import generate_password

            generated[name] = generate_password()
            resolved[name] = generated[name]
    _reject_shared(resolved, usernames)
    if generated:
        _write_private(
            CREDENTIALS_FILE,
            (
                "# Local Linden Ledger passphrases, one per demo account. Git ignores this file.\n"
                "# Do not commit it or paste it into a report, chat, or screenshot.\n"
                + "".join(f"{name}={resolved[name]}\n" for name in usernames)
            ),
        )
    return resolved


def _reject_shared(mapping: dict[str, str], usernames: tuple[str, ...]) -> None:
    values = [mapping[name] for name in usernames]
    if len(set(values)) != len(values):
        raise RuntimeError("Each demo account needs its own passphrase. Nothing was stored.")
