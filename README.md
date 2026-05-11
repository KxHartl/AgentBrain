# AgentBrain 🧠

The Single Source of Truth (SSOT) for local AI Agent skills, prompts, and architectural patterns. This repository is designed to be the foundational knowledge base for LangGraph, CrewAI, and Docling-based RAG systems.

## 📂 Directory Structure

- **`/skills`**: Standardized engineering workflows and multi-agent architectural patterns.
- **`/prompts`**: Advanced reasoning templates (CoT, ReAct, ToT) and security/adversarial defense strategies.
- **`/gotchas`**: Documented failure modes, edge cases, and "what NOT to do" for AI agents.

## 📜 Standardized Format (`_TEMPLATE.md`)

All knowledge in this repository MUST follow the strict metadata and structure format defined in `_TEMPLATE.md`:

1.  **Metadata Block**: Domain, Type, and Author. Must be under 100 tokens.
2.  **Title**: Clear, descriptive name of the skill or prompt.
3.  **Context**: *When* and *why* an AI agent should use this knowledge.
4.  **Solution**: The actual logic, code, or instruction.
5.  **Gotchas / Warnings**: Critical constraints and failure modes.

## 🛠 Usage for AI Agents

Future AI agents interacting with this workspace are **commanded** to:
- Reference these files to align with existing engineering standards (e.g., TDD, Diagnose loop).
- Use the advanced reasoning prompts when faced with complex logic or external tool requirements.
- Abide by the formatting rules when injecting new knowledge into this repository.

---
*Initialized on Monday, 11 May 2026.*
