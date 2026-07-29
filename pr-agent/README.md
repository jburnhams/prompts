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

## Memory, learnings, and retrospectives

See [`agent-memory-learning.md`](../agent-memory-learning.md) for the
cross-source comparison this feeds into. PR-Agent is the open-source
half of a product whose learning loop is closed-source — and the split
is unusually legible, because the OSS repo ships the *entire
configuration and injection surface* of the feature with the generation
side removed.

- **Two best-practices channels, one injection point.** A live clone of
  `qodo-ai/pr-agent` (`main`) shows `configuration.toml` carrying both
  `[best_practices]` (human-authored: `content`, `organization_name`,
  `max_lines_allowed = 800`, `enable_global_best_practices`) and
  `[auto_best_practices]` (machine-generated:
  `enable_auto_best_practices` — "public - general flag to disable all
  auto best practices usage", `utilize_auto_best_practices` — "disable
  usage of auto best practices in the 'improve' tool",
  `extra_instructions` for the generation prompt, `content`, and
  `max_patterns = 5`). In `pr_agent/tools/pr_code_suggestions.py` the
  corresponding prompt variable is present and hardcoded empty:
  `"relevant_best_practices": ""`. The hook is open; the thing that
  fills it is not.
- **What fills it, per Qodo's documentation**: accepted suggestions are
  tracked over time, and roughly **once a month** an LLM flow mines them
  for recurring patterns and writes a `.pr_agent_auto_best_practices`
  wiki file — "practices that your team implicitly approves through
  repeated adoption" — which the `improve` tool then applies as an
  additional analysis layer, tagging anything derived from it with a
  **"Learned best practice"** label. A feedback loop trained on *what
  the team merged*, not on what the bot thought of itself.
- **Contrast with the in-run self-critique already documented here**:
  `code_suggestions/pr_code_suggestions_reflect_prompts.toml` is a
  second LLM pass that scores and filters freshly-generated suggestions
  within the same run (see
  [`agent-self-verification.md`](../agent-self-verification.md)).
  Reflection improves *this* PR's output; auto best practices change the
  *next* PR's priors. Same product, two different loops, easy to
  conflate.
- **A newer, adjacent mechanism in the same repo**: `[agent_skills]`
  discovers `*/SKILL.md` files from configured `paths` and injects a
  combined `skills_context` block (budgeted at `max_skills_tokens =
  8000`) into the reviewer, description, and suggestions prompts — the
  `SKILL.md` convention arriving in a PR-review tool, and a third
  channel of durable, human-curated knowledge alongside the two
  best-practices ones.
