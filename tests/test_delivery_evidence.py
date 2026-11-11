"""Checks that saved SQLMap evidence and the CI workflow stay local and free of secrets."""

from __future__ import annotations

import json
from urllib.parse import urlparse

import pytest

from app.paths import ROOT
from tests.helpers import CHANGED_PASSWORD, FIXTURE_PASSWORDS, WEB_CHANGED_PASSWORD, make_app

pytestmark = pytest.mark.acceptance

_SUMMARY = ROOT / "docs" / "security" / "sqlmap_summary.md"
_OUTCOME = ROOT / "reports" / "sqlmap_outcome.json"
_WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"


def _banned(tmp_path) -> list[str]:
    application = make_app(tmp_path)
    values = [
        *FIXTURE_PASSWORDS.values(),
        CHANGED_PASSWORD,
        WEB_CHANGED_PASSWORD,
        application.config["SECRET_KEY"],
    ]
    return [value for value in values if value]


def test_sqlmap_evidence_targets_localhost_only(tmp_path):
    outcome = json.loads(_OUTCOME.read_text(encoding="utf-8"))
    summary = _SUMMARY.read_text(encoding="utf-8")
    assert outcome["host"] == "127.0.0.1"
    assert outcome["bind"] == "127.0.0.1"
    assert "U" in outcome["techniques"]
    assert "B" in outcome["techniques"]
    assert outcome["targets"]
    assert outcome["runs"]
    for url in outcome["targets"]:
        parsed = urlparse(url)
        assert parsed.scheme == "http"
        assert parsed.hostname == "127.0.0.1"
        assert parsed.port
    seen = set()
    for run in outcome["runs"]:
        seen.add(run["technique"])
        parsed = urlparse(run["url"])
        assert parsed.hostname == "127.0.0.1"
        log_path = ROOT / run["log"]
        text = log_path.read_text(encoding="utf-8", errors="replace")
        assert "127.0.0.1" in text
        assert "sqlmap" in text.lower()
        assert run["conclusion"]
        assert run["conclusion"] in text
    assert seen == {"U", "B"}
    assert "127.0.0.1" in summary
    assert "sqlmap" in summary.lower()
    if outcome["injectable"]:
        assert outcome.get("cvss")
        assert "CVSS" in summary
    else:
        assert outcome.get("cvss") in (None, "")
        assert "CVSS" not in summary
    blob = summary + "\n" + _OUTCOME.read_text(encoding="utf-8")
    for log in outcome["runs"]:
        blob += "\n" + (ROOT / log["log"]).read_text(encoding="utf-8", errors="replace")
    for secret in _banned(tmp_path):
        assert secret not in blob


def test_ci_workflow_runs_pytest_and_uploads_reports(tmp_path):
    text = _WORKFLOW.read_text(encoding="utf-8")
    assert "pull_request" in text
    assert "main" in text
    assert "pytest" in text
    assert "--cov=app" in text or "run_tests.sh" in text
    assert "reports/junit.xml" in text
    assert "reports/coverage.xml" in text
    assert "reports/pytest-report.html" in text
    assert "allure-results" in text
    assert "BANK_SEED_PASSWORD" not in text
    assert "BANK_SECRET_KEY" not in text
    for secret in _banned(tmp_path):
        assert secret not in text
