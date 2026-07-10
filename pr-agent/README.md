# PR-Agent (Qodo Merge)

- **Type**: Code review agent
- **License**: Apache-2.0
- **Source**: https://github.com/qodo-ai/pr-agent
- **Retrieved from**: `main` branch, `pr_agent/settings/` (2026-07-10)

Qodo's (formerly CodiumAI's) open-source PR review tool. Prompts are TOML
files with Jinja2-style templating, each pairing a `system` and `user`
prompt for a specific PR command.

## Files

- `pr_reviewer_prompts.toml` — the `/review` command: finds bugs, security
  issues, and suggests improvements on a PR diff.
- `pr_description_prompts.toml` — the `/describe` command: auto-generates a
  PR title/description/labels from the diff.
- `pr_questions_prompts.toml` — the `/ask` command: answers free-form
  questions about a PR.
- `pr_add_docs.toml` — the `/add_docs` command: generates docstrings for
  code in the PR.
- `code_suggestions/` — the `/improve` command: proposes concrete code
  fixes (see that folder's README) — added after initially being missed.

## Scaffolding (beyond the prompt text)

The `.toml` files themselves reveal a lot of this, since they're Jinja2
templates with the variable names left in place:

- **Custom diff format, not a raw unified diff**: PR-Agent reformats each
  changed file into paired `__new hunk__` / `__old hunk__` sections, with
  line numbers injected into the *new* hunk only (so the model can cite
  line numbers in suggestions) and `+`/`-`/` ` prefixes preserved. The
  system prompt spells the format out in full with a worked example before
  any real diff is shown — see `pr_reviewer_prompts.toml`.
- **External context beyond the diff**: linked issue-tracker tickets
  (title, labels, description, requirements — Jira/Linear-shaped), the PR
  title/branch/description, today's date, an optional
  `repo_context` block, and an optional `skills_context` block for
  injecting org-specific review standards — all templated into the user
  message alongside the diff.
- **Explicit context-window management**: `num_pr_files` and
  `num_max_findings` variables suggest the diff/findings are capped rather
  than assumed to always fit; large PRs are likely chunked or truncated
  before reaching the model (not fully visible from the prompt files
  alone — would need the Python source to confirm exactly how).
- **Output isn't freeform**: the response schema is constrained (the
  reviewer prompt goes on to define a structured findings format the model
  must follow, consumed programmatically by PR-Agent to post as PR
  comments/labels rather than left as a chat reply).

### Existing comments, new comments, proposed changes

- **Existing PR comments/discussion are not fed back into `/review`'s
  prompt.** Neither `pr_reviewer_prompts.toml` nor
  `code_suggestions/pr_code_suggestions_prompts.toml` reference prior
  review threads, other reviewers' comments, or "has this already been
  raised" — each run is a fresh read of the diff plus PR
  title/description/tickets. (There is a separate `pr_line_questions_prompts.toml`
  for answering follow-up questions on a specific line, not fetched here,
  which is the closest thing to "responding to a comment.")
- **New comments**: `/review`'s output is one structured summary object
  (`PRReview` — title-level fields like `score`, `security_concerns`, plus
  a capped list of `key_issues_to_review` with file/line links) rather than
  N separate inline comments — it reads as a single review summary, not a
  GitHub-native "N comments on M lines" review. `key_issues_to_review` has
  **no proposed fix** — it's issue-only (location + description + why it
  matters), by design (see `code_suggestions/`, which is the fix-proposing
  half of the tool, kept as a separate command with a separate prompt and
  its own self-verification pass).
- **Proposed changes**: see `code_suggestions/README.md` — structured
  `existing_code`/`improved_code` snippet pairs, self-scored 0-10 by a
  second reflect prompt before being surfaced, rendered as GitHub-native
  suggested-change blocks.
