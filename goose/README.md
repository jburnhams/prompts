# Goose

- **Type**: Coding agent (Block's general-purpose, extensible AI agent — CLI
  + desktop)
- **License**: Apache-2.0
- **Source**: https://github.com/block/goose
- **Retrieved from**: `main` branch,
  `crates/goose/src/prompts/` (2026-07-10)

Goose's prompts are Jinja2-style templates (`{% if %}` / `{{ var }}`)
rendered by its Rust core, covering the main system prompt plus a set of
task-specific prompts used for sub-features (planning, recipes, session
naming, compaction, etc). This is the complete contents of the `prompts/`
directory.

## Files

- `system.md` — the main system prompt (persona, extensions/tools framing,
  operating rules).
- `tiny_model_system.md` — a shorter system prompt variant for small/local
  models.
- `subagent_system.md` — system prompt used when Goose spawns a sub-agent to
  handle a delegated task.
- `plan.md` — prompt for "plan mode" (produce a plan before executing).
- `recipe.md` — prompt for generating/following a Goose "recipe" (a
  reusable, shareable YAML task definition — the feature block.com credits
  with scaling Goose internally).
- `compaction.md` — prompt used to summarize/compact long conversation
  history.
- `session_name.md` — prompt for auto-generating a short session title.
- `apps_create.md` / `apps_iterate.md` — prompts for Goose's app-building
  mode (scaffolding vs. iterating on an existing app).

Not included: `permission_judge.md`, which was empty (0 bytes) at the
retrieved commit.

## Tool surface

- **Shell**: not fixed — `{{shell}}` is a template variable filled in at
  runtime (so it adapts to whatever the OS/user actually has: bash, zsh,
  PowerShell, etc.), the only source in this collection whose base prompt
  treats "which shell" as a variable rather than assuming one.
- **Tools generally**: `system.md` names **no built-in tools at all** —
  everything comes from dynamically-loaded **Extensions** ("Extensions
  provide additional tools and context from different data sources and
  applications. You can dynamically enable or disable extensions"), each
  contributing its own tools and, optionally, its own `### Instructions`
  block folded into the prompt. There's also a stated soft limit —
  `extension_tool_limits` triggers a suggestion to disable some
  extensions if the user exceeds a configured extension/tool count,
  because "exceeding recommended limits" degrades "tool selection
  accuracy" — the only source in this collection with an explicit
  too-many-tools warning built into the prompt logic itself.
- **Small/local-model fallback — a genuinely different tool-calling
  convention**: `tiny_model_system.md` abandons structured tool calling
  entirely for a `$`-prefixed plain-text shell convention ("To run a
  shell command, start a new line with $: `$ ls`"), text-parsed rather
  than API-native — directly comparable to mini-swe-agent's and
  Live-SWE-agent's text-block action parsing (see
  [`agent-tool-surfaces.md`](../agent-tool-surfaces.md)), but chosen here
  specifically for *weaker models*, not as a general design philosophy.
- **Code execution**: whatever the active extensions provide — nothing
  fixed in the base prompt.
- **Browser/web, multimodal**: not addressed in the base prompt (would
  come from extensions).
- **Sandbox/isolation**: not specified.
