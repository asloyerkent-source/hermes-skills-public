# 技能瘦身：把细节外移到 references 的重复流程

> 触发时机：SKILL.md 超过 12KB 规范上限，或载入一次吃掉 >10K tok 时。
> 原则：**只降级路径，不降标准**——核心规则留 SKILL.md，案例细节移 references。

## 流程

1. **测量**：`stat -c%s <skill>/SKILL.md` 得字节数（不是 `len(text)/1024`——中文 1 字符 = 3 字节）
2. **找最大段**：按 `##` 切章节，算每段字节数，找占比 >20% 的段
3. **判可外移性**：该段是「案例细节」还是「核心规则」？
   - 案例细节（实测数据、命令选型、故障排查步骤）→ 可外移
   - 核心规则（判据、禁令、执行顺序）→ 留 SKILL.md
4. **提取**：把细节段写入 `references/<topic>.md`，加 header 说明来源与触发时机
5. **留指针**：SKILL.md 留 5-8 条核心规则 + 一行 `→ references/<topic>.md`
6. **验证零丢失**：关键词 grep 确认内容在 ref 里
7. **跑体检**：`skill_repo_doctor.py --root ~/.hermes/skills` 确认无断链
8. **接受新 ref**：`--update-stamp` 登记新判据文件
9. **备份**：改前 `cp` 到 `~/.hermes/private/backups/`

## 实测数据（2026-10-10）

| 技能 | 前 | 后 | 省 | 外移内容 |
|---|---|---|---|---|
| measurement-integrity | 104.3 KB | 80.4 KB | 23.9 KB | 22b 段（判据型代码设计） |
| skill-library-curation | 85.1 KB | 72.1 KB | 13.0 KB | 铁律 30（静态检查器设计） |
| hermes-memory-ops | 70.7 KB | 55.5 KB | 15.2 KB | §8 细节（holographic 层操作） |

## 坑

- **字节 vs 字符**：`len(text)/1024` 算的是字符数，中文 UTF-8 是 3 字节/字符。10.4K 字符 = 25.1K 字节。用 `stat -c%s` 或 `len(text.encode('utf-8'))`。
- **已有 ref 覆盖**：外移前先读已有 ref，避免重复。`hermes-memory-ops` 的 §8 细节追加到已有 `holographic-store.md`，不新建文件。
- **指针与文件同次改动**：写指针和写文件必须在同一次改动里（铁律 32）。
- **新 ref 需登记**：`skill_repo_doctor.py` 的判据指纹会报「新增判据文件」，跑 `--update-stamp` 接受。

## 附带：`.usage.json` 幽灵记录清理

`.usage.json` 会积累已删除技能的条目（幽灵记录）。清理流程：

1. **备份**：`cp .usage.json ~/.hermes/private/backups/usage.json.bak-<ts>`
2. **提取有用信息**：有 `use_count > 0` 的幽灵条目存档到 vault（防日后追溯）
3. **清理**：只保留磁盘上存在的技能条目
4. **验证**：JSON 合法 + 技能载入仍正常记录 + 体检不报错

实测：152 KB → 36 KB（342 条 → 80 条，删 262 条幽灵）。
