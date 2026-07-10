# security-guidance

Unlike the other two folders here, this isn't a slash command — it's a set
of Claude Code hooks that run automatically as you edit/commit, doing
pattern-based + LLM-based security review in the background. Most of the
directory is Python plumbing (state tracking, git utilities, hook wiring);
only the two files below carry actual prompt text.

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
