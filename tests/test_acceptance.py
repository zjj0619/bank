"""交付物检查。不读取、不打印演示口令。"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app import create_app
from app.db import init_db
from app.paths import CREDENTIALS_FILE, ROOT, SECRET_FILE
from app.seed_data import DEMO_ACCOUNTS
from tests.case_catalog import CASES
from tests.helpers import FIXTURE_PASSWORDS, login

pytestmark = pytest.mark.acceptance


def test_readme_lists_seed_accounts_and_secrets_are_untracked():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    app_text = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "app").rglob("*.py"))
    for item in DEMO_ACCOUNTS:
        assert item["username"] in readme
        assert item["account_no"] in readme
    assert "10,000.00" in readme
    assert "5,000.00" in readme
    assert "2,580.25" in readme
    assert "BANK_SEED_PASSWORD" in readme
    assert ".demo_credentials" in readme
    assert "python scripts/reset_db.py --yes" in readme
    for secret in FIXTURE_PASSWORDS.values():
        assert secret not in readme
        assert secret not in app_text
    assert ".demo_credentials" in gitignore
    assert ".session_secret" in gitignore
    tracked = __import__("subprocess").check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    assert ".demo_credentials" not in tracked
    assert ".session_secret" not in tracked
    assert all(not name.endswith(".sqlite3") for name in tracked)


def test_catalog_matches_test_functions():
    names = []
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                names.append(node.name)
    catalog = [case["function"] for case in CASES]
    assert sorted(names) == sorted(catalog)
    assert len(catalog) == len(set(catalog)) >= 20
    functional = [case for case in CASES if case["category"] == "Functional"]
    assert len(functional) >= 40
    for case in functional:
        assert case["id"].startswith("FC-")
        assert case["preconditions"] and case["steps"] and case["expected"] and case["title"]
        path_text, function_name = case["trace"].split("::")
        assert (ROOT / path_text).is_file(), path_text
        assert function_name.isidentifier()


def test_reset_command_recreates_isolated_database(tmp_path, monkeypatch):
    database = tmp_path / "reset.sqlite3"
    database.write_bytes(b"dirty")
    monkeypatch.setenv("BANK_DATABASE", str(database))
    monkeypatch.delenv("BANK_SEED_PASSWORD", raising=False)
    monkeypatch.setenv("BANK_SEED_PASSWORD_DEMO_ZHANG", FIXTURE_PASSWORDS["demo_zhang"])
    monkeypatch.setenv("BANK_SEED_PASSWORD_DEMO_LI", FIXTURE_PASSWORDS["demo_li"])
    monkeypatch.setenv("BANK_SEED_PASSWORD_DEMO_WANG", FIXTURE_PASSWORDS["demo_wang"])
    monkeypatch.setenv("BANK_SECRET_KEY", "reset-test-secret")
    monkeypatch.setenv("BANK_ARGON2_TIME_COST", "1")
    monkeypatch.setenv("BANK_ARGON2_MEMORY_COST", "8192")
    monkeypatch.setenv("BANK_ARGON2_PARALLELISM", "1")
    credentials_existed = CREDENTIALS_FILE.exists()
    secret_existed = SECRET_FILE.exists()
    from scripts.reset_db import main

    assert main([]) == 2
    assert database.read_bytes() == b"dirty"
    assert main(["--yes"]) == 0
    application = create_app(
        {
            "TESTING": True,
            "DATABASE": str(database),
            "SECRET_KEY": "reset-test-secret",
            "ARGON2_TIME_COST": 1,
            "ARGON2_MEMORY_COST": 8192,
            "ARGON2_PARALLELISM": 1,
        }
    )
    with application.app_context():
        init_db(seed=True)
    client = application.test_client()
    headers = login(client, "demo_wang")
    body = client.get("/api/v1/account", headers=headers).get_json()["account"]
    assert body["balance_fen"] == 258_025
    assert body["account_no"] == "SIM-1003"
    if not credentials_existed:
        assert not CREDENTIALS_FILE.exists()
    if not secret_existed:
        assert not SECRET_FILE.exists()
