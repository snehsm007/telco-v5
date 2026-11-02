# Benchmark — holdout-d4041be (2026-11-02T05:13:16Z)

- App: `projects/google.com:nextgen-sandbox/locations/us/apps/35f18685-dced-4784-9ef5-b82b1d0e8f87`
- Modality: text
- Full visible run: False
- Runs per eval: 3; verdict = majority of scored results
- Headline: **strict 3/3: 16/20 (80.0%)** | majority >=2/3: 18/20 (90.0%) | individual: 53/60 (p=0.883, N*p^3=13.8)
- Result: **18/20 PASS**, 2 FAIL, 0 INCONCLUSIVE
- Efficiency (passing runs only): avg turns = `4.32`, avg tool calls = `5.27`
- App versions seen in results: ['(draft)']

## Evaluation runs

| Label | Run | run_count | Evals | State |
|---|---|---|---|---|
| bench: targeted run, batch 1/1 | `projects/google.com:nextgen-sandbox/locations/us/apps/35f18685-dced-4784-9ef5-b82b1d0e8f87/evaluationRuns/ebc063bd-6761-4bcd-90c7-55c3ed54d70e` | 3 | 20 | COMPLETED |

## By language

| Group | Passed | Failed | Inconclusive | Total |
|---|---|---|---|---|
| en | 13 | 1 | 0 | 14 |
| fr | 5 | 1 | 0 | 6 |

## By topic

| Group | Passed | Failed | Inconclusive | Total |
|---|---|---|---|---|
| autopay | 1 | 0 | 0 | 1 |
| cancel_or_port_out | 2 | 0 | 0 | 2 |
| dispute_refund_credit | 2 | 0 | 0 | 2 |
| fraud | 0 | 1 | 0 | 1 |
| move_number_in | 1 | 0 | 0 | 1 |
| outage_check | 1 | 0 | 0 | 1 |
| password_reset | 2 | 0 | 0 | 2 |
| pay_bill | 0 | 1 | 0 | 1 |
| restore_service | 2 | 0 | 0 | 2 |
| talk_to_a_person | 1 | 0 | 0 | 1 |
| technician_or_ticket_status | 1 | 0 | 0 | 1 |
| troubleshooting | 1 | 0 | 0 | 1 |
| two_step_login_mfa | 1 | 0 | 0 | 1 |
| upgrade | 2 | 0 | 0 | 2 |
| warranty | 1 | 0 | 0 | 1 |

## Per eval

| Id | Eval | Topic | Lang | Scored runs | Passes | Avg pass turns | Avg pass tools | Infra re-runs | Verdict | Reference |
|---|---|---|---|---|---|---|---|---|---|---|
| VE-01 | sim__cancel_service_internet_english | cancel_or_port_out | en | P P P | 3/3 | 4.67 | 6.00 | 0 | PASS | — |
| VE-02 | sim__cancel_tv_service_english | cancel_or_port_out | en | P P P | 3/3 | 3.67 | 6.00 | 0 | PASS | — |
| VE-03 | sim__check_outage_french_active | outage_check | fr | P P P | 3/3 | 4.00 | 4.33 | 0 | PASS | — |
| VE-04 | sim__check_ticket_status_french | technician_or_ticket_status | fr | P P P | 3/3 | 4.33 | 5.33 | 0 | PASS | — |
| VE-05 | sim__dispute_billing_charge_french | dispute_refund_credit | fr | P P P | 3/3 | 4.00 | 5.67 | 0 | PASS | — |
| VE-06 | sim__manage_mfa_pivot_tech | two_step_login_mfa | en | P P P | 3/3 | 6.67 | 7.00 | 0 | PASS | — |
| VE-07 | sim__pay_bill_declined_card_retry | pay_bill | en | F F F | 0/3 | — | — | 0 | FAIL | — |
| VE-08 | sim__report_fraud_french | fraud | fr | F F P | 1/3 | 1.00 | 2.00 | 0 | FAIL | — |
| VE-09 | sim__request_credit_outage_days | dispute_refund_credit | en | P P P | 3/3 | 3.67 | 5.00 | 0 | PASS | — |
| VE-10 | sim__reset_password_french | password_reset | fr | P P P | 3/3 | 4.33 | 3.33 | 0 | PASS | — |
| VE-11 | sim__reset_password_pivot_billing | password_reset | en | P P P | 3/3 | 5.67 | 7.67 | 0 | PASS | — |
| VE-12 | sim__restore_service_business_deflection | restore_service | en | P P P | 3/3 | 1.00 | 2.67 | 0 | PASS | — |
| VE-13 | sim__restore_service_french | restore_service | fr | P P P | 3/3 | 6.33 | 6.33 | 0 | PASS | — |
| VE-14 | sim__setup_autopay_after_paying_bill | autopay | en | P F P | 2/3 | 6.00 | 7.00 | 0 | PASS | — |
| VE-15 | sim__speak_frustrated_english | talk_to_a_person | en | P P P | 3/3 | 1.00 | 2.00 | 0 | PASS | — |
| VE-16 | sim__transfer_family_member_number | move_number_in | en | P F P | 2/3 | 5.50 | 6.50 | 0 | PASS | — |
| VE-17 | sim__troubleshoot_tv_signal | troubleshooting | en | P P P | 3/3 | 6.00 | 5.00 | 0 | PASS | — |
| VE-18 | sim__upgrade_mobile_plan_data | upgrade | en | P P P | 3/3 | 4.33 | 6.33 | 0 | PASS | — |
| VE-19 | sim__upgrade_tv_package_sports | upgrade | en | P P P | 3/3 | 4.33 | 6.00 | 0 | PASS | — |
| VE-20 | sim__warranty_replacement_pixel_mic | warranty | en | P P P | 3/3 | 5.67 | 6.00 | 0 | PASS | — |

Non-passing result data: `bench-holdout/runs/failing_runs_data/holdout-d4041be` (see index.md there).
