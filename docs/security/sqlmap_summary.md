# SQLMap evidence

Linden Ledger is a coursework simulation. It is not a bank and it does not move real funds. This file is not a penetration test of a real system.

SQLMap 1.10.3#pip was run from this repository against a temporary server bound only to 127.0.0.1. No other host was scanned. The sign-in field sent to SQLMap used the marker `probe`. Session cookies and tokens were removed from the saved logs.

Generated (UTC): 2026-11-11T12:48:56Z

Injectable parameter reported: False

No run reported an injection point. The saved conclusion from SQLMap is quoted below. No vulnerability score was assigned.

- `login-password-union` technique `U` parameters password: [12:48:51] [CRITICAL] all tested parameters do not appear to be injectable. Try to increase values for '--level'/'--risk' options if you wish to perform more tests. Rerun without providing the option '--technique'. If you suspect that there is some kind of protection mechanism involved (e.g. WAF) maybe you could try to use option '--tamper' (e.g. '--tamper=space2comment') and/or switch '--random-agent'
  Log: `docs/security/sqlmap/login-password-union.log`
- `login-password-blind` technique `B` parameters password: [12:48:52] [CRITICAL] all tested parameters do not appear to be injectable. Try to increase values for '--level'/'--risk' options if you wish to perform more tests. Rerun without providing the option '--technique'. If you suspect that there is some kind of protection mechanism involved (e.g. WAF) maybe you could try to use option '--tamper' (e.g. '--tamper=space2comment') and/or switch '--random-agent'
  Log: `docs/security/sqlmap/login-password-blind.log`
- `login-username-union` technique `U` parameters username: [12:48:52] [CRITICAL] all tested parameters do not appear to be injectable. Try to increase values for '--level'/'--risk' options if you wish to perform more tests. Rerun without providing the option '--technique'. If you suspect that there is some kind of protection mechanism involved (e.g. WAF) maybe you could try to use option '--tamper' (e.g. '--tamper=space2comment') and/or switch '--random-agent'
  Log: `docs/security/sqlmap/login-username-union.log`
- `login-username-blind` technique `B` parameters username: [12:48:53] [CRITICAL] all tested parameters do not appear to be injectable. Try to increase values for '--level'/'--risk' options if you wish to perform more tests. Rerun without providing the option '--technique'. If you suspect that there is some kind of protection mechanism involved (e.g. WAF) maybe you could try to use option '--tamper' (e.g. '--tamper=space2comment') and/or switch '--random-agent'
  Log: `docs/security/sqlmap/login-username-blind.log`
- `account-union` technique `U` parameters account_no, user_id: [12:48:53] [CRITICAL] all tested parameters do not appear to be injectable. Try to increase values for '--level'/'--risk' options if you wish to perform more tests. Rerun without providing the option '--technique'. If you suspect that there is some kind of protection mechanism involved (e.g. WAF) maybe you could try to use option '--tamper' (e.g. '--tamper=space2comment') and/or switch '--random-agent'
  Log: `docs/security/sqlmap/account-union.log`
- `account-blind` technique `B` parameters account_no, user_id: [12:48:54] [CRITICAL] all tested parameters do not appear to be injectable. Try to increase values for '--level'/'--risk' options if you wish to perform more tests. Rerun without providing the option '--technique'. If you suspect that there is some kind of protection mechanism involved (e.g. WAF) maybe you could try to use option '--tamper' (e.g. '--tamper=space2comment') and/or switch '--random-agent'
  Log: `docs/security/sqlmap/account-blind.log`
- `transactions-union` technique `U` parameters limit, offset: [12:48:55] [CRITICAL] all tested parameters do not appear to be injectable. Try to increase values for '--level'/'--risk' options if you wish to perform more tests. Rerun without providing the option '--technique'. If you suspect that there is some kind of protection mechanism involved (e.g. WAF) maybe you could try to use option '--tamper' (e.g. '--tamper=space2comment') and/or switch '--random-agent'
  Log: `docs/security/sqlmap/transactions-union.log`
- `transactions-blind` technique `B` parameters limit, offset: [12:48:56] [CRITICAL] all tested parameters do not appear to be injectable. Try to increase values for '--level'/'--risk' options if you wish to perform more tests. Rerun without providing the option '--technique'. If you suspect that there is some kind of protection mechanism involved (e.g. WAF) maybe you could try to use option '--tamper' (e.g. '--tamper=space2comment') and/or switch '--random-agent'
  Log: `docs/security/sqlmap/transactions-blind.log`

The checked parameters were the sign-in username and passphrase fields, `account_no` and `user_id` on the account read, and `limit` and `offset` on activity. UNION (`U`) and boolean blind (`B`) were separate runs. Existing parameterized checks in the pytest suite were left in place and extended with UNION and boolean-style strings.

A state-changing transfer was not used as a SQLMap target. Its idempotency key would change later responses and could be mistaken for a finding. Transfer fields remain covered by the pytest cases, which keep SQL text as data.
