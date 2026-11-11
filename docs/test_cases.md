# Integration case table

59 cases were authored. Actual status comes from `reports/junit.xml` at 2026-11-11T08:30:58Z.
Skipped is not passed. A case missing from this JUnit file is marked Not run.

| Case ID | Category | Test function | Title | Actual status |
| --- | --- | --- | --- | --- |
| IT-01 | Integration | `test_seed_balances_match_opening_ledger` | Opening balances match the opening ledger | Passed |
| IT-02 | Integration | `test_deposit_success_updates_balance_and_ledger` | A deposit posts one credit | Passed |
| IT-03 | Integration | `test_withdrawal_success_updates_balance_and_ledger` | A withdrawal posts one debit | Passed |
| IT-04 | Integration | `test_transfer_syncs_both_balances_and_ledgers` | A transfer updates both balances and both ledger rows | Passed |
| IT-05 | Integration | `test_transfer_visible_in_both_histories` | A transfer appears in both histories | Passed |
| IT-06 | Integration | `test_transfer_entire_balance_conserves_money` | Transferring the whole balance keeps both sides consistent | Passed |
| IT-07 | Integration | `test_transfer_account_number_is_case_insensitive` | The receiving account number ignores case | Passed |
| IT-08 | Integration | `test_withdrawal_insufficient_funds` | A withdrawal over the balance is rejected | Passed |
| IT-09 | Integration | `test_transfer_insufficient_funds` | A transfer over the balance is rejected | Passed |
| IT-10 | Integration | `test_transfer_invalid_recipient_format` | A malformed recipient is rejected | Passed |
| IT-11 | Integration | `test_transfer_nonexistent_recipient` | An unknown recipient is rejected | Passed |
| IT-12 | Integration | `test_transfer_to_self_rejected` | A transfer to oneself is rejected | Passed |
| IT-13 | Integration | `test_minimum_fen_deposit_boundary` | The minimum amount of 0.01 CNY posts | Passed |
| IT-14 | Integration | `test_zero_amount_rejected` | Zero is rejected on deposit, withdrawal, and transfer | Passed |
| IT-15 | Integration | `test_negative_amount_rejected` | Negative amounts are rejected | Passed |
| IT-16 | Integration | `test_overprecision_rejected` | More than two decimal places are rejected | Passed |
| IT-17 | Integration | `test_nonfinite_amount_rejected` | Non-finite amounts are rejected | Passed |
| IT-18 | Integration | `test_invalid_amount_strings_rejected` | Invalid amount strings and types are rejected | Passed |
| IT-19 | Integration | `test_json_float_amount_rejected` | JSON floats are rejected and JSON integers mean whole CNY | Passed |
| IT-20 | Integration | `test_overflow_amount_rejected` | Amounts above the cap are rejected | Passed |
| IT-21 | Integration | `test_deposit_rejected_when_balance_would_overflow` | A deposit that would pass the balance cap is rejected | Passed |
| IT-22 | Integration | `test_balance_matches_ledger_after_mixed_operations` | Mixed deposits, withdrawals, and transfers still match the ledger | Passed |
| IT-23 | Integration | `test_withdraw_exact_balance_boundary` | Withdrawing the exact balance succeeds | Passed |
| IT-24 | Integration | `test_duplicate_deposit_is_idempotent` | A repeated deposit posts only once | Passed |
| IT-25 | Integration | `test_duplicate_transfer_is_idempotent` | A repeated transfer posts only once | Passed |
| IT-26 | Integration | `test_idempotency_conflict_does_not_apply_second_amount` | The same key with a different amount conflicts | Passed |
| IT-27 | Integration | `test_failed_withdrawal_does_not_consume_idempotency_key` | A failed withdrawal does not consume the idempotency key | Passed |
| IT-28 | Integration | `test_idempotency_keys_are_isolated_per_user` | Idempotency keys are isolated per user | Passed |
| IT-29 | Integration | `test_concurrent_withdrawals_do_not_overdraft` | Concurrent withdrawals do not overdraw | Passed |
| IT-30 | Security | `test_account_query_ignores_foreign_account_parameters` | Query parameters cannot read another account | Passed |
| IT-31 | Security | `test_history_isolated_between_users` | Activity is isolated to the signed-in user | Passed |
| IT-32 | Security | `test_unauthorized_reads_require_login` | Account reads require a session | Passed |
| IT-33 | Security | `test_logout_invalidates_session` | Sign-out invalidates the session | Passed |
| IT-34 | Security | `test_mutation_without_login_is_rejected` | A deposit without a session is rejected | Passed |
| IT-35 | Security | `test_missing_csrf_rejected_and_balance_unchanged` | Missing CSRF does not post | Passed |
| IT-36 | Security | `test_csrf_rotates_on_login` | Sign-in rotates the CSRF token | Passed |
| IT-37 | Security | `test_injected_fault_rolls_back_all_writes` | An injected fault after the write rolls the entry back | Passed |
| IT-38 | Security | `test_fault_header_ignored_when_injection_disabled` | The fault header is ignored unless tests enable it | Passed |
| IT-39 | Security | `test_sql_injection_login_does_not_authenticate` | SQL injection in the sign-in form does not authenticate | Passed |
| IT-40 | Security | `test_sql_injection_in_transaction_form_is_stored_not_executed` | SQL text in a transaction form is stored as data | Passed |
| IT-41 | Security | `test_history_escapes_html_in_note` | Activity escapes HTML in a note | Passed |
| IT-42 | Security | `test_session_cookie_is_httponly_and_samesite` | The session cookie is HttpOnly and SameSite | Passed |
| IT-43 | Security | `test_login_failure_messages_are_uniform` | Unknown users and wrong passphrases get the same message | Passed |
| IT-44 | Interface | `test_web_login_deposit_and_history_pages` | The pages sign in, move money, ignore a duplicate post, and sign out | Passed |
| IT-45 | Security | `test_login_does_not_redirect_off_site` | Sign-in ignores an external next address | Passed |
| IT-46 | Security | `test_api_errors_do_not_leak_tracebacks` | Error responses do not leak stack traces | Passed |
| IT-47 | Interface | `test_selenium_login_shows_balance` | The browser signs in and shows the balance | Passed |
| IT-48 | Interface | `test_selenium_transactions_and_history` | The browser deposits, withdraws, transfers, and checks activity | Passed |
| IT-49 | Delivery | `test_readme_lists_seed_accounts_and_secrets_are_untracked` | The README lists the accounts and does not contain a passphrase | Passed |
| IT-50 | Delivery | `test_catalog_matches_test_functions` | The catalog matches the test functions | Passed |
| IT-51 | Delivery | `test_reset_command_recreates_isolated_database` | The reset command rebuilds a database only after confirmation | Passed |
| IT-52 | Delivery | `test_english_login_and_local_assets` | Sign-in is English and images are stored locally | Passed |
| IT-53 | Interface | `test_signed_in_pages_are_english` | Signed-in pages use English chrome | Passed |
| IT-54 | Security | `test_password_policy_rejects_incomplete_and_weak` | The passphrase policy rejects incomplete and weak values | Passed |
| IT-55 | Security | `test_lockout_blocks_correct_passphrase_until_cooldown` | Lockout blocks the correct passphrase until the cooldown ends | Passed |
| IT-56 | Security | `test_password_hashes_are_argon2_and_distinct` | Stored passphrases are distinct Argon2id hashes | Passed |
| IT-57 | Security | `test_change_password_updates_hash_and_ends_other_sessions` | Changing the passphrase updates the hash and ends other sessions | Passed |
| IT-58 | Security | `test_shared_seed_passphrase_is_refused` | A shared seed passphrase is refused | Passed |
| IT-59 | Security | `test_weak_seed_passphrase_is_refused` | A weak seed passphrase is refused | Passed |

Preconditions, steps, inputs, expected results, and actual summaries are in the CSV beside this file.
