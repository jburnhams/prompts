# Codex Review (reference implementation)

- **Publisher**: OpenAI
- **License**: MIT (`openai/openai-cookbook`)
- **Source**: https://github.com/openai/openai-cookbook/blob/main/examples/codex/build_code_review_with_codex_sdk.md
- **Retrieved from**: `main` branch (2026-07-10)

**Important distinction**: OpenAI's actual hosted "Codex Cloud" PR-review
bot (the one that auto-reviews connected GitHub repos, triggered by
`@codex review` or automatically on PR open) is closed-source SaaS — its
real prompt/diff-formatting isn't published. What's here is OpenAI's own
**published reference implementation** for replicating that experience
yourself in CI (GitHub Actions/GitLab/Azure DevOps/Jenkins — only the
GitHub Actions path is kept here), explicitly framed by OpenAI as "if your
code is hosted on-prem, or you don't have GitHub as an SCM." Treat this as
OpenAI's best public approximation, not a confirmed match to the hosted
service's actual internals.

## Scaffolding

- **Context construction**: a genuinely plain unified diff — no custom
  hunk format like PR-Agent, no LEFT/RIGHT split like Gemini's. The
  workflow runs `git diff --unified=5 "$BASE_SHA" "$HEAD_SHA"` (5 lines of
  context) plus a `--stat` summary, and both get appended as raw text
  directly into the prompt file — pre-baked into the request rather than
  fetched on demand via a tool call (contrast Claude Action's tag mode,
  which has Claude run `git diff` itself at review time).
- **Existing comments: not read at all.** No check for prior Codex runs,
  no dedup against earlier comments — every workflow run posts fresh
  inline comments regardless of what's already on the PR. This is the one
  source in the whole collection with zero existing-comment awareness of
  any kind, worth knowing if you adapt this workflow (re-running it on the
  same PR will duplicate comments).
- **AGENTS.md-aware** (per OpenAI's own docs, not fully spelled out in
  this cookbook's workflow YAML): the hosted service applies guidance from
  the closest `AGENTS.md` "Review guidelines" section to each changed
  file. The cookbook's plain-CLI version would pick this up implicitly
  since Codex CLI reads `AGENTS.md` as part of its normal operation, not
  because the review prompt references it explicitly.
- **Output format: OpenAI's native structured-outputs JSON Schema** — the
  strictest, most formally-typed output format anywhere in this
  collection (contrast everyone else's "please format your Markdown like
  this" instructions). Each finding requires `title`, `body`,
  `confidence_score` (0-1), `priority` (integer 0-3, i.e. P0-P3), and
  `code_location.{absolute_file_path, line_range.{start,end}}` —
  `additionalProperties: false` throughout, so the model literally cannot
  return a differently-shaped object. Plus a mandatory top-level
  `overall_correctness` verdict (enum: `"patch is correct"` /
  `"patch is incorrect"`), explanation, and confidence score.
- **Proposed changes: none.** Like PR-Agent's `/review` and
  `anthropic/pr-review-toolkit`, findings are issue-only — the schema has
  no field for a suggested fix or code snippet.
- **Delivery: raw GitHub REST API calls**, not `gh` CLI and not an MCP
  tool — a `curl -X POST` per finding to
  `/repos/{repo}/pulls/{pr}/comments` (using `commit_id`/`path`/`line`/
  `side: "RIGHT"`, plus `start_line`/`start_side` for multi-line ranges),
  and a separate `curl -X POST` to `/repos/{repo}/issues/{pr}/comments`
  for the overall verdict as a normal (non-review) issue comment.
- **Safety note carried over from `openai/codex-action`**: the GitHub
  Actions example explicitly calls out that the action drops sudo so
  Codex can't read its own `OPENAI_API_KEY` during execution — relevant
  since this runs on untrusted PR content in public repos.

## Files

- `review_prompt.md` — the core review prompt (extracted standalone from
  the cookbook doc).
- `codex-output-schema.json` — the structured-output JSON Schema.
- `github-actions-workflow-example.md` — the full annotated GitHub Actions
  workflow: diff construction, schema generation, prompt assembly, running
  `codex-action`, and posting both inline and summary comments via `curl`.
  (Trimmed from the source doc, which also has GitLab/Azure DevOps/Jenkins
  variants of the same thing — not included here since they're the same
  prompt/schema, just different CI YAML.)
