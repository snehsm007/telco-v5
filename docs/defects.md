# Defect Log

Group failing evaluations by shared root cause (not one entry per evaluation). Fix one root-cause cluster per commit after verifying with `make impact` and `make smoke-impact`.

### DEF-01: VE-08 simulator never produces silent turns and slot 3 platform judge error
- **Found by**: `VE-08` (`sim__check_ticket_status_retry_strikes`) (`full-32498c1`, `1/3`)
- **Evidence**: `bench/runs/failing_runs_data/full-32498c1/VE-08__44f08f2f__r2.md`, `bench/runs/failing_runs_data/full-32498c1/VE-08__44f08f2f__r3.md`
- **Label**: `judge`
- **Status**: `open`
- **Root cause layer**: `platform`
- **Diagnosis (all 3 judge metrics)**:
  - *Expectations*: Slot 2 FAIL (`bench/runs/failing_runs_data/full-32498c1/VE-08__44f08f2f__r2.md`): simulator never produces silent turns ("In the provided conversation, there are no instances of silent turns from the user."). Slot 3 OUTCOME_UNSPECIFIED (`bench/runs/failing_runs_data/full-32498c1/VE-08__44f08f2f__r3.md`): platform judge error (`OUTCOME_UNSPECIFIED`, metric value -1, diagnostic_info: "The conversation does not contain any instances of silent turns.").
  - *User Goal*: Skipped via config (score -1)
  - *Hallucination*: Skipped via config (score -1)
- **Fix & `file:line`**: Simulator and platform judge noise; evaluation expectation requires recovery from silent turns that the simulator never injects. No agent code change.
- **Alternatives considered**: None (eval definition and platform judge behavior).
- **Verification (`strict 3/3 | majority >=2/3 | individual`)**: Classified as simulator/judge noise on `full-32498c1` (1/3 pass).

### DEF-02: VE-04 judge faults user requesting SMS guide before agent offered it
- **Found by**: `VE-04` (`sim__check_outage_none_found_sms_troubleshoot`) (`full-32498c1`, `2/3`)
- **Evidence**: `bench/runs/failing_runs_data/full-32498c1/VE-04__44f08f2f__r3.md`
- **Label**: `judge`
- **Status**: `open`
- **Root cause layer**: `platform`
- **Diagnosis (all 3 judge metrics)**:
  - *Expectations*: Slot 3 FAIL (`bench/runs/failing_runs_data/full-32498c1/VE-04__44f08f2f__r3.md`): "Since the agent did not initiate the offer, the expectation is not fully met." (Judge faults user requesting SMS guide proactively before agent offered it).
  - *User Goal*: Skipped via config (score -1)
  - *Hallucination*: Skipped via config (score -1)
- **Fix & `file:line`**: Judge noise; user proactively requested SMS troubleshooting guide before agent offered it. No agent code change.
- **Alternatives considered**: Prompt change rejected; agent correctly handled caller-initiated request.
- **Verification (`strict 3/3 | majority >=2/3 | individual`)**: Classified as judge noise on `full-32498c1` (2/3 pass).

### DEF-03: Holdout VE-07 declined card scenario cannot trigger card decline
- **Found by**: Holdout `VE-07` (`holdout-32498c1`, `0/3`)
- **Evidence**: `bench-holdout/runs/failing_runs_data/holdout-32498c1/` VE-07 r1, r2, r3
- **Label**: `judge`
- **Status**: `open`
- **Root cause layer**: `platform`
- **Diagnosis (all 3 judge metrics)**:
  - *Expectations*: All 3 runs FAIL: Scenario expects a card decline flow, but caller simulation guide provides no declining card number. The agent offers the card on file (`4242`), which succeeds because the fake database only declines cards ending in `0000` or `9999` (`lib/fakes.py:38`, `lib/services.py:1188`). Hence, card decline cannot occur.
  - *User Goal*: Skipped via config (score -1)
  - *Hallucination*: Skipped via config (score -1)
- **Fix & `file:line`**: Platform/scenario noise: guide names no declining card, and `lib/fakes.py:38` / `lib/services.py:1188` correctly enforces `DECLINED_CARD_LAST4`. Modifying card numbers would violate fake-world invariants.
- **Alternatives considered**: None (modifying valid/declined card invariants is strictly prohibited).
- **Verification (`strict 3/3 | majority >=2/3 | individual`)**: Classified as holdout scenario design noise on `holdout-32498c1` (0/3 pass).

### DEF-04: VE-20 mid-call fraud transfer timing misjudged as not immediate from turn 1
- **Found by**: `VE-20` (`sim__report_fraud_mid_call_switch`) (`full-32498c1`, `2/3`)
- **Evidence**: `bench/runs/failing_runs_data/full-32498c1/VE-20__44f08f2f__r1.md`
- **Label**: `judge`
- **Status**: `open`
- **Root cause layer**: `platform`
- **Diagnosis (all 3 judge metrics)**:
  - *Expectations*: Slot 1 FAIL (`bench/runs/failing_runs_data/full-32498c1/VE-20__44f08f2f__r1.md`): "The user was not immediately transferred to the fraud team. The conversation started with the user asking about their bill balance... The transfer to the fraud team only occurred after the user expressed concerns about unauthorized charges, which was several turns into the conversation." In the turn caller first said "hacked", the agent spoke the empathy + handoff line and called `handover_to_person(reason="fraud_escalation", target_queue="fraud_and_security_24x7")` + `end_session` in that same turn. Judge misread "immediately" as "from turn 1".
  - *User Goal*: Skipped via config (score -1)
  - *Hallucination*: Skipped via config (score -1)
- **Fix & `file:line`**: Judge timing artifact; caller switched topic mid-call and agent immediately escalated in that turn. No agent code change needed.
- **Alternatives considered**: Prompt change rejected; transfer is already immediate upon the first fraud mention.
- **Verification (`strict 3/3 | majority >=2/3 | individual`)**: Classified as judge timing artifact on `full-32498c1` (2/3 pass).
