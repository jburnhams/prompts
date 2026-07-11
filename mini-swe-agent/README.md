# mini-swe-agent

- **Type**: Coding agent (SWE-bench Verified agent — "the 100 line AI
  agent that solves GitHub issues," built by the same team as
  `swe-agent/` after they concluded a much smaller scaffold could still
  score competitively)
- **License**: MIT
- **Source**: https://github.com/SWE-agent/mini-swe-agent
- **Retrieved from**: `main` branch,
  `src/minisweagent/config/` (2026-07-10)

Referenced as a "reference baseline" in the arXiv paper *"Inside the
Scaffold: A Source-Code Taxonomy of Coding Agent Architectures"*
([2604.03515](https://arxiv.org/html/2604.03515v1)), which analyzes 13
open-source coding agents by scaffold architecture rather than prompt
content — a useful complementary read to
[`coding-agent-approaches.md`](../coding-agent-approaches.md) in this
repo. Also the base that [`../live-swe-agent/`](../live-swe-agent) forks
"with very minimal modifications" — see that folder's README for the
diff.

## Files

- `config/mini.yaml` — the default interactive-agent config. Genuinely
  minimal: a **one-line** system prompt ("You are a helpful assistant
  that can interact with a computer."), native tool-calling for the
  `bash` tool (confirmed by `format_error_template`'s reference to
  `finish_reason`/`has_tool_calls`, an API-level tool-calling signal, not
  text-parsed action blocks), and the same 6-step reproduce → fix →
  verify → edge-cases → submit workflow lineage seen in
  `../swe-agent/default.yaml` and `../augment-swebench-agent/` — see
  [`agent-self-verification.md`](../agent-self-verification.md) §1 for
  the full step-by-step comparison across all four SWE-bench-lineage
  sources.
- `config/benchmarks/swebench.yaml` — the actual SWE-bench-tuned variant
  used for benchmark runs, meaningfully different from `mini.yaml`:
  wraps the task in a `<pr_description>` tag, adds explicit **modify vs.
  don't-modify boundaries** (regular source files yes, tests/config files
  no), explicitly allows **multiple independent bash tool calls per
  response** ("searching multiple files, reading different parts of the
  codebase" — `mini.yaml` doesn't offer this), and drops the "submit"
  command instructions from the system template (kept only in the
  instance template).

## Tool surface

The floor of this collection: **exactly one tool, `bash`, and nothing
else** — no dedicated edit tool, no search tool, no browser, no
multimodal input, no planning tool. Everything (reading files, editing,
searching, submitting) happens through bash commands the model chooses
to run, using the "Useful command examples" section (heredoc file
creation, `sed -i` editing with a macOS `Darwin` variant, `nl -ba | sed
-n` for viewing numbered line ranges) as the only editing guidance given
— there is no SEARCH/REPLACE or old_string/new_string convention taught
at all, because there's no edit tool to teach it for.
- **Execution model**: **non-persistent** — "Directory or environment
  variable changes are not persistent. Every action is executed in a new
  subshell," worked around by prefixing commands with
  `MY_ENV_VAR=... cd /path && ...`. This is the opposite persistence model
  from Augment SWE-bench Agent's `pexpect`-backed persistent shell.
- **Calling convention**: native API tool-calling, not text-parsed action
  blocks — confirmed by `format_error_template`'s reference to
  `finish_reason`/`has_tool_calls`. `swebench.yaml` additionally permits
  multiple bash tool calls in one response; `mini.yaml` implicitly expects
  one.
- **Termination**: a magic bash command, `echo
  COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`, rather than a dedicated
  "submit"/"complete" tool (contrast Augment SWE-bench Agent's
  `complete_tool.py`).
- **Browser/multimodal/planning**: none.
- **Sandbox/isolation**: not specified in these configs — left to
  whatever harness runs the agent (local subprocess, container, etc.).
- **Extensibility**: none built in — this is the deliberately minimal
  "100 line agent" baseline that `live-swe-agent` forks specifically to
  add a tool-creation capability on top of (see below).
