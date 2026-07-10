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

## Tool surface

Composio's tools are namespaced by integration/toolkit (`FILETOOL_*`,
`CODE_ANALYSIS_TOOL_*`, `GITHUB_*`) rather than given the short generic
names (`bash`, `edit`, `grep`) used elsewhere in this collection — the
prompt text spells out the fully-qualified tool name at every call site.
Per-role tool access is a hard boundary here, not just a convention: the
orchestrator/analyzer/editor roles in `swe/langgraph/` are wired to
disjoint tool sets, enforced by the framework's per-node tool bindings,
not merely instructed in prose.
- **Shell**: none exposed directly — no bash/terminal tool appears in
  either template. All action happens through the named FILETOOL/
  CODE_ANALYSIS_TOOL/GITHUB tool calls instead of a general-purpose shell.
- **Search/exploration**: `FILETOOL_GIT_REPO_TREE` (repo structure) for
  the orchestrator; the read-only `CODE_ANALYSIS_TOOL` family
  (`GET_CLASS_INFO`, `GET_METHOD_BODY`, `GET_METHOD_SIGNATURE`) plus
  `FILETOOL_OPEN_FILE`/`FILETOOL_SCROLL`/`FILETOOL_SEARCH_WORD` for the
  analyzer — symbol-level lookups closer to Copilot Chat's
  `SearchWorkspaceSymbols` than to plain grep, though scoped to
  class/method granularity rather than full LSP integration.
  `FILETOOL_SEARCH_WORD` is the closest thing to a grep-equivalent.
- **Editing**: `FILETOOL_EDIT_FILE` (line-range based — `start_line`/
  `end_line` params) and `FILETOOL_GIT_PATCH` for generating patches,
  restricted to the editing role only.
- **PR review / GitHub integration**: a dedicated set only in
  `pr_review/langgraph/` — `GITHUB_GET_A_PULL_REQUEST`,
  `GITHUB_GET_PR_METADATA`, `GITHUB_LIST_COMMITS_ON_A_PULL_REQUEST`,
  `GITHUB_GET_A_COMMIT`, `GITHUB_GET_DIFF` for fetching, and
  `GITHUB_CREATE_A_REVIEW_COMMENT_FOR_A_PULL_REQUEST`/
  `GITHUB_CREATE_AN_ISSUE_COMMENT`/
  `GITHUB_LIST_REVIEW_COMMENTS_ON_A_PULL_REQUEST` for posting — real
  GitHub-API-backed tools, not a shelled-out `gh` CLI (contrast the
  `github-pr-bots/` sources in this collection, several of which do shell
  out to `gh`/`git`).
- **Sub-agent handoff as the extensibility mechanism**: control passes
  between the three roles via literal keyword strings in the conversation
  (`"ANALYZE CODE"`, `"EDITING COMPLETED"`, etc.) rather than a
  dispatcher tool — see the role-handoff description above.
- **Browser/multimodal**: none.
- **Sandbox/isolation**: not specified by the prompts — depends on
  wherever the generated LangGraph/CrewAI app is deployed.
- **Framework-conditional tool wiring**: since SWE-Kit is a code
  generator (`swekit scaffold`) targeting five different agent
  frameworks, the actual tool-calling mechanism (LangGraph tool nodes vs.
  CrewAI's tool-equipped `Agent` vs. AutoGen/LlamaIndex/CamelAI
  equivalents) varies by generated project, though the Composio tool
  *names* stay constant across all of them.
