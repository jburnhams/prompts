# Roo Code

- **Type**: Coding agent (VS Code extension; fork of Cline)
- **License**: Apache-2.0
- **Source**: https://github.com/RooCodeInc/Roo-Code — **archived/read-only as
  of 2026-05-15** (project shut down)
- **Retrieved from**: `main` branch, `src/core/prompts/` (2026-07-10)

Roo Code (formerly "Roo Cline") diverged from Cline early on and developed
its own prompt structure: a `system.ts` entry point that assembles a system
prompt from many small, single-purpose section files, plus a mode system
(Code/Ask/Debug/Architect/etc.) that swaps in different role definitions.

## Files

- `system.ts` — assembles the full system prompt from the section files
  below, based on the active mode and enabled tools.
- `responses.ts` — templates for tool-result/error messages fed back to the
  model.
- `sections/capabilities.ts` — describes what the agent can do (tools,
  environment_details, MCP).
- `sections/custom-instructions.ts` — folds in user/workspace custom
  instructions, language preferences, and mode-specific rules.
- `sections/markdown-formatting.ts` — output formatting rules (clickable
  file/symbol links).
- `sections/modes.ts` — lists available modes and how to switch between them.
- `sections/objective.ts` — the "how to approach a task" framing.
- `sections/rules.ts` — operational rules and constraints.
- `sections/skills.ts` — skill-system instructions.
- `sections/system-info.ts` — injects OS/shell/cwd environment info.
- `sections/tool-use.ts` / `sections/tool-use-guidelines.ts` — tool-calling
  protocol and guidance on choosing/sequencing tools.
