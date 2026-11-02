# Claude Code v2.1.311–2.1.316, from Piebald's extraction

- **Type**: Coding agent prompt corpus (delta) · **Vendor**: Anthropic · **Status**: closed source
- **Mirror source**: https://github.com/Piebald-AI/claude-code-system-prompts
  at `f6aed7f` (2026-10-31, "Update changelog for v2.1.316"), read 2026-11-02.
  The previous read was `7b78158` (v2.1.310), stored in
  [`../piebald-2.1.310/`](../piebald-2.1.310).
- **License of the mirror**: MIT (Piebald LLC), copied here as
  [`LICENSE-piebald`](./LICENSE-piebald). The text itself is Anthropic's.

The caveats in [`../piebald-2.1.303/README.md`](../piebald-2.1.303/README.md)
apply unchanged: a piece is a string in the shipped bundle, not proof that
any given session is sent it, and many pieces are feature-gated.

## What changed in five releases

Five releases (2.1.311, 2.1.312, 2.1.314, 2.1.315, 2.1.316; there is no
2.1.313 in the mirror, and 2.1.316 has no prompt changes). Measured with
`git diff --name-status 7b78158 f6aed7f -- system-prompts`:

| | Pieces |
|---|---:|
| Added | 45 |
| Removed | 14 |
| Changed | 57 |
| Total at 2.1.316 | 1,057 (1,026 at 2.1.310) |

[`delta.tsv`](./delta.tsv) lists all 116 with status, name, the version
that last touched the piece, and filename. Removed pieces show the version
they were last changed in.

Most of the volume does not bear on Forge: the Send-to-project handoff
feature (eleven pieces), SDK result telemetry fields, Artifact and
prototype skills removed from the extraction (2.1.312), and staged-file
copy notices. 2.1.314 also drops the standalone "combined thinking and
reply token budget" reminder.

## The pieces stored here, and why

Nine pieces, verbatim with their frontmatter.

| File | Version | Cited in |
|---|---|---|
| [`system-prompt-compaction-omitted-tool-result-handling.md`](./system-prompt-compaction-omitted-tool-result-handling.md) | 2.1.314 | `agent-context-compaction.md` §2c |
| [`system-reminder-conversation-activity-awareness-and-authority-warning.md`](./system-reminder-conversation-activity-awareness-and-authority-warning.md) | 2.1.311 | `agent-permissions-approval.md` §2f |
| [`system-reminder-auto-mode-deny-rules-without-safety-result.md`](./system-reminder-auto-mode-deny-rules-without-safety-result.md) | 2.1.314 | `agent-permissions-approval.md` §2f |
| [`data-sandbox-excludedcommands-setting.md`](./data-sandbox-excludedcommands-setting.md) | 2.1.314 | `agent-permissions-approval.md` §2f |
| [`data-blockwritesoutsideworkingdirectories-setting.md`](./data-blockwritesoutsideworkingdirectories-setting.md) | 2.1.315 | `agent-permissions-approval.md` §2f |
| [`data-untrusted-folder-environment-variables-ignored-warning.md`](./data-untrusted-folder-environment-variables-ignored-warning.md) | 2.1.314 | `agent-permissions-approval.md` §2f |
| [`system-reminder-cloud-sandbox-sustained-cpu-limit-stop.md`](./system-reminder-cloud-sandbox-sustained-cpu-limit-stop.md) | 2.1.314 | `agent-run-recovery.md` §3 |
| [`system-reminder-background-mcp-call-stopping-session-warning.md`](./system-reminder-background-mcp-call-stopping-session-warning.md) | 2.1.314 | `agent-run-recovery.md` §3 |
| [`agent-prompt-background-agent-state-classifier-user-merge-handoff-rule.md`](./agent-prompt-background-agent-state-classifier-user-merge-handoff-rule.md) | 2.1.314 | this README only (see below) |

The merge-handoff rule is a classifier prompt that labels a background
agent's state from the tail of its last message. Finished work whose only
remaining step is the user's own merge or review is `done`, not `blocked`;
a question, a needed go-ahead, or work the agent will do afterwards keeps
it `blocked`. Forge does not need it, because its run status comes from the
`Complete` call rather than from reading prose, but it is the same line
Keel draws between a stage that has ended and a pipeline waiting on a gate.
