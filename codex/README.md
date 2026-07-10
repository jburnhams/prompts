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
