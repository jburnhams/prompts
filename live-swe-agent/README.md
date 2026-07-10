# Live-SWE-agent

- **Type**: Coding agent (SWE-bench Verified agent)
- **License**: MIT
- **Source**: https://github.com/OpenAutoCoder/live-swe-agent
- **Retrieved from**: `main` branch,
  `config/livesweagent.yaml` (2026-07-10)

Builds on [`../mini-swe-agent/`](../mini-swe-agent) "with very minimal
modifications," per its own README — but those modifications turn out to
be a genuinely distinct scaffolding idea, not a gimmick: instead of
giving the agent a fixed, pre-built toolset, **the agent is told to write
its own Python tools on the fly**, mid-task, whenever it decides one
would help. "Live" refers to this — the agent's capabilities expand while
it's working, rather than being fixed at session start.

## What's actually different from mini-swe-agent

Diffing `config/livesweagent.yaml` against `../mini-swe-agent/config/mini.yaml`:

- **No file-editing tool at all** — bash is the only tool. All file
  edits, including creating whole new tool scripts, happen via bash
  heredocs (`cat <<'EOF' > file.py`) or `sed`. Every other agent in this
  collection has at least one dedicated edit tool; this one deliberately
  doesn't.
- **A whole new "Creating your own tools" section**, absent from
  mini-swe-agent entirely: instructs the model to write custom
  single-purpose Python scripts specific to the current task (not
  general-purpose utilities) whenever plain bash commands aren't a good
  fit — "at least create a simple edit tool that can help you effectively
  edit arbitrary files instead of using bash commands" is the one
  concrete suggestion given, with a worked example of writing and then
  invoking such a tool.
- **The observation template nudges tool-creation reflection after every
  single action**: "Reflect on the previous trajectories and decide if
  there are any tools you can create to help you with the current task.
  Note that just because you can use basic bash commands doesn't mean you
  should not create any tools that can still be helpful." — mini-swe-agent
  has no equivalent nudge.
- **Text-parsed action blocks, not native tool-calling** — the system
  prompt requires "exactly ONE bash code block" in triple backticks per
  response, parsed out of the text (the older SWE-agent-style convention),
  whereas `mini.yaml`'s `format_error_template` references
  `finish_reason`/`has_tool_calls`, indicating it uses the API's native
  tool-calling mechanism instead. A real scaffolding divergence between
  two configs from adjacent projects, not just a wording difference.
- **Explicit macOS `sed -i ''` handling** templated by OS
  (`{%- if system == "Darwin" -%}`) — a small but concrete portability
  detail mini-swe-agent's configs don't carry.
- **Operational limits set directly in config**: `cost_limit: 3.` (a
  dollar-cost budget per task), `step_limit: 0.` (unlimited), and
  `mode: confirm`.

## Files

- `config/livesweagent.yaml` — the full agent config: system prompt,
  instance/task template, action-observation template (including the
  tool-creation reflection nudge), and format-error recovery template.
