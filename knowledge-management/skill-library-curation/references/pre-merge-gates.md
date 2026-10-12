# pre-merge-gates — 原 skill-library-curation/SKILL.md 第 130–166 行（逐字）

> 2026-09-26 「技能管理簇」5→1 合并：本节从主 SKILL.md 拆出，内容逐字未改。

## Pre-merge gates (run BEFORE drafting any cluster plan)

Two gates that usage-data clustering gets wrong on its own. Both have silently
cost work; run them on every cluster.

### Gate A — protection markers

Ranking by `use_count` puts the *protected* skill in the cluster as often as not,
because the protected one is frequently the most-used member. Sweep the library
for protection markers first and drop every hit from the cluster:

```bash
cd ~/.hermes/skills
grep -rnE 'sacred|never merge|never delete|禁止合并|不要合并|不可合并' --include='*.md' . | grep -v '/.archive/'
```

The markers live in another skill's prose, not in machine-readable metadata, so
there is no shortcut — read the hits. Skills pinned with `hermes curator pin`
are likewise off-limits to autonomous edits.

### Gate B — external references

A skill's name is referenced from outside its own directory. Enumerate every
reference to every cluster member and update them in the same change:

```bash
for n in <cluster members>; do
  grep -rn "$n" ~/.hermes/skills --include='*.md' | grep -v '/.archive/'
  grep -n  "$n" ~/.hermes/cron/jobs.json
done
```

Three classes break in practice, all observed: cron `jobs.json` (both the
`skills:` list and free text in `prompt`), other skills' `related_skills:`
frontmatter and inline "see `<name>`" prose, and the generated `INDEX.md`.
A merged-away name left in a cron `prompt` is invisible until the job runs.
