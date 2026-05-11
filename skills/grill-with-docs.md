---
domain: engineering
type: skill
author: mattpocock/skills
---
# Grill With Docs
## Context
Use when the user wants to stress-test a plan against their project's language and documented decisions. It challenges your plan against the existing domain model, sharpens terminology, and updates documentation (CONTEXT.md, ADRs) inline as decisions crystallise.

## Solution
Interview the user relentlessly about every aspect of the plan until a shared understanding is reached. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide a recommended answer.

- **Ask questions one at a time**, waiting for feedback.
- **Explore codebase** to answer questions if possible.
- **Challenge against the glossary**: Call out conflicts with existing language in `CONTEXT.md` immediately.
- **Sharpen fuzzy language**: Propose precise canonical terms for vague or overloaded words.
- **Discuss concrete scenarios**: Stress-test domain relationships with specific edge cases.
- **Cross-reference with code**: Check if the code agrees with how the user says things work.
- **Update CONTEXT.md inline**: Capture resolved terms immediately in `CONTEXT.md`. Only include terms meaningful to domain experts, not implementation details.
- **Offer ADRs sparingly**: Only for decisions that are hard to reverse, surprising without context, and the result of a real trade-off.

## Gotchas / Warnings
- Do NOT batch updates to `CONTEXT.md`; update it inline as decisions happen.
- Do NOT create ADRs for every decision; only when the three criteria (hard to reverse, surprising, real trade-off) are met.
- Do NOT use absolute paths; use `$PROJECT_ROOT`.
