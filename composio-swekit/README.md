# Composio SWE-Kit

- **Type**: Coding agent framework (SWE issue-resolving + PR review, both
  as multi-agent pipelines) — a framework for scaffolding these agents
  around Composio's tool ecosystem, not a single fixed agent
- **License**: Apache-2.0
- **Publisher source**: https://github.com/ComposioHQ/composio
- **Retrieved from**: the [`swekit` PyPI package](https://pypi.org/project/swekit/), version 0.4.18, `sdist` tarball (2026-07-10) —
  **not from GitHub directly**. SWE-Kit used to live at
  `python/swe/agent` in the main Composio monorepo; that path 404s on
  both `main` and `master` today. Composio's repo has since been
  restructured into a general-purpose "1000+ toolkits" agent platform,
  and the SWE-specific agent scaffolding no longer appears to be part of
  the actively-developed tree. The PyPI package is still published and
  installable, so this is sourced from there instead — treat this as a
  snapshot of a de-emphasized/possibly-unmaintained feature, not
  necessarily current best practice from Composio.

SWE-Kit is a `swekit scaffold` CLI that generates one of these prompt
templates into your own project, wired to your framework of choice
(LangGraph, CrewAI, AutoGen, LlamaIndex, CamelAI). Only two of the five
framework variants are kept here — LangGraph (the richest) and CrewAI (to
show how much the prompt *architecture* itself changes per framework, not
just the wiring around it) — Autogen/LlamaIndex/CamelAI are structurally
similar to one or the other and weren't fetched.

## `swe/langgraph/` — SWE issue-resolving, 3-role handoff

A single LangGraph state machine with three separately-prompted roles that
hand off to each other via **literal keyword responses** rather than a
tool call or structured field:

- `SOFTWARE_ENGINEER_PROMPT` — the orchestrator/decision-maker. Never edits
  code or analyzes it directly; responds with exactly one of `"ANALYZE
  CODE"`, `"EDIT FILE"`, or `"PATCH COMPLETED"` per turn, explicitly
  forbidden from combining actions in one message.
- `CODE_ANALYZER_PROMPT` — read-only by design ("you cannot modify files,
  execute shell commands, or directly access the file system"), reports
  findings back and ends every turn with `"ANALYSIS COMPLETE"` to return
  control.
- `EDITING_AGENT_PROMPT` — the only role with file-editing tools, ends each
  turn with `"EDITING COMPLETED"`.

This is a genuinely different sub-agent pattern from anything else in this
collection's `coding-agent-approaches.md` §10 — not a "Task tool" spun up
for isolated context, but a fixed 3-role team where control passes back and
forth via a shared conversation and a small closed vocabulary of handoff
keywords.

## `swe/crewai/` — SWE issue-resolving, single-agent backstory

The same job (reproduce → understand → fix → verify), but in CrewAI's
`ROLE`/`GOAL`/`BACKSTORY` convention as one agent, not three — the
framework choice changes the entire prompt architecture, not just which
API it's sent through. Numbered "mentor tips" replace the LangGraph
version's role split, covering the same ground (read the repo tree, read
READMEs, form a thesis, reproduce the bug, minimal fix).

## `pr_review/langgraph/` — PR review, 3-role pipeline

A separate, dedicated code-review pipeline, worth cross-referencing with
[`../code-review-approaches.md`](../code-review-approaches.md):

- `PR_FETCHER_PROMPT` — pulls PR metadata, per-commit diffs, and the
  whole-PR diff via GitHub tools, then hands off with `"ANALYZE REPO"`.
- `REPO_ANALYZER_PROMPT` — read-only codebase investigation scoped to
  what's relevant to the diff, hands off with `"ANALYSIS COMPLETED"`.
- `PR_COMMENT_PROMPT` — the reviewer proper. Notably one of the more
  careful sources on **existing-comment handling** in this whole
  collection: it's explicitly instructed to call
  `GITHUB_LIST_REVIEW_COMMENTS_ON_A_PULL_REQUEST` and "check before
  commenting if that comment has already been made, and avoid making
  duplicate comments" — stated as an explicit, repeated (twice in the
  prompt) rule, not just implied. Posts real inline review comments via
  `GITHUB_CREATE_A_REVIEW_COMMENT_FOR_A_PULL_REQUEST`, plus a final
  overall quality-rating comment, and is told to "be very skeptical" and
  keep comments non-verbose.
