"""Run SQLMap against this coursework app on 127.0.0.1 only.

The process refuses any other host. It writes a sanitized summary and logs.
It does not print passphrases.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timezone
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from werkzeug.serving import make_server

from tests.helpers import FIXTURE_PASSWORDS, make_app

SUMMARY = ROOT / "docs" / "security" / "sqlmap_summary.md"
LOG_DIR = ROOT / "docs" / "security" / "sqlmap"
OUTCOME = ROOT / "reports" / "sqlmap_outcome.json"
SQLMAP = Path(__import__("sqlmap").__file__).resolve().parent / "sqlmap.py"


def assert_local(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or not parsed.port:
        raise SystemExit("Refusing a target that is not http://127.0.0.1:<port>")


def scrub(text: str, banned: list[str]) -> str:
    cleaned = text
    for secret in banned:
        if secret:
            cleaned = cleaned.replace(secret, "[redacted]")
    cleaned = re.sub(r"chengbu_session=[^'\"\s)]+", "chengbu_session=[redacted]", cleaned)
    cleaned = re.sub(r"(csrf_token=)[^&\s\"']+", r"\1[redacted]", cleaned)
    return cleaned


def banned_values(application) -> list[str]:
    return [
        *FIXTURE_PASSWORDS.values(),
        application.config.get("SECRET_KEY", ""),
    ]


def judge(text: str) -> tuple[bool | None, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if "identified the following injection point" in line.lower():
            return True, line
    finals = [line for line in lines if "all tested parameters do not appear to be injectable" in line.lower()]
    if finals:
        return False, finals[-1]
    return None, lines[-1] if lines else "no output"


def request(opener, method: str, url: str, data: bytes | None = None, headers: dict | None = None):
    assert_local(url)
    req = Request(url, data=data, headers=headers or {}, method=method)
    try:
        with opener.open(req, timeout=20) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def session_cookie(jar: CookieJar) -> str:
    for cookie in jar:
        if cookie.name == "chengbu_session":
            return cookie.value
    raise SystemExit("The local sign-in did not set a session cookie.")


def run_sqlmap(cmd: list[str], workdir: Path) -> tuple[int, str]:
    for part in cmd:
        if part.startswith("http://") or part.startswith("https://"):
            assert_local(part)
    completed = subprocess.run(
        cmd,
        cwd=workdir,
        text=True,
        capture_output=True,
        check=False,
        timeout=420,
    )
    return completed.returncode, completed.stdout + "\n" + completed.stderr


def main() -> int:
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    for old_log in LOG_DIR.glob("*.log"):
        old_log.unlink()
    OUTCOME.parent.mkdir(parents=True, exist_ok=True)
    version = subprocess.run(
        [sys.executable, str(SQLMAP), "--version"],
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()
    with tempfile.TemporaryDirectory(prefix="linden-sqlmap-") as temporary:
        root = Path(temporary)
        application = make_app(root, LOCKOUT_THRESHOLD=100000, LOCKOUT_SECONDS=1)
        server = make_server("127.0.0.1", 0, application, threaded=True)
        host, port = server.server_address[0], int(server.server_address[1])
        if host != "127.0.0.1":
            raise SystemExit(f"Refusing to scan a server bound to {host}")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{port}"
        assert_local(base + "/")
        jar = CookieJar()
        opener = build_opener(HTTPCookieProcessor(jar))
        status, body = request(opener, "GET", base + "/api/v1/csrf")
        if status != 200:
            raise SystemExit(f"Local CSRF request failed with status {status}")
        token = json.loads(body)["csrf_token"]
        payload = json.dumps(
            {"username": "demo_zhang", "password": FIXTURE_PASSWORDS["demo_zhang"]}
        ).encode("utf-8")
        status, body = request(
            opener,
            "POST",
            base + "/api/v1/auth/login",
            data=payload,
            headers={"Content-Type": "application/json", "X-CSRF-Token": token},
        )
        if status != 200:
            raise SystemExit(f"Local sign-in failed with status {status}")
        cookie = session_cookie(jar)
        banned = banned_values(application) + [cookie, token, json.loads(body)["csrf_token"]]
        plans = [
            {
                "name": "login-password-union",
                "technique": "U",
                "url": base + "/login",
                "parameters": ["password"],
                "extra": [
                    "--data",
                    "csrf_token=placeholder&username=demo_zhang&password=probe",
                    "--csrf-token",
                    "csrf_token",
                    "--csrf-url",
                    base + "/login",
                    "--ignore-code",
                    "401",
                    "-p",
                    "password",
                ],
            },
            {
                "name": "login-password-blind",
                "technique": "B",
                "url": base + "/login",
                "parameters": ["password"],
                "extra": [
                    "--data",
                    "csrf_token=placeholder&username=demo_zhang&password=probe",
                    "--csrf-token",
                    "csrf_token",
                    "--csrf-url",
                    base + "/login",
                    "--ignore-code",
                    "401",
                    "-p",
                    "password",
                ],
            },
            {
                "name": "login-username-union",
                "technique": "U",
                "url": base + "/login",
                "parameters": ["username"],
                "extra": [
                    "--data",
                    "csrf_token=placeholder&username=demo_zhang&password=probe",
                    "--csrf-token",
                    "csrf_token",
                    "--csrf-url",
                    base + "/login",
                    "--ignore-code",
                    "401",
                    "-p",
                    "username",
                ],
            },
            {
                "name": "login-username-blind",
                "technique": "B",
                "url": base + "/login",
                "parameters": ["username"],
                "extra": [
                    "--data",
                    "csrf_token=placeholder&username=demo_zhang&password=probe",
                    "--csrf-token",
                    "csrf_token",
                    "--csrf-url",
                    base + "/login",
                    "--ignore-code",
                    "401",
                    "-p",
                    "username",
                ],
            },
            {
                "name": "account-union",
                "technique": "U",
                "url": base + "/api/v1/account?account_no=SIM-1001&user_id=1",
                "parameters": ["account_no", "user_id"],
                "extra": ["--cookie", f"chengbu_session={cookie}", "-p", "account_no,user_id"],
            },
            {
                "name": "account-blind",
                "technique": "B",
                "url": base + "/api/v1/account?account_no=SIM-1001&user_id=1",
                "parameters": ["account_no", "user_id"],
                "extra": ["--cookie", f"chengbu_session={cookie}", "-p", "account_no,user_id"],
            },
            {
                "name": "transactions-union",
                "technique": "U",
                "url": base + "/api/v1/transactions?limit=20&offset=0",
                "parameters": ["limit", "offset"],
                "extra": ["--cookie", f"chengbu_session={cookie}", "-p", "limit,offset"],
            },
            {
                "name": "transactions-blind",
                "technique": "B",
                "url": base + "/api/v1/transactions?limit=20&offset=0",
                "parameters": ["limit", "offset"],
                "extra": ["--cookie", f"chengbu_session={cookie}", "-p", "limit,offset"],
            },
        ]
        runs = []
        try:
            for plan in plans:
                assert_local(plan["url"])
                work = root / plan["name"]
                work.mkdir()
                cmd = [
                    sys.executable,
                    str(SQLMAP),
                    "-u",
                    plan["url"],
                    "--batch",
                    "--technique",
                    plan["technique"],
                    "--level",
                    "1",
                    "--risk",
                    "1",
                    "--threads",
                    "1",
                    "--timeout",
                    "15",
                    "--retries",
                    "1",
                    "--fresh-queries",
                    "--flush-session",
                    "--output-dir",
                    str(work),
                    *plan["extra"],
                ]
                code, output = run_sqlmap(cmd, work)
                cleaned = scrub(output, banned)
                injectable, conclusion = judge(cleaned)
                if injectable is None:
                    (LOG_DIR / f"{plan['name']}.log").write_text(cleaned, encoding="utf-8")
                    raise SystemExit(f"{plan['name']} had no recognizable SQLMap conclusion")
                conclusion = scrub(conclusion, banned)
                log_rel = f"docs/security/sqlmap/{plan['name']}.log"
                header = (
                    f"Target: {plan['url']}\n"
                    f"Technique: {plan['technique']}\n"
                    f"Parameters: {', '.join(plan['parameters'])}\n\n"
                )
                (ROOT / log_rel).write_text(header + cleaned, encoding="utf-8")
                runs.append(
                    {
                        "name": plan["name"],
                        "technique": plan["technique"],
                        "url": plan["url"],
                        "parameters": plan["parameters"],
                        "exit_code": code,
                        "injectable": injectable,
                        "conclusion": conclusion,
                        "log": log_rel,
                    }
                )
        finally:
            server.shutdown()
    injectable = any(item["injectable"] for item in runs)
    outcome = {
        "tool": "sqlmap",
        "tool_version": version,
        "host": "127.0.0.1",
        "bind": "127.0.0.1",
        "techniques": ["U", "B"],
        "injectable": injectable,
        "cvss": None,
        "targets": [item["url"] for item in runs],
        "runs": runs,
    }
    OUTCOME.write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8")
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# SQLMap evidence",
        "",
        "Linden Ledger is a coursework simulation. It is not a bank and it does not move real funds. This file is not a penetration test of a real system.",
        "",
        f"SQLMap {version} was run from this repository against a temporary server bound only to 127.0.0.1. No other host was scanned. The sign-in field sent to SQLMap used the marker `probe`. Session cookies and tokens were removed from the saved logs.",
        "",
        f"Generated (UTC): {generated}",
        "",
        f"Injectable parameter reported: {injectable}",
        "",
    ]
    if injectable:
        lines.append("At least one run reported an injection point. See the issue log before treating the application as unchanged.")
    else:
        lines.extend(
            [
                "No run reported an injection point. The saved conclusion from SQLMap is quoted below. No vulnerability score was assigned.",
                "",
            ]
        )
    for item in runs:
        lines.append(
            f"- `{item['name']}` technique `{item['technique']}` parameters {', '.join(item['parameters'])}: {item['conclusion']}"
        )
        lines.append(f"  Log: `{item['log']}`")
    lines.extend(
        [
            "",
            "The checked parameters were the sign-in username and passphrase fields, `account_no` and `user_id` on the account read, and `limit` and `offset` on activity. UNION (`U`) and boolean blind (`B`) were separate runs. Existing parameterized checks in the pytest suite were left in place and extended with UNION and boolean-style strings.",
            "",
            "A state-changing transfer was not used as a SQLMap target. Its idempotency key would change later responses and could be mistaken for a finding. Transfer fields remain covered by the pytest cases, which keep SQL text as data.",
            "",
        ]
    )
    SUMMARY.write_text("\n".join(lines), encoding="utf-8")
    # The temporary database from make_app lives under the deleted temp dir.
    # Drop any sqlite session files SQLMap may have left in the log directory.
    for path in LOG_DIR.rglob("*"):
        if path.suffix in {".sqlite", ".sqlite3"} or path.name.endswith(".session"):
            path.unlink()
    print(f"injectable {injectable}; runs {len(runs)}; summary {SUMMARY}")
    return 1 if injectable else 0


if __name__ == "__main__":
    raise SystemExit(main())
