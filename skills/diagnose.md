---
domain: engineering
type: skill
author: mattpocock/skills
---
# Diagnose
## Context
Disciplined diagnosis loop for hard bugs and performance regressions. Use when a user reports a bug, says something is broken/throwing/failing, or describes a performance regression.

## Solution
Follow the disciplined loop: Reproduce → Minimise → Hypothesise → Instrument → Fix → Regression-test.

### Phase 1: Build a feedback loop
Everything else is mechanical. If you have a fast, deterministic, agent-runnable pass/fail signal for the bug, you will find the cause.
- **Reproduction methods**: Failing test, Curl/HTTP script, CLI invocation, Headless browser script, Replay captured trace, Throwaway harness, Property/fuzz loop, Bisection harness, Differential loop.
- **Iterate on the loop**: Make it faster, sharper (specific symptom), and more deterministic.

### Phase 2: Reproduce
Run the loop and watch the bug appear. Confirm it produces the specific failure mode described by the user.

### Phase 3: Hypothesise
Generate 3–5 ranked, falsifiable hypotheses. State the prediction each makes: "If <X> is the cause, then <changing Y> will make the bug disappear." Show the list to the user before testing.

### Phase 4: Instrument
Change one variable at a time. Use debugger/REPL inspection first, then targeted logs. Tag every debug log with a unique prefix (e.g., `[DEBUG-a4f2]`) for easy cleanup.

### Phase 5: Fix + Regression Test
Write the regression test before the fix if a correct seam exists.
1. Turn minimized repro into failing test.
2. Apply fix.
3. Watch it pass.
4. Re-run Phase 1 feedback loop against original scenario.

### Phase 6: Cleanup + Post-mortem
- Re-run original repro to confirm fix.
- Remove all `[DEBUG-...]` logs.
- Document what would have prevented the bug.

## Gotchas / Warnings
- Do NOT proceed to hypothesise without a loop.
- Do NOT "log everything and grep"; use targeted logs.
- Do NOT skip phases unless explicitly justified.
- Do NOT leave debug logs in the codebase.
