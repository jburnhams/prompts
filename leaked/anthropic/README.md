# Anthropic (Claude.ai / API default assistant)

- **Type**: General assistant (not coding-specific) · **Vendor**: Anthropic
- **Status**: closed source (leaked) — included for completeness/comparison
  since it's the same lab as this repo owner's usual tooling, not because
  it's a coding agent.
- **Mirror source**: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Anthropic (2026-07-10)

## Files
- `Claude Sonnet 5.txt` / `Claude Sonnet 5 Tools.txt` — current default
  Claude.ai assistant prompt + tool definitions.
- `Claude Fable 5.txt` — prompt for the Fable model variant.
- `Claude Code 2.0.txt` — an older leak labeled as Claude Code (compare
  against `../claude-code/` for a separately-sourced, differently-dated
  extraction).
- `Claude Sonnet 4.6.txt`, `Sonnet 4.5 Prompt.txt` — earlier model-version
  prompts, kept for historical comparison.

See also `../claude-code/` and `../claude-for-chrome/` for other
Anthropic-product leaks kept in separate folders.

## Sub-agents

`Claude Code 2.0.txt` (a separately-dated snapshot from `../claude-code/`)
carries the same `Task` tool mechanics described in detail in
[`../claude-code/README.md`](../claude-code) — typed `subagent_type`
registry, stateless one-shot invocation, orchestrator must summarize the
result for the user, launch concurrently via one message with multiple
tool uses. Two things worth noting that this snapshot adds beyond that
one:

- **Task-tool access is itself task-conditional, not just tool-scoped**:
  the same file's git-commit-creation and PR-creation instruction blocks
  each carry their own explicit override — "NEVER use the TodoWrite or
  Task tools" — scoped only to those specific sub-workflows. The general
  policy elsewhere in the same prompt is "proactively use the Task tool";
  committing/PR-creation is carved out as an exception where delegation
  isn't wanted, presumably because those flows need the orchestrator's
  own direct, auditable command history rather than a summarized report
  back from a sub-agent.
- **Confirms the search-tool cross-reference is standard phrasing, not
  Claude-Code-specific**: `Grep`'s own tool description repeats "Use
  Task tool for open-ended searches requiring multiple rounds" almost
  verbatim across this file and `../claude-code/Prompt.txt` — the
  delegation guidance is duplicated at both the persona-prompt level and
  the individual tool-description level.

The other files in this folder (`Claude Sonnet 5.txt`/`Claude Sonnet 5
Tools.txt`, `Claude Fable 5.txt`, `Claude Sonnet 4.6.txt`, `Sonnet 4.5
Prompt.txt`) are the general-purpose Claude.ai assistant prompt, not the
coding-agent one, and don't carry a Task-tool-equivalent delegation
mechanism in what's captured here.
