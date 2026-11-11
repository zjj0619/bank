# Linden Ledger

Linden Ledger is a coursework simulation of a small house ledger. It shows sign-in, balance, deposit, withdrawal, transfer, and activity. The books live in a local SQLite file.

It is not a bank. It does not connect to a payment network and it does not move real funds. Every page says so.

## Stack

- Python 3.11 or newer (developed on 3.12)
- Flask 3.1.3, server-rendered pages
- SQLite, with money stored as integer fen. 1 CNY = 100 fen
- pytest 9.2.0 and pytest-cov 7.1.0
- Selenium 4.52.0, only when a local browser can be discovered

Pinned dependencies are in `requirements.txt`. No paid service is required.

## Fictional accounts

Each fictional account has its own passphrase. The passphrases are not written in this file and are not shown on the page.

| Username | Name | Simulated account | Opening balance |
| --- | --- | --- | --- |
| demo_zhang | Mingyuan Zhang | SIM-1001 | 10,000.00 CNY |
| demo_li | Wanqing Li | SIM-1002 | 5,000.00 CNY |
| demo_wang | Qinian Wang | SIM-1003 | 2,580.25 CNY |

`SIM-` numbers are fictional. They are not card numbers. The names were romanized for the English interface. The account ids and opening amounts did not change.

## Passphrase

Each account has a different passphrase. The program never prints one.

Set these before the first start, one value per account:

- `BANK_SEED_PASSWORD_DEMO_ZHANG`
- `BANK_SEED_PASSWORD_DEMO_LI`
- `BANK_SEED_PASSWORD_DEMO_WANG`

A passphrase must be at least 12 characters and include an uppercase letter, a lowercase letter, a digit, and a symbol. The same rules apply when you change it after sign-in. Common, repeated, sequential, and keyboard-pattern passphrases are rejected, as are passphrases that contain the username, the display name, or the simulated account id. Two accounts cannot be given the same passphrase.

If an account has no environment value and no saved value, the first initialization writes `.demo_credentials` in the project root, with one line per username. Git ignores that file. Read it locally. Do not commit it or paste it into a report. An older file that only has `BANK_SEED_PASSWORD` is ignored.

The session key works the same way: set `BANK_SECRET_KEY`, or let the app write the ignored file `.session_secret`.

Passphrases are stored as Argon2id hashes. Five failed sign-ins lock that account for 15 minutes. The failure message does not say whether the username exists. A signed-in user can change the passphrase on the Passphrase page or with `POST /api/v1/auth/password`. That signs out other sessions for the same account. The banking session lasts 30 minutes.

Tests use a separate temporary database and fixture passphrases. They do not read or overwrite the demo file.

Rebuilding the database deletes the simulated entries. It does not print the passphrases.

## Install and run

From the project root.

### Linux and macOS

```bash
bash scripts/start.sh
```

That creates `.venv` if needed, installs the pinned dependencies, and starts the server.

By hand:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
```

By hand:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run.py
```

The default address is <http://127.0.0.1:47653>. Set `PORT` if that port is taken, and `HOST` for the bind address. Use it on your own machine or an isolated classroom network. Do not expose it to the public internet.

## Tests

```bash
bash scripts/run_tests.sh
```

On Windows, after the virtual environment is active:

```powershell
python -m pytest --junitxml=reports/junit.xml --cov=app --cov-report=term-missing --cov-report=xml:reports/coverage.xml
python scripts/build_report.py
```

Each case uses its own temporary database. Raw results are in `reports/junit.xml`. The English case table and report are written from that file to `docs/test_cases.csv`, `docs/test_cases.md`, and `docs/integration_report.md`.

Browser cases do not hard-code a machine-specific Chrome path.

- `CHROME_BIN` or `BANK_CHROME_BIN` selects the browser executable when set.
- Otherwise Selenium Manager looks for Chrome or Chromium on `PATH`.
- `CHROMEDRIVER` or `BANK_CHROMEDRIVER` can select the driver. Otherwise that is discovered too.
- If no browser can be started, those cases are skipped and the reason is kept in the report. A skip is not a pass.

GitHub Actions runs this suite on pull requests and on `main`. The workflow is `.github/workflows/tests.yml`. It installs Chrome, runs the browser cases headless, and uploads JUnit, coverage, the HTML report, and Allure results as artifacts. `reports/pytest-report.html` is the HTML report from pytest-html. Allure's raw result files are not committed.

SQLMap evidence, from a run bound only to `127.0.0.1`, is in `docs/security/sqlmap_summary.md`.

## API example

Fetch a CSRF token, then sign in. Replace the passphrase with your own.

```bash
curl -c /tmp/linden.txt -b /tmp/linden.txt http://127.0.0.1:47653/api/v1/csrf
curl -c /tmp/linden.txt -b /tmp/linden.txt \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: THE_TOKEN_FROM_THE_PREVIOUS_CALL" \
  -d '{"username":"demo_zhang","password":"YOUR_PASSPHRASE"}' \
  http://127.0.0.1:47653/api/v1/auth/login
curl -b /tmp/linden.txt http://127.0.0.1:47653/api/v1/account
```

Send amounts as strings with at most two decimal places. JSON floats are rejected. See `docs/api.md`.

## Pictures and type

Photographs and fonts are stored in the repository. Licenses and sources are in `docs/assets.md`.

## Reset

This command deletes the local simulated database and every entry. It cannot be undone.

```bash
python scripts/reset_db.py --yes
```

Without `--yes` it only prints a warning and deletes nothing.

## Optional Docker

Python alone is enough. If you use Docker, pass the passphrase from the environment. Do not bake it into the image.

```bash
docker build -t linden-ledger .
docker run --rm -p 47653:47653 -e BANK_SEED_PASSWORD_DEMO_ZHANG -e BANK_SEED_PASSWORD_DEMO_LI -e BANK_SEED_PASSWORD_DEMO_WANG linden-ledger
```

## Trouble

- Port in use: choose another `PORT`.
- Sign-in fails: the usernames are `demo_zhang`, `demo_li`, and `demo_wang`. Each passphrase comes from its own `BANK_SEED_PASSWORD_DEMO_ZHANG`, `BANK_SEED_PASSWORD_DEMO_LI`, or `BANK_SEED_PASSWORD_DEMO_WANG` variable, or from `.demo_credentials`. After you change the saved values, run the reset command. Five failures lock that account for 15 minutes.
- The page says the security check failed: refresh and submit again. Sign-in invalidates the previous CSRF token.
- A second click did not post twice: that is the idempotency guard.
- The page says the operation was cancelled: look at the server log. The page does not show a stack trace.
- Browser cases were skipped: install Chrome or Chromium, or set `CHROME_BIN`. The skip reason is in the integration report.

## Layout

- `app/` application, pages, and API
- `tests/` integration, security, English UI, and browser cases
- `docs/` architecture, schema, API, assets, cases, and management files
- `scripts/` start, reset, report, and packaging
- `reports/` JUnit and coverage from a real run
