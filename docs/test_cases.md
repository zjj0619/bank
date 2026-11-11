# Integration case table

119 cases were authored. Actual status comes from `reports/junit.xml` at 2026-11-11T12:51:43Z.
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
| FC-01 | Functional | `test_note_of_100_characters_is_stored` | A 100-character note is stored on a deposit | Passed |
| FC-02 | Functional | `test_note_of_101_characters_is_rejected` | A 101-character note is rejected | Passed |
| FC-03 | Functional | `test_note_is_trimmed_to_100_characters` | Surrounding spaces do not count toward the note limit | Passed |
| FC-04 | Functional | `test_note_drops_null_bytes` | A null byte is removed from a note | Passed |
| FC-05 | Functional | `test_missing_note_is_stored_empty` | A null note is stored as an empty string | Passed |
| FC-06 | Functional | `test_non_text_note_is_rejected` | A numeric note is rejected | Passed |
| FC-07 | Functional | `test_idempotency_key_of_8_characters_is_accepted` | An 8-character idempotency key is accepted | Passed |
| FC-08 | Functional | `test_idempotency_key_of_80_characters_is_accepted` | An 80-character idempotency key is accepted | Passed |
| FC-09 | Functional | `test_idempotency_key_of_7_characters_is_rejected` | A 7-character idempotency key is rejected | Passed |
| FC-10 | Functional | `test_idempotency_key_of_81_characters_is_rejected` | An 81-character idempotency key is rejected | Passed |
| FC-11 | Functional | `test_idempotency_key_with_a_space_is_rejected` | An idempotency key with a space is rejected | Passed |
| FC-12 | Functional | `test_missing_idempotency_key_is_rejected` | A deposit without an idempotency key is rejected | Passed |
| FC-13 | Functional | `test_idempotency_key_in_json_body_posts_a_withdrawal` | A withdrawal accepts the idempotency key in JSON | Passed |
| FC-14 | Functional | `test_replayed_withdrawal_does_not_debit_twice` | Repeating a withdrawal with the same key does not debit twice | Passed |
| FC-15 | Functional | `test_failed_transfer_does_not_consume_idempotency_key` | A failed transfer leaves the idempotency key unused | Passed |
| FC-16 | Functional | `test_transfer_rejected_when_receiver_balance_would_exceed_cap` | A transfer that would push the receiver over the cap is rejected | Passed |
| FC-17 | Functional | `test_transfer_that_lands_receiver_on_cap_succeeds` | A transfer may land the receiver exactly on the cap | Passed |
| FC-18 | Functional | `test_concurrent_transfers_of_full_balance_do_not_overspend` | Two full-balance transfers cannot both post | Passed |
| FC-19 | Functional | `test_concurrent_transfers_from_two_senders_both_post` | Concurrent transfers from two senders both post | Passed |
| FC-20 | Functional | `test_concurrent_same_key_deposits_post_once` | Two deposits with one key post once | Passed |
| FC-21 | Functional | `test_integrity_error_without_stored_key_returns_conflict` | A unique-key collision with no stored result returns conflict | Passed |
| FC-22 | Functional | `test_integrity_error_with_matching_key_returns_replay` | A unique-key collision returns the stored result when the fingerprint matches | Passed |
| FC-23 | Functional | `test_integrity_error_with_different_fingerprint_conflicts` | A unique-key collision with a different fingerprint conflicts | Passed |
| FC-24 | Functional | `test_history_limit_one_returns_newest_entry` | Activity limit 1 returns the newest entry | Passed |
| FC-25 | Functional | `test_history_offset_skips_newest_entry` | Activity offset 1 skips the newest entry | Passed |
| FC-26 | Functional | `test_history_limit_above_100_is_rejected` | Activity limit above 100 is rejected | Passed |
| FC-27 | Functional | `test_history_offset_above_100000_is_rejected` | Activity offset above 100000 is rejected | Passed |
| FC-28 | Functional | `test_profile_returns_signed_in_user_only` | The profile endpoint ignores another user's query | Passed |
| FC-29 | Functional | `test_opening_activity_is_labeled_opening` | The opening entry is labeled Opening | Passed |
| FC-30 | Functional | `test_transfer_activity_labels_direction` | A transfer is Out for the sender and In for the receiver | Passed |
| FC-31 | Functional | `test_one_decimal_amount_posts_whole_fen` | One decimal place posts the right number of fen | Passed |
| FC-32 | Functional | `test_leading_zero_amount_is_rejected` | A leading zero in the yuan amount is rejected | Passed |
| FC-33 | Functional | `test_amount_with_surrounding_spaces_is_accepted` | Spaces around an amount are ignored | Passed |
| FC-34 | Functional | `test_account_number_with_surrounding_spaces_transfers` | Spaces around an account number still find the receiver | Passed |
| FC-35 | Functional | `test_non_string_recipient_is_rejected` | A numeric recipient is rejected | Passed |
| FC-36 | Functional | `test_signed_out_deposit_page_redirects_to_sign_in` | The deposit page requires a session | Passed |
| FC-37 | Functional | `test_signed_out_activity_page_redirects_to_sign_in` | The activity page requires a session | Passed |
| FC-38 | Functional | `test_signed_in_user_is_sent_from_sign_in_to_overview` | A signed-in user opening sign-in is sent to the overview | Passed |
| FC-39 | Functional | `test_web_withdrawal_over_balance_stays_on_the_form` | A web withdrawal over the balance stays on the form | Passed |
| FC-40 | Functional | `test_web_transfer_to_unknown_account_stays_on_the_form` | A web transfer to an unknown account stays on the form | Passed |
| FC-41 | Functional | `test_web_passphrase_mismatch_does_not_change_the_hash` | Mismatched passphrase confirmation does not change the hash | Passed |
| FC-42 | Functional | `test_sign_out_without_csrf_keeps_the_session` | Sign-out without CSRF keeps the session | Passed |
| FC-43 | Functional | `test_dashboard_shows_posted_balance_line_after_a_second_entry` | The posted-balance line appears after a second entry | Passed |
| FC-44 | Functional | `test_wrong_csrf_token_rejects_a_deposit` | A wrong CSRF token rejects a deposit | Passed |
| FC-45 | Functional | `test_username_longer_than_64_characters_does_not_sign_in` | A username longer than 64 characters does not sign in | Passed |
| FC-46 | Functional | `test_non_string_password_does_not_sign_in` | A non-text passphrase does not sign in | Passed |
| FC-47 | Functional | `test_wrong_current_passphrase_keeps_the_hash` | The wrong current passphrase does not change the hash | Passed |
| FC-48 | Functional | `test_security_headers_are_present_on_a_page` | Pages send the simulation security headers | Passed |
| FC-49 | Functional | `test_transfer_chain_conserves_the_three_balances` | A three-step transfer chain conserves the balances | Passed |
| FC-50 | Functional | `test_unicode_note_respects_the_100_character_limit` | The note limit counts characters | Passed |
| FC-51 | Functional | `test_stale_balance_guard_rejects_the_update` | A stale expected balance does not update the account | Passed |
| FC-52 | Functional | `test_balance_guard_rejects_an_out_of_range_result` | The balance guard rejects a result outside the allowed range | Passed |
| IT-60 | Interface | `test_selenium_failed_login_stays_on_login_page` | A wrong passphrase stays on the sign-in page | Passed |
| SC-01 | Security | `test_local_env_file_fills_only_missing_names` | A local env file fills only names that are not already set | Passed |
| SC-02 | Security | `test_secret_key_resolution_uses_override_env_file_or_generates` | The session key comes from an override, the environment, a file, or a new file | Passed |
| SC-03 | Security | `test_private_file_write_ignores_chmod_errors` | A private-file write still returns the key when chmod fails | Passed |
| SC-04 | Security | `test_seed_passwords_come_from_env_or_file_and_testing_refuses` | Seed passphrases come from the environment or a file, and tests refuse to invent one | Passed |
| SC-05 | Security | `test_configured_seed_map_must_name_every_account` | A configured seed map must name every demo account | Passed |
| DV-01 | Delivery | `test_sqlmap_evidence_targets_localhost_only` | SQLMap evidence targets only the local coursework app | Passed |
| DV-02 | Delivery | `test_ci_workflow_runs_pytest_and_uploads_reports` | GitHub Actions runs pytest and uploads the reports | Passed |

