# Claude Code v2.1.303, from Piebald's extraction

- **Type**: Coding agent prompt corpus · **Vendor**: Anthropic · **Status**: closed source
- **Mirror source**: https://github.com/Piebald-AI/claude-code-system-prompts
  at `d895c8d` (2026-10-18, "Update changelog for v2.1.303"), read 2026-10-19
- **License of the mirror**: MIT (Piebald LLC), copied here as
  [`LICENSE-piebald`](./LICENSE-piebald). The text itself is Anthropic's.

## Why this folder exists

Everything else in [`../`](..) is either a capture of what a model saw in
one session (the 2.1.172 files, July 2026) or strings pulled out of one
binary (`artifact-skills/`, September 2026). Piebald does something
different: a script extracts **every prompt string** from each npm release
of `@anthropic-ai/claude-code`, splits it into named pieces with the
template variables left as `${...}`, counts tokens, and keeps a changelog
across 317 versions since v2.0.14. It is updated within minutes of each
release.

Provenance is therefore as strong as `artifact-skills/` (read from shipped
code, not from a model's context) and much broader. The caveat runs the
other way: a string in the bundle is not proof that it is ever sent. Many
pieces are feature-gated (all the "lean rewrite" pieces, coordinator mode,
the Ultracode reminder), and the extraction cannot tell which gates are on
for which users. Treat a piece as "exists in the shipped client", not
"every session sees this".

Two smaller caveats. The extraction script itself is not in Piebald's
repo; `tools/updatePrompts.js` only turns its JSON output into files.
Token counts come from the `count_tokens` endpoint with the Sonnet 4.5
tokenizer, so they are close but not exact for other models.

## What the corpus is, in numbers

From [`inventory.tsv`](./inventory.tsv), which lists all 961 pieces with
section, token count, the version each was last changed in, and filename.

| Section | Pieces | Tokens | Changed after 2.1.172 |
|---|---:|---:|---:|
| System Prompt (parts of the main prompt) | 192 | 83,601 | 150 |
| Builtin Tool Descriptions | 275 | 99,793 | 230 |
| Agent Prompts (sub-agents, utilities, slash commands) | 91 | 81,556 | 82 |
| System Reminders | 155 | 40,141 | 138 |
| Skills | 73 | 94,632 | 70 |
| Data (reference docs, schemas, settings text) | 175 | 116,847 | 173 |
| **Total** | **961** | **516,570** | **843** |

So 88% of the pieces were created or changed after the build our main
captures come from. Between 2.1.172 and 2.1.303 the changelog records 113
versions, 502 new pieces, 117 removed pieces and a net growth of about
118k tokens.

## Files stored here

63 of the 961 pieces, chosen because a document in this collection now
cites them. Each keeps Piebald's HTML-comment frontmatter (name,
description, `ccVersion`, template variables). Use `inventory.tsv` and the
mirror for the rest.

**Code review** (cited in `code-review-approaches.md` §14):
`agent-prompt-code-review-part-1…7`, `agent-prompt-code-review-minimal-mode`,
`skill-code-review-angle-{b,c,d,e}-*`, `skill-code-review-conventions-dimension`,
`skill-code-review-phase-2-verify-3-state`, `skill-code-review-phase-3-sweep-for-gaps`.

**Auto mode and the action classifier** (`agent-permissions-approval.md` §1c, §2c):
`agent-prompt-security-monitor-for-autonomous-agent-actions-first-part`
(the 14k-token classifier; its rule lists are a `<permissions_template>`
placeholder filled at runtime and are not in the extraction),
`agent-prompt-security-monitor-forwarded-user-turns`,
`agent-prompt-security-monitor-host-context-line-guidance`,
`system-prompt-auto-mode`, `system-reminder-auto-mode-consent-flow`,
`system-reminder-auto-mode-clarification-bias`,
`system-prompt-deny-rule-circumvention-classifier-guidance`,
`system-prompt-permission-classifier-strict-review-guidance`,
`system-reminder-proactivity-level-{high,medium,low}`,
`system-reminder-scheduled-task-automated-firing`.

**Run-state classifiers** (`agent-turn-output.md` §1d):
`agent-prompt-background-agent-state-classifier`,
`agent-prompt-background-agent-state-classifier-ask-opens-message-rule`,
`agent-prompt-project-thread-status-card-classifier`,
`agent-prompt-coding-session-title-generator`.

**Orchestration** (`agent-subagent-architectures.md` §7c):
`system-prompt-coordinator-mode-orchestration`,
`agent-prompt-coordinator-worker-instructions`, `agent-prompt-worker-fork`,
`agent-prompt-parent-messages-and-user-authorization-lean-rewrite`,
`agent-prompt-subagent-reporting-notes-lean-rewrite`,
`agent-prompt-workflow-subagent-structured-output`,
`agent-prompt-workflow-script-plain-text-return-note`,
`skill-workflow-authoring-reference` (the Workflow guide that §7b said had
not been read), `system-reminder-resume-agents-interrupted-by-container-restart`,
`system-reminder-still-running-tool-call`,
`system-reminder-background-command-quiet-check-in`,
`agent-prompt-pr-follow-up-cron`, `agent-prompt-pr-follow-up-cron-pr-steward-label-check`,
`system-prompt-pr-steward-handoff-guidance`.

