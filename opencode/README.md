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
