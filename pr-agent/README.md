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

Note: the code-suggestions (`/improve`) prompt lives elsewhere in the repo
under a different filename and wasn't tracked down yet — worth adding later.
