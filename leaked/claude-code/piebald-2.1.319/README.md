# Claude Code v2.1.317–2.1.319, from Piebald's extraction

- **Type**: Coding agent prompt corpus (delta) · **Vendor**: Anthropic · **Status**: closed source
- **Mirror source**: https://github.com/Piebald-AI/claude-code-system-prompts
  at `d2fd553` (2026-11-05, "Update changelog for v2.1.319"), read 2026-11-09.
  The previous read was `f6aed7f` (v2.1.316), stored in
  [`../piebald-2.1.316/`](../piebald-2.1.316).
- **License of the mirror**: MIT (Piebald LLC), copied here as
  [`LICENSE-piebald`](./LICENSE-piebald). The text itself is Anthropic's.

The caveats in [`../piebald-2.1.303/README.md`](../piebald-2.1.303/README.md)
apply unchanged: a piece is a string in the shipped bundle, not proof that
any given session is sent it, and many pieces are feature-gated. That
matters more than usual here, because the REPL pieces are behind flags
(`IS_REPL_SCRIPT_INNER_CALL`, `IS_REPL_JSON_EVENT_FORMAT_ENABLED`, an
async lane) and this pass did not establish who gets them.

## What changed in three releases

Three releases (2.1.317, 2.1.318, 2.1.319). Measured with
`git diff --name-status f6aed7f d2fd553 -- system-prompts`:

| | Pieces |
|---|---:|
| Added | 87 |
| Removed | 10 |
| Changed | 60 |
| Total at 2.1.319 | 1,134 (1,057 at 2.1.316) |

[`delta.tsv`](./delta.tsv) lists all 157 with status, name, the version
that last touched the piece, and filename. Removed pieces show the version
they were last changed in.

The largest single addition is a **REPL tool**, Claude Code's own Code
Mode (2.1.318–2.1.319): one persistent, sealed JavaScript context in which
every tool, MCP tools included, is an async function; named child-agent
"contexts" started from code; dispatched scripts with receipts; and an
auto-mode rule for what a pre-execution check of a script can and cannot
cover. The rest that bears on Forge is permission plumbing for hosts and
headless use (`denyInsteadOfPrompting`, connector aliases, host-rendered
MCP calls), worktree-isolation tamper refusals, and MCP task-monitoring
notices. Most of the remaining volume is SDK telemetry fields, the
Cloud gateway, Artifact database refusals, voice calls, and sign-in
guidance for the `ant` CLI.

## The pieces stored here, and why

Sixteen pieces, verbatim with their frontmatter.

| File | Version | Cited in |
|---|---|---|
| [`tool-description-repl.md`](./tool-description-repl.md) | 2.1.318 | `code-mode/README.md` "Claude Code's REPL" |
| [`tool-description-repl-persistent-helper-interface.md`](./tool-description-repl-persistent-helper-interface.md) | 2.1.319 | `code-mode/README.md` |
| [`tool-description-repl-dispatched-script-execution-and-event-delivery.md`](./tool-description-repl-dispatched-script-execution-and-event-delivery.md) | 2.1.318 | `code-mode/README.md`; `agent-run-recovery.md` §5 |
| [`data-repl-asynchronous-context-api-declarations.md`](./data-repl-asynchronous-context-api-declarations.md) | 2.1.318 | `code-mode/README.md` |
| [`system-reminder-code-mode-auto-mode-subagent-creation-refusal.md`](./system-reminder-code-mode-auto-mode-subagent-creation-refusal.md) | 2.1.319 | `code-mode/README.md`; `agent-design/future.md` |
| [`system-reminder-code-mode-auto-mode-agent-message-refusal.md`](./system-reminder-code-mode-auto-mode-agent-message-refusal.md) | 2.1.319 | `code-mode/README.md`; `agent-design/future.md` |
| [`system-reminder-code-mode-auto-mode-hook-rewrite-refusal.md`](./system-reminder-code-mode-auto-mode-hook-rewrite-refusal.md) | 2.1.318 | `code-mode/README.md`; `agent-design/future.md` |
| [`data-denyinsteadofprompting-setting.md`](./data-denyinsteadofprompting-setting.md) | 2.1.319 | `agent-permissions-approval.md` §2g; `agent-design/keel/tools-and-agents.md` §4e |
| [`data-sdk-mcp-server-connectorid-field.md`](./data-sdk-mcp-server-connectorid-field.md) | 2.1.319 | `agent-permissions-approval.md` §2g |
| [`data-mcp-call-check-permissions-field.md`](./data-mcp-call-check-permissions-field.md) | 2.1.319 | `agent-permissions-approval.md` §2g |
| [`system-reminder-voice-call-record-background-framing.md`](./system-reminder-voice-call-record-background-framing.md) | 2.1.319 | `agent-permissions-approval.md` §2g |
| [`system-reminder-mcp-task-monitoring-continues-after-a-failure.md`](./system-reminder-mcp-task-monitoring-continues-after-a-failure.md) | 2.1.319 | `agent-run-recovery.md` §5; `agent-design/keel/tools-and-agents.md` §4e |
| [`system-reminder-mcp-task-monitoring-stopped.md`](./system-reminder-mcp-task-monitoring-stopped.md) | 2.1.319 | `agent-run-recovery.md` §5 |
| [`data-worktree-isolation-redirected-git-directory-refusal.md`](./data-worktree-isolation-redirected-git-directory-refusal.md) | 2.1.319 | this README only (see below) |
| [`system-reminder-sandbox-hard-linked-guarded-file-refusal.md`](./system-reminder-sandbox-hard-linked-guarded-file-refusal.md) | 2.1.317 | this README only (see below) |
| [`system-reminder-oversized-mentioned-file-reading-guidance.md`](./system-reminder-oversized-mentioned-file-reading-guidance.md) | 2.1.318 | this README only (see below) |

Three pieces are kept for the record without a new section:

- **Worktree tamper refusals** (four pieces in 2.1.319, one stored). A
  worktree whose `.git` now points somewhere other than its registry entry,
  whose parent is a symlink, or whose host registry is unreadable, is
  treated as tampered with: "run no git in it, and do not re-link it with
  git worktree repair … code running in a worktree can add such an entry."
  This extends `agent-git-vcs.md` §8 (a sandbox-writable `.git` is a
  channel out); Keel already mounts the git directory read-only
  (`agent-design/keel/tools-and-agents.md` §4a), so no change.
- **Hard-linked guarded files** (2.1.317). The sandbox refuses to start
  while a file it guards has a second hard link, and refuses the
  unsandboxed retry too. The same class as the hard-link note in
  `agent-permissions-approval.md` §6.
- **Oversized mentioned files** (2.1.318). "A search shows only the lines
  that match its words, so it misses what is worded differently … If you
  answer from searches or from part of the file, tell the user so, and
  name what you searched for." Forge's reports already carry
  `unverified`; this is the same rule at the read level.

Not stored: the removal of three conversation-summarization variants
(capped, lean, short) in 2.1.318. That reads as an experiment ending, and
the remaining prompt drops its 2,000-word cap; see
`agent-context-compaction.md` §2d.
