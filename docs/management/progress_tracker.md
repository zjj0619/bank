# Progress check

Checked on 2026-11-11. This list says whether a deliverable is in the repository. Pass, fail, and skip counts belong only in `docs/integration_report.md`, from a real run. They are not copied here as a second set of numbers.

| Stream | Weight | Task | Status | Evidence |
| --- | --- | --- | --- | --- |
| System | 30% | Sign-in, balance, movements, integer fen, transactions, idempotency | Done | `app/`, `run.py` |
| System | 30% | English pages, local photograph, local type | Done | `app/templates/`, `app/static/` |
| Integration | 40% | Case catalog | Done | `tests/case_catalog.py` |
| Integration | 40% | Executed results | See the report | `reports/junit.xml`, `docs/integration_report.md` |
| Management | 30% | README, architecture, schema, API, asset notes | Done | `README.md`, `docs/` |
| Management | 30% | Plan, standup template, risk log | Done | this directory |
| Integration | 40% | Separate functional inventory | Done | `tests/test_functional.py`, `tests/functional_catalog.py` |
| Integration | 40% | Local SQLMap evidence | Done | `docs/security/sqlmap_summary.md` |
| Integration | 40% | Page objects, HTML report, and CI | Done | `tests/pages.py`, `reports/pytest-report.html`, `.github/workflows/tests.yml` |
| Management | 30% | Written status updates | Done | `docs/management/standup_log.md` |

The spreadsheet form is `progress_tracker.csv`. The functional inventory, SQLMap evidence, page objects, CI, and written status updates were added after the first 59-case report. Pass counts stay in the integration report.
