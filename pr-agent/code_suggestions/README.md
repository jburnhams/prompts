# Code suggestions (`/improve`)

The prompt this collection was previously missing — PR-Agent's code-suggestion
generator, as opposed to `../pr_reviewer_prompts.toml`'s issue-finding
(no-fix-proposed) review.

- `pr_code_suggestions_prompts.toml` — the default prompt. Diff uses the same
  decoupled `__new hunk__`/`__old hunk__` format as the reviewer prompt.
- `pr_code_suggestions_prompts_not_decoupled.toml` — a variant that shows a
  single combined hunk (context + `+`/`-` lines inline) instead of splitting
  old/new — an alternate diff presentation, not a different task.
- `pr_code_suggestions_reflect_prompts.toml` — a **second-pass self-review**
  prompt: takes the suggestions the first prompt generated and scores each
  0-10, validating that `existing_code` actually matches a real `__new
  hunk__` line and that `improved_code` is a faithful application of the
  suggestion — explicitly zeroing out suggestions that misread the diff or
  contradict the PR's actual changes. Low-value suggestion categories
  (add-a-docstring, add-missing-import, etc.) are also capped or zeroed here.

## Proposed-change format

Each suggestion is a structured `(existing_code, improved_code)` snippet
pair (full before/after code, not a unified diff patch) plus a one-line
summary and a label (`security`, `possible bug`, `performance`, etc.) — see
`CodeSuggestion` in `pr_code_suggestions_prompts.toml`. PR-Agent's Python
layer turns this pair into a GitHub-native "suggested change" block. Unlike
`../pr_reviewer_prompts.toml` (which explicitly does *not* propose fixes,
only flags issues), this command's entire output is proposed fixes.
