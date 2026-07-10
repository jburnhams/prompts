# Claude Code Cookbook

- **Publisher**: wasabeef
- **License**: Apache-2.0
- **Source**: https://github.com/wasabeef/claude-code-cookbook
- **Retrieved from**: `main` branch, `plugins/en/` (2026-07-10)

A large (40+ command) grab-bag of Claude Code commands/roles, translated
into multiple languages (`plugins/en`, `plugins/ja`, `plugins/ko`, etc. —
only the English versions are included here). Only the review-relevant
subset is pulled in; the repo also has commands for dependency analysis,
performance tuning, commit messages, refactoring, and more.

## Scaffolding (beyond the prompt text)

This one looks noticeably different from the other skills in this
collection: rather than an orchestration script that runs `git diff` itself
and pipes it through fixed pipeline stages, `pr-review.md` is written as a
**set of example shell-command-then-natural-language-instruction pairs**
(e.g. `gh pr diff 123` then `"Focus on reviewing security risks..."`) —
context-gathering is left to whichever command the user/model chooses to
run (`gh pr view --comments`, `gh pr diff`, `grep`, `find ... -exec wc -l`,
etc.) rather than being a fixed, validated step. It's closer to a reference
card the model follows loosely than a strict state machine like
`../bmad-code-review/`.
- **Comment taxonomy**: findings are labeled with a
  Conventional-Comments-style prefix (`critical.must`, `high.imo`,
  `medium.imo`, `low.nits`, `info.q`) baked directly into the output,
  rather than a numeric confidence score.
- **`smart-review.md`** does its own lightweight context-detection layer:
  before reviewing, it pattern-matches changed file paths/extensions
  against a routing table to auto-suggest which specialist role
  (`security`, `frontend`, `performance`, `qa`, etc. — see
  `agents/roles/`) should run the review.
- **Output delivery**: unlike the Anthropic/TuringMind/BMAD skills, this one
  doesn't specify a fixed presentation template — comment templates are
  given as *examples* (e.g. the security-issue template), not a strict
  schema, and there's no explicit false-positive filtering pass.

### Existing comments, new comments, proposed changes

This is the only source in the collection where "existing comments" is the
entire point of one of its two commands, rather than a side concern of one:

- **`pr-review.md` produces new comments**, using its own `critical.must` /
  `high.imo` / `medium.imo` / `low.nits` / `info.q` taxonomy (a labeling
  scheme borrowed from the wider "Conventional Comments" convention). Each
  comment template pairs a priority label with a proposed fix as a plain
  code example (not a diff, not a strict before/after schema) and a
  rationale. No mention of checking for or avoiding duplicate/prior
  comments — nothing here prevents re-raising a point another reviewer (or
  a previous run) already made.
- **`pr-fix.md` consumes existing comments**: `gh pr view --comments`
  pulls the full review thread, which then gets classified using the
  *same* must/imo/nits/q taxonomy (so a `pr-review.md`-authored comment and
  a human's comment sort into the same buckets), phased into a fix order
  (Critical → High → Medium → Low), and — uniquely in this collection —
  the workflow ends with **reply templates** for responding back to the
  reviewer on GitHub (a fix-completion report format and a
  technical-decision-explanation format), not just a private fix log.
- **Proposed changes** across both commands are illustrative code
  snippets/examples in the prompt text (e.g. "use bcrypt instead of
  plaintext"), not a machine-checkable format like PR-Agent's
  `existing_code`/`improved_code` pair or TuringMind's fenced `diff` block.

## Files

- `commands/pr-review.md` — the main systematic PR review command
  (comment taxonomy, four review perspectives: correctness, security,
  performance, architecture; comment templates).
- `commands/smart-review.md` — auto-detects which specialist role fits the
  changed files and suggests/runs that review.
- `commands/pr-fix.md` — addresses PR review feedback via a 3-stage error
  analysis approach (companion to `pr-review.md`).
- `agents/roles/reviewer.md` — general code-reviewer role definition
  (readability/maintainability focus).
- `agents/roles/security.md` — security-specialist role definition,
  invoked by `smart-review.md` for security-relevant changes.
