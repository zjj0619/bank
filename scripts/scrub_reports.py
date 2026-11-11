"""Replace fixture secrets if a report captured them. Prints filenames only."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from tests.helpers import CHANGED_PASSWORD, FIXTURE_PASSWORDS, WEB_CHANGED_PASSWORD

TARGETS = [
    ROOT / "reports",
    ROOT / "docs" / "security",
    ROOT / "docs" / "test_cases.csv",
    ROOT / "docs" / "test_cases.md",
    ROOT / "docs" / "integration_report.md",
    ROOT / "docs" / "management" / "standup_log.md",
]
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".woff2", ".sqlite", ".sqlite3"}


def banned() -> list[str]:
    database = ROOT / "data" / "scrub-check.sqlite3"
    application = create_app(
        {
            "TESTING": True,
            "DATABASE": str(database),
            "SECRET_KEY": "scrub-placeholder",
            "SEED_PASSWORDS": dict(FIXTURE_PASSWORDS),
        }
    )
    values = [*FIXTURE_PASSWORDS.values(), CHANGED_PASSWORD, WEB_CHANGED_PASSWORD]
    # The testing default is the value resolve_secret_key returns when no override is set.
    from app.secrets import resolve_secret_key

    values.append(resolve_secret_key(True, None))
    database.unlink(missing_ok=True)
    return [value for value in values if value and value != "scrub-placeholder"]


def files() -> list[Path]:
    found = []
    for target in TARGETS:
        if target.is_file():
            found.append(target)
        elif target.is_dir():
            for path in target.rglob("*"):
                if path.is_file() and path.suffix.lower() not in SKIP_SUFFIXES:
                    found.append(path)
    return found


def main() -> int:
    secrets = banned()
    changed = []
    for path in files():
        text = path.read_text(encoding="utf-8", errors="replace")
        updated = text
        for secret in secrets:
            updated = updated.replace(secret, "[redacted]")
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed.append(path.relative_to(ROOT).as_posix())
    if changed:
        print("scrubbed " + ", ".join(changed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
