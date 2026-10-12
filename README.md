# Hermes Agent Skills — 精选方法论库

> 从生产环境提炼的 AI Agent 工作方法论。不依赖特定平台，任何 AI 编码助手都能用。

## 核心理念

**生产者不自审** — 写代码的不审代码，审代码的不写代码。
**验证闭环** — 每个结论都要有实测证据，不靠记忆和印象。
**根因修复** — 修 bug 修根因，不修症状。

## 15 个精选技能

### 决策与规划

| 技能 | 功能 | 搜索词 |
|------|------|--------|
| `decision-loop` | 九步决策循环：查真相源→出任务书→派活→验收 | 决策循环, 任务分解, 工作流规划 |
| `competitive-product-analysis` | 竞品对比+模式提取+选型建议 | 竞品分析, 产品调研, 选型 |
| `deep-reading-long-documents` | 长文档精读方法论，必抓全文 | 长文阅读, 文档分析, 知识提取 |
| `structured-input-collection` | 问卷/画像/清单核对，条目超 3 个出文件 | 信息采集, 结构化数据, 问卷设计 |

### 执行与调试

| 技能 | 功能 | 搜索词 |
|------|------|--------|
| `execution-discipline` | 查证→执行→验证三段式，动手前必走 | 执行纪律, 任务验证, 部署检查 |
| `systematic-debugging` | 故障已复现→定位根因→修复→验证 | 调试方法, 故障定位, 根因分析 |
| `measurement-integrity` | 防假阳性：先验读数通道再下结论 | 测量误差, 假阳性, 数据验证 |
| `doubt-driven-development` | 对抗式审稿人：只传产物不传结论 | 代码审查, 对抗验证, 独立审核 |

### 安全与治理

| 技能 | 功能 | 搜索词 |
|------|------|--------|
| `private-data-egress-guard` | 私料出网守卫（身份证/病史/收入） | 数据安全, 隐私保护, 合规检查 |
| `skill-security` | 技能安全审查（prompt 注入/数据外传） | 技能安全, prompt 注入, 插件审计 |
| `safe-file-organization` | 防误删：rm 改 trash，整理磁盘 | 文件管理, 防误删, 磁盘清理 |
| `skill-library-curation` | 技能库治理：准入/合并/审计/重建 INDEX | 技能管理, 库治理, 技能审计 |

### 多模型与协作

| 技能 | 功能 | 搜索词 |
|------|------|--------|
| `multi-model-review` | 多模型交叉审核+独立审稿人 | 多模型, 交叉验证, 独立审核 |
| `coding-delegation` | 派活纪律：生产者不手写+实测验收 | 代码委派, 任务分配, 验收流程 |

### 发布与工具

| 技能 | 功能 | 搜索词 |
|------|------|--------|
| `skill-publish` | 脱敏+推送+独立验证，私有库转公开 | 技能发布, 脱敏, 开源准备 |

## 使用方法

每个技能是一个 `SKILL.md` 文件，放在你的 AI 助手的 skills 目录下即可。

```bash
# 克隆整个库
git clone https://github.com/asloyerkent-source/hermes-skills-public.git

# 或者只复制你需要的技能
cp -r hermes-skills-public/flows/decision-loop ~/.hermes/skills/flows/
```

## 许可证

MIT
