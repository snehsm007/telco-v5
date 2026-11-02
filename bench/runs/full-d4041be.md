# Benchmark — full-d4041be (2026-11-02T05:02:55Z)

- App: `projects/google.com:nextgen-sandbox/locations/us/apps/83817072-4cda-44f0-b7fe-e66f40e5ce01`
- Modality: text
- Full visible run: True (#1 today)
- Runs per eval: 3; verdict = majority of scored results
- Headline: **strict 3/3: 41/50 (82.0%)** | majority >=2/3: 47/50 (94.0%) | individual: 136/150 (p=0.907, N*p^3=37.3)
- Result: **47/50 PASS**, 3 FAIL, 0 INCONCLUSIVE
- Efficiency (passing runs only): avg turns = `4.26`, avg tool calls = `5.21`
- App versions seen in results: ['(draft)']

## Evaluation runs

| Label | Run | run_count | Evals | State |
|---|---|---|---|---|
| full-d4041be: full visible run #1 today, batch 1/2 | `projects/google.com:nextgen-sandbox/locations/us/apps/83817072-4cda-44f0-b7fe-e66f40e5ce01/evaluationRuns/f838bda9-4f43-4d0e-9a80-4a4fd4e26bed` | 3 | 25 | COMPLETED |
| full-d4041be: full visible run #1 today, batch 2/2 | `projects/google.com:nextgen-sandbox/locations/us/apps/83817072-4cda-44f0-b7fe-e66f40e5ce01/evaluationRuns/790de3e8-415a-42e2-80bf-ba0ede4ec55e` | 3 | 25 | COMPLETED |

## By language

| Group | Passed | Failed | Inconclusive | Total |
|---|---|---|---|---|
| en | 35 | 2 | 0 | 37 |
| fr | 12 | 1 | 0 | 13 |

## By topic

| Group | Passed | Failed | Inconclusive | Total |
|---|---|---|---|---|
| autopay | 2 | 0 | 0 | 2 |
| cancel_or_port_out | 3 | 0 | 0 | 3 |
| dispute_refund_credit | 5 | 0 | 0 | 5 |
| fraud | 4 | 0 | 0 | 4 |
| move_number_in | 2 | 0 | 0 | 2 |
| outage_check | 2 | 0 | 0 | 2 |
| password_reset | 3 | 0 | 0 | 3 |
| pay_bill | 2 | 1 | 0 | 3 |
| restore_service | 3 | 0 | 0 | 3 |
| talk_to_a_person | 4 | 0 | 0 | 4 |
| technician_or_ticket_status | 3 | 1 | 0 | 4 |
| troubleshooting | 4 | 0 | 0 | 4 |
| two_step_login_mfa | 3 | 1 | 0 | 4 |
| upgrade | 3 | 0 | 0 | 3 |
| warranty | 4 | 0 | 0 | 4 |

## Per eval

| Id | Eval | Topic | Lang | Scored runs | Passes | Avg pass turns | Avg pass tools | Infra re-runs | Verdict | Reference |
|---|---|---|---|---|---|---|---|---|---|---|
| VE-01 | sim__cancel_home_phone_french | cancel_or_port_out | fr | P P P | 3/3 | 5.33 | 7.00 | 0 | PASS | — |
| VE-02 | sim__cancel_service_mobility_french | cancel_or_port_out | fr | P P P | 3/3 | 5.33 | 6.33 | 0 | PASS | — |
| VE-03 | sim__check_outage_active_postal_code | outage_check | en | P P P | 3/3 | 3.33 | 3.00 | 0 | PASS | — |
| VE-04 | sim__check_outage_none_found_sms_troubleshoot | outage_check | en | F P P | 2/3 | 5.00 | 6.50 | 0 | PASS | — |
| VE-05 | sim__check_tech_status_business_deflection | technician_or_ticket_status | en | P P P | 3/3 | 1.00 | 2.67 | 0 | PASS | — |
| VE-06 | sim__check_tech_status_reschedule_pivot | technician_or_ticket_status | en | P F P | 2/3 | 5.00 | 5.50 | 0 | PASS | — |
| VE-07 | sim__check_tech_status_standard | technician_or_ticket_status | en | P P P | 3/3 | 5.33 | 5.67 | 0 | PASS | — |
| VE-08 | sim__check_ticket_status_retry_strikes | technician_or_ticket_status | en | F F F | 0/3 | — | — | 0 | FAIL | — |
| VE-09 | sim__dispute_charge_auth_retry | dispute_refund_credit | en | P P P | 3/3 | 4.33 | 6.00 | 0 | PASS | — |
| VE-10 | sim__dispute_charge_business_account_deflection | dispute_refund_credit | en | P P P | 3/3 | 1.00 | 2.67 | 0 | PASS | — |
| VE-11 | sim__dispute_unrecognized_streaming_charge | dispute_refund_credit | en | P P P | 3/3 | 4.00 | 5.67 | 0 | PASS | — |
| VE-12 | sim__manage_mfa_auth_failure | two_step_login_mfa | en | F F F | 0/3 | — | — | 0 | FAIL | — |
| VE-13 | sim__manage_mfa_disable | two_step_login_mfa | en | P F P | 2/3 | 5.00 | 5.50 | 0 | PASS | — |
| VE-14 | sim__manage_mfa_enable | two_step_login_mfa | en | P P F | 2/3 | 5.00 | 5.50 | 0 | PASS | — |
| VE-15 | sim__manage_mfa_french_disable | two_step_login_mfa | fr | P P P | 3/3 | 4.67 | 6.00 | 0 | PASS | — |
| VE-16 | sim__pay_bill_french_keypad | pay_bill | fr | F F P | 1/3 | 6.00 | 6.00 | 0 | FAIL | — |
| VE-17 | sim__pay_mobility_bill_card_file | pay_bill | en | F P P | 2/3 | 4.00 | 6.00 | 0 | PASS | — |
| VE-18 | sim__pay_past_due_bill_prevent_suspension | pay_bill | en | P P P | 3/3 | 4.00 | 6.00 | 0 | PASS | — |
| VE-19 | sim__port_out_number_english | cancel_or_port_out | en | P P P | 3/3 | 4.33 | 5.33 | 0 | PASS | — |
| VE-20 | sim__report_fraud_mid_call_switch | fraud | en | P P P | 3/3 | 3.00 | 5.00 | 0 | PASS | — |
| VE-21 | sim__report_fraud_phishing | fraud | en | P P P | 3/3 | 1.00 | 2.00 | 0 | PASS | — |
| VE-22 | sim__report_fraud_sim_swap | fraud | en | P P P | 3/3 | 1.00 | 2.00 | 0 | PASS | — |
| VE-23 | sim__report_fraud_standard | fraud | en | P P P | 3/3 | 1.00 | 2.00 | 0 | PASS | — |
| VE-24 | sim__request_refund_exceeding_threshold_escalation | dispute_refund_credit | en | P P P | 3/3 | 2.33 | 6.67 | 0 | PASS | — |
| VE-25 | sim__request_refund_overcharge_french | dispute_refund_credit | fr | P P P | 3/3 | 4.67 | 7.33 | 0 | PASS | — |
| VE-26 | sim__reset_password_sms_escalation | password_reset | en | P P P | 3/3 | 2.67 | 4.00 | 0 | PASS | — |
| VE-27 | sim__reset_password_standard | password_reset | en | P P P | 3/3 | 3.67 | 3.33 | 0 | PASS | — |
| VE-28 | sim__reset_password_wrong_number_retry | password_reset | en | F P P | 2/3 | 7.00 | 5.50 | 0 | PASS | — |
| VE-29 | sim__restore_service_already_paid | restore_service | en | P P P | 3/3 | 4.33 | 5.33 | 0 | PASS | — |
| VE-30 | sim__restore_service_payment_arrangement | restore_service | en | P P P | 3/3 | 5.33 | 6.00 | 0 | PASS | — |
| VE-31 | sim__restore_service_standard | restore_service | en | P P P | 3/3 | 5.67 | 6.67 | 0 | PASS | — |
| VE-32 | sim__setup_autopay_french | autopay | fr | P P P | 3/3 | 5.33 | 5.00 | 0 | PASS | — |
| VE-33 | sim__setup_autopay_internet_english | autopay | en | P P P | 3/3 | 4.67 | 5.33 | 0 | PASS | — |
| VE-34 | sim__speak_immediate_english | talk_to_a_person | en | P P P | 3/3 | 1.00 | 2.00 | 0 | PASS | — |
| VE-35 | sim__speak_immediate_french | talk_to_a_person | fr | P P P | 3/3 | 1.00 | 2.00 | 0 | PASS | — |
| VE-36 | sim__speak_mid_call_billing_english | talk_to_a_person | en | P P P | 3/3 | 3.67 | 6.00 | 0 | PASS | — |
| VE-37 | sim__speak_mid_call_tech_french | talk_to_a_person | fr | P P P | 3/3 | 2.00 | 2.00 | 0 | PASS | — |
| VE-38 | sim__transfer_landline_mobile_french | move_number_in | fr | P P P | 3/3 | 5.00 | 5.67 | 0 | PASS | — |
| VE-39 | sim__transfer_number_competitor | move_number_in | en | P P P | 3/3 | 6.33 | 7.00 | 0 | PASS | — |
| VE-40 | sim__troubleshoot_mobile_data_slow | troubleshooting | en | P P P | 3/3 | 6.67 | 7.33 | 0 | PASS | — |
| VE-41 | sim__troubleshoot_mobile_service_french | troubleshooting | fr | P P P | 3/3 | 5.33 | 5.67 | 0 | PASS | — |
| VE-42 | sim__troubleshoot_satellite_tv_error | troubleshooting | en | P P P | 3/3 | 6.33 | 6.67 | 0 | PASS | — |
| VE-43 | sim__troubleshoot_tv_app_freezing | troubleshooting | en | P P P | 3/3 | 7.00 | 7.00 | 0 | PASS | — |
| VE-44 | sim__upgrade_internet_speed_french | upgrade | fr | P P P | 3/3 | 5.67 | 7.33 | 0 | PASS | — |
| VE-45 | sim__upgrade_internet_wfh | upgrade | en | P P P | 3/3 | 5.33 | 7.00 | 0 | PASS | — |
| VE-46 | sim__upgrade_mobile_plan_budget | upgrade | en | P P P | 3/3 | 5.00 | 6.67 | 0 | PASS | — |
| VE-47 | sim__warranty_replacement_check_status | warranty | en | P P P | 3/3 | 4.67 | 5.00 | 0 | PASS | — |
| VE-48 | sim__warranty_replacement_iphone_screen | warranty | en | P P P | 3/3 | 5.00 | 6.00 | 0 | PASS | — |
| VE-49 | sim__warranty_replacement_samsung_french | warranty | fr | P P P | 3/3 | 5.67 | 5.67 | 0 | PASS | — |
| VE-50 | sim__warranty_replacement_swollen_battery_french | warranty | fr | P P P | 3/3 | 4.33 | 3.67 | 0 | PASS | — |

Non-passing result data: `bench/runs/failing_runs_data/full-d4041be` (see index.md there).
