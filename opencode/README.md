# OpenCode

- **Type**: Coding agent (terminal-based, multi-provider)
- **License**: MIT
- **Source**: https://github.com/anomalyco/opencode (formerly `sst/opencode`;
  the GitHub org was renamed)
- **Retrieved from**: `dev` branch (the repo's default branch),
  `packages/opencode/src/session/` (2026-07-10)

OpenCode selects a different base system prompt per model family/provider
(see `system.ts`'s `provider()` function), then layers on repo-discovered
instructions (`AGENTS.md`/`CLAUDE.md` via `instruction.ts`), skills, MCP
context, and mode-specific reminders (e.g. plan mode).

## Files

- `system.ts` — provider → prompt-variant selection logic, plus environment
  block assembly (model, cwd, platform, date).
- `instruction.ts` — walks the filesystem for `AGENTS.md`/`CLAUDE.md` files
  and folds their contents into the prompt.
- `prompt/default.txt` — fallback system prompt (base "build" agent
  persona/rules/tone, used when no provider-specific variant matches).
- `prompt/anthropic.txt` — variant for Claude models.
- `prompt/gpt.txt` / `prompt/codex.txt` / `prompt/beast.txt` — variants for
  GPT-4/GPT-5/o1/o3/Codex models (`beast.txt` is used for the reasoning
  "o-series" models).
- `prompt/gemini.txt` — variant for Gemini models.
- `prompt/kimi.txt`, `prompt/trinity.txt`, `prompt/meta.txt`,
  `prompt/copilot-gpt-5.txt` — variants for Kimi, Trinity, and other
  provider/model families.
- `prompt/plan.txt`, `prompt/plan-mode.txt`, `prompt/plan-reminder-anthropic.txt`
  — prompts/reminders for the read-only "plan" agent mode.
- `prompt/build-switch.txt` — short reminder injected when switching from
  plan mode back into the "build" (editing) agent.

Not included: `prompt.ts` (~1600 lines) — the session/agentic-loop
orchestrator that wires prompts, tools, and streaming together. It's mostly
implementation code with only a small amount of embedded prompt text
(`MAX_STEPS_PROMPT` etc.), so it's out of scope for this collection.

## Tool surface

- **Shell**: `Bash` — non-trivial commands must be explained to the user
  before running, "especially important when... making changes to the
  user's system."
- **Search**: separate `grep` and `glob` tools (named explicitly in the
  worked example), plus a delegated `Task` tool "to reduce context usage"
  for open-ended search.
- **Code execution**: none beyond `Bash` — no dedicated Python/Node
  execution tool.
- **Browser/web**: `WebFetch`, but scoped narrowly in this prompt to
  self-documentation ("first use the WebFetch tool... from opencode
  docs") — not framed as a general research tool here.
- **Multimodal**: not addressed in `default.txt`.
- **Sandbox/isolation**: not in the prompt text; see
  [`../github-pr-bots/opencode-review/`](../github-pr-bots/opencode-review)
  for the GitHub Action's execution context.
- **Extensibility**: MCP support (`MCP.Service` in `system.ts`) and a
  skills system (`Skill.Service`), both conditionally injected only when
  something is actually configured/available — same "don't pad the prompt
  with unused capability text" instinct as Pi's dynamic tool listing.

## Sub-agents

A `Task` tool is referenced by name repeatedly, but — unlike leaked
Claude Code's `Tools.json` — none of the files captured here include the
tool's own schema/description text, only the persona prompt's
instructions to *use* it: "prefer to use the Task tool in order to
reduce context usage," "proactively use the Task tool with specialized
agents when the task at hand matches the agent's description," and "if
you need to launch multiple agents in parallel, send a single message
with multiple Task tool calls." Functionally this reads as the same
delegate-and-summarize pattern as leaked Claude Code's `Task` (unsurprising
— OpenCode's `anthropic.txt` variant is closely modeled on Claude Code's
own prompt), just without the underlying tool description to confirm
details like statelessness or the `subagent_type` registry.

- **The Task-tool instructions are Claude-lineage-only, not universal
  across OpenCode's provider variants**: they appear in `default.txt`,
  `anthropic.txt`, `trinity.txt`, and `meta.txt`, but are **absent** from
  `gpt.txt`, `codex.txt`, `beast.txt`, `gemini.txt`, `kimi.txt`, and
  `copilot-gpt-5.txt` — none of those other seven per-provider variants
  mention Task-based delegation at all. Sub-agent delegation is one of
  the clearest per-model-family divergences in this repo's whole
  collection: it's present only in the variants descended from Claude
  Code's own prompt conventions, not a capability OpenCode explains
  uniformly regardless of which model is driving.
