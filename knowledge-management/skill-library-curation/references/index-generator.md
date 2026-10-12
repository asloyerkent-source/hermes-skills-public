# index-generator — 原 skill-catalog（skill-index）正文（逐字）

> 2026-09-26 「技能管理簇」5→1 合并：本文件逐字并入 `flows/skill-catalog` 的 SKILL.md 正文（去 frontmatter）。
> 源目录 `flows/skill-catalog/` 已归档于 `.archive/skill-catalog/`，原件逐字保留。
> **脚本已搬入本技能** `scripts/register.sh`、`scripts/install-hooks.sh`、`_meta.json`（INDEX 生成器必须活）。

# Skill Index

Auto-scan every SKILL.md under `skills/`, extract metadata, categorize, and produce a single searchable INDEX.md. Git hooks keep the index fresh on every commit and pull.

## Problem It Solves

As skill count grows past 20+, finding the right one becomes painful — especially for the AI agent that must read descriptions at startup. Manual lists go stale fast.

Skill Index solves this by:

- **One command** → complete, up-to-date inventory
- **Zero maintenance** → git hooks auto-update on commit/pull
- **Instant lookup** → AI reads INDEX.md instead of crawling the whole directory

## Quick Start

### Manual scan
```bash
bash skills/knowledge-management/skill-library-curation/scripts/register.sh
```

### Install git hooks (one-time)
```bash
bash skills/knowledge-management/skill-library-curation/scripts/install-hooks.sh
```

After that, INDEX.md updates automatically whenever you commit or pull.

## How It Works

1. **Scan** — Recursively find all `SKILL.md` files under `skills/`
2. **Extract** — Parse YAML frontmatter: `name`, `description`, relative path
3. **Categorize** — Smart matching by directory structure + description keywords
4. **Generate** — Write `skills/INDEX.md` as a categorized Markdown table

## ⚠️ `description` 有三种形态，只抓第一行会读出符号

`register.sh` 早期写法是 `grep -oP 'description:\s*\K.*' | head -1`，只取第一行。
于是 YAML **块标量**写法的描述会被读成**标量符号本身**：

| 源文件写法 | 索引里显示成 |
|---|---|
| `description: 单行中文` | ✅ 正常 |
| `description: "带引号单行"` | ✅ 正常（要剥外层引号） |
| `description: \|` + 缩进多行 | ❌ 显示成竖线本身 |
| `description: >` + 缩进多行 | ❌ 显示成大于号本身 |

**症状**：用户视角就是「这个技能没有功能说明」，而源文件里描述写得好好的——
**从输出上完全看不出是解析器的错**，会误以为是技能作者没写。

**修法**：块标量时把后续**缩进行**拼成一行，遇到第一个非缩进非空行停止；
用一段 `awk` 一次做完（单行/引号/块标量三种形态都走同一条路径），不要再叠 `grep | head -1`。
现有 `register.sh` 已按此法实现。

**另一个坑：描述正文里出现竖线会断 Markdown 表格列。** 描述落表前统一把 `|` 换成全角。

## Output Format

```markdown
# Skills Index
> Auto-generated. Run `bash skills/knowledge-management/skill-library-curation/scripts/register.sh` to update.

## Category Name
| Skill | Path | Trigger |
|-------|------|---------|
| my-skill | path/to/SKILL.md | Description preview... |
```

## Customization

### Adding categories

Edit the `categorize()` function in `register.sh` to add your own rules:

```bash
    *your-keyword*) echo "Your Category"; return ;;
```

### Excluding skills

Add the skill's directory to the `find` exclusion list in `register.sh`:

```bash
find "$SKILLS_DIR" -name "SKILL.md" -type f \
    -not -path "$SKILLS_DIR/.archive/*" \
    -not -path "$SKILLS_DIR/your-private-skill/*"
```

## Requirements

- Bash 4+
- Git (for hooks)
- OpenClaw workspace with `skills/` directory

## License

MIT
