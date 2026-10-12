---
name: competitive-product-analysis
description: Use when 竞品对比/选型/对标拆解：深度技术解析与模式提取，看别人怎么做的。
---

# Competitive Product Analysis

Analyze a software product or framework to extract reusable architectural patterns, identify genuine innovations vs marketing, and assess applicability to the user's context. This is not a feature comparison — it's a technical deep-dive that maps unfamiliar systems onto familiar ones.

## When to Use

- "Analyze X" / "Deep dive into X" / "What can we learn from X"
- User wants to understand a competing or related product's architecture
- Evaluating whether a product's approach is technically novel or just well-integrated
- Preparing to decide whether to adopt/adapt a pattern

Don't use for: ongoing monitoring (use `competitor-news-monitor`), one-off fact-finding (use `web_search`), or pre-task research (use `execution-discipline`).

## Procedure

### 1. Surface the product

Gather official positioning, feature list, and marketing claims from the product's official site and recent news. Record: what they say they do, who they're for, what tech they claim to use.

**Pitfall:** Marketing materials conflate roadmap with reality. Record claims as "claimed" until verified.

### 2. Find technical depth

**For open-source projects:** Clone or download the source tarball and read it directly. Start with README → pyproject.toml/package.json (dependencies) → core source files. For large codebases (>500 files), delegate to a sub-agent with specific reading instructions.

**For closed-source products:** Search for technical breakdowns, architecture deep-dives, and community analyses. Look for:
- Engineering blogs and technical whitepapers
- Conference talks and slide decks
- Community reverse-engineering or analysis articles
- Job postings (reveal tech stack and priorities)

**Pitfall:** Vendor "technical" content is often marketing in disguise. Cross-reference claims against independent analysis.

**Pitfall:** For open-source projects, don't rely on secondary analyses — read the source. Secondary sources may be outdated or wrong about implementation details.

### 3. Map to a structured framework

Decompose the product into a consistent framework:
- **Entry points:** How do users interact with it? (chat, API, GUI, IM)
- **Gateway/Routing:** How are requests received and dispatched?
- **Agent/Executor model:** How many agents? How do they coordinate?
- **Context/Memory:** How is state managed? What scopes exist?
- **Extensions:** How does it integrate with external systems? (MCP, Skills, Connectors)
- **Security/Permission model:** What can it access? How is that controlled?
- **Deployment:** Where does it run? (cloud, local, hybrid)

**Pitfall:** Products describe their architecture in idiosyncratic terms. Translate to generic concepts for fair comparison.

### 4. Compare to user's existing system

Map the product's components onto the user's system (e.g., Hermes). Identify:
- What they have that we don't
- What we have that they don't
- What's the same but named differently
- What's genuinely novel vs. just well-packaged

**Pitfall:** Platform differences matter. A feature that's trivial on Windows/Mac may be hard on Linux headless, and vice versa. Don't assume portability.

**Pitfall:** Enterprise features assume enterprise context. Multi-tenant RBAC, member management, and project isolation are worthless to a solo user. When mapping, strip features that only make sense at scale — they inflate the perceived gap without creating real value.

**Step:** Explicitly map by scope/role (account identity → active context → task → session), not by feature name. Products rename familiar concepts; matching by role surfaces the real differences.

### 5. Assess materiality

Not everything interesting is useful. For each potential learning:
- Is it a genuine technical innovation or just good UX?
- Does it solve a problem the user actually has?
- What's the implementation cost?
- Does it require infrastructure the user doesn't have?

**Pitfall:** "Cool" is not the same as "useful." Be honest about whether something is just interesting academically vs. actually applicable.

### 6. Present findings

Structure the analysis:
1. **What it is** (one sentence, no marketing speak)
2. **Architecture map** (structured breakdown)
3. **What's genuinely new** (if anything)
4. **What we can learn** (specific, actionable)
5. **What's not applicable** (and why)
6. **Recommendation** (watch, adopt, or ignore)

**Pitfall:** Don't recommend implementation unless the user has an explicit need. Default to "watch" — most products aren't worth the adaptation cost.

## Pitfalls

- Taking marketing materials at face value — always verify with technical sources
- Ignoring platform/OS differences when assessing portability
- Confusing "well-integrated" with "technically innovative"
- Recommending changes before the user has an explicit need
- Presenting feature lists instead of architectural analysis
- Overlooking the boring infrastructure (networking, process management) that makes the flashy features work

## User Preferences

- Prefers deep technical analysis over surface-level feature comparison
- Wants to understand "why" and "how," not just "what"
- Defaults to "观望" (watching) over immediate implementation — respect this
- Values honest assessment of whether something is actually useful to their specific context
- Dislikes marketing-driven analysis; wants the technical reality
- After analysis, tends to "继续观望" — don't push for implementation
- Doesn't want changes unless there's an explicit need ("有就更好，没有也行")
