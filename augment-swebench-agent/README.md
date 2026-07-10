# Augment SWE-bench Verified Agent

- **Type**: Coding agent (SWE-bench Verified benchmark agent — same category
  as `swe-agent/` and `openhands/` in this collection, not to be confused
  with `leaked/augment-code/`, which is a leaked snapshot of Augment's
  separate commercial IDE product)
- **License**: MIT
- **Source**: https://github.com/augmentcode/augment-swebench-agent
- **Retrieved from**: `main` branch, `prompts/` + `tools/` (2026-07-10)

Augment's (the AI coding-assistant company) open-source baseline agent for
the SWE-bench Verified benchmark, explicitly built with off-the-shelf
models (Claude 3.7 Sonnet as the driver, o1 as an ensembler) rather than
Augment's own models — a "strong open-source baseline" they published
alongside a 65.4% SWE-bench Verified score. Both the instruction prompt and
the file-editing/bash tool descriptions are explicit forks of
[Anthropic's own SWE-bench blog post](https://www.anthropic.com/engineering/swe-bench-sonnet)
reference implementation — worth diffing against `swe-agent/default.yaml`
in this collection, since that config's `instance_template` shares the
same lineage (near-identical steps: reproduce with a script, fix, rerun,
consider edge cases) despite being a different project entirely. All three
— this repo, SWE-agent, and (per public reporting) early Claude Code — 
plausibly trace back to the same Anthropic reference design.

## Files

### `prompts/`
- `system_prompt.py` — the core system prompt: senior-engineer framing,
  "don't break other components," prefer simpler solutions, must call the
  `complete` tool when done.
- `instruction.py` — the per-task instruction template (the fork of
  Anthropic's blog post), including detailed guidance on using a
  `sequential_thinking` tool (5-7 candidate root causes before narrowing
  down, 5-25 total thoughts) and a list of environment gotchas (e.g. a
  note about symlinked file paths inside their Docker sandbox).
- `ensembler_prompt.py` — a distinct concept not seen elsewhere in this
  collection: `build_ensembler_prompt()` builds a prompt that shows an LLM
  (o1) N candidate solution diffs side by side and asks it to pick the
  majority-vote best one, returning the index in an XML tag. Used by
  `majority_vote_ensembler.py` to select among multiple candidate agent
  runs per problem.

### `tools/`
Tool implementations with their API-facing `description` strings — also
directly forked from Anthropic's reference tool descriptions (the
`str_replace` editor and `bash` tool descriptions here are close to
verbatim matches of Anthropic's published computer-use/SWE-bench tool
prompts):
- `str_replace_tool.py` — the `view`/`create`/`str_replace`/`insert`/
  `undo_edit` file-editing tool (`old_str`/`new_str` based, must be unique
  in the file — same family as Claude Code's and Gemini CLI's edit tools;
  see `coding-agent-approaches.md` §5).
- `bash_tool.py` — persistent-state bash tool, with notes about no
  internet access and a preference for backgrounding long-lived commands.
- `sequential_thinking_tool.py` — the structured "thoughts" tool referenced
  by `instruction.py`.
- `complete_tool.py` — trivial by design: "Call this tool when you are
  done with the task, and supply your answer or summary." The task's
  actual termination condition, kept deliberately minimal.
