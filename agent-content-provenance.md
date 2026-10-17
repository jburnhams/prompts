# Content provenance: tagging who supplied each piece of context

A short drill-down written 2026-10-17. Every agent's context window mixes
text from sources with very different authority: the operator, the user,
repository files, tools, other agents, and strangers who can comment on a
PR. This document compares how harnesses keep track of which is which
**inside** the prompt. It sits next to
[`agent-context-file-loading.md`](./agent-context-file-loading.md), which
covers where repository instructions come from, and to Forge's
nonce-wrapped envelope blocks (`agent-design/formats.md` §1b,
`agent-design/context-files.md` §5).

## 1. Codex: a provenance value on every content part

Source: `openai/codex` (Apache-2.0) at `ce0323f2f2`,
`codex-rs/protocol/src/models/item_metadata.rs` and
`codex-rs/context-fragments/src/annotated_content.rs`. Added 2026-10-08
(#52195), removed the same day (#52329), and re-added 2026-10-14 (#53831)
with compaction support.

- **Each position in a message's content array** carries a
  `ContentItemMetadata { provenance }` alongside its `ContentItemKind`.
  The module's own description: "Per-part context sources, independent
  of message role, visibility, and trust."
- **The provenance values:**
  - `User`: "Ordinary user input, not an injected instruction fragment
    with a user role".
  - `DeveloperInstructions { from_additional_requirements }`, which
    distinguishes the operator's managed requirements layer from the
    ordinary slot.
  - `AgentsMd`.
  - `Skills`.
  - `Harness { hook }`, which separates command-hook output from built-in
    context.
  - `Tool { namespace }`. Built-in namespaces are typed and MCP ones stay
    open strings. "Tool-related context remains Tool even when the
    harness writes it."
  - `Unknown`, the default.
- **It survives editing and compaction.** "Content, classification and
  attribution travel together through edits and truncation." When text is
  truncated, "Retained slices keep their kind and source; the generated
  notice has harness provenance." The truncation marker is attributed to
  the harness, not to whoever wrote the text around it.
- **Older history is never upgraded.** Persisted rollouts without
  attribution deserialize as `Unknown`. A legacy `harness_injected: false`
  flag "[does not] identify a source precisely enough" to count as `User`.
- **It goes to the model as API metadata, not as text.** The per-part
  metadata is sent only to the Responses Lite endpoint and stripped for
  endpoints that don't support it. The model sees provenance as a
  structured field beside the content, so nothing in the content can
  forge it.

The same-day removal and the week-later return with compaction handling
suggest the first version didn't hold up once history was truncated.
Attribution that disappears when the context is compacted is worse than
none, because later turns look attributed when they aren't.

Guardian (`codex/guardian-mechanics.md` §5) applies the same idea to its
reviewer. "Source roles remain line-labeled evidence, not instructions
or a change to the delivery role." Host-verified items (skill paths,
trusted MCP tool sources, prior-review records) are attested separately
and placed after the transcript.

## 2. The text-level approaches

| Source | Mechanism | Forgeable from inside the content? |
|---|---|---|
| Forge (`agent-design/formats.md` §1b) | A per-run **nonce** on the open and close tags of each untrusted block (`<existing_comments nonce=…>`), transcluded whole and never re-wrapped | No, unless the nonce leaks; the close tag carries it |
| OpenClaw (`openclaw/README.md`) | A general `<untrusted-text>` escaping wrapper, used for sub-agent results, attachments and operator `/compact` text, but **not** for `AGENTS.md` | Escaping prevents breaking out; nothing marks *which* untrusted source it was |
| PR-Agent (`pr-agent/README.md`, 2026-10) | Start and end markers around the CI artifact, plus a system-prompt line listing title, description, commits, tickets, code and CI as untrusted data | Plain markers; an attacker who knows them can imitate them |
| Claude Code Review | `REVIEW.md` from the protected base branch only; PR content never supplies instructions | Not a tagging mechanism; provenance is enforced by *where the file is read from* |
| ClawSweeper (`clawsweeper/review-item.md`) | Typed context sections (`## Provenance Evidence`, `PR Introduction Evidence`) assembled by the host, with explicit statements of what each proves ("parent records prove neither introduction nor authorship") | Partly: the sections are host-assembled, and the prompt tells the model what each kind of evidence can and can't establish |

## 3. Provenance is not trust

Codex's choice to keep provenance **separate from trust** ("independent
of message role, visibility, and trust") is the useful lesson. Trust is a
policy over provenance, and the policy varies by consumer:
- To Guardian's reviewer, user messages and `AGENTS.md` can establish
  authorization; tool output can't.
- To a PR reviewer, the repository's conventions file is trusted *at the
  base SHA* and untrusted at head (`agent-design/context-files.md` §5).
- To the same reviewer, a human reviewer's thread is intent context but
  not a verdict (`agent-design/review.md` §4).

One provenance tag can serve all three only if it records *who supplied
the text*, and each consumer decides what that's worth.

## 4. What this means for Forge

Forge's nonce makes a block's boundary impossible to forge. It doesn't
record who wrote what is inside. Two additions, recorded as amendments in
[`agent-design/review.md`](./agent-design/review.md) §11:

1. **A `source` attribute on every envelope block**, next to the nonce:
   `harness`, `repo@base`, `repo@head`, `pr_author`, `commenter`,
   `ticket`, `tool`. It is set by the harness and never by the model, and
   the reviewer core states how much each source may establish. This is
   Codex's provenance list, adapted to a PR envelope.
2. **Provenance survives compaction.** If an envelope block is ever
   summarised or truncated (a long thread elided under §3's trimming),
   the replacement keeps the original block's `source`, and the elision
   marker is attributed to `harness`. That is the mistake Codex fixed in
   its second attempt.
