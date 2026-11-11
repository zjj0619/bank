"""根据本次 JUnit 和覆盖率结果生成中文用例表与集成报告。"""

from __future__ import annotations

import csv
import json
import platform
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.case_catalog import CASES
from tests.helpers import CHANGED_PASSWORD, FIXTURE_PASSWORDS, WEB_CHANGED_PASSWORD

JUNIT = ROOT / "reports" / "junit.xml"
COVERAGE = ROOT / "reports" / "coverage.xml"
NOTES = ROOT / "reports" / "observed_issues.json"
EXIT_CODE = ROOT / "reports" / "pytest-exit-code.txt"
CSV_PATH = ROOT / "docs" / "test_cases.csv"
MD_PATH = ROOT / "docs" / "test_cases.md"
REPORT_PATH = ROOT / "docs" / "integration_report.md"


def scrub(text: str) -> str:
    cleaned = text
    for secret in (*FIXTURE_PASSWORDS.values(), CHANGED_PASSWORD, WEB_CHANGED_PASSWORD):
        cleaned = cleaned.replace(secret, "[fixture-password]")
    cleaned = cleaned.replace("\r", " ").replace("\n", " ").strip()
    return cleaned


def load_results() -> dict[str, dict]:
    if not JUNIT.exists():
        return {}
    root = ET.parse(JUNIT).getroot()
    found: dict[str, dict] = {}
    for case in root.findall(".//testcase"):
        name = case.attrib.get("name", "")
        failure = case.find("failure")
        error = case.find("error")
        skipped = case.find("skipped")
        if failure is not None:
            status = "Failed"
            detail = scrub(failure.attrib.get("message", "") or (failure.text or ""))
        elif error is not None:
            status = "Error"
            detail = scrub(error.attrib.get("message", "") or (error.text or ""))
        elif skipped is not None:
            status = "Skipped"
            detail = scrub(skipped.attrib.get("message", "") or (skipped.text or ""))
        else:
            status = "Passed"
            detail = "Passed in this run"
        found[name] = {
            "status": status,
            "detail": detail[:500],
            "classname": case.attrib.get("classname", ""),
            "time": case.attrib.get("time", ""),
        }
    return found


def coverage_rows() -> tuple[str, list[tuple[str, str, str, str, str]]]:
    if not COVERAGE.exists():
        return "coverage.xml was not produced for this run", []
    root = ET.parse(COVERAGE).getroot()
    rate = float(root.attrib.get("line-rate", "0"))
    valid = root.attrib.get("lines-valid", "0")
    covered = root.attrib.get("lines-covered", "0")
    summary = f"Line coverage {rate * 100:.1f}% ({covered}/{valid} lines)"
    branch_rate = root.attrib.get("branch-rate")
    branches_valid = root.attrib.get("branches-valid")
    branches_covered = root.attrib.get("branches-covered")
    if branch_rate is not None and branches_valid not in (None, ""):
        summary += (
            f". Branch coverage {float(branch_rate) * 100:.1f}% "
            f"({branches_covered}/{branches_valid} branches)"
        )
    rows = []
    for clazz in root.findall(".//class"):
        filename = clazz.attrib.get("filename", "").replace("\\", "/")
        if not filename:
            continue
        if not filename.startswith("app/"):
            filename = "app/" + filename
        line_nodes = clazz.findall("./lines/line")
        valid_lines = str(len(line_nodes))
        covered_lines = str(sum(1 for line in line_nodes if int(line.attrib.get("hits", "0")) > 0))
        line_rate = float(clazz.attrib.get("line-rate", "0"))
        branch = clazz.attrib.get("branch-rate")
        branch_text = f"{float(branch) * 100:.1f}%" if branch not in (None, "") else ""
        rows.append((filename, f"{line_rate * 100:.1f}%", valid_lines, covered_lines, branch_text))
    return summary, rows


