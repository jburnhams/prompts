# PR-Agent (Qodo Merge)

- **Type**: Code review agent
- **License**: Apache-2.0
- **Source**: https://github.com/qodo-ai/pr-agent
- **Retrieved from**: `main` branch, `pr_agent/settings/` — first read
  2026-07-10; **re-read 2026-10-17 at `5a50bf1e`**, and every `.toml` here
  was refreshed to that commit. What changed is in "The 2026-10-17
  re-read" below, and it supersedes two claims further down.

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
- `prompt_fragments.toml` — added 2026-10-17. Shared fragments, chiefly
  `diff_hunk_format`: the `__new hunk__`/`__old hunk__` explanation that
  used to be inlined in each tool's prompt moved here on 2026-09-02
  (#2994), and the reviewer prompt now renders `{{ diff_hunk_format }}`.

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

- **Superseded 2026-10-17 — see below: `/review` now receives its own
  earlier findings.** As of 2026-07-10: **existing PR comments/discussion
  were not fed back into `/review`'s prompt.** Neither `pr_reviewer_prompts.toml` nor
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

## The 2026-10-17 re-read: an attention axis, and memory of its own findings

Three months of changes, almost all to `/review`. Two of them move
PR-Agent from "a list of findings" towards "a statement about how much
human attention this PR needs", which is the question
[`agent-design/risk.md`](../agent-design/risk.md) builds on.

**Opt-in assessment fields (2026-08-31, #2391; failure modes 2026-10-09,
#4012).** Four `require_*` flags in `configuration.toml`, each off by
default and each adding one field to the `PRReview` schema:

| Flag | Field | What the prompt asks for |
|---|---|---|
| `require_risk_assessment` | `risk_level: low \| medium \| high` | high only for a clear bug, security concern or major logic risk; medium when nothing is clearly broken but "non-trivial areas … require careful human verification"; low when small, low-impact and nothing important found |
| `require_merge_recommendation` | `merge_recommendation: no_concerns_found \| needs_review \| changes_required` | Renamed on 2026-10-09 (#4010) so the values "describe findings" rather than sound like approvals. When a CI artifact is supplied, any concern in it (including allowed-to-fail jobs, planned destroys, new vulnerabilities) caps the answer at `needs_review` even on a green pipeline (#4031) |
| `require_failure_modes` | up to 3 × `{what, where, trigger, detected_by, covered_in_this_pr}` | "How could this PR break after merge, and what would catch it?" — grounded in visible code; `detected_by` may be `nothing`; `covered_in_this_pr` is true only if a test *visible in the PR* covers the trigger. The schema text says these "guide review and do not decide whether merging is safe" |
| `require_priority_files` | `review_priority_files: [path]` | "the most important files a human reviewer should inspect first", empty when nothing deserves it |

The ticket-compliance field `overall_compliance_level` was renamed
`requires_further_human_verification` — the same move again: from a
grade to a statement of what a person still has to check.

What is notable is what the design does *not* do. All four are model
self-reports on one pass, with no deterministic floor, no path rules and
no escalate-only constraint; `risk_level` is defined almost entirely by
findings ("introduces a clear bug"), so a clean-looking change to a
sensitive area reads `low`. `failure_modes` is the exception and the
best idea here: it asks about **detection**, not just defects, which is a
question about how a mistake would surface after merge.

**Earlier findings fed back to `/review` (2026-10-02, #3750, with
dismissal handling through 2026-10-10).** With `persistent_finding_state`
on, `/review` receives a `previous_findings` JSON block (budget
`max_previous_findings_chars = 8000`) with each finding marked:

- `active` — re-report it if it still holds, **with the same
  `issue_header` and `issue_content`, word for word**, updating only line
  numbers; identical text is how PR-Agent recognises it as the same
  finding.
- `resolved` — a later commit fixed it; re-report only if reintroduced.
- `dismissed` — a reviewer closed the thread without fixing; `reply`
  carries their reason; do not re-raise unless the code makes it worse.
  A thread resolved by **anyone other than PR-Agent** on GitHub, GitLab
  or Azure counts as dismissed (#3925, #4025, #4032).

Earlier findings compete for the same `num_max_findings` slots (default
3) as new ones, and "a finding that restates an earlier one in different
words" is forbidden. Compare `agent-design/review.md` §7, which reaches
the same goals through structured state and a dedup step rather than by
asking the model to reproduce text verbatim.

**Smaller changes.** The reviewer system prompt now states that title,
description, commits, tickets, code and CI artifacts are untrusted
(#3921, #3978), and the CI artifact is wrapped in start/end markers;
`skills_context` moved to the top of the system prompt; linked Linear
issues join Jira for ticket compliance (#4078); inline key issues are
supported on GitLab, Gitea and Azure; a review-coverage footer and
opt-in large-diff chunking report what a budget left out.

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
