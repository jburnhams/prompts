# code-review

Reviews a GitHub pull request. Launches 4 parallel reviewer agents (2x
CLAUDE.md-compliance Sonnet agents, 2x bug/security-focused Opus agents),
then validates each candidate finding with a dedicated subagent before
posting only validated issues as inline GitHub PR comments.

(Correction: earlier notes here described 5 agents including
git-history/blame and prior-PR-comment reviewers — that was wrong, likely
carried over from an inaccurate summary rather than the actual command
file. Fixed after reading `commands/code-review.md` directly.)

This is the plugin `agent37`'s `local-review` (see `../../agent37/`) says
it's explicitly modeled on — worth comparing the two side by side.

## Scaffolding (beyond the prompt text)

- **Context construction**: no custom diff format — a Sonnet agent is told
  to "view the pull request" via `gh` CLI directly (explicitly *not* web
  fetch) and summarize the changes; reviewer agents work from that plus the
  live PR, not a pre-baked diff blob.
- **Two-stage find-then-validate pipeline**: bug/logic-issue agents (Opus)
  and CLAUDE.md-compliance agents (Sonnet) run in parallel to *find*
  candidate issues, then a **separate** validation pass launches one
  subagent per candidate issue whose only job is to confirm it's real
  (e.g. re-check that a flagged undefined variable is actually undefined,
  or that a cited CLAUDE.md rule is actually scoped to that file and
  actually violated). Unvalidated issues are dropped before anything is
  posted — a stricter two-pass structure than the single confidence-score
  filter used by TuringMind/agent37/BMAD's triage.
- **Tool-mediated delivery, not chat**: findings are posted as real GitHub
  inline PR comments via the
  `mcp__github_inline_comment__create_inline_comment` tool, one comment per
  unique issue — not printed to the terminal (a terminal summary is only a
  fallback for `--comment`-less runs).
- **Fix suggestions are conditional on size**: small, self-contained fixes
  get a GitHub "committable suggestion" block; anything 6+ lines or
  spanning multiple locations gets a description instead — the prompt is
  explicit that a suggestion should never be posted unless committing it
  alone fully fixes the issue.
- **Precise deep-linking spec**: inline comments must link to the exact
  file/line range using the *full* git SHA (not a shell substitution like
  `$(git rev-parse HEAD)`, since the comment is rendered as static
  Markdown), with at least one line of context on each side of the cited
  range — the command prompt gives the exact URL format required for
  GitHub's Markdown preview to render it as a code snippet.

### Existing comments, new comments, proposed changes

- **Existing comments are checked, but only to decide whether to run at
  all**: step 1 checks `gh pr view <PR> --comments` for a comment already
  left *by Claude* — if found, it skips the PR entirely (with an explicit
  carve-out to still review Claude-authored PRs). It does not read human
  reviewers' existing comments to avoid re-raising the same point, or to
  incorporate their feedback into the review.
- **New comments**: real inline PR comments via
  `mcp__github_inline_comment__create_inline_comment`, one per unique
  issue, each required to cite/link its source (e.g. link the CLAUDE.md
  rule quoted). A todo list of planned comments is drafted first as a
  self-check, but never posted.
- **Proposed changes**: conditional on fix size — small, fully-self-contained
  fixes get a GitHub committable suggestion block (only if committing it
  *alone* fully resolves the issue); larger/multi-location fixes get a
  prose description instead, no suggestion block. No structured
  before/after schema like PR-Agent's `existing_code`/`improved_code` —
  it's left to the model's judgment within that one constraint.

## Files
- `commands/code-review.md` — the full command prompt.
- `plugin.json` — plugin metadata.
- `README-orig.md` — the plugin's own README from the source repo (usage,
  config options), kept for reference.
