---
domain: reasoning
type: prompt
author: dair-ai/Prompt-Engineering-Guide
---
# Tree of Thoughts (ToT)
## Context
Use for complex tasks that require exploration, strategic lookahead, or backtracking (e.g., creative writing, mathematical puzzles like Game of 24, strategic planning). ToT allows the model to evaluate multiple "thought branches" and discard those that are unlikely to lead to a solution.

## Solution
Prompt the model to act as multiple experts or to maintain a tree of intermediate thoughts.

### Simple Single-Prompt Implementation:
```
Imagine three different experts are answering this question.
All experts will write down 1 step of their thinking, then share it with the group.
Then all experts will go on to the next step, etc.
If any expert realises they're wrong at any point then they leave.
The question is... [Your Question]
```

### Structured Framework Approach:
1. **Thought Generation**: Generate several potential next steps.
2. **State Evaluation**: Evaluate each step (e.g., "sure", "maybe", "impossible").
3. **Search**: Use BFS or DFS to explore the most promising branches.

## Gotchas / Warnings
- ToT can be token-intensive as it involves generating and evaluating multiple paths.
- Requires the model to be capable of self-evaluation; if the model cannot accurately judge its own thoughts, ToT fails.