Preconditions, steps, inputs, expected results, traces, and actual summaries are in the CSV beside this file.

## Functional inventory

52 functional cases were authored as their own tests. Trace is file::function.

| Case ID | Test function | Trace | Title | Actual status |
| --- | --- | --- | --- | --- |
| FC-01 | `test_note_of_100_characters_is_stored` | `app/services.py::clean_note` | A 100-character note is stored on a deposit | Passed |
| FC-02 | `test_note_of_101_characters_is_rejected` | `app/services.py::clean_note` | A 101-character note is rejected | Passed |
| FC-03 | `test_note_is_trimmed_to_100_characters` | `app/services.py::clean_note` | Surrounding spaces do not count toward the note limit | Passed |
| FC-04 | `test_note_drops_null_bytes` | `app/services.py::clean_note` | A null byte is removed from a note | Passed |
| FC-05 | `test_missing_note_is_stored_empty` | `app/services.py::clean_note` | A null note is stored as an empty string | Passed |
| FC-06 | `test_non_text_note_is_rejected` | `app/services.py::clean_note` | A numeric note is rejected | Passed |
| FC-07 | `test_idempotency_key_of_8_characters_is_accepted` | `app/services.py::clean_idempotency_key` | An 8-character idempotency key is accepted | Passed |
| FC-08 | `test_idempotency_key_of_80_characters_is_accepted` | `app/services.py::clean_idempotency_key` | An 80-character idempotency key is accepted | Passed |
| FC-09 | `test_idempotency_key_of_7_characters_is_rejected` | `app/services.py::clean_idempotency_key` | A 7-character idempotency key is rejected | Passed |
| FC-10 | `test_idempotency_key_of_81_characters_is_rejected` | `app/services.py::clean_idempotency_key` | An 81-character idempotency key is rejected | Passed |
| FC-11 | `test_idempotency_key_with_a_space_is_rejected` | `app/services.py::clean_idempotency_key` | An idempotency key with a space is rejected | Passed |
| FC-12 | `test_missing_idempotency_key_is_rejected` | `app/webutil.py::read_idempotency_key` | A deposit without an idempotency key is rejected | Passed |
| FC-13 | `test_idempotency_key_in_json_body_posts_a_withdrawal` | `app/services.py::withdraw` | A withdrawal accepts the idempotency key in JSON | Passed |
| FC-14 | `test_replayed_withdrawal_does_not_debit_twice` | `app/services.py::_apply` | Repeating a withdrawal with the same key does not debit twice | Passed |
| FC-15 | `test_failed_transfer_does_not_consume_idempotency_key` | `app/services.py::transfer` | A failed transfer leaves the idempotency key unused | Passed |
| FC-16 | `test_transfer_rejected_when_receiver_balance_would_exceed_cap` | `app/services.py::_plan_transfer` | A transfer that would push the receiver over the cap is rejected | Passed |
| FC-17 | `test_transfer_that_lands_receiver_on_cap_succeeds` | `app/services.py::_plan_transfer` | A transfer may land the receiver exactly on the cap | Passed |
| FC-18 | `test_concurrent_transfers_of_full_balance_do_not_overspend` | `app/services.py::transfer` | Two full-balance transfers cannot both post | Passed |
| FC-19 | `test_concurrent_transfers_from_two_senders_both_post` | `app/services.py::transfer` | Concurrent transfers from two senders both post | Passed |
| FC-20 | `test_concurrent_same_key_deposits_post_once` | `app/services.py::deposit` | Two deposits with one key post once | Passed |
| FC-21 | `test_integrity_error_without_stored_key_returns_conflict` | `app/services.py::_apply` | A unique-key collision with no stored result returns conflict | Passed |
| FC-22 | `test_integrity_error_with_matching_key_returns_replay` | `app/services.py::_apply` | A unique-key collision returns the stored result when the fingerprint matches | Passed |
| FC-23 | `test_integrity_error_with_different_fingerprint_conflicts` | `app/services.py::_apply` | A unique-key collision with a different fingerprint conflicts | Passed |
| FC-24 | `test_history_limit_one_returns_newest_entry` | `app/services.py::list_history` | Activity limit 1 returns the newest entry | Passed |
| FC-25 | `test_history_offset_skips_newest_entry` | `app/services.py::list_history` | Activity offset 1 skips the newest entry | Passed |
| FC-26 | `test_history_limit_above_100_is_rejected` | `app/routes/api.py::_paging` | Activity limit above 100 is rejected | Passed |
| FC-27 | `test_history_offset_above_100000_is_rejected` | `app/routes/api.py::_paging` | Activity offset above 100000 is rejected | Passed |
| FC-28 | `test_profile_returns_signed_in_user_only` | `app/routes/api.py::me` | The profile endpoint ignores another user's query | Passed |
| FC-29 | `test_opening_activity_is_labeled_opening` | `app/services.py::_history_item` | The opening entry is labeled Opening | Passed |
| FC-30 | `test_transfer_activity_labels_direction` | `app/services.py::_history_item` | A transfer is Out for the sender and In for the receiver | Passed |
| FC-31 | `test_one_decimal_amount_posts_whole_fen` | `app/money.py::parse_amount_to_fen` | One decimal place posts the right number of fen | Passed |
| FC-32 | `test_leading_zero_amount_is_rejected` | `app/money.py::parse_amount_to_fen` | A leading zero in the yuan amount is rejected | Passed |
| FC-33 | `test_amount_with_surrounding_spaces_is_accepted` | `app/money.py::parse_amount_to_fen` | Spaces around an amount are ignored | Passed |
| FC-34 | `test_account_number_with_surrounding_spaces_transfers` | `app/services.py::normalize_account_no` | Spaces around an account number still find the receiver | Passed |
| FC-35 | `test_non_string_recipient_is_rejected` | `app/services.py::normalize_account_no` | A numeric recipient is rejected | Passed |
| FC-36 | `test_signed_out_deposit_page_redirects_to_sign_in` | `app/routes/web.py::deposit_page` | The deposit page requires a session | Passed |
| FC-37 | `test_signed_out_activity_page_redirects_to_sign_in` | `app/routes/web.py::history_page` | The activity page requires a session | Passed |
| FC-38 | `test_signed_in_user_is_sent_from_sign_in_to_overview` | `app/routes/web.py::login_form` | A signed-in user opening sign-in is sent to the overview | Passed |
| FC-39 | `test_web_withdrawal_over_balance_stays_on_the_form` | `app/routes/web.py::withdraw_page` | A web withdrawal over the balance stays on the form | Passed |
| FC-40 | `test_web_transfer_to_unknown_account_stays_on_the_form` | `app/routes/web.py::transfer_page` | A web transfer to an unknown account stays on the form | Passed |
| FC-41 | `test_web_passphrase_mismatch_does_not_change_the_hash` | `app/routes/web.py::password_page` | Mismatched passphrase confirmation does not change the hash | Passed |
| FC-42 | `test_sign_out_without_csrf_keeps_the_session` | `app/routes/web.py::logout` | Sign-out without CSRF keeps the session | Passed |
| FC-43 | `test_dashboard_shows_posted_balance_line_after_a_second_entry` | `app/routes/web.py::sparkline_for` | The posted-balance line appears after a second entry | Passed |
| FC-44 | `test_wrong_csrf_token_rejects_a_deposit` | `app/webutil.py::require_csrf` | A wrong CSRF token rejects a deposit | Passed |
| FC-45 | `test_username_longer_than_64_characters_does_not_sign_in` | `app/services.py::authenticate` | A username longer than 64 characters does not sign in | Passed |
| FC-46 | `test_non_string_password_does_not_sign_in` | `app/services.py::authenticate` | A non-text passphrase does not sign in | Passed |
| FC-47 | `test_wrong_current_passphrase_keeps_the_hash` | `app/services.py::change_password` | The wrong current passphrase does not change the hash | Passed |
| FC-48 | `test_security_headers_are_present_on_a_page` | `app/__init__.py::_register_handlers` | Pages send the simulation security headers | Passed |
| FC-49 | `test_transfer_chain_conserves_the_three_balances` | `app/services.py::transfer` | A three-step transfer chain conserves the balances | Passed |
| FC-50 | `test_unicode_note_respects_the_100_character_limit` | `app/services.py::clean_note` | The note limit counts characters | Passed |
| FC-51 | `test_stale_balance_guard_rejects_the_update` | `app/services.py::_update_balance` | A stale expected balance does not update the account | Passed |
| FC-52 | `test_balance_guard_rejects_an_out_of_range_result` | `app/services.py::_update_balance` | The balance guard rejects a result outside the allowed range | Passed |
