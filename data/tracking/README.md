# T+1 Verification Guide

## Execution Process
1. **Time**: Tomorrow (T+1) after market close (after 15:00 CST)
2. **Command**: `python tools/verify_t1_performance.py`
3. **Decision**: Execute corresponding action based on "FINAL DECISION"

## Falsification Criteria (Red Flags)
- **Condition A (Core Crash)**: 002514.SZ drops > 4%
  - *Action*: Immediate rollback to v9.4.5
- **Condition B (Group Failure)**: 3+ stocks close negative
  - *Action*: Emergency parameter adjustment (Phase 3)

## Expected Matrix
| Win Rate | Evaluation | Action |
|---|---|---|
| ≥ 75% | Excellent | Continue monitoring (1 week) |
| 50-75%| Good | Prepare Phase 3 |
| < 25% | Failure | Immediate rollback |
