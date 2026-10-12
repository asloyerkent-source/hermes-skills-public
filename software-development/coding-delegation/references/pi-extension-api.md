# Pi 0.87 扩展 API 契约

## 为什么重要
Pi 升级后，用旧 API 写的扩展会导致 **Pi 整体拒绝启动**（不是那个工具不可用，是整个
`pi` 起不来），必须加 `-ne` 才能用。报错形如：

```
Error: Failed to load extension ".../cbmem.ts": ... Tool "X" ... must define
an object parameter schema.  Hint: Start without extensions using "pi -ne".
```

## 1. 运行时只校验 parameters
`dist/core/extensions/loader.js`:
```js
if (typeof tool.parameters != "object" || tool.parameters === null || Array.isArray(tool.parameters))
  throw new Error(`Tool "${tool.name}" ... must define an object parameter schema.`);
```
→ `parameters` 必须是个对象（非 null、非数组）。

## 2. 方法名是 execute，不是 run
`dist/core/tools/tool-definition-wrapper.js`:
```js
execute: (toolCallId, params, signal, onUpdate, ctx) => definition.execute(...)
```
→ **`params` 是第 2 个参数**（第 1 个是 `toolCallId`）。旧扩展若写
`run: (args, ctx) => ...`，即使补上 `parameters` 能启动，**调用时也必然失败**，
因为 `run` 根本不会被调用。这是最容易漏的第二个坑。

## 3. ToolDefinition 形状
`dist/core/extensions/types.d.ts`:
```ts
{
  name: string; label: string; description: string;
  parameters: TSchema;   // TypeBox schema；普通 JSON Schema 对象字面量即可
  execute(toolCallId, params, signal?, onUpdate?, ctx?): Promise<AgentToolResult>
}
```
（`label`/`description` 只是 TS 类型要求，运行时不强校验；但模型要靠 `description` 才知道怎么用。）

## 4. 返回值
`pi-agent-core/dist/types.d.ts`:
```ts
interface AgentToolResult<T> { content: (TextContent|ImageContent)[]; details: T; usage?; terminate?; }
```
`pi-ai/dist/types.d.ts`: `interface TextContent { type: "text"; text: string; }`

最小可用返回：
```js
{ content: [{ type: "text", text: JSON.stringify(result) }], details: result }
```

## 5. 排查口诀
改完扩展后，**必须验证「不带 -ne 能否启动」**：
```bash
export PATH="$HOME/.local/bin:$PATH"
for v in DEEPSEEK_API_KEY KIMI_API_KEY; do
  val=$(grep "^$v=" ~/.pi/agent/.env | cut -d= -f2-); [ -n "$val" ] && export $v="$val"; done
pi --provider deepseek --model deepseek-chat -p "reply with exactly: OK"
```
看到 `OK` 才算扩展没坏。只看报错消失不够——还要真调用一次扩展提供的工具。

## 6. 实例
`codebase-memory-mcp` 生成的 `~/.pi/agent/extensions/cbmem.ts` 曾因此崩溃
（2026-09-26，Pi 0.87.1）。修法：按上述契约重写注册块，15 个工具的完整
`inputSchema` 从 MCP 服务器 `tools/list` 导出后内联进 TS 文件。
**注意：不要用 `codebase-memory-mcp install` 去"重新生成"它**——那个安装器会重写
`~/.hermes/config.yaml`（实测剥离全部注释、改坏 MCP 路径），得不偿失。
