# pr-review-toolkit

A more elaborate PR-review command than `../code-review/`, invoked as
`/review-pr`. Delegates to 6 specialized subagents rather than one-shot
prompts per concern.

## Scaffolding (beyond the prompt text)

- **Context construction**: `git diff --name-only` for scope, plus
  `gh pr view` if a PR already exists — file-type/content detection then
  decides which subagents are even applicable (e.g.
  `type-design-analyzer` only runs if types were added/modified,
  `comment-analyzer` only if comments/docs changed).
- **Sequential vs. parallel is a user choice**, not fixed: the command
  prompt explicitly offers both — sequential for "easier to act on, one
  complete report at a time" vs. parallel for speed — unlike every other
  skill in this collection, which hardcodes parallel subagent launches.
- **`code-simplifier` runs last, after the others pass** — quality/clarity
  cleanup is explicitly sequenced as a final polish step rather than
  running alongside the bug-hunting agents (this repo's own `/code-review`
  vs `/simplify` split embodies the same separation of concerns).
- **Output includes what's good, not just problems**: the aggregated
  summary template has a "Strengths" / "Positive Observations" section
  alongside Critical/Important/Suggestions — the only skill in this
  collection that does.

### Existing comments, new comments, proposed changes

- **Doesn't touch GitHub PR comments at all**, in either direction. Its
  `allowed-tools` are `Bash, Glob, Grep, Read, Task` — no `gh pr comment`,
  no inline-comment MCP tool. Despite being framed as PR review, it neither
  reads existing review discussion nor posts anything back to GitHub —
  output is the aggregated Markdown summary (Critical/Important/
  Suggestions/Strengths), presented in-chat only. Contrast with
  `../code-review/`, which is built specifically to post real inline
  comments.
- **Proposed changes**: each finding in the aggregate template is
  `[agent-name]: Issue description [file:line]` — no fix snippet or diff
  format specified in the orchestrating prompt; individual agents (e.g.
  `code-reviewer.md`) are told to include a "concrete fix suggestion" but
  the format is left to the model, not templated like TuringMind's
  `` ```diff `` blocks or PR-Agent's structured snippet pairs.

## Files
- `commands/review-pr.md` — the orchestrating command prompt (decides which
  subagents to run and how to combine their findings).
- `agents/code-reviewer.md` — general-purpose correctness/bug review.
- `agents/code-simplifier.md` — flags unnecessary complexity/verbosity
  (quality only, not bug-hunting — same split as this repo's own
  `/code-review` vs `/simplify` skills).
- `agents/comment-analyzer.md` — checks that code comments are accurate and
  still match the code they describe.
- `agents/pr-test-analyzer.md` — evaluates whether the PR's tests actually
  cover the change.
- `agents/silent-failure-hunter.md` — looks for swallowed errors/exceptions
  and other failure modes that don't surface visibly.
- `agents/type-design-analyzer.md` — reviews type design (overly loose
  types, missing invariants, etc.).
- `plugin.json` — plugin metadata.
- `README-orig.md` — the plugin's own README from the source repo, kept for
  reference.