**Compaction** (`agent-context-compaction.md` §2b):
`agent-prompt-conversation-summarization-{lean,short}-variant`,
`agent-prompt-summarization-no-tools-guard`,
`system-reminder-output-token-limit-continuation`.

**Memory** (`agent-memory-learning.md` §13):
`agent-prompt-dream-memory-consolidation`,
`agent-prompt-determine-which-memory-files-to-attach`,
`system-reminder-memory-sync-mass-deletion-guard`,
`system-reminder-memory-extraction-{tool-constraints,turn-budget}`.

**Untrusted content and provenance** (`agent-content-provenance.md` §5):
`agent-prompt-web-reading-specialist`,
`system-reminder-web-fetch-untrusted-content-reporting-guidance`,
`system-reminder-external-source-trust-boundary`,
`system-reminder-file-summary-completeness-disclosure`.

**The "lean rewrite" family** (style observation in
`../../../agent-design/proposals-claude-code-2.1.303.md` §10):
`system-prompt-{delivering-requested-work,handling-corrections,focus-mode,harness-instructions,irreversible-action-caution}-lean-rewrite`.

## What Piebald has that this collection lacked

The comparison was made subsystem by subsystem against every Claude Code
file in [`../`](..) and every cross-source document that cites Claude
Code. "Lacked" means no file here held the text and no document described
it, or a document described it wrongly.

| Subsystem | What we had | What Piebald adds | Where it is now covered |
|---|---|---|---|
| `/code-review` | One effort level (`bundled-skills/code-review.md`, high) | The whole effort ladder: low (one pass, ≤4, no verify, tests skipped), medium (precision, 3-state verify, ≤8), high (recall-biased verify, ≤10), xhigh/max (5 correctness angles, ≤8 each, gap sweep); angles B–E and the conventions angle as separate pieces | `code-review-approaches.md` §14 |
| Auto mode classifier | Inferred from the May 2026 leaked source; described as internal-only | The full prompt: HARD/SOFT block, consent bars with a "must name" slot, Path A/B consent, harness meta lines as ground truth, outcome vocabulary, nonce-keyed forwarded user turns | `agent-permissions-approval.md` §2c, with corrections to §2 and §2a |
| Proactivity levels | Nothing | Three levels that change what the agent may do without asking, including commit/push/PR | `agent-permissions-approval.md` §1c |
| Background/thread state classifiers | Nothing | Two classifiers that read a run's last message and decide working/blocked/done/failed; they disagree on two boundaries | `agent-turn-output.md` §1d |
| Session title generator | 2.1.172 wording | Rewritten: no request verbs, no trailing abstract nouns, untrusted session content | `agent-turn-output.md` §1d |
| Coordinator mode and workers | `Team` tools only | The coordinator prompt (continue-vs-spawn table, synthesise-don't-delegate-understanding, fresh worker for approved actions), worker, fork and workflow-subagent prompts | `agent-subagent-architectures.md` §7c |
| Workflow authoring guide | Tool definition only | `pipeline()` as the default, barrier rules, nondeterminism banned for resume, concurrency caps, loop-until-dry dedup | `agent-subagent-architectures.md` §7c |
| Compaction | `bundled-skills/compact.md` and the 2.1.172 prompt | Lean, short and capped variants; the manifest of what survives; "the summary is the only record of what the user said" | `agent-context-compaction.md` §2b |
| Memory | The May 2026 leaked `memdir` source | The shipped dream prompt, the attachment selector's rule on profile memories, the mass-deletion guard, the extraction agent's tool and turn limits | `agent-memory-learning.md` §13 |
| Web reading and external content | Nothing for Claude Code | A web-reading sub-agent, "report injected instructions as a finding", external-source banners | `agent-content-provenance.md` §5 |
| PR follow-up and PR Steward | A mention in `agent-design/README.md` | The cron prompt and the label-based hand-off protocol between two agents on one PR | `agent-subagent-architectures.md` §7c |
| System reminders | A handful, inside the 2.1.172 captures | 155 named reminders; the attached-machine reachability set alone is 25 | Inventory only; the ones a document uses are stored |
| Data pieces | Nothing | 175 reference docs, SDK schemas, settings text, self-hosted runner warnings | Inventory only; mostly product reference, not agent design |
| Per-piece token counts and a version changelog | Nothing | Both, for every release | `sources.md`; re-read by diffing `inventory.tsv` |

**Not covered, on purpose.** The Artifact, Slides, Design canvas and
Claude in Chrome pieces (about 180 between them) continue what
`artifact-skills/` and `agent-generative-output.md` already analyse; the
attached-machine reminders are product plumbing for one remote-device
feature; the `Data` section is mostly SDK and API reference. They are in
the inventory for a later pass.

## Re-reading

```sh
git clone --depth 1 https://github.com/Piebald-AI/claude-code-system-prompts.git
```

Then rebuild `inventory.tsv` with the same columns and diff it against
this one: a changed `cc_version` marks a piece to re-read. Piebald's
`CHANGELOG.md` gives a one-line description of every change per release,
which is quicker than diffing text.
