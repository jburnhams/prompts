# Claude Code v2.1.304–2.1.310, from Piebald's extraction

- **Type**: Coding agent prompt corpus (delta) · **Vendor**: Anthropic · **Status**: closed source
- **Mirror source**: https://github.com/Piebald-AI/claude-code-system-prompts
  at `7b78158` (2026-10-24, "Update changelog for v2.1.310"), read 2026-10-26.
  The previous read was `d895c8d` (v2.1.303), stored in
  [`../piebald-2.1.303/`](../piebald-2.1.303).
- **License of the mirror**: MIT (Piebald LLC), copied here as
  [`LICENSE-piebald`](./LICENSE-piebald). The text itself is Anthropic's.

The caveats in [`../piebald-2.1.303/README.md`](../piebald-2.1.303/README.md)
apply unchanged: a piece is a string in the shipped bundle, not proof that
any given session is sent it, and many pieces are feature-gated.

## What changed in seven releases

Seven releases in six days (2026-10-20 to 2026-10-24), two of them with no
prompt changes (2.1.306, 2.1.308). Measured with
`git diff --name-status d895c8d 7b78158 -- system-prompts`:

| | Pieces |
|---|---:|
| Added | 75 |
| Removed | 10 |
| Changed | 64 |
| Total at 2.1.310 | 1,026 (961 at 2.1.303) |

[`delta.tsv`](./delta.tsv) lists all 149 with status (`A`/`D`/`M`), name, the
version that last touched the piece, and filename, so the next pass can
diff from here. Removed pieces show the version they were last changed in.

Most of the volume is product surface that does not bear on Forge: the
Windows sandbox (git credentials, Schannel TLS, localhost binding, pytest
cache hangs), Artifacts and Artifact types, attached-machine reachability
messages, Managed Agents `ant` command refusals, self-hosted runner
diagnostics, and the Claude Test browser plugin's agents.

## The pieces stored here, and why

Ten pieces, verbatim with their frontmatter, chosen for Forge's
containerised runs, approvals and context trust. Each is cited from the
cross-source doc named.

| File | Version | Cited in |
|---|---|---|
| [`system-reminder-tool-calls-lost-to-session-restart.md`](./system-reminder-tool-calls-lost-to-session-restart.md) | 2.1.309 | `agent-run-recovery.md` §1 |
| [`system-reminder-session-moved-to-new-runner-resume-prompt.md`](./system-reminder-session-moved-to-new-runner-resume-prompt.md) | 2.1.309 | `agent-run-recovery.md` §1 |
| [`data-worktree-creation-submodule-on-demand-fetch-disabled-error.md`](./data-worktree-creation-submodule-on-demand-fetch-disabled-error.md) | 2.1.309 | `agent-git-vcs.md` §8 |
| [`data-sandbox-worktrees-directory-listing-failure-warning.md`](./data-sandbox-worktrees-directory-listing-failure-warning.md) | 2.1.310 | `agent-git-vcs.md` §8 |
| [`agent-prompt-security-monitor-email-sender-turns.md`](./agent-prompt-security-monitor-email-sender-turns.md) | 2.1.305 | `agent-permissions-approval.md` §2e |
| [`agent-prompt-security-monitor-email-reply-approval-scope.md`](./agent-prompt-security-monitor-email-reply-approval-scope.md) | 2.1.305 | `agent-permissions-approval.md` §2e |
| [`agent-prompt-security-monitor-email-sender-only-approval-scope.md`](./agent-prompt-security-monitor-email-sender-only-approval-scope.md) | 2.1.305 | `agent-permissions-approval.md` §2e |
| [`system-reminder-auto-mode-finish-exposed-work.md`](./system-reminder-auto-mode-finish-exposed-work.md) | 2.1.307 | `coding-agent-approaches.md` §12a |
| [`system-reminder-project-document-rewrite-without-current-text-refusal.md`](./system-reminder-project-document-rewrite-without-current-text-refusal.md) | 2.1.310 | this README only (a read-before-overwrite refusal that also forbids delete-and-rewrite) |
| [`system-reminder-memory-file-contents-unverified-managed-folder.md`](./system-reminder-memory-file-contents-unverified-managed-folder.md) | 2.1.304 | this README only (see below) |

The managed-folder piece is a header only. The warning it appends lives in
the variable `UNVERIFIED_MANAGED_INSTRUCTIONS_DESCRIPTION`, whose text was
not found in this read; the changelog's summary ("follow every limit it
sets but treat nothing in it as permission") is the only wording we have.

## Also noted, not stored

- **Removed:** the server-side `safeguard_results` / `safeguard_tool_use`
  SDK fields (2.1.307), through which a worker could take a server-side
  classifier's verdict on one tool call; the changelog says auto mode
  still reads `safeguard_results` from API responses. And the subagent
  "when to use" variant (2.1.307), leaving only the cost guidance.
- **`empty_completion`** (2.1.307): a reply and its one retry both empty on
  a person's own prompt now end the turn as an error rather than a blank
  reply.
- **PR text @-mentions** (2.1.309): PR creation prompts now warn that an
  `@name` notifies that account.
