# Milestone plan

The coursework weights are 30% system, 40% integration, and 30% management. This table is an editable checklist of deliverables. It is not a timesheet and it is not the minutes of a meeting.

| Milestone | Weight | Deliverable | Done when | Status |
| --- | --- | --- | --- | --- |
| M1 System | 30% | Flask app, SQLite books, sign-in, deposit, withdrawal, transfer, activity, integer fen, idempotency, CSRF | The app starts locally and can post a simulated movement | Done |
| M2 Integration | 40% | Case catalog, English case table, balance and ledger checks, both sides of a transfer, security cases, browser sign-in, JUnit | The report separates authored cases from passed, failed, and skipped | Done |
| M3 Management | 30% | README, architecture, schema, this plan, standup template, progress and risk notes, source zip | Docs are editable, the reset command is explicit, and the passphrase is not in the report | Done |
| M2 Integration | 40% | At least 40 separate functional cases, with the receiver cap, race recovery, concurrent transfers, and the 100-character note | Each case has its own test and a trace | Done |
| M2 Integration | 40% | SQLMap UNION and blind runs against 127.0.0.1 only | Sanitized logs are saved and no score is invented | Done |
| M2 Integration | 40% | Page objects, a browser failed-login case, HTML and Allure output, and GitHub Actions | CI runs pytest headless and uploads the reports | Done |
| M3 Management | 30% | Written status updates reconstructed from the repository | The log says it is not minutes of a verbal standup | Done |

The weights add to 100%. The spreadsheet form is `milestone_plan.csv`. Later rows record deliverables that were missing from the first report.
