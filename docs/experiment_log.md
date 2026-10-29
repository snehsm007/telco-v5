# Experiment Log

Every cloud evaluation run and hill-climb iteration is logged here in chronological order.
Always report **Strict `3/3`**, **Majority `>=2/3`**, and **Individual** pass rates side-by-side (never composite slices across runs/SHAs).
Gate 3 requires **Strict `3/3` >= 90% AND 100% Majority (`>=2/3`, zero `0/3` or `1/3` evals)** with `0` tool runtime errors.

| Iteration | Date (UTC) | Commit | Mechanism / Change | Impact Verdict (`make smoke-impact`) | Strict `3/3` | Majority `>=2/3` | Individual | Decision / Keep? | Full Run ID & Notes |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-10-29 | `32498c1` | Pass-1 visible 50-evaluation baseline (`make bench-full ENV=staging`) | — | `31/50 (62.0%)` | `44/50 (88.0%)` | `125/150 (83.3%)` | baseline | `full-32498c1` (`44f08f2f-ceb2-4682-ae8d-17cf35c72663`, `22dc33b6-f8d9-4c56-8741-cbb3a5bcf7e1`), holdout `12/20 (60.0%)` |
| 2 | 2026-10-29 | `dbaceb3` | Asymmetric session language lock across 21 tools in `lib/services.py` | FULL (50 evals) | `33/50 (66.0%)` | `43/50 (86.0%)` | `123/150 (82.0%)` | KEPT | Lane B exp2 full runs `3cb7b2ec…`/`b2b7259c…` (33/50) and revised `c6f5481e…`/`244c499a…` (33/50 vs baseline 31/50, 0 tool errors; every non-3/3 judge reason is auth/C1, missing facts, port/catalog or DEF-01/03/04 noise, none language) |
| 3 | 2026-10-29 | `818ead3` | Payment confirmation `spoken_summary`, `service_status: "active"`, `suspension_avoided` in `process_bill_payment_impl` | SMOKE (15 evals) | `7/15 (46.7%)` | `12/15 (80.0%)` | `34/45 (75.6%)` | KEPT | Lane A exp1 smoke `62ba64bb-e469-4f0b-9bfe-f379def85bde` (7/15: targets VE-18 3/3, VE-17 2/3 with miss an auth/C1 failure; all other misses attributable to A/C1/E4/DEF-04) |
| 4 | 2026-10-29 | `779d51a` | Sales catalog facts (speed, modem, addons, tax) & `confirmed` gate in `commit_plan_or_order_impl` | FULL (7 evals) | `6/7 (85.7%)` | `7/7 (100.0%)` | `20/21 (95.2%)` | KEPT | Lane A exp1 smoke `21505be4-3a3a-4084-8427-1a5c033599b6` (6/7: targets VE-44 and VE-46 3/3, controls VE-47..50 3/3, VE-45 2/3 miss = caller pivoted to business options → handover) |
| 5 | 2026-10-29 | `0adb003` | Port-out and port-in tool facts (disclosures, fees, PIN, request status) & relaxed donor detail gating | SMOKE (27 evals) | `22/27 (81.5%)` | `24/27 (88.9%)` | `71/81 (87.7%)` | KEPT | Lane B exp2 smoke `315272d5…`/`0664b743…` (22/27, targets VE-19 1/3→3/3 and VE-39 3/3, controls VE-01/02/38 3/3; misses VE-16 DTMF-greeting noise, VE-25/32/33 identification (lane-3), VE-44 r2 current-plan facts) |
