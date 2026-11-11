# Linden Ledger integration report

Linden Ledger is a coursework simulation. It is not a bank and it does not move real funds. This report is not a security audit.

## 1. How to read the counts

Authored cases, collected tests, passed, failed, errors, and skipped are different numbers. Skipped is not counted as passed.

- Authored cases: 119
- Tests collected in this JUnit file: 119
- Passed: 119
- Failed: 0
- Errors: 0
- Skipped: 0
- Authored but missing from this run: 0
- In JUnit but not in the catalog: 0
- pytest exit code: 0
- Member B functional cases authored: 52
- Member B functional cases passed in this run: 52

## 2. Environment

- Generated (UTC): 2026-11-11T12:51:43Z
- System: Linux-6.12.113+-x86_64-with-glibc2.39
- Python: 3.12.3
- Application: Flask and SQLite. Tests: pytest, pytest-cov, Selenium
- Database: each case uses its own temporary SQLite file
- Command: `bash scripts/run_tests.sh`

## 3. Coverage

Line coverage 95.3% (947/994 lines). Branch coverage 89.6% (283/316 branches)

| File | Line coverage | Valid lines | Covered lines | Branch coverage |
| --- | --- | --- | --- | --- |
| `app/__init__.py` | 87.5% | 80 | 70 | 61.1% |
| `app/db.py` | 86.7% | 60 | 52 | 71.4% |
| `app/errors.py` | 100.0% | 8 | 8 | 100.0% |
| `app/maintenance.py` | 100.0% | 17 | 17 | 100.0% |
| `app/money.py` | 94.3% | 53 | 50 | 91.2% |
| `app/passwords.py` | 94.1% | 102 | 96 | 95.0% |
| `app/paths.py` | 93.3% | 15 | 14 | 50.0% |
| `app/routes/__init__.py` | 100.0% | 0 | 0 | 100.0% |
| `app/routes/api.py` | 99.1% | 108 | 107 | 94.4% |
| `app/routes/web.py` | 97.0% | 166 | 161 | 89.5% |
| `app/secrets.py` | 100.0% | 84 | 84 | 100.0% |
| `app/seed_data.py` | 100.0% | 2 | 2 | 100.0% |
| `app/services.py` | 96.0% | 247 | 237 | 90.0% |
| `app/webutil.py` | 94.2% | 52 | 49 | 87.5% |

## 4. Skip reasons

No authored case was skipped in this run.

## 5. Failures and errors

No executed case failed or errored in this run.

## 6. Problems actually seen and fixed

- The first test run failed while seeding because immediate_transaction was used without an import. The import was added and the suite was run again.
- Very long digit-only amounts were labeled invalid_amount. They now return amount_overflow.
- The visible interface was still Chinese and visually plain. It was rebuilt in English as Linden Ledger with bundled type and photography. Account ids and opening amounts were not changed.

## 7. Evidence

- `reports/junit.xml`
- `reports/pytest-output.txt`
- `reports/pytest-exit-code.txt`
- `reports/coverage.xml`
- `reports/pytest-report.html`
- `docs/test_cases.csv`
- `docs/test_cases.md`
- `docs/security/sqlmap_summary.md`
- `docs/screenshots/` when the browser cases saved images

## 8. SQLMap

