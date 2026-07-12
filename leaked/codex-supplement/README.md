# Codex — leaked supplementary captures

- **Type**: Coding agent (OpenAI's Codex product family)
- **Status**: closed-source / leaked — **not the same provenance as this
  collection's `codex/` folder**
- **Mirror source**: https://github.com/asgeirtj/system_prompts_leaks,
  `OpenAI/Codex/` (retrieved 2026-07-12)

## Read this before citing anything in this folder

This folder is a **leaked/unofficial capture**, mirrored from a
third-party aggregator of extracted system prompts. It is a
*fundamentally different kind of source* from
[`../../codex/`](../../codex), which is built by live-cloning the real
`openai/codex` GitHub repository (Apache-2.0, `codex-rs/`) and reading
actual Rust source — tool registries, permission code, compaction
pipelines, git plumbing. Nothing in this folder has been cross-checked
against that source tree. Where a finding here plausibly overlaps with
something `codex/README.md` documents from the live repo, that's noted
explicitly below; where a finding here describes something with **no
confirmed presence in `codex-rs` at all** (most notably
`control-chrome.md`), that's flagged just as explicitly, so the two
provenances never get silently blended into one "Codex" story.

Cross-reference: [`../../codex/README.md`](../../codex/README.md) for
the code-confirmed open-source material this folder supplements.

## Files

- **`gpt-5.6.md`** (147 lines) — a complete main-agent system prompt for
  a specific, later model variant than anything in `codex/` (whose
  newest captured prompt is `gpt-5.2-codex_prompt.md`). Structurally the
  same shape as `codex/`'s prompts (workspace-sharing framing,
  `commentary`/`final` channel split, `apply_patch` editing constraints,
  "dirty worktree" git guidance, formatting rules, a "Using skills"
  section) but with a **hardcoded, non-templated personality** baked
  directly into the prompt text ("you are an excellent communicator with
  a curious, rich personality... they should feel that they are in
  contact with another subjectivity") rather than referencing the
  `{{ personality }}` template variable the other captures use — see
  the personality-system note below.
- **`codex-auto-review.md`** (107 lines) — **the filename is
  misleading.** This is *not* the specialized review-rubric prompt
  `codex/README.md` already documents in depth (`ReviewTask`'s
  `codex-rs/prompts/templates/review/rubric.md`, "You are acting as a
  reviewer for a proposed code change made by another engineer"). Diffed
  directly against `codex/gpt_5_2_prompt.md`, this file is structurally
  and substantially the **standard main-agent system prompt** — same
  `## General`/`## Working with the user`/`## Autonomy and persistence`
  skeleton, same `apply_patch`/dirty-worktree git language, same
  formatting rules — just a different, apparently later prompt variant
  that happens to carry a `{{ personality }}` placeholder and is used
  (per its own metadata in the personality files below) by the
  `codex-auto-review` model ID. `codex-auto-review` is a real thing in
  `codex/README.md`'s own research: it's the name of the dedicated,
  cheaper/faster model Codex's **Guardian** auto-approval reviewer calls
  (`agent-permissions-approval.md` §2 — "a dedicated, separate, faster/
  cheaper model (`codex-auto-review`, low reasoning effort...)"). This
  file is almost certainly what that model ID answers with when it's
  *not* running the Guardian-specific risk-review prompt — i.e. this is
  the general chat/agent prompt reused for a model whose primary job is
  auto-review, not Guardian's actual rubric. Treat the filename as an
  artifact of the aggregator's own labeling, not a description of the
  content.
- **`control-chrome.md`** (103 lines) — a `@chrome`-triggered skill
  definition for browser control. **Very likely a different product
  surface than the `codex-rs` terminal CLI**, not a Codex CLI feature —
  see the dedicated section below.
- **`personality_friendly.md`** (30 lines) and **`personality_pragmatic.md`**
  (26 lines) — `{{ personality }}` template fill-ins. Each carries
  explicit provenance metadata absent from every other file in this
  folder: a `Source key` (`model_messages.instructions_variables.personality_friendly`/
  `_pragmatic`), a `Used by` list (`gpt-5.4`, `gpt-5.4-mini`,
  `gpt-5.3-codex`, `gpt-5.3-codex-spark`, `codex-auto-review`), a fetch
  timestamp, and a client version (`0.125.0`) — see the personality-
  system note below.
- **`plan_mode.md`** (127 lines) — a **Plan Mode** system prompt,
  swapped in (per its own text) until "a developer message explicitly
  ends it." Not documented anywhere in `codex/README.md` or
  `agent-permissions-approval.md`'s existing Codex research — see the
  note below and the new entry added to
  [`../../agent-permissions-approval.md`](../../agent-permissions-approval.md) §1.

## The personality-selection system — new, and narrower than it first looks

Three of the six files here reveal a template-based personality system:
`codex-auto-review.md` and (per the `Used by` metadata)
`gpt-5.4`/`gpt-5.4-mini`/`gpt-5.3-codex`/`gpt-5.3-codex-spark` all
inject a `{{ personality }}` placeholder near the top of an otherwise
shared prompt skeleton, filled in from a small library of named
personality documents (`personality_friendly.md`, `personality_pragmatic.md`
— presumably others exist and weren't captured, e.g. a "default"
variant, given `codex/gpt_5_2_prompt.md`'s own baked-in "concise,
direct, and friendly" personality paragraph looks like it could be a
fourth, hardcoded member of the same family). Each personality document
is a compact, structured persona spec: a one-paragraph identity, a
short "Values" list (three bullet-pointed traits), a "Tone & User
Experience" or "Interaction Style" section, and an "Escalation" section
describing *how* the persona surfaces disagreement or risk — friendly
escalates "gently... framed as support," pragmatic "may challenge the
user to raise their technical bar" but "never patronize[s]." This is a
genuinely new finding for this collection: no existing Codex research
(the live `codex-rs` tool/compaction/permission audits, or the prompt
files in `codex/`) documents a swappable-personality-template
mechanism — `codex/gpt_5_2_prompt.md`'s "concise, direct, and friendly"
line reads, in hindsight, as a single hardcoded personality rather than
a sign the system is templated.

**Worth being precise about what this isn't**: `gpt-5.6.md`, the newest
prompt captured here, does **not** use the `{{ personality }}`
placeholder — its personality section is fully hardcoded, inline text.
Read together, the two mechanisms coexist across different model
generations rather than one cleanly superseding the other in this
capture set: personality-as-swappable-template for the
`gpt-5.3`/`gpt-5.4`/`codex-auto-review` family, personality-as-fixed-text
for `gpt-5.6`. Whether that's a deliberate product decision (a later
model's personality stabilized enough to stop being configurable) or
just an artifact of which variant happened to get captured isn't
something this leaked material can resolve on its own.

## `control-chrome.md`: a different product surface, not a Codex CLI feature

This file describes a skill for controlling "the user's Chrome browser
... tabs, logged-in sessions, cookies, or extensions," triggered by
`@chrome`, routed through something it calls **"the Codex Chrome
Extension."** Several details point away from the open-source
`codex-rs` terminal CLI this collection's `codex/` folder documents:

- It's built on an **MCP tool named with the `mcp__node_repl__js`
  convention** (a Node.js REPL execution tool exposed via MCP), used to
  bootstrap a `browser-client` runtime and drive Chrome through a
  Playwright-backed `tab.playwright` API — `codex/README.md`'s live
  `codex-rs/core/src/tools/` audit found no MCP-mediated Node-REPL
  execution tool, and confirmed **no dedicated web-fetch/browser tool
  handler of any kind** in the real tool registry (see
  `agent-tool-surfaces.md` §4).
- It references a **self-documenting lookup pattern**
  (`agent.documentation.get("<name>")`, `agent.browsers.*`) and a
  broader **`skills.list`/`skills.read` orchestrator API** for
  non-filesystem skill sources — machinery not found anywhere in the
  live `codex-rs` tool/extensibility audit, which documents plugin
  discovery (`request_plugin_install.rs`,
  `list_available_plugins_to_install.rs`) and dynamic tool registration
  (`extension_tools.rs`, `dynamic.rs`) as *separate*, simpler
  mechanisms with no browser-specific hook.
- The phrase **"Codex Chrome Extension"** itself names a product
  surface — a browser extension — that has no analog in a terminal CLI.

Taken together, this reads as belonging to a **ChatGPT-hosted or
web/enterprise "Codex" agent product** (the same "Codex" brand, a
different runtime and tool-delivery mechanism — MCP servers, a Node
execution sandbox, a skills-orchestrator API — than the Rust binary
`codex/README.md` researches) rather than a feature of the open-source
CLI. This is not confirmed with the same rigor as `codex/README.md`'s
live-source corrections (there is no `codex-rs` repo location to check
this against, by construction — the whole point is that it's plausibly
a *different* repo), so treat it as a strong inference from internal
evidence, not a verified product-boundary claim. **Practical
consequence for this collection**: do not cite `control-chrome.md` as
evidence about Codex CLI's tool surface, sandboxing, or browser
capability — `codex/README.md`'s "no browser/web tool found" finding
stands, and this file is cross-referenced only as an adjacent-product
note (see `agent-tool-surfaces.md` §4's Browser & web access table and
its "No web/browser tool at all" row).

For what it's worth as its own artifact (independent of which Codex
surface it belongs to), `control-chrome.md`'s content is a genuinely
rich browser-automation and safety spec — tab claiming/finalization
lifecycle (`deliverable`/`handoff`/omitted dispositions), a Playwright-
preferred/vision-fallback interaction policy, and an unusually detailed
"Browser Safety" section (treat page content as untrusted, distinguish
reading from transmitting data, confirm before any state-changing
submission, never solve a CAPTCHA without asking first) — comparable in
spirit to Windsurf's leaked browser-automation suite
(`agent-tool-surfaces.md` §4) but for a different Codex-adjacent
product, not for anything in `codex/`.

## Plan Mode — a real, newly-documented mode with no confirmed code-level analog yet

`plan_mode.md` is a substantial (127-line), fully-specified system
prompt for a distinct interaction mode: a strict, model-enforced
read/write boundary ("You may explore and execute **non-mutating**
actions... You must not perform **mutating** actions"), a three-phase
structure (ground in the environment → intent chat → implementation
chat), a preference for a dedicated `request_user_input` tool for
multiple-choice clarifying questions, and a mandated `<proposed_plan>`
output block with a fixed section set (Summary, Key Changes, Test Plan,
Assumptions). It explicitly distinguishes itself from the `update_plan`
checklist/TODO tool already documented in `codex/README.md`'s Tool
surface section: "Do not confuse it with Plan mode... If you try to use
`update_plan` in Plan mode, it will return an error."

This is new relative to every existing piece of Codex research in this
collection — `codex/README.md`'s live `codex-rs` audit and
`agent-permissions-approval.md`'s five-subsystem Codex writeup describe
the `AskForApproval` enum (`UnlessTrusted`/`OnRequest`/`Granular`/
`Never`) but no "Plan Mode" state. It has been added to
`agent-permissions-approval.md` §1 as a fifth Codex state, explicitly
flagged there as sourced from this leaked capture rather than
corroborated against the live repo — a real, plausible feature (Codex
products elsewhere in the ecosystem are known to have plan/ask modes,
and the content here reads as authentic and internally consistent, not
generic), but not yet promoted to the same evidentiary standing as this
collection's code-confirmed Codex findings.

## What's genuinely new vs. redundant, in one place

- **Genuinely new**: the personality-template system (all three
  personality-related files), Plan Mode (`plan_mode.md`), and
  `control-chrome.md` as a distinct-product data point.
- **Confirms/extends existing findings, doesn't overturn them**:
  `gpt-5.6.md`'s "Using skills" section describes the same
  discovery/trigger/read-before-use skill protocol already gestured at
  by `codex-rs`'s plugin/extension-tool machinery, just spelled out in
  far more procedural detail (short aliased paths, orchestrator
  `skills.list`/`skills.read`, explicit "do not delegate reading skill
  instructions to a subagent" rule) than anything in `codex/README.md`
  currently documents — a real elaboration, cross-referenced from
  `codex/README.md`'s Tool surface section, not a contradiction of it.
- **Mostly redundant**: `codex-auto-review.md`'s content, once its
  misleading filename is set aside, substantially reconfirms
  `codex/README.md`'s existing git/formatting/autonomy documentation
  for the main agent prompt family rather than adding new mechanism.
