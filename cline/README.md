# Cline

- **Type**: Coding agent (VS Code / JetBrains / CLI extension)
- **License**: Apache-2.0
- **Source**: https://github.com/cline/cline
- **Retrieved from tag**: [`v3.20.4`](https://github.com/cline/cline/tree/v3.20.4/src/core/prompts) (2026-07-10)

Cline later restructured its repo into a monorepo (`apps/`, `sdk/`) where the
system prompt is composed differently. `v3.20.4` is the last tag with the
classic, single-file prompt layout, so it's used here for a clean read.

## Files

- `system.ts` — entry point; picks a prompt variant based on model family and
  assembles it with live context (cwd, shell, MCP servers, browser support).
- `model_prompts/claude4.ts` — the full system prompt used for Claude 4 models
  (tool definitions, rules, capabilities, objective).
- `model_prompts/claude4-experimental.ts` — an experimental variant of the
  above.
- `responses.ts` — templates for tool-result / error messages fed back to the
  model mid-conversation (not the system prompt itself, but part of the
  overall prompting strategy).

## Tool surface

- **Shell**: `execute_command` — generic, "tailor your command to the
  user's system," one command per tool call (this version predates native
  parallel tool-calling; see `coding-agent-approaches.md` §4).
- **Search**: `search_files` (regex-based), `list_files`, and
  `list_code_definition_names` — the last one lists source-definition
  symbols (classes/functions) rather than raw text matches, a lightweight
  AST-adjacent capability distinct from plain grep.
- **Code execution**: none beyond the shell.
- **Browser/web**: `browser_action` — a full **vision-based, Puppeteer
  browser control tool**: launch → click/type/scroll by pixel coordinate
  read off a returned screenshot → close. Explicitly exclusive ("only the
  `browser_action` tool can be used" while a browser session is open, no
  interleaving with other tools) and conditionally included via the
  `supportsBrowserUse` parameter passed into `SYSTEM_PROMPT()` — only
  shown to the model if the underlying provider/model actually supports
  image input.
- **Multimodal**: implicit in `browser_action` — every browser action
  except `close` returns a screenshot the model must visually interpret
  to pick click coordinates.
- **Sandbox/isolation**: none described — runs directly on the user's
  machine/VS Code environment.
- **Extensibility**: `use_mcp_tool`/`access_mcp_resource`/
  `load_mcp_documentation` for MCP servers, plus `new_task` for spawning a
  follow-on task and `plan_mode_respond` for its plan/act mode split.
