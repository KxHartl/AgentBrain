---
domain: workflow
type: skill
author: SriLaxmi1993/Generative-AI-Projects
---
# Multi-Agent Role Definition (CrewAI/AutoGen Pattern)
## Context
Use when a complex task needs to be decomposed into specialized roles. This pattern is ideal for sequential or collaborative workflows where distinct expertise (e.g., Analysis, Planning, Execution, QA) improves the quality of the final output.

## Solution
Define agents with specific roles, goals, and backstories to "prime" their behavior and expertise.

### 1. Role Anatomy
Every agent should have:
- **Role**: A clear title (e.g., "Curriculum Analyst").
- **Goal**: A concise statement of what they are trying to achieve.
- **Backstory**: A detailed personality and experience profile to provide context for their decision-making.

### 2. Standardized Roles for Engineering/Research
- **The Analyst**: Breaks down complex requirements into structured components.
- **The Planner**: Orchestrates the timeline, resource allocation, and dependencies.
- **The Developer/Executor**: Performs the actual work (coding, writing, searching).
- **The Coach/Reviewer**: Quality assurance, resource recommendation, and final polishing.

### 3. Task Handover Pattern
Tasks should be linked such that the output of one serves as the context for the next:
- **Sequential Process**: Agent A (Analyst) -> Agent B (Planner) -> Agent C (Reviewer).
- **Context Injection**: Explicitly pass the results of preceding tasks to ensure continuity.

## Gotchas / Warnings
- **Role Overlap**: Avoid making goals too broad; if two agents can do the same task, they will often conflict or duplicate effort.
- **Context Bloat**: Passing too much irrelevant history between agents can cause model confusion or token limit issues.
- **Lack of Critique**: Without a dedicated "Reviewer" or "QA" agent, errors from the "Executor" often pass through to the final result.
