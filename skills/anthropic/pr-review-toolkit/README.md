# pr-review-toolkit

A more elaborate PR-review command than `../code-review/`, invoked as
`/review-pr`. Delegates to 6 specialized subagents rather than one-shot
prompts per concern.

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
