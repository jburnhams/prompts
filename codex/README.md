# Codex CLI

- **Type**: Coding agent (OpenAI's terminal coding agent, Rust)
- **License**: Apache-2.0
- **Source**: https://github.com/openai/codex
- **Retrieved from**: `main` branch, `codex-rs/core/` (2026-07-10)

Codex CLI ships a separate prompt file per model, selected at runtime based
on which model is configured. There's no single "the" Codex system prompt —
these files are the current set for the GPT-5.x/Codex model family.

## Files

- `gpt_5_codex_prompt.md` — prompt for the original GPT-5-Codex model.
- `gpt_5_1_prompt.md` — prompt for GPT-5.1.
- `gpt_5_2_prompt.md` — prompt for GPT-5.2.
- `gpt-5.1-codex-max_prompt.md` — prompt for GPT-5.1-Codex-Max.
- `gpt-5.2-codex_prompt.md` — prompt for GPT-5.2-Codex.
- `prompt_with_apply_patch_instructions.md` — a variant that adds explicit
  instructions for the `apply_patch` file-editing tool format (used for
  models that need it spelled out rather than relying on native tool-calling
  conventions).

Not included: the repo's root `AGENTS.md` — that's contributor/build
instructions for working on the Codex codebase itself, not part of the
agent's system prompt.

## Tool surface

- **Shell**: unnamed generic shell, but with an explicit ripgrep
  preference: "prefer using `rg` or `rg --files`... because `rg` is much
  faster than alternatives like `grep`. (If the `rg` command is not
  found, then use alternatives.)" — the clearest, most explicit
  fast-search-tool endorsement in this collection.
- **Search**: no dedicated search tool named beyond shell + `rg` — file
  discovery and code search both go through the shell.
- **Code execution**: none beyond the shell (scripts run via shell
  invocation, same as any other command).
- **Editing**: `apply_patch` preferred for single-file edits, but
  explicitly *not* mandatory — "it is fine to explore other options...
  Do not use apply_patch for changes that are auto-generated... or when
  scripting is more efficient (such as search and replacing a string
  across a codebase)." A distinct `prompt_with_apply_patch_instructions.md`
  variant exists for models that need the format spelled out rather than
  relying on native tool-calling.
- **Planning**: a "Plan tool," explicitly told to skip it for the
  "easiest 25%" of tasks and never use it for single-step plans — the
  only source in the collection with a quantified threshold for when
  *not* to plan.
- **Browser/web**: not addressed in this prompt.
- **Multimodal**: not addressed.
- **Sandbox/isolation**: not specified here — see
  [`../github-pr-bots/codex-review/`](../github-pr-bots/codex-review) for
  a `sandbox: read-only` example from the Action wiring, and
  `openai/codex-action`'s documented credential-isolation strategy.