- Tool: sqlmap 1.10.3#pip
- Bind and host: 127.0.0.1
- Techniques: U, B
- Injectable parameter reported: False
- CVSS: not assigned, because no injectable parameter was reported.
- login-password-union: technique U on http://127.0.0.1:40037/login — [12:48:51] [CRITICAL] all tested parameters do not appear to be injectable. Try to increase values for '--level'/'--risk' options if you wish to perform more tests. Rerun without providing the option '--technique'. If you suspect that there is some kind of protection mechanism involved (e.g. WAF) maybe you could try to use option '--tamper' (e.g. '--tamper=space2comment') and/or switch '--random-agent'
- login-password-blind: technique B on http://127.0.0.1:40037/login — [12:48:52] [CRITICAL] all tested parameters do not appear to be injectable. Try to increase values for '--level'/'--risk' options if you wish to perform more tests. Rerun without providing the option '--technique'. If you suspect that there is some kind of protection mechanism involved (e.g. WAF) maybe you could try to use option '--tamper' (e.g. '--tamper=space2comment') and/or switch '--random-agent'
- login-username-union: technique U on http://127.0.0.1:40037/login — [12:48:52] [CRITICAL] all tested parameters do not appear to be injectable. Try to increase values for '--level'/'--risk' options if you wish to perform more tests. Rerun without providing the option '--technique'. If you suspect that there is some kind of protection mechanism involved (e.g. WAF) maybe you could try to use option '--tamper' (e.g. '--tamper=space2comment') and/or switch '--random-agent'
- login-username-blind: technique B on http://127.0.0.1:40037/login — [12:48:53] [CRITICAL] all tested parameters do not appear to be injectable. Try to increase values for '--level'/'--risk' options if you wish to perform more tests. Rerun without providing the option '--technique'. If you suspect that there is some kind of protection mechanism involved (e.g. WAF) maybe you could try to use option '--tamper' (e.g. '--tamper=space2comment') and/or switch '--random-agent'
- account-union: technique U on http://127.0.0.1:40037/api/v1/account?account_no=SIM-1001&user_id=1 — [12:48:53] [CRITICAL] all tested parameters do not appear to be injectable. Try to increase values for '--level'/'--risk' options if you wish to perform more tests. Rerun without providing the option '--technique'. If you suspect that there is some kind of protection mechanism involved (e.g. WAF) maybe you could try to use option '--tamper' (e.g. '--tamper=space2comment') and/or switch '--random-agent'
- account-blind: technique B on http://127.0.0.1:40037/api/v1/account?account_no=SIM-1001&user_id=1 — [12:48:54] [CRITICAL] all tested parameters do not appear to be injectable. Try to increase values for '--level'/'--risk' options if you wish to perform more tests. Rerun without providing the option '--technique'. If you suspect that there is some kind of protection mechanism involved (e.g. WAF) maybe you could try to use option '--tamper' (e.g. '--tamper=space2comment') and/or switch '--random-agent'
- transactions-union: technique U on http://127.0.0.1:40037/api/v1/transactions?limit=20&offset=0 — [12:48:55] [CRITICAL] all tested parameters do not appear to be injectable. Try to increase values for '--level'/'--risk' options if you wish to perform more tests. Rerun without providing the option '--technique'. If you suspect that there is some kind of protection mechanism involved (e.g. WAF) maybe you could try to use option '--tamper' (e.g. '--tamper=space2comment') and/or switch '--random-agent'
- transactions-blind: technique B on http://127.0.0.1:40037/api/v1/transactions?limit=20&offset=0 — [12:48:56] [CRITICAL] all tested parameters do not appear to be injectable. Try to increase values for '--level'/'--risk' options if you wish to perform more tests. Rerun without providing the option '--technique'. If you suspect that there is some kind of protection mechanism involved (e.g. WAF) maybe you could try to use option '--tamper' (e.g. '--tamper=space2comment') and/or switch '--random-agent'

## 9. Remaining limits

- This is not a penetration test and not an assessment of a real bank. SQL injection, CSRF, session, and authorization checks cover only the cases named here.
- SQLite immediate transactions prevent overdraft on one machine. They are not a production payment system.
- Browser cases need a discoverable local Chrome or Chromium. If none is found, those cases are skipped and the reason is kept. A skip is not a pass.
- The session cookie is not marked Secure on local HTTP. Set BANK_COOKIE_SECURE=1 only for HTTPS.
- Pages do not show stack traces. Use the server log.
- Demo passphrases are not in this report. Each fictional account has its own. They come from per-account environment variables or a gitignored local file, and only an Argon2id hash is stored.
