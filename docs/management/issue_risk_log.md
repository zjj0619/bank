# Issues and risks

Only items that actually showed up, plus limits that are still true. There are no invented ticket numbers and no invented meetings.

| ID | Type | What happened | Effect | Handling | Status |
| --- | --- | --- | --- | --- | --- |
| F-01 | Defect | `services.py` called the immediate-transaction helper without importing it | Seeding failed | Import added and the suite re-run | Fixed |
| F-02 | Defect | Very long digit amounts were labeled as bad format | Overflow cases were unstable | They now return `amount_overflow` | Fixed |
| F-03 | Design | The first pages were plain and in Chinese | The coursework UI did not meet the later brief | Rebuilt as Linden Ledger in English, with local type and a bundled photograph. Account ids and opening amounts were kept | Fixed |
| R-01 | Risk | SQLite has one writer | Fine for class, not a payment system | Stated in the architecture and the report | Accepted |
| R-02 | Risk | Browser cases need local Chrome or Chromium | They skip when the browser cannot start | `CHROME_BIN` override, otherwise auto-discovery. The skip reason is kept | Accepted |
| R-03 | Risk | A committed passphrase would leak | Someone else could open the local demo | Git ignores the file and the program does not print it | Accepted |
| R-04 | Limit | The security cases are not a full audit | They do not describe a real bank | The report says so | Accepted |

The spreadsheet form is `issue_risk_log.csv`.

On 2026-11-11, SQLMap 1.10.3 was run against a temporary server bound only to 127.0.0.1. UNION and boolean-blind checks were separate runs. SQLMap reported that every tested parameter does not appear to be injectable. No new defect was opened, and no CVSS score was assigned. The sanitized output is in `docs/security/sqlmap_summary.md`.
