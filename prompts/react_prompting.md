---
domain: reasoning
type: prompt
author: dair-ai/Prompt-Engineering-Guide
---
# ReAct Prompting (Reasoning + Acting)
## Context
Use when an LLM needs to interact with external tools (search engines, calculators, APIs) to gather information and reason about it to reach a conclusion. This reduces hallucinations by grounding reasoning in external observations.

## Solution
Prompt the model to generate interleaved reasoning traces (Thoughts) and actions (Acts) in a specific format.

### Template:
```
Question: [The user's question]
Thought 1: [Reasoning about what information is needed]
Action 1: [Tool call, e.g., Search(query)]
Observation 1: [Result from the tool]
Thought 2: [Reasoning based on the observation]
...
Final Answer: [The conclusive result]
```

### Example (Few-Shot Exemplar):
```
Question: Aside from the Apple Remote, what other devices can control the program Apple Remote was originally designed to interact with?
Thought 1: I need to search for the program Apple Remote was designed for, then find other devices that can control it.
Action 1: Search[Apple Remote]
Observation 1: The Apple Remote is a remote control introduced in 2005 for the Front Row media center program...
Thought 2: The program is Front Row. I need to search for other devices that can control Front Row.
Action 2: Search[Front Row control devices]
...
Final Answer: [Answer]
```

## Gotchas / Warnings
- ReAct is highly dependent on the quality of the information retrieved; non-informative search results can derail the model.
- The model may get stuck in a loop if the observations do not resolve the thought; ensure tools have clear failure modes.
