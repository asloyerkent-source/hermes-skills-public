---
name: hermes-skills-public
description: Curated AI agent methodology skills — decision, execution, security, and multi-model collaboration. Platform-agnostic, works with any AI coding assistant.
topics:
  - ai-agent
  - agent-skills
  - llm
  - ai-coding
  - ai-workflow
  - decision-making
  - debugging
  - security
  - multi-model-review
  - prompt-engineering
---

# Hermes Agent Skills — Curated Methodology Library

> Production-tested AI agent methodologies. Platform-agnostic — works with any AI coding assistant.

## Core Principles

**Producers don't self-review** — those who write code don't review it; those who review don't write it.
**Verification loop** — every claim needs real test evidence, not memory or impressions.
**Root-cause fixes** — fix the root cause, not the symptom.

## 15 Curated Skills

### Decision & Planning

| Skill | Purpose |
|-------|---------|
| `decision-loop` | Nine-step decision cycle: source-of-truth → brief → delegate → verify |
| `competitive-product-analysis` | Competitor comparison + pattern extraction + selection |
| `deep-reading-long-documents` | Long-document deep-reading methodology |
| `structured-input-collection` | Surveys, profiles, checklist validation |

### Execution & Debugging

| Skill | Purpose |
|-------|---------|
| `execution-discipline` | Verify → Execute → Validate, always before acting |
| `systematic-debugging` | Reproduce → Root-cause → Fix → Verify |
| `measurement-integrity` | Anti-false-positive: validate the probe before blaming the target |
| `doubt-driven-development` | Adversarial reviewer: artifacts + contracts only, no conclusions |

### Security & Governance

| Skill | Purpose |
|-------|---------|
| `private-data-egress-guard` | Private data egress guard (PII / health / financial) |
| `skill-security` | Skill security audit (prompt injection / data exfiltration) |
| `safe-file-organization` | Anti-accidental-delete: rm → trash |
| `skill-library-curation` | Skill library governance: admission / merge / audit |

### Multi-Model & Collaboration

| Skill | Purpose |
|-------|---------|
| `multi-model-review` | Multi-model cross-review + independent reviewer |
| `coding-delegation` | Delegation discipline: producer doesn't hand-write + real-test acceptance |

### Publishing & Tooling

| Skill | Purpose |
|-------|---------|
| `skill-publish` | Sanitize + push + independent verification, private → public |

## Usage

Each skill is a `SKILL.md` file. Place it in your AI assistant's skills directory.

```bash
# Clone the whole library
git clone https://github.com/asloyerkent-source/hermes-skills-public.git

# Or copy only the skills you need
cp -r hermes-skills-public/flows/decision-loop ~/.hermes/skills/flows/
```

### How Skills Get Triggered

Skills auto-match on **search keywords** inside their content — no manual invocation needed. When your request hits a skill's keywords, that skill activates:

| You say | Triggers | What it does |
|---------|----------|--------------|
| "help me pick / compare competitors" | `competitive-product-analysis` | competitor teardown + pattern extraction |
| "track down this bug" | `systematic-debugging` | root-cause, not symptom |
| "can I delete this file?" | `safe-file-organization` | rm → trash, prevents accidental loss |
| "organize my vault / make a plan" | `decision-loop` | nine-step loop: verify → delegate → validate |

### A Complete Example

> User: "help me organize my vault"
>
> → triggers `decision-loop` → runs the nine steps: check sources → write the task brief → delegate → validate
> → during cleanup triggers `safe-file-organization`: every delete goes to trash first, real delete only after md5 reconciliation

### Contributing

Issues welcome — whether a skill helped or fell short, and especially scenarios no skill covers:

https://github.com/asloyerkent-source/hermes-skills-public/issues

## License

MIT
