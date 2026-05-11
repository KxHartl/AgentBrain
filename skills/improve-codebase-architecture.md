---
domain: engineering
type: skill
author: mattpocock/skills
---
# Improve Codebase Architecture
## Context
Use when the user wants to improve architecture, find refactoring opportunities, consolidate tightly-coupled modules, or make a codebase more testable and AI-navigable.

## Solution
Surface architectural friction and propose deepening opportunities (turning shallow modules into deep ones).

### 1. Explore
Note friction points:
- Bouncing between many small modules to understand one concept.
- **Shallow modules**: Interface is nearly as complex as implementation.
- **Lacking Locality**: Pure functions extracted for tests, but real bugs hide in how they are called.
- Tightly-coupled modules leaking across seams.
- **Deletion test**: If deleting a module concentrates complexity in callers, it was EARNING its keep. If complexity vanishes, it was a pass-through.

### 2. Present Candidates
Provide a numbered list with: Files, Problem, Solution (Plain English), and Benefits (Locality/Leverage/Tests).
- Use `CONTEXT.md` vocabulary for the domain.
- Use architectural terms: Module, Interface, Implementation, Depth, Seam, Adapter, Leverage, Locality.

### 3. Grilling Loop
Walk the design tree for chosen candidates.
- **Update CONTEXT.md**: Add new terms or sharpen fuzzy ones as they crystallize.
- **Offer ADRs**: Record load-bearing reasons for rejecting candidates to prevent future re-suggestions.

### Key Definitions
- **Deep Module**: Lots of behavior behind a small interface (High leverage).
- **Shallow Module**: Interface nearly as complex as implementation.
- **Seam**: Place where behavior can be altered without editing in place (not "boundary").

## Gotchas / Warnings
- Do NOT propose interfaces until the user picks a candidate.
- Do NOT re-litigate decisions in existing ADRs unless friction is extreme.
- Do NOT drift from standard architectural vocabulary (e.g., don't use "service" if "module" fits).
