---
domain: engineering
type: skill
author: mattpocock/skills
---
# TDD (Test-Driven Development)
## Context
Use when building features or fixing bugs using a strict red-green-refactor loop. Focuses on verifying behavior through public interfaces rather than implementation details.

## Solution
Follow the vertical slice approach: One test → one implementation → repeat.

### 1. Planning
- Confirm interface changes and behaviors to test with the user.
- Prioritize behaviors (you can't test everything).
- List behaviors to test, not implementation steps.

### 2. Tracer Bullet
Write ONE test for the first behavior that fails (RED), then write minimal code to pass (GREEN). This proves the path works end-to-end.

### 3. Incremental Loop
For each remaining behavior:
- **RED**: Write next test → fails.
- **GREEN**: Minimal code to pass → passes.
- Rules: One test at a time, only enough code to pass, no anticipation of future tests.

### 4. Refactor
After all tests pass:
- Extract duplication, deepen modules, apply SOLID principles.
- Run tests after each refactor step.
- **Never refactor while RED.**

### Testing Principles
- **Good tests** are integration-style, exercising real code paths through public APIs.
- **Bad tests** are coupled to implementation (mocking internal collaborators, testing private methods). They break during refactors even if behavior hasn't changed.

## Gotchas / Warnings
- Do NOT write all tests first, then all implementation (horizontal slicing).
- Do NOT refactor while the tests are failing (RED).
- Do NOT test implementation details or private methods.
- Do NOT use absolute paths; use `$PROJECT_ROOT`.
