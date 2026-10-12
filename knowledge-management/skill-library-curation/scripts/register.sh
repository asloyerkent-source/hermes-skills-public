#!/bin/bash
# Skill Registry - 自动扫描所有 SKILL.md 并生成 INDEX.md
# 用法: bash register.sh
# 输出: skills/INDEX.md
#
# 注意: 本脚本位于 skills/<category>/<skill>/scripts/ 下（4 级）,
# 因此 SKILLS_DIR 需要向上三级才能回到 skills/ 根目录。
# ⚠️ 2026-09-26: 随「技能管理簇」合并从 flows/skill-catalog/ 搬到
#    knowledge-management/skill-library-curation/scripts/，层级从 2 级变 4 级，
#    `../..` 会算成 skills/knowledge-management/（已实测生成错位置的 INDEX.md 并已删除）。

SKILLS_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
INDEX_FILE="$SKILLS_DIR/INDEX.md"
WORKSPACE_DIR="$(cd "$SKILLS_DIR/.." && pwd)"
# 用脚本自身真实路径算出可复制的调用命令（本脚本可能位于 skills/<category>/ 下，
# 不要硬编码目录层级，否则重排后文档里的路径就失效了）
SELF_REL=$(realpath --relative-to="$WORKSPACE_DIR" "$(realpath "$0")" 2>/dev/null)
[ -z "$SELF_REL" ] && SELF_REL="$(realpath "$0")"

echo "🔍 扫描 skills 目录..."
echo "   目录: $SKILLS_DIR"
echo "   输出: $INDEX_FILE"
echo ""

# 临时文件
TMPFILE=$(mktemp)
CATFILE=$(mktemp)
trap "rm -f $TMPFILE $CATFILE" EXIT

