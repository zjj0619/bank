# Written status updates

These are asynchronous written status updates reconstructed from the git history, the issue and risk log, the test reports, and the documents in this repository. They are not minutes of a verbal standup. No meeting was held. No attendance was taken. No dialogue or quotations are recorded, because none exist.

The repository owner is Jiaqi Zhu. The git history records the co-author handle `zjj0619`. No other personal names are recorded. The names below are role names only.

## 2026-11-11, commit 6ce4abb

### Member E

## Date
2026-11-11

## Name
Member E

## Yesterday
This repository has no earlier commit.

## Today
The initial commit is present. It does not contain the ledger application.

## Blocked by
Nothing is recorded.

## Help needed
Nothing is recorded.

## 2026-11-11 09:06 UTC, commit 56c23b1

The files in that commit are the evidence. The issue rows inside it are dated 2026-11-10. That date is not treated here as a meeting.

### Member A

## Date
2026-11-11

## Name
Member A

## Yesterday
The only earlier commit does not contain the application.

## Today
The Flask ledger, English pages, SQLite books, and three fictional accounts are in the tree. The issue log marks F-01, F-02, and F-03 Fixed.

## Blocked by
Nothing is recorded.

## Help needed
Nothing is recorded.

### Member B

## Date
2026-11-11

## Name
Member B

## Yesterday
No separate functional inventory is in the earlier commit.

## Today
The catalog has 59 cases. `docs/integration_report.md` in that commit says it was generated at 2026-11-11T08:30:58Z with 59 collected, 59 passed, 0 failed, 0 errors, 0 skipped, and pytest exit code 0. Line coverage in that report is 87.7% (872/994). There is no separate inventory of 40 functional cases. The coverage table shows `app/secrets.py` at 59.5% and `app/services.py` missing the receiver-cap check and the race-recovery path.

## Blocked by
Nothing is recorded.

## Help needed
Nothing is recorded.

### Member C

## Date
2026-11-11

## Name
Member C

## Yesterday
No SQLMap output is in the tree.

## Today
Pytest cases IT-39 and IT-40 passed in the 59-case report. They are application tests, not SQLMap runs. The issue log has no CVSS score. Risks R-01 through R-04 are marked Accepted.

## Blocked by
Nothing is recorded.

## Help needed
Nothing is recorded.

### Member D

## Date
2026-11-11

## Name
Member D

## Yesterday
Nothing is recorded before the application commit.

## Today
Browser cases IT-47 and IT-48 passed in that report. The tests use a server fixture and helper functions. There is no Page Object class, no HTML or Allure report, no GitHub Actions workflow, and no browser-level failed-login test. Failed login is the API case IT-43.

## Blocked by
Nothing is recorded. R-02 says the browser cases need Chrome or Chromium.

## Help needed
Nothing is recorded.

### Member E

## Date
2026-11-11

## Name
Member E

## Yesterday
Nothing is recorded before the application commit.

## Today
The README, architecture, schema, milestone plan, progress tracker, and risk log are present. This file said that no standup had been held.

## Blocked by
Nothing is recorded.

## Help needed
Nothing is recorded.

## 2026-11-11, follow-up written from the new run

This section describes the change after commit 56c23b1. It was written from the files in that change. The pytest numbers are copied from `docs/integration_report.md` generated at 2026-11-11T12:51:43Z.

### Member A

## Date
2026-11-11

## Name
Member A

## Yesterday
The application in commit 56c23b1, with F-01, F-02, and F-03 already marked Fixed.

## Today
No new product defect was opened. `app/secrets.py` line coverage in this run is 100.0% (84/84). The earlier three fixes stay Fixed.

## Blocked by
Nothing is recorded.

## Help needed
Nothing is recorded.

### Member B

## Date
2026-11-11

## Name
Member B

## Yesterday
59 catalog cases and no separate functional inventory.

## Today
52 functional cases, FC-01 through FC-52, were written as their own tests and executed. The run collected 119 tests: 119 passed, 0 failed, 0 errors, 0 skipped, pytest exit code 0. Line coverage is 95.3% (947/994). Branch coverage is 89.6% (283/316). All 52 functional cases passed. They include the 100-character note limit, the receiver balance cap, concurrent transfers, and the integrity-error recovery branches.

## Blocked by
Nothing is recorded.

## Help needed
Nothing is recorded.

### Member C

## Date
2026-11-11

## Name
Member C

## Yesterday
SQLMap had not been run.

## Today
SQLMap 1.10.3 was run against a temporary server bound only to 127.0.0.1. Eight runs used techniques U and B on the sign-in username, the sign-in passphrase field, `account_no`, `user_id`, `limit`, and `offset`. Every saved conclusion says the tested parameters do not appear to be injectable. No CVSS score was assigned. No new defect was opened. IT-39 and IT-40 remain and now also send UNION and boolean-style strings.

## Blocked by
Nothing is recorded.

## Help needed
Nothing is recorded.

### Member D

## Date
2026-11-11

## Name
Member D

## Yesterday
No Page Object classes, HTML report, or CI workflow.

## Today
The Selenium tests use page objects in `tests/pages.py`. The browser failed-login case passed and stayed on the sign-in page. `reports/pytest-report.html` was generated by pytest-html. The test command also writes Allure results; that directory is gitignored and the workflow uploads it. The workflow is `.github/workflows/tests.yml`.

## Blocked by
Nothing new is recorded. R-02 still applies: the browser cases need Chrome or Chromium.

## Help needed
Nothing is recorded.

### Member E

## Date
2026-11-11

## Name
Member E

## Yesterday
This file said that no standup had been held.

## Today
That sentence is replaced by these written updates. The progress tracker and milestone plan now list the functional inventory, the SQLMap evidence, the page objects and CI, and these updates. Pass counts stay in the integration report.

## Blocked by
Nothing is recorded.

## Help needed
Nothing is recorded.
