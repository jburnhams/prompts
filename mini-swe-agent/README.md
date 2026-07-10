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
  `../swe-agent/default.yaml` and `../augment-swebench-agent/`.
- `config/benchmarks/swebench.yaml` — the actual SWE-bench-tuned variant
  used for benchmark runs, meaningfully different from `mini.yaml`:
  wraps the task in a `<pr_description>` tag, adds explicit **modify vs.
  don't-modify boundaries** (regular source files yes, tests/config files
  no), explicitly allows **multiple independent bash tool calls per
  response** ("searching multiple files, reading different parts of the
  codebase" — `mini.yaml` doesn't offer this), and drops the "submit"
  command instructions from the system template (kept only in the
  instance template).
