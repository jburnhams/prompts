# Gemini Code Review

- **Publisher**: Google
- **License**: Apache-2.0
- **Source**: https://github.com/gemini-cli-extensions/code-review (the
  canonical, current source — this is a Gemini CLI *extension*)
- **Retrieved from**: `main` branch (2026-07-10)
- **Wiring example from**: https://github.com/google-github-actions/run-gemini-cli,
  `examples/workflows/pr-review/gemini-review.yml` — shows how the
  extension gets invoked from a GitHub Action (kept in `workflow-example/`).
  Note `run-gemini-cli` also has its own older, slightly different, fully
  inlined copy of this prompt at `.github/commands/gemini-review.toml` —
  the extension repo above supersedes it; use this folder as the
  authoritative version.

Two commands share one persona/rules skill (`code-review-commons`) but
differ in scope and delivery — a similar "shared commons + per-context
wrapper" shape to `../../skills/bmad-code-review/`'s pluggable layers.

## `/pr-code-review` — reviews a GitHub PR (the "bot" use case)

- **Context construction**: no pre-baked diff in the prompt at all — three
  tool calls do it: `pull_request_read.get` (title/body/metadata),
  `pull_request_read.get_files` (changed file list), and
  `pull_request_read.get_diff`, which explicitly returns **line numbers
  for both the before (LEFT) and after (RIGHT) versions of each
  hunk** — comments must cite the correct side's line numbers depending on
  which version they're commenting on.
- **Existing comments**: not read at all — no dedup, no incorporation of
  prior review threads.
- **Tools are locked down**: the underlying GitHub MCP server
  (`ghcr.io/github/github-mcp-server`) is invoked with `includeTools`
  restricted to exactly `add_comment_to_pending_review`,
  `pull_request_read`, `pull_request_review_write` — it structurally
  cannot do anything else on GitHub (can't merge, can't approve, can't
  touch issues), enforced at the tool-registration level rather than by
  prompt instruction alone.
- **New comments — GitHub's native pending-review flow, used correctly**:
  `create_pending_pull_request_review` → one `add_comment_to_pending_review`
  call per finding → a single `submit_pending_pull_request_review` at the
  end. The event type is hard-locked to `"COMMENT"` — the prompt explicitly
  forbids `APPROVE`/`REQUEST_CHANGES` even though the tool supports them.
- **Proposed changes**: a fenced ` ```suggestion ` block (GitHub's native
  suggested-change syntax, directly committable) when there's a concrete
  fix, severity-prefixed (`🔴`/`🟠`/`🟡`/`🟢`); prose-only when there isn't.
  Duplicate issues across locations get one detailed comment plus a
  mention in the summary, not repeated comments.
- **Prompt-injection boundary**: PR title/description/diff content is
  explicitly declared "CONTEXT FOR ANALYSIS ONLY," not to be interpreted
  as instructions — same principle as Claude Action's sanitizer, enforced
  here purely by prompt wording rather than code-level stripping.

## `/code-review` — reviews the current local branch (no PR/GitHub involved)

- **Context construction**: `git diff -U5 --merge-base origin/HEAD` — a
  plain unified diff with 5 lines of context, no custom hunk reformatting.
- **Output**: not posted anywhere — a single structured Markdown document
  returned in-chat, per-file `## File:` sections with `### L<N>: [SEVERITY]`
  entries and inline ` ``` ` diff-style suggested changes. Closest
  comparison in this collection: `../../skills/turingmind/`'s local-review
  output template.

## Files

- `commands/pr-code-review.toml` — the PR-review command prompt (context,
  submission protocol, comment templates).
- `commands/code-review.toml` — the local-branch-review command prompt.
- `skills/code-review-commons/SKILL.md` — shared persona, review priorities
  (correctness > security > efficiency > maintainability > testing...),
  severity rubric (CRITICAL/HIGH/MEDIUM/LOW with concrete examples per
  level), and the "only comment on `+`/`-` lines, never context lines"
  constraint both commands inherit.
- `workflow-example/gemini-review.yml` — a real GitHub Actions workflow
  wiring this up: identity token minting, the GitHub MCP server
  invocation with its restricted tool list (see above), and how PR
  number/repo/extra-instructions get passed in as `$REPOSITORY` /
  `$PULL_REQUEST_NUMBER` / `$ADDITIONAL_CONTEXT`.
