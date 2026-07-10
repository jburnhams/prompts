# TuringMind Code Review

- **Publisher**: TuringMind AI
- **License**: MIT
- **Source**: https://github.com/turingmindai/turingmind-code-review
- **Retrieved from**: `main` branch, `plugins/turingmind/` (2026-07-10)

Reviews uncommitted local changes, similar in goal to `../agent37/local-review/`
but with a more explicit, documented scaffolding — worth comparing the two.
Two modes: `/turingmind-code-review:review` (quick, 4 agents) and
`/turingmind-code-review:deep-review` (thorough, 6 Sonnet + 3 Haiku agents,
adds architecture/test-coverage analysis).

## Scaffolding (beyond the prompt text)

- **Context construction**: `git status` + `git diff` / `git diff --staged`
  via a Haiku agent (see `commands/review.md` Step 1), which extracts files
  changed, languages (from extensions), line counts, and whether a
  `CLAUDE.md` exists — before any review agent runs. Nothing is reviewed
  outside the diff; each reviewer agent still reads full file context for
  changed files but is instructed to only flag issues in the diff itself.
- **Progressive agent loading**: agents aren't all loaded unconditionally —
  `bugs.md` and `security.md` always load, `compliance.md` loads only if a
  `CLAUDE.md` exists, language-specific agents load only if matching file
  extensions are present (see `agents/index.md` for the routing table).
- **Tools**: `Bash(git diff/status/log/blame/show)` only — read-only, no
  edit access, matching its "pre-commit sanity check" scope.
- **Confidence scoring**: a second pass of Haiku agents scores each finding
  0-100 against an explicit point rubric (in-diff +20, would-cause-failure
  +30, in-CLAUDE.md +20, senior-engineer-would-flag +20, has-ignore-comment
  -50) — see `templates/false-positive-rules.md`.
- **Output format**: a fixed Markdown template (`templates/output-format.md`)
  with severity bands (Critical/Warning/Medium — Medium only in deep review),
  a found/reported/filtered count table, diff-style (`` ```diff ``) suggested
  fixes, and — notably — an always-shown "Filtered Issues" section explaining
  *what was excluded and why*, explicitly to build user trust rather than
  just suppressing noise silently.

## Files

- `commands/review.md` / `commands/deep-review.md` — the two orchestrating
  command prompts.
- `agents/index.md` — routing logic for which agents load when.
- `agents/bugs.md`, `agents/security.md`, `agents/compliance.md`,
  `agents/architecture.md` — general-purpose reviewer agents.
- `agents/language-python.md`, `agents/language-typescript.md` —
  language-specific reviewer agents.
- `templates/output-format.md` — the full output template (see above).
- `templates/false-positive-rules.md` — filtering rules + confidence-scoring
  rubric.
