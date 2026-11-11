# Progress check

Checked on 2026-11-10. This list says whether a deliverable is in the repository. Pass, fail, and skip counts belong only in `docs/integration_report.md`, from a real run. They are not copied here as a second set of numbers.

| Stream | Weight | Task | Status | Evidence |
| --- | --- | --- | --- | --- |
| System | 30% | Sign-in, balance, movements, integer fen, transactions, idempotency | Done | `app/`, `run.py` |
| System | 30% | English pages, local photograph, local type | Done | `app/templates/`, `app/static/` |
| Integration | 40% | Case catalog | Done | `tests/case_catalog.py` |
| Integration | 40% | Executed results | See the report | `reports/junit.xml`, `docs/integration_report.md` |
| Management | 30% | README, architecture, schema, API, asset notes | Done | `README.md`, `docs/` |
| Management | 30% | Plan, standup template, risk log | Done | this directory |

The spreadsheet form is `progress_tracker.csv`.
