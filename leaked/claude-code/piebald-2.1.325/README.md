# Claude Code v2.1.320–2.1.325, from Piebald's extraction

- **Type**: Coding agent prompt corpus (delta) · **Vendor**: Anthropic · **Status**: closed source
- **Mirror source**: https://github.com/Piebald-AI/claude-code-system-prompts
  at `7aca957` (2026-11-13, "Update changelog for v2.1.325"), read 2026-11-16.
  The previous read was `d2fd553` (v2.1.319), stored in
  [`../piebald-2.1.319/`](../piebald-2.1.319).
- **License of the mirror**: MIT (Piebald LLC), copied here as
  [`LICENSE-piebald`](./LICENSE-piebald). The text itself is Anthropic's.

The caveats in [`../piebald-2.1.303/README.md`](../piebald-2.1.303/README.md)
apply unchanged: a piece is a string in the shipped bundle, not proof that
any given session is sent it, and many pieces are feature-gated. Pieces
marked `@internal` are SDK field descriptions for hosts, not text the
model reads.

## What changed in six releases

Piebald lists 2.1.321, 2.1.322 (no prompt changes), 2.1.323, 2.1.324 and
2.1.325 (no prompt changes). No 2.1.320 entry appears in its changelog.
Measured with `git diff --name-status d2fd553 7aca957 -- system-prompts`:

| | Pieces |
|---|---:|
| Added | 79 |
| Removed | 4 |
| Changed | 87 |
| Total at 2.1.325 | 1,209 (1,134 at 2.1.319) |

[`delta.tsv`](./delta.tsv) lists all 170 with status, name, the version
that last touched the piece, and filename. Removed pieces show the version
they were last changed in.

The part that bears on Forge is **what happens when the model's own
response fails**: a reply cut off inside a tool call (the call did not
run), a response whose tool call could not be parsed (dropped from the
conversation and asked again), content-free completions, and an error
classification for hosts that says which failures must never be resent.
Also new: a "Finishing work" section for unattended work, memory-saving
rules ("applicable and durable"), a `Yield` tool for waiting on
asynchronous tools, and a reminder for output too large to save. Most of
the remaining volume is SDK host fields, `/teleport` stash refusals,
worktree failures in partial clones, Artifact plumbing, mods and sign-in
guidance.

## The pieces stored here, and why

Eleven pieces, verbatim with their frontmatter.

| File | Version | Cited in |
|---|---|---|
| [`system-reminder-output-token-limit-tool-call-cutoff.md`](./system-reminder-output-token-limit-tool-call-cutoff.md) | 2.1.323 | `agent-run-recovery.md` §7; `agent-design/formats.md` §7 item 4 |
| [`data-sdk-user-message-retracted-message-uuids-field.md`](./data-sdk-user-message-retracted-message-uuids-field.md) | 2.1.323 | `agent-run-recovery.md` §7 |
| [`data-sdk-api-error-kind-field.md`](./data-sdk-api-error-kind-field.md) | 2.1.324 | `agent-run-recovery.md` §7; `agent-design/formats.md` §7 item 4 |
| [`data-sdk-api-error-params-field.md`](./data-sdk-api-error-params-field.md) | 2.1.321 | `agent-run-recovery.md` §7 (`cut`: output limit vs context window) |
| [`data-sdk-api-error-type-field.md`](./data-sdk-api-error-type-field.md) | 2.1.324 | `agent-run-recovery.md` §7 (error type alone does not say a retry helps) |
| [`system-reminder-unsaved-tool-output-truncation.md`](./system-reminder-unsaved-tool-output-truncation.md) | 2.1.323 | `agent-run-recovery.md` §7 |
| [`system-prompt-work-completion-and-direct-editing.md`](./system-prompt-work-completion-and-direct-editing.md) | 2.1.321 | `agent-run-recovery.md` §7 (closing note) |
| [`tool-description-yield.md`](./tool-description-yield.md) | 2.1.323 | `agent-run-recovery.md` §7 (closing note) |
| [`system-prompt-memory-notes-and-feedback-rules.md`](./system-prompt-memory-notes-and-feedback-rules.md) | 2.1.321 | recorded for `agent-design/keel/memory.md` §16 (proposal); not used |
| [`system-reminder-post-compaction-conversation-reread-guidance.md`](./system-reminder-post-compaction-conversation-reread-guidance.md) | 2.1.324 | recorded; Forge has no compaction in v1 |
| [`data-sdk-warning-hook-no-verdict-field.md`](./data-sdk-warning-hook-no-verdict-field.md) | 2.1.324 | recorded; a hook failure that did not refuse the call |

`data-sdk-api-error-kind-field.md` was last changed in 2.1.324, but most
of its kinds (including `unattended_start_limit`, `tool_history_mismatch`
and `malformed_tool_use_exhausted`) were already present at 2.1.317; only
the `empty_completion` wording changed in this range. It is stored here
because this pass is the first to use it.
