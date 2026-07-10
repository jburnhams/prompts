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

## Tool surface

- **Shell**: `execute_command`, runs in the user's actual VS Code
  terminal — explicitly notes commands run in "a new terminal instance"
  each time and that interactive/long-running/background commands are
  supported with status updates, unlike Cline's more generic framing.
- **Search**: regex search + "view source code definitions" (per
  `getCapabilitiesSection`) — same lightweight symbol-listing capability
  as Cline's `list_code_definition_names`, consistent with the shared
  Cline lineage. `system.ts` also instantiates a `CodeIndexManager`
  (semantic code indexing service), though it's not obviously surfaced as
  prompt text in the files captured here — worth revisiting if the
  relevant section file is added later.
- **Code execution**: none beyond the shell.
- **Browser/web**: **no browser tool** in what's captured here — a real
  divergence from Cline (its fork parent), which has a full
  screenshot-driven Puppeteer `browser_action` tool (see
  [`../cline/README.md`](../cline)).
- **Multimodal**: not addressed (consistent with dropping the browser
  tool).
- **Sandbox/isolation**: none described — runs directly in the user's VS
  Code environment.
- **Extensibility**: MCP support (conditionally included, same pattern as
  Cline), plus its own **mode system** — different modes can expose
  different *tool groups*, so the available tool surface itself, not just
  the persona, changes per mode (see `coding-agent-approaches.md` §13).
  Also imports a `SkillsManager` and a pluggable `DiffStrategy` for the
  edit-format layer.

## Sub-agents

**No sub-agent/delegation tool of any kind appears in the files captured
here** — no `new_task`-as-delegate, no `Task`-equivalent, nothing
matching Claude Code's, Gemini CLI's, or Copilot Chat's spawn-and-report
pattern. This is a second real divergence from Cline (alongside the
missing browser tool noted in "Tool surface" above): Roo Code's **mode
system** is the closest thing it has to task-splitting, but modes change
*what the single active agent is allowed to do* (which tool group is
exposed, what persona framing applies), not *how many agents are
running* — there's no fan-out, no separate context window for a
delegated task, and no summarized-report-back step. If Roo Code added
genuine sub-agent delegation after this snapshot (`main` branch,
2026-07-10, on an archived/read-only repo — see the note above), it
isn't reflected in these files.