# 收集所有 SKILL.md 信息（排除隐藏的归档/备份/缓存目录）
declare -A skills
while IFS= read -r -d '' sk_file; do
    # 直接用前缀裁剪，不用 realpath：技能目录可能是符号链接（如 flows/json-canvas ->
    # ~/.agents/skills/json-canvas），realpath 会把路径解析到 skills/ 之外，
    # 生成出无法使用的索引路径。
    rel_path="${sk_file#"$SKILLS_DIR/"}"
    # tr -d '\r': 部分 SKILL.md 用 CRLF 行尾，否则 name 会带 ^M 导致按名查找失败
    name=$(grep -oP 'name:\s*\K.*' "$sk_file" 2>/dev/null | head -1 | tr -d '\r' | sed 's/^["'\'']//;s/["'\'']$//' | xargs)
    # description 可能是三种形态：单行、带引号单行、或 YAML 块标量（| / > / |- / >-）。
    # 块标量时后续缩进行才是正文，且必须拼成一行——否则索引里只剩一个 "|" 或 ">"，
    # 表现为「这个技能没有功能说明」（实测china-briefing / hermes-dojo 两个中招）。
    desc=$(awk '
      /^description:/ {
        sub(/^description:[[:space:]]*/, "")
        if ($0 ~ /^[|>][-+]?[[:space:]]*$/) { block = 1; next }
        print; exit
      }
      block {
        if ($0 ~ /^[[:space:]]*$/) next
        if ($0 ~ /^[[:space:]]+/) { gsub(/^[[:space:]]+/, ""); printf "%s ", $0; next }
        exit
      }
    ' "$sk_file" 2>/dev/null | tr -d '\r' | sed 's/^"//; s/"$//' | sed 's/[[:space:]]*$//')
    [ -z "$name" ] && name=$(basename "$(dirname "$sk_file")")
    # 注意: 本环境的 cut -c 按字节截断, 会把多字节汉字/emoji 切成非法 UTF-8。
    # 一律用 bash 子串展开（字符级）替代 cut。
    # 竖线会在 Markdown 表格里断列，换成全角。
    desc="${desc//|/｜}"
    desc="${desc:0:80}"

    if [ -n "$name" ]; then
        echo "$rel_path|$name|$desc" >> "$TMPFILE"
    fi
done < <(find -L "$SKILLS_DIR" -name "SKILL.md" -type f \
            -not -path "$SKILLS_DIR/.archive/*" \
            -not -path "$SKILLS_DIR/.curator_backups/*" \
            -not -path "$SKILLS_DIR/.hub/*" \
            -not -path "$SKILLS_DIR/.locks/*" \
            -print0 | sort -z)

# 统计
TOTAL=$(wc -l < "$TMPFILE")
echo "   找到 $TOTAL 个 skill"
echo ""

# 分类逻辑（路径 + 描述 双重匹配）
categorize() {
    local path="$1"
    local desc="$2"
    local combined="$path $desc"

    # 1. 按目录结构优先
    case "$path" in
        scm-skill/*) echo "SCM 采购体系"; return ;;
        skynet-monitor/ai/*) echo "天网-AI 监控"; return ;;
        skynet-monitor/procurement/*) echo "天网-供应链监控"; return ;;
        skynet-monitor/weekly/*) echo "天网-周报"; return ;;
        skynet-monitor/common/*) echo "天网-通用"; return ;;
        skynet-monitor/*) echo "天网-其他"; return ;;
    esac

    # 2. 按描述关键词匹配
    case "$combined" in
        *内容创作*|*baoyu-*|*article*|*illustrator*|*comic*|*infographic*|*slide*|*xhs*|*cover*|*format-markdown*) echo "内容创作"; return ;;
        *视频*|*video*|*avatar*|*lipsync*|*talking*|*remotion*|*veo*|*seedance*) echo "媒体生成"; return ;;
        *图片*|*image*|*photo*|*compress*) echo "媒体生成"; return ;;
        *采购*|*supplier*|*寻源*|*p2p*|*替代料*|*降本*|*成本*|*质量*|*1688*|*sourcing*) echo "SCM 采购体系"; return ;;
        *github*|*coding-agent*|*browser*|*playwright*|*mcp*|*smart-explore*|*web-artifacts*|*web-design*) echo "开发工具"; return ;;
        *claude*|*claude-*) echo "Claude 生态"; return ;;
        *memory*|*mem-*|*diary*|*todo*|*shopping*|*daily*) echo "效率工具"; return ;;
        *搜索*|*search*|*extract*|*crawl*|*research*|*target*|*summarize*|*tavily*|*研究*) echo "研究搜索"; return ;;
        *飞书*|*feishu*|*公众号*|*wechat*|*微信*|*发布*) echo "内容发布"; return ;;
        *监控*|*monitor*|*weather*|*healthcheck*|*updater*|*cron*) echo "系统运维"; return ;;
        *英语*|*english*|*humanizer*|*scene-english*) echo "语言工具"; return ;;
        *AI*monitor*|*giants*|*资本*|*政策*|*人才*|*社会*|*Karpathy*|*博客*|*digest*) echo "行业监控"; return ;;
        *plan*|*do*|*make-plan*) echo "项目管理"; return ;;
        *agent*|*council*|*proactive*|*self-improving*) echo "AI Agent"; return ;;
        *专家*|*expert*) echo "专家系统"; return ;;
        *chip*|*半导体*|*半导*) echo "供应链"; return ;;
        *d3*|*visualization*) echo "可视化"; return ;;
        *skill*|*registry*|*index*|*vetter*|*creator*|*usage*) echo "Skill 管理"; return ;;
    esac

    # 3. 兜底
    echo "其他"
}

# 预计算分类并按分类名排序：必须先排序再输出，否则同一分类会被
# 路径顺序切碎，导致表头重复输出、续行丢失首尾管道符。
while IFS='|' read -r path name desc; do
    cat=$(categorize "$path" "$desc")
    printf '%s|%s|%s|%s\n' "$cat" "$path" "$name" "$desc" >> "$CATFILE"
done < "$TMPFILE"
LC_ALL=C sort -t'|' -k1,1 "$CATFILE" -o "$CATFILE"

# 生成 INDEX.md
{
    echo "# Skills Index"
    echo ""
    echo "> 自动生成，勿手动编辑。运行 \`bash $SELF_REL\` 更新。"
    echo "> 生成时间: $(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M:%S %Z')"
    echo "> Skill 总数: $TOTAL"
    echo ""

    # 按分类分组
    current_cat=""
    while IFS='|' read -r cat path name desc; do
        if [ "$cat" != "$current_cat" ]; then
            echo "## $cat"
            echo ""
            echo "| Skill | 路径 | 触发场景 |"
            echo "|-------|------|----------|"
            current_cat="$cat"
        fi
        # 截断描述（bash 子串 = 字符级，避免切断多字节字符）
        short_desc="${desc:0:60}"
        echo "| $name | $path | $short_desc |"
    done < "$CATFILE"

    echo ""
    echo "---"
    echo ""
    echo "## 索引使用说明"
    echo ""
    echo "1. AI 启动时读取此文件，获得所有可用 skill 的路径和触发场景"
    echo "2. 路径为相对于 \`skills/\` 的路径，完整路径需拼上 \`\$WORKSPACE/skills/\`"
    echo "3. 新增/删除 skill 后，运行 \`bash $SELF_REL\` 更新"
    echo "4. Git hooks 会在 commit/pull 时自动触发更新"
} > "$INDEX_FILE"

echo "✅ 索引已生成: $INDEX_FILE"
echo "   包含 $TOTAL 个 skill，按分类整理"
