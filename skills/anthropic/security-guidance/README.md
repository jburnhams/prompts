# security-guidance

Unlike the other two folders here, this isn't a slash command — it's a set
of Claude Code hooks that run automatically as you edit/commit, doing
pattern-based + LLM-based security review in the background. Most of the
directory is Python plumbing (state tracking, git utilities, hook wiring);
only the two files below carry actual prompt text.

## Scaffolding (beyond the prompt text)

- **Diff format**: a standard unified diff (not a custom hunk format like
  PR-Agent's), with an explicit note that only `+` lines are new — plus a
  capped list of touched file paths (first 50) and an instruction that the
  model may `Read` any file in the repo for more context, not just what's
  in the diff (via the Agent SDK path, `agentic_review` — it can actually
  explore the codebase rather than being limited to the diff text handed
  to it).
- **Stateful re-review**: `diffstate.py`/`session_state.py` track what was
  already reviewed, so on a second pass the prompt is told which lines
  changed *since the prior review* and instructed to only flag something
  again if it's an incomplete fix or a newly introduced issue — avoids
  re-flagging the same finding every time a file is touched.
- **Two calling paths**: a raw HTTP call to the Anthropic API
  (`_call_claude`) and an Agent-SDK-based `agentic_review` path that can
  use tools (like `Read`) — `llm.py` prefers the user's locally installed
  `claude` CLI over the SDK's bundled one specifically to avoid
  protocol-version skew between them.
- **Two-pass verification**: an initial scan prompt is followed by a
  second "security architect doing a final review" pass (around line 1605
  of `llm.py`) that looks for broader *areas of concern* rather than exact
  bugs, plus a distinct refutation prompt to challenge/confirm findings
  before they're surfaced — conceptually similar to the
  find-then-validate split in `../code-review/`, but done via prompt
  chaining within one hook rather than separate subagents.
- **Delivery**: not a chat reply or PR comment — findings surface as
  inline reminders injected by the hook system as you edit/commit (see
  `hooks/hooks.json` for which Claude Code events trigger this).

## Files
- `hooks/llm.py` — owns all the LLM calls. Contains several full prompt
  templates (e.g. "You are a security expert reviewing {language}...",
  "You are a security architect doing a final review...") used for
  first-pass vulnerability scanning, a second verification/refutation pass,
  and a broader area-of-concern review.
- `hooks/patterns.py` — regex-based pattern definitions paired with short
  reminder-text snippets (e.g. warnings about unsafe pickle/YAML/torch
  deserialization) that get surfaced inline when a pattern matches, without
  needing an LLM call.
- `hooks/hooks.json` — wires the above into Claude Code's hook system
  (which events trigger which handler).
- `plugin.json` — plugin metadata.
- `README-orig.md` — the plugin's own README from the source repo, kept for
  reference.

Not included: `_base.py`, `diffstate.py`, `ensure_agent_sdk.py`,
`extensibility.py`, `gitutil.py`, `review_api.py`, `session_state.py`,
`sg-python.sh` — supporting code with no embedded prompt text.
