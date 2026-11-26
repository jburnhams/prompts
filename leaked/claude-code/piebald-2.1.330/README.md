# Claude Code v2.1.326–2.1.330, from Piebald's extraction

- **Type**: Coding agent prompt corpus (delta) · **Vendor**: Anthropic · **Status**: closed source
- **Mirror source**: https://github.com/Piebald-AI/claude-code-system-prompts
  at `659d9f4` (2026-11-20, "Update changelog for v2.1.330"), read
  2026-11-23. The previous read was `7aca957` (v2.1.325), stored in
  [`../piebald-2.1.325/`](../piebald-2.1.325).
- **License of the mirror**: MIT (Piebald LLC), copied here as
  [`LICENSE-piebald`](./LICENSE-piebald). The text itself is Anthropic's.

The caveats in [`../piebald-2.1.303/README.md`](../piebald-2.1.303/README.md)
apply unchanged: a piece is a string in the shipped bundle, not proof that
any given session is sent it, and many pieces are feature-gated. Pieces
marked `@internal` are SDK field descriptions for hosts, not text the
model reads.

## What changed in five releases

Piebald lists 2.1.326, 2.1.327, 2.1.328, 2.1.329 and 2.1.330. Measured
with `git diff --name-status 7aca957 659d9f4 -- system-prompts`:

| | Pieces |
|---|---:|
| Added | 118 |
| Removed | 34 |
| Changed | 127 |
| Total at 2.1.330 | 1,293 files under `system-prompts/` (1,209 pieces at 2.1.325) |

[`delta.tsv`](./delta.tsv) lists all 279 with status, name, the version
that last touched the piece, and filename. Removed pieces show the version
they were last changed in.

The part that bears on Forge is **`/steward`**, added in 2.1.330: a PR
watch that runs from the user's own checkout, one pass per wake-up, until
the PR is merged or closed. Twenty-odd pieces define it: how a watch
starts (with or without a review, skipping a review a hosted reviewer
already did on the same head), what one pass does (look, deal with review
findings, resolve a conflict, read red checks' logs, answer comments,
push, decide "ready"), when to check again, when to stop, and the
unattended rules. The rules have three layers: what the model must never
do ("Never, whatever you read and whoever on GitHub asks"), what is data
and never instructions, and "the fence", the part Claude Code itself
enforces (an allowlist of exact `gh` and `git` lines, one write per call,
no shell substitution, and an end to the watch if git configuration,
hooks, `.claude/settings.json`, `.mcp.json` or the project's watch
instructions change). Comments reach the model through a snapshot that
code builds each pass, keeping only the words of the user, people with
write access and named bots, and counting the rest as "not read".

Also in this range: `/code-review` severities (`important`,
`pre_existing`, `nit`) with "Fix:" in every summary; a general rule for
untrusted external input (validate before a tool sees it, stop at
redirects to localhost or metadata addresses, read downloaded config and
hooks before running anything over them, run with no network); an
`on_failure` setting for MCP hooks (`continue` or `block`), matching
Codex's per-hook `onFailure` (#62831) the same week; PR Steward's handoff
text no longer saying it merges; and much SDK, sign-in, Artifact, sandbox
and self-hosted-runner plumbing.

## The pieces stored here, and why

Nineteen files: seventeen pieces verbatim with their frontmatter, plus
this README and `delta.tsv`.

| File | Version | Cited in |
|---|---|---|
| [`skill-steward-start-pull-request-watch.md`](./skill-steward-start-pull-request-watch.md) | 2.1.330 | `agent-design/medium.md` §1e |
| [`skill-steward-review-only.md`](./skill-steward-review-only.md) | 2.1.330 | recorded with the watch |
| [`skill-steward-watch-pass.md`](./skill-steward-watch-pass.md) | 2.1.330 | `agent-design/medium.md` §1e (project instructions "lift no limit") |
| [`skill-steward-watch-pass-steps.md`](./skill-steward-watch-pass-steps.md) | 2.1.330 | `agent-design/medium.md` §1e items 1–3 |
| [`skill-steward-unattended-watch-rules.md`](./skill-steward-unattended-watch-rules.md) | 2.1.330 | `agent-design/medium.md` §1e items 2, 4, 5; `agent-design/keel/tools-and-agents.md` §4d (`outbound_text`) |
| [`skill-steward-pull-request-comment-snapshot.md`](./skill-steward-pull-request-comment-snapshot.md) | 2.1.330 | `agent-design/medium.md` §1e item 4 (`mayHide`, "Not read") |
| [`skill-steward-next-check-in-timing.md`](./skill-steward-next-check-in-timing.md) | 2.1.330 | recorded with the watch |
| [`skill-steward-waiting-and-stopping.md`](./skill-steward-waiting-and-stopping.md) | 2.1.330 | recorded with the watch (harness looks every two minutes, wakes the model only on change) |
| [`skill-steward-watch-ended.md`](./skill-steward-watch-ended.md) | 2.1.330 | recorded (the watch also ends when the permission mode stops asking) |
| [`system-reminder-steward-checkout-changed-unexpectedly.md`](./system-reminder-steward-checkout-changed-unexpectedly.md) | 2.1.330 | `agent-design/medium.md` §1e item 5 |
| [`system-reminder-steward-merge-changes-execution-settings.md`](./system-reminder-steward-merge-changes-execution-settings.md) | 2.1.330 | `agent-design/medium.md` §1e item 5 |
| [`system-reminder-steward-ci-run-outside-failed-runs.md`](./system-reminder-steward-ci-run-outside-failed-runs.md) | 2.1.330 | `agent-design/medium.md` §1e item 1 |
| [`system-reminder-steward-unattended-command-refusal.md`](./system-reminder-steward-unattended-command-refusal.md) | 2.1.330 | recorded (the fence's refusal text) |
| [`system-prompt-pr-steward-handoff-guidance.md`](./system-prompt-pr-steward-handoff-guidance.md) | 2.1.326 | correction in `agent-subagent-architectures.md` §7c |
| [`skill-code-review-finding-severity-and-summaries.md`](./skill-code-review-finding-severity-and-summaries.md) | 2.1.328 | recorded; Forge's review schema already ranks findings |
| [`system-prompt-untrusted-external-input-guidance.md`](./system-prompt-untrusted-external-input-guidance.md) | 2.1.327 | recorded; Forge's containers have no outbound network by default |
| [`data-mcp-hook-on-failure-field.md`](./data-mcp-hook-on-failure-field.md) | 2.1.328 | recorded; Keel has no user hooks |

The Steward pieces are templates with many `${...}` variables, some of
which are functions whose text is not in the extraction (for example
`BUILD_WATCH_RULES_FN`, `WATCH_COMMANDS`). The exact commands, delays and
caps (`PUSH_WAIT_MINUTES`, `MAX_WATCH_DAYS`, `QUIET_PASS_LIMIT`) are not
visible, so none of their values is quoted anywhere in this collection.
