# HTTP API

The base path is `/api/v1`. Reads other than health require a session. Every change also requires the `X-CSRF-Token` header. Sign-in replaces the CSRF token. Use the new value from the sign-in response.

Send `amount` as a string such as `"10.50"`. It must be greater than 0 and have at most two decimal places. A JSON integer is whole CNY. JSON floats, NaN, Infinity, negatives, zero, and values over the cap are rejected.

Write calls need `Idempotency-Key`, or the JSON field `idempotency_key`. Length 8 to 80. Letters, digits, underscores, and hyphens only.

Success responses include `"simulation": true`. A failure looks like:

```json
{"ok": false, "simulation": true, "error": {"code": "insufficient_funds", "message": "The balance is not sufficient."}}
```

`GET /api/v1/account` returns only the signed-in user. Extra query parameters do not widen that. `balance` is CNY without grouping. `balance_fen` is the integer. `balance_display` is grouped.

`POST /api/v1/transfers` returns the sender's new balance, not the receiver's. The receiver sees the incoming transfer in their own activity.

`POST /api/v1/auth/password` takes `current_password` and `new_password`. It requires a session and CSRF. A weak replacement is rejected with one policy message. Success returns a new CSRF token and signs out other sessions for that account. A wrong current passphrase and an unknown username at sign-in use generic failures. After five failures the account stays locked until the cooldown ends, and the message still does not say whether the username exists.

Repeating a successful request with the same key and the same body returns the original entry with `"replayed": true` and does not post again.
