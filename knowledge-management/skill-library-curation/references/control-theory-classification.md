# Control Theory Framework for Skill Classification

## 1. Feedback Control
Skills that provide immediate correction, audit trails, or status reports.
- **When to use**: User asks for verification, validation, or real-time monitoring.
- **Examples**: execution-discipline, hermes-dojo, prism-reflect, evey-status, evey-cost-guard.
- **Key signal**: The skill closes a loop — it takes action, measures result, and adjusts.

## 2. Black Box Analysis
Skills that analyze systems without opening or modifying them.
- **When to use**: User asks to understand code, architecture, or data flow.
- **Examples**: prism-scan, prism-discover, prism-3way, codebase-memory.
- **Key signal**: The skill reads inputs/outputs to infer internal structure.

## 3. Information Flow
Skills that handle data extraction, transformation, or filtering.
- **When to use**: User asks to fetch, clean, or move data.
- **Examples**: defuddle, web-extract, evey-digest, evey-rag.
- **Key signal**: The skill reduces noise and increases signal quality.

## 4. Stability Theory
Skills that maintain system health, handle errors, or enable recovery.
- **When to use**: User asks for deployment, rollback, or fault tolerance.
- **Examples**: terminal-run, deployment, evey-watchdog, evey-session-guard.
- **Key signal**: The skill keeps the system in a safe operating region.

## 5. Optimal Control
Skills that optimize cost, performance, or resource allocation under constraints.
- **When to use**: User asks to reduce cost, speed up, or choose the best model.
- **Examples**: evey-delegate-model, evey-goals, coding-delegation.
- **Key signal**: The skill finds the best path given limited resources.

## 6. System Modeling
Skills that create abstractions, graphs, or simulations of complex systems.
- **When to use**: User asks to map dependencies, trace paths, or build knowledge graphs.
- **Examples**: codebase-memory, knowledge-vault-ops, skill-evolution.
- **Key signal**: The skill builds a representation that can be queried.

> ⚠️ **2026-10-01 已归档**：依赖 `gepa`/`fastembed` 缺失、无 cron 任务、126 次评估 0 采纳。
> 备份在 `cache/trash/skill-evolution.20261001-2109/`（含 126 条 eval_history + 报告）。
> 本节保留作为决策记录——它解释了当时为何「修，不弃」。


## 7. Human-Machine Collaboration
Skills that integrate human judgment into the agent loop.
- **When to use**: User asks to capture preferences, build personas, or create UIs.
- **Examples**: distilly, hermes-workspace, agent-communication-discipline.
- **Key signal**: The skill treats the human as a component in the control loop.

## Usage Notes
- A single skill can span multiple categories. Classify by its PRIMARY function.
- When merging skills, the merged result should have a clear primary classification.
- If a skill doesn't fit any category, it may be a candidate for deletion (too narrow to generalize).
