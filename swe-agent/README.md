# SWE-agent

- **Type**: Coding agent (autonomous GitHub issue resolver, Princeton NLP)
- **License**: MIT
- **Source**: https://github.com/SWE-agent/SWE-agent
- **Retrieved from**: `main` branch, `config/default.yaml` (2026-07-10)

SWE-agent defines its prompts inline in a YAML config rather than in Python
source. `default.yaml` includes the system template, instance (task) template,
and the full custom tool/command definitions the agent can call (bash-like
filesystem and search commands, file editor, submit, etc).

## Files

- `default.yaml` — full agent config: system prompt, instance prompt,
  next-step templates, and tool/command definitions.

## Tool surface

- **Shell**: "the bash tool," referenced generically in the instance
  template (e.g. "execute it with `python <filename.py>` using the bash
  tool"). Interactive-output env vars are explicitly disabled for
  headless operation: `PAGER`/`MANPAGER`/`GIT_PAGER` set to `cat`,
  `PIP_PROGRESS_BAR`/`TQDM_DISABLE` turned off — since there's no human
  watching a live terminal, progress bars and pagers would just pollute
  captured output.
- **Search / editing**: not inlined in `default.yaml` itself — the actual
  tool implementations are pulled in via `bundles` (external path
  references: `tools/registry`, `tools/edit_anthropic`,
  `tools/review_on_submit_m`), not fetched for this collection. The name
  `edit_anthropic` and the file's own header comment ("heavily inspired
  by anthropic's computer use demo") strongly suggest the same
  view/create/str_replace/insert/undo_edit tool family used by
  [`../augment-swebench-agent/`](../augment-swebench-agent).
- **Code execution**: `python <filename.py>` via the bash tool, same as
  everyone else in the benchmark-solver archetype — no dedicated
  execution tool.
- **Self-review**: `review_on_submit_m` — a bundle name implying a
  built-in review pass before submission completes; `registry_variables`
  includes a full `SUBMIT_REVIEW_MESSAGES` prompt block asking the agent
  to "carefully follow the steps below to help review your changes,"
  i.e. SWE-agent bakes in something like a mini self-code-review step
  most other benchmark solvers in this collection don't have as a named,
  separate stage.
- **Browser/web, multimodal**: not addressed.
- **Sandbox/isolation**: not specified in this config (handled by
  SWE-agent's Docker-based runtime outside the prompt).
