"""Argon2id passphrase hashing and the teaching-bank passphrase policy."""

from __future__ import annotations

import re
import string

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from flask import current_app

from app.errors import BusinessError

MIN_LENGTH = 12
MAX_LENGTH = 128
POLICY_MESSAGE = (
    "Use at least 12 characters with an uppercase letter, a lowercase letter, a digit, and a symbol. "
    "Do not use your username, account number, or a common or easily guessed passphrase."
)

_DENY = {
    "password",
    "passw0rd",
    "letmein",
    "welcome",
    "qwerty",
    "qwertyuiop",
    "asdfghjkl",
    "zxcvbnm",
    "admin",
    "administrator",
    "changeme",
    "iloveyou",
    "abc123",
    "login",
    "secret",
    "dragon",
    "monkey",
    "master",
    "sunshine",
    "princess",
    "football",
    "baseball",
    "shadow",
    "trustno1",
    "demo",
    "linden",
    "bank",
    "banking",
    "welcome1",
    "pass123",
}
_KEYBOARD = ("qwertyuiop", "asdfghjkl", "zxcvbnm", "1234567890")
_HASHERS: dict[tuple[int, int, int], PasswordHasher] = {}
_DUMMY: dict[tuple[int, int, int], str] = {}


def policy_error() -> BusinessError:
    return BusinessError("weak_password", POLICY_MESSAGE)


def validate_password(password: object, *identifiers: str) -> str:
    if not isinstance(password, str) or not password or password.strip() != password:
        raise policy_error()
    if len(password) < MIN_LENGTH or len(password) > MAX_LENGTH:
        raise policy_error()
    if not re.search(r"[A-Z]", password) or not re.search(r"[a-z]", password):
        raise policy_error()
    if not re.search(r"[0-9]", password) or not re.search(r"[^A-Za-z0-9]", password):
        raise policy_error()
    if re.search(r"(.)\1{3,}", password):
        raise policy_error()
    folded = password.lower()
    if _has_run(folded, 4) or _has_keyboard_run(folded, 4):
        raise policy_error()
    alnum = re.sub(r"[^a-z0-9]", "", folded)
    core = alnum.rstrip("0123456789")
    if alnum in _DENY or core in _DENY or folded in _DENY:
        raise policy_error()
    for raw in identifiers:
        whole = (raw or "").strip().lower()
        if len(whole) >= 3 and whole in folded:
            raise policy_error()
        for token in re.findall(r"[a-z0-9]{4,}", whole):
            if token in folded or token in alnum:
                raise policy_error()
    return password


def generate_password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_"
    for _ in range(32):
        pieces = [
            _choice(string.ascii_uppercase),
            _choice(string.ascii_lowercase),
            _choice(string.digits),
            _choice("!@#$%^&*-_"),
        ]
        pieces.extend(_choice(alphabet) for _ in range(12))
        import secrets

        secrets.SystemRandom().shuffle(pieces)
        candidate = "".join(pieces)
        try:
            return validate_password(candidate)
        except BusinessError:
            continue
    raise RuntimeError("Could not generate a passphrase that meets the policy.")


def hash_password(password: str) -> str:
    return _hasher().hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher().verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, VerificationError):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher().check_needs_rehash(password_hash)
    except (InvalidHashError, VerificationError):
        return True


def dummy_hash() -> str:
    key = _hasher_key()
    cached = _DUMMY.get(key)
    if cached is None:
        cached = _hasher().hash("not-a-login-secret")
        _DUMMY[key] = cached
    return cached


def _hasher() -> PasswordHasher:
    key = _hasher_key()
    cached = _HASHERS.get(key)
    if cached is None:
        cached = PasswordHasher(
            time_cost=key[0],
            memory_cost=key[1],
            parallelism=key[2],
            hash_len=32,
            salt_len=16,
        )
        _HASHERS[key] = cached
    return cached


def _hasher_key() -> tuple[int, int, int]:
    return (
        int(current_app.config.get("ARGON2_TIME_COST", 3)),
        int(current_app.config.get("ARGON2_MEMORY_COST", 65536)),
        int(current_app.config.get("ARGON2_PARALLELISM", 2)),
    )


def _choice(alphabet: str) -> str:
    import secrets

    return secrets.choice(alphabet)


def _has_run(text: str, length: int) -> bool:
    for index in range(len(text) - length + 1):
        chunk = text[index : index + length]
        if not chunk.isalnum():
            continue
        diffs = [ord(chunk[i + 1]) - ord(chunk[i]) for i in range(length - 1)]
        if all(diff == 1 for diff in diffs) or all(diff == -1 for diff in diffs):
            return True
    return False


def _has_keyboard_run(text: str, length: int) -> bool:
    for row in _KEYBOARD:
        for index in range(len(row) - length + 1):
            piece = row[index : index + length]
            if piece in text or piece[::-1] in text:
                return True
    return False
