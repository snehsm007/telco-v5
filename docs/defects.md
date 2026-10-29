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