def sqlmap_lines() -> list[str]:
    path = ROOT / "reports" / "sqlmap_outcome.json"
    if not path.exists():
        return ["SQLMap outcome was not recorded for this run."]
    outcome = json.loads(path.read_text(encoding="utf-8"))
    lines = [
        f"- Tool: {outcome.get('tool', 'sqlmap')} {outcome.get('tool_version', '')}".rstrip(),
        f"- Bind and host: {outcome.get('bind', '')}",
        f"- Techniques: {', '.join(outcome.get('techniques') or [])}",
        f"- Injectable parameter reported: {outcome.get('injectable')}",
    ]
    if outcome.get("injectable"):
        lines.append(f"- CVSS: {outcome.get('cvss')}")
    else:
        lines.append("- CVSS: not assigned, because no injectable parameter was reported.")
    for run in outcome.get("runs") or []:
        lines.append(
            f"- {run.get('name')}: technique {run.get('technique')} on {run.get('url')} — {run.get('conclusion')}"
        )
    return lines


def main() -> int:
    results = load_results()
    counts = Counter(item["status"] for item in results.values())
    authored = len(CASES)
    executed_names = set(results)
    catalog_names = {case["function"] for case in CASES}
    missing = sorted(catalog_names - executed_names)
    extra = sorted(executed_names - catalog_names)
    passed = counts.get("Passed", 0)
    failed = counts.get("Failed", 0)
    errors = counts.get("Error", 0)
    skipped = counts.get("Skipped", 0)
    collected = passed + failed + errors + skipped
    functional_cases = [case for case in CASES if case.get("category") == "Functional"]
    functional_passed = sum(
        1 for case in functional_cases if results.get(case["function"], {}).get("status") == "Passed"
    )
    exit_code = EXIT_CODE.read_text(encoding="utf-8").strip() if EXIT_CODE.exists() else "unknown"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    notes = {"fixes": [], "limits": []}
    if NOTES.exists():
        notes.update(json.loads(NOTES.read_text(encoding="utf-8")))

    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "reports").mkdir(exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Case ID", "Category", "Test function", "Title", "Preconditions", "Steps", "Inputs", "Expected", "Trace", "Actual status", "Actual summary"])
        for case in CASES:
            result = results.get(case["function"])
            if result is None:
                status = "Not run"
                detail = "This function has no result in the JUnit file"
            else:
                status = result["status"]
                detail = result["detail"]
            writer.writerow(
                [
                    case["id"],
                    case["category"],
                    case["function"],
                    case["title"],
                    case["preconditions"],
                    case["steps"],
                    case["inputs"],
                    case["expected"],
                    case.get("trace", ""),
                    status,
                    detail,
                ]
            )

    lines = [
        "# Integration case table",
        "",
        f"{authored} cases were authored. Actual status comes from `{JUNIT.relative_to(ROOT)}` at {now}.",
        "Skipped is not passed. A case missing from this JUnit file is marked Not run.",
        "",
        "| Case ID | Category | Test function | Title | Actual status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for case in CASES:
        result = results.get(case["function"])
        status = "Not run" if result is None else result["status"]
        lines.append(f"| {case['id']} | {case['category']} | `{case['function']}` | {case['title']} | {status} |")
    functional = [case for case in CASES if case.get("category") == "Functional"]
    lines.extend(
        [
            "",
            "Preconditions, steps, inputs, expected results, traces, and actual summaries are in the CSV beside this file.",
            "",
            "## Functional inventory",
            "",
            f"{len(functional)} functional cases were authored as their own tests. Trace is file::function.",
            "",
            "| Case ID | Test function | Trace | Title | Actual status |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for case in functional:
        result = results.get(case["function"])
        status = "Not run" if result is None else result["status"]
        lines.append(
            f"| {case['id']} | `{case['function']}` | `{case.get('trace', '')}` | {case['title']} | {status} |"
        )
    lines.append("")
    MD_PATH.write_text("\n".join(lines), encoding="utf-8")

    coverage_summary, coverage_files = coverage_rows()
    report = [
        "# Linden Ledger integration report",
        "",
        "Linden Ledger is a coursework simulation. It is not a bank and it does not move real funds. This report is not a security audit.",
        "",
        "## 1. How to read the counts",
        "",
        "Authored cases, collected tests, passed, failed, errors, and skipped are different numbers. Skipped is not counted as passed.",
        "",
        f"- Authored cases: {authored}",
        f"- Tests collected in this JUnit file: {collected}",
        f"- Passed: {passed}",
        f"- Failed: {failed}",
        f"- Errors: {errors}",
        f"- Skipped: {skipped}",
        f"- Authored but missing from this run: {len(missing)}",
        f"- In JUnit but not in the catalog: {len(extra)}",
        f"- pytest exit code: {exit_code}",
        f"- Member B functional cases authored: {len(functional_cases)}",
        f"- Member B functional cases passed in this run: {functional_passed}",
        "",
        "## 2. Environment",
        "",
        f"- Generated (UTC): {now}",
        f"- System: {platform.platform()}",
        f"- Python: {sys.version.split()[0]}",
        "- Application: Flask and SQLite. Tests: pytest, pytest-cov, Selenium",
        "- Database: each case uses its own temporary SQLite file",
        "- Command: `bash scripts/run_tests.sh`",
        "",
        "## 3. Coverage",
        "",
        coverage_summary,
        "",
    ]
    if coverage_files:
        report.extend(["| File | Line coverage | Valid lines | Covered lines | Branch coverage |", "| --- | --- | --- | --- | --- |"])
        for filename, rate, valid, covered, branch in sorted(coverage_files):
            report.append(f"| `{filename}` | {rate} | {valid} | {covered} | {branch} |")
        report.append("")
    report.extend(["## 4. Skip reasons", ""])
    skip_rows = [
        (case["id"], case["function"], results[case["function"]]["detail"])
        for case in CASES
        if case["function"] in results and results[case["function"]]["status"] == "Skipped"
    ]
    if skip_rows:
        for case_id, function, detail in skip_rows:
            report.append(f"- {case_id} `{function}`: {detail}")
    else:
        report.append("No authored case was skipped in this run.")
    if missing:
        report.extend(["", "Authored cases with no result in this run:"])
        report.extend(f"- `{name}`" for name in missing)
    report.extend(["", "## 5. Failures and errors", ""])
    bad = [
        (case["id"], case["function"], results[case["function"]]["status"], results[case["function"]]["detail"])
        for case in CASES
        if case["function"] in results and results[case["function"]]["status"] in {"Failed", "Error"}
    ]
    if bad:
        for case_id, function, status, detail in bad:
            report.append(f"- {case_id} `{function}` {status}: {detail}")
    else:
        report.append("No executed case failed or errored in this run.")
    report.extend(["", "## 6. Problems actually seen and fixed", ""])
    fixes = notes.get("fixes") or []
    if fixes:
        for item in fixes:
            report.append(f"- {item}")
    else:
        report.append("No additional product defects were recorded before this run.")
    report.extend(
        [
            "",
            "## 7. Evidence",
            "",
            "- `reports/junit.xml`",
            "- `reports/pytest-output.txt`",
            "- `reports/pytest-exit-code.txt`",
            "- `reports/coverage.xml`",
            "- `reports/pytest-report.html`",
            "- `docs/test_cases.csv`",
            "- `docs/test_cases.md`",
            "- `docs/security/sqlmap_summary.md`",
            "- `docs/screenshots/` when the browser cases saved images",
            "",
            "## 8. SQLMap",
            "",
            *sqlmap_lines(),
            "",
            "## 9. Remaining limits",
            "",
            "- This is not a penetration test and not an assessment of a real bank. SQL injection, CSRF, session, and authorization checks cover only the cases named here.",
            "- SQLite immediate transactions prevent overdraft on one machine. They are not a production payment system.",
            "- Browser cases need a discoverable local Chrome or Chromium. If none is found, those cases are skipped and the reason is kept. A skip is not a pass.",
            "- The session cookie is not marked Secure on local HTTP. Set BANK_COOKIE_SECURE=1 only for HTTPS.",
            "- Pages do not show stack traces. Use the server log.",
            "- Demo passphrases are not in this report. Each fictional account has its own. They come from per-account environment variables or a gitignored local file, and only an Argon2id hash is stored.",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(report), encoding="utf-8")
    print(f"authored {authored}; collected {collected}; passed {passed}; failed {failed}; errors {errors}; skipped {skipped}")
    print(REPORT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
