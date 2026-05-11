---
domain: reasoning
type: prompt
author: dair-ai/Prompt-Engineering-Guide
---
# Chain-of-Thought (CoT) Prompting
## Context
Use when solving complex arithmetic, commonsense, or symbolic reasoning tasks that a model fails to solve with standard zero-shot or few-shot prompting. CoT enables the model to break down problems into intermediate steps.

## Solution
Provide examples that include the reasoning process leading to the answer.

### Few-Shot CoT Example:
```
Q: The odd numbers in this group add up to an even number: 4, 8, 9, 15, 12, 2, 1.
A: Adding all the odd numbers (9, 15, 1) gives 25. The answer is False.

Q: The odd numbers in this group add up to an even number: 15, 32, 5, 13, 82, 7, 1. 
A: Adding all the odd numbers (15, 5, 13, 7, 1) gives 41. The answer is False.
```

### Zero-Shot CoT:
Simply append the following phrase to the end of your prompt:
`Let's think step by step.`

## Gotchas / Warnings
- CoT is an emergent ability that works best with sufficiently large language models.
- "Let's think step by step" can be improved by more specific instructions like "Let's work this out in a step by step way to be sure we have the right answer."
