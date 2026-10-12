#!/bin/bash
# 安装 Git Hooks - pre-commit + post-merge
# 在 skill 目录变更时自动更新 INDEX.md
#
# 注意: 本脚本位于 skills/<category>/skill-catalog/ 下,
# WORKSPACE_DIR 需要向上三级才是 skills/ 的父目录。

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../../../.." && pwd)"  # = ~/.hermes（脚本在 skills/<类>/<技能>/scripts/，向上四级）
SKILLS_DIR="$WORKSPACE_DIR/skills"
REGISTER_SCRIPT="$SCRIPT_DIR/register.sh"
GIT_DIR="$WORKSPACE_DIR/.git"
HOOKS_DIR="$GIT_DIR/hooks"

echo "🔧 安装 Skill Registry Git Hooks..."
echo "   Workspace: $WORKSPACE_DIR"
echo "   Register:  $REGISTER_SCRIPT"
echo "   Git hooks: $HOOKS_DIR"
echo ""

if [ ! -d "$GIT_DIR" ]; then
    echo "⚠️  $WORKSPACE_DIR 不是 git 仓库（无 $GIT_DIR）——hooks 无法安装。"
    echo "    跳过。register.sh 仍可手动运行。"
    exit 0
fi

mkdir -p "$HOOKS_DIR"

# pre-commit hook
cat > "$HOOKS_DIR/pre-commit" << HOOKEOF
#!/bin/bash
# Skill Registry pre-commit hook
# 自动更新 INDEX.md 并加入当前 commit

SKILLS_DIR="$(git rev-parse --show-toplevel)/skills"
REGISTER_SCRIPT="$REGISTER_SCRIPT"
INDEX_FILE="\$SKILLS_DIR/INDEX.md"

if [ -f "\$REGISTER_SCRIPT" ] && git diff --cached --name-only | grep -q "^skills/"; then
    echo "🔄 Skill 目录有变更，更新索引..."
    bash "\$REGISTER_SCRIPT"
    git add "\$INDEX_FILE"
    echo "✅ INDEX.md 已更新并加入 commit"
fi
HOOKEOF
chmod +x "$HOOKS_DIR/pre-commit"
echo "   ✅ pre-commit hook 已安装"

# post-merge hook
cat > "$HOOKS_DIR/post-merge" << HOOKEOF
#!/bin/bash
# Skill Registry post-merge hook
# pull 后自动更新索引

REGISTER_SCRIPT="$REGISTER_SCRIPT"

if [ -f "\$REGISTER_SCRIPT" ]; then
    echo "🔄 Pull 完成，更新 skill 索引..."
    bash "\$REGISTER_SCRIPT"
fi
HOOKEOF
chmod +x "$HOOKS_DIR/post-merge"
echo "   ✅ post-merge hook 已安装"

echo ""
echo "✅ 全部安装完成！"
echo "   - commit 时自动更新索引（如果 skills/ 目录有变更）"
echo "   - pull 时自动更新索引"
