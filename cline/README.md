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
