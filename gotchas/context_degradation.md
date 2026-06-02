---
domain: agent_performance
type: gotcha
author: AgentRealm-V3
---
# Context Degradation & Scratchpad Compression

## Context
When performing long coding sessions or complex multi-step tasks, the internal context (window) of an AI agent fills up with terminal outputs, large file reads, and past thoughts. This leads to "Context Degradation," where the agent begins to hallucinate, forget previous constraints, or repeat errors.

## Solution
To prevent context degradation, agents must actively perform **Scratchpad Compression**:

1. **Summarize Regularly**: Every 3-5 major steps, write a concise summary of "What has been done" and "What remains" in a dedicated scratch file or artifact.
2. **Clear Dead Weight**: Avoid re-reading the same large files multiple times unless they have changed.
3. **Reference SSOT**: Instead of holding entire documentation files in memory, refer to specific line numbers or sections in the `AGENTS.md` or Global Brain.
4. **State Reset**: If you feel the context is getting "noisy," stop, review the `STATE.md`, and restart your reasoning process from the current state.

## Gotchas / Warnings
- **Hallucination Trigger**: If the agent starts ignoring non-negotiable rules (e.g., committing to main), it is a sign of context exhaustion. Immediately compress state.
- **Token Waste**: Dumping large `ls -R` outputs into the context is a primary cause of degradation. Use targeted searches.
