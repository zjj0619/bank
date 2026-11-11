# Linden Ledger integration report

Linden Ledger is a coursework simulation. It is not a bank and it does not move real funds. This report is not a security audit.

## 1. How to read the counts

Authored cases, collected tests, passed, failed, errors, and skipped are different numbers. Skipped is not counted as passed.

- Authored cases: 59
- Tests collected in this JUnit file: 59
- Passed: 59
- Failed: 0
- Errors: 0
- Skipped: 0
- Authored but missing from this run: 0
- In JUnit but not in the catalog: 0
- pytest exit code: 0

## 2. Environment

- Generated (UTC): 2026-11-11T08:30:58Z
- System: Linux-6.12.113+-x86_64-with-glibc2.39
- Python: 3.12.3
- Application: Flask and SQLite. Tests: pytest, pytest-cov, Selenium
- Database: each case uses its own temporary SQLite file
- Command: `python -m pytest --junitxml=reports/junit.xml --cov=app --cov-report=term-missing --cov-report=xml:reports/coverage.xml`

## 3. Coverage

Line coverage 87.7% (872/994 lines)

| File | Line coverage | Valid lines | Covered lines |
| --- | --- | --- | --- |
| `app/__init__.py` | 87.5% | 80 | 70 |
| `app/db.py` | 86.7% | 60 | 52 |
| `app/errors.py` | 100.0% | 8 | 8 |
| `app/maintenance.py` | 100.0% | 17 | 17 |
| `app/money.py` | 94.3% | 53 | 50 |
| `app/passwords.py` | 83.3% | 102 | 85 |
| `app/paths.py` | 93.3% | 15 | 14 |
| `app/routes/__init__.py` | 100.0% | 0 | 0 |
| `app/routes/api.py` | 98.2% | 108 | 106 |
| `app/routes/web.py` | 92.8% | 166 | 154 |
| `app/secrets.py` | 59.5% | 84 | 50 |
| `app/seed_data.py` | 100.0% | 2 | 2 |
| `app/services.py` | 87.0% | 247 | 215 |
| `app/webutil.py` | 94.2% | 52 | 49 |

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
- `reports/coverage.xml`
- `docs/test_cases.csv`
- `docs/test_cases.md`
- `docs/screenshots/` when the browser cases saved images

## 8. Remaining limits

- This is not a penetration test and not an assessment of a real bank. SQL injection, CSRF, session, and authorization checks cover only the cases named here.
- SQLite immediate transactions prevent overdraft on one machine. They are not a production payment system.
- Browser cases need a discoverable local Chrome or Chromium. If none is found, those cases are skipped and the reason is kept. A skip is not a pass.
- The session cookie is not marked Secure on local HTTP. Set BANK_COOKIE_SECURE=1 only for HTTPS.
- Pages do not show stack traces. Use the server log.
- Demo passphrases are not in this report. Each fictional account has its own. They come from per-account environment variables or a gitignored local file, and only an Argon2id hash is stored.
