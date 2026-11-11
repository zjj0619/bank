# Data model

Amount columns are integer fen. 1 CNY = 100 fen. A single amount and a single balance cannot exceed 10^15 fen, which is 10,000,000,000,000.00 CNY. That cap is far below SQLite's signed 64-bit integer limit.

## Accounts

| Username | Name | Simulated account | Opening |
| --- | --- | --- | --- |
| demo_zhang | Mingyuan Zhang | SIM-1001 | 1,000,000 fen = 10,000.00 CNY |
| demo_li | Wanqing Li | SIM-1002 | 500,000 fen = 5,000.00 CNY |
| demo_wang | Qinian Wang | SIM-1003 | 258,025 fen = 2,580.25 CNY |

The opening is also a credit posting, so the balance and the activity agree from the start.

## Tables

- `users` holds the username, romanized display name, and an Argon2id passphrase hash. It also stores failed sign-in attempts, a lockout time, and the time the passphrase last changed. The hash is not reversible, and the passphrase is not stored.
- `accounts` holds one simulated account per user. `balance_fen` is checked to be at least 0.
- `transactions` records only committed movements: opening, deposit, withdrawal, transfer.
- `ledger_entries` records the debit or credit, the amount, and the balance after that posting.
- `idempotency_keys` is unique per user and key, and stores only successful results.

A transfer is one transaction with one debit and one credit. Failed attempts are not stored, so they cannot change the balance.

The view `account_ledger_totals` places `balance_fen` next to the signed sum of the ledger. Tests require those two numbers to match, and they require each `balance_after_fen` to match a running total.
