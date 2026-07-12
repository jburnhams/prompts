# Turn output: session titles and reasoning display

A further drill-down alongside [`agent-context-compaction.md`](./agent-context-compaction.md):
a single LLM turn in a coding agent typically produces several distinct
things at once — narration text, tool calls, and (for reasoning models)
thinking/chain-of-thought content — plus, separately, most products need
a short label for the session/task itself somewhere in a history list or
sidebar. The underlying mechanism that lets one API response carry
interleaved text/tool-call/thinking blocks is a **model-API capability**
every scaffold just consumes (Anthropic's Messages API, OpenAI's
Responses API, Gemini's `thinkingConfig` all expose this natively) — but
what scaffolds *do* with that capability varies a lot: whether reasoning
is shown by default or hidden until opted into, whether a session gets
an AI-generated title at all or just the raw first message truncated,
and how much prose narration the model is instructed to produce between
tool calls (already covered under "communication style" in
`coding-agent-approaches.md`, cross-referenced rather than repeated
here).

**Methodology note**: a first pass covered nine sources, all via
live-source investigation except two (Crush, Goose) whose title-
generation prompts were already sitting in this collection unused for
this specific question. A second pass added nine more, read from local
files already in this collection: OpenHands and Pi (title generation
only — both already had a Compaction section), and Aider plus the
leaked Cursor, Devin, Windsurf, Warp, Replit, Factory/Droid (both
topics). The richest single find from that second pass is Devin's
`<think>` tool (§2e) — a mandatory, categorically-hidden reasoning
mechanism that doesn't fit either "native API reasoning block" or
"ordinary prompted narration," the two categories this doc otherwise
treats as exhaustive. This remains a narrower survey than
`agent-tool-surfaces.md`/`agent-subagent-architectures.md`/
`agent-context-compaction.md` — it covers exactly the sources
investigated, not every source in the collection; see "Absences" for
what wasn't checked.

## Sources covered

**With confirmed title-generation and/or reasoning-display content**:
Claude Code (leaked, via `leaked/claude-code/architecture-notes.md`),
Codex CLI, OpenCode, Gemini CLI, GitHub Copilot Chat, Cline, Roo Code,
Crush, Goose, Devin (leaked, reasoning display only), Google
Antigravity (leaked — title generation absent, reasoning display
absent, but a structurally novel narration/communication-gating
mechanism found; see §3a).

**Checked, nothing found for either topic** (targeted search across
all locally-available files, no capture-gap caveat needed beyond the
usual one for prompt-only extractions): OpenHands, Pi, Aider, Windsurf
(leaked, title only — reasoning display absent, but see its
Compaction-doc entry for a related structurally novel finding), Cursor
(leaked, mostly absent — see §1c for one adjacent near-miss), Warp
(leaked), Replit (leaked, see §1c for a near-miss), Factory/Droid
(leaked), Zed (genuinely open source — title generation and reasoning
display both absent from what's captured, a capture gap rather than a
confirmed absence since this folder holds only agent prompt templates,
not session/UI code; one ordinary §3-style narration rule found —
"send a brief one- to two-sentence preamble... Skip the preamble for
trivial single reads"), GitHub Copilot CLI (leaked — title generation
and reasoning display both absent from both files, but a structurally
novel dedicated narration *tool* found; see §3), Grok Build (leaked —
title generation absent despite a real surrounding TUI product
(`~/.grok/docs/user-guide/`); reasoning display absent too, worth
flagging given xAI's public reasoning-transparency branding for
consumer Grok — plausibly both live entirely outside this system-prompt
capture; a structurally distinctive tool-call-before-narration
completion-discipline rule found instead — see §3).

---

## 1. Session/task title generation

Three genuinely different architectural answers to "how does a session
get a short label," not just wording variations.

| Approach | Sources |
|---|---|
| **A dedicated, separate cheap/fast-model LLM call**, decoupled from the main agent loop | OpenCode (`title` hidden native agent, small-model preference with fallback chain, forked into the background non-blockingly at the start of the first turn), Claude Code (three separate generators, **all** explicitly calling Haiku rather than the main Sonnet/Opus model — see §1a), Crush (`title.md`, model/trigger not confirmed), Goose (`session_name.md`, model/trigger not confirmed) |
| **No generation at all — the raw first message, formatted/truncated** | Cline (confirmed: `HistoryItem` has no title field at all; UI falls back to `metadata.title || prompt || "Untitled"`, and `metadata.title` is only ever set by an explicit user command, never an LLM), Roo Code (confirmed via direct schema read: `historyItemSchema` has no title field either — same lineage, same design answer, independently re-verified rather than assumed from the Cline connection) |
| **Folded into the main model's own turn as a tool call**, not a separate call at all | Gemini CLI — `update_topic` is a tool the primary model chooses to invoke mid-conversation with a `title`/`summary`/`strategic_intent` schema, framed as managing "narrative flow" across logical phases. The opposite architectural choice from OpenCode's/Claude Code's side-call pattern — no extra API round-trip, but the title-setting decision competes for the main model's attention and tool budget. Not confirmed to actually drive a persistent UI/sidebar title (no wiring to the CLI package's session list was found), so this may be a narrative-chaptering aid rather than a full title feature — flagged as unresolved, not asserted either way. |
| **Confirmed absence at the client; server-side behavior unknown** | Codex CLI — `task.title` (for the separate Codex Cloud product) is deserialized from the backend API response with no client-side generation code; the local TUI's session-resume list falls back to a raw server-provided preview string. Whether an LLM generates the title server-side is invisible to this repo. |
| **Not found in captured files — likely a genuine capture gap, not a design choice** | Aider, OpenHands, Pi, Cursor (leaked, all five dated prompt versions plus the tools JSON checked), Devin (leaked), Windsurf (leaked, despite the richest tool surface surveyed anywhere in this collection), Warp (leaked), Replit (leaked), Factory/Droid (leaked), GitHub Copilot CLI (leaked — despite a session-state architecture rich enough to include a per-session SQL database and a cross-session FTS5-indexed history store, §7 of `leaked/github-copilot-cli/README.md`; the product visibly shows session identifiers in its `~/.copilot/session-state/<session-id>/` path convention, so a titling/labeling layer plausibly exists outside what either capture shows), Grok Build (leaked — no title-generation tool or instruction anywhere in the 1329-line capture, despite `~/.grok/docs/user-guide/` confirming a real surrounding TUI product with its own configuration/theming docs). None of these products' prompts carry a title-generation instruction, but in every case the product itself visibly shows named sessions/conversations in its UI — the generating logic almost certainly lives in orchestration or server-side code that simply isn't part of what got captured. Distinct from the Cline/Roo Code row above, which is confirmed via a direct data-schema read, not just an absent instruction. |
| **Not investigated in this pass** | Copilot Chat, and every source outside the sources-covered list above |

### 1a. Claude Code's three separate generators — worth detailing on its own

The richest (and most fragmented) title architecture surveyed: three
independent implementations, not one mechanism reused three ways.

- `generateSessionTitle()` — 3-7-word sentence-case, JSON-schema-constrained
  output, triggered **only** for remote/background sessions started
  without an initial prompt (a code comment explains why: giving the
  session "a meaningful title on claude.ai instead of 'Background
  task'"). Ordinary interactive terminal sessions with an initial
  prompt don't appear to get an AI title at all under this path.
- `generateTitleAndBranch` — a 6-word title *plus* a git branch name in
  one call, specific to the remote/teleport flow.
- `generateSessionName` — a kebab-case 2-4-word name, used only by the
  explicit `/rename` command.

All three call Haiku specifically (never the main model) and share a
helper that tail-slices to the last 1,000 characters of conversation
rather than reading full history — titling is deliberately cheap on
every axis (model choice, context read, trigger scope) even before
accounting for the narrow, non-overlapping trigger conditions.

### 1b. Format constraints, compared

| Source | Length limit | Format notes |
|---|---|---|
| Goose | 4 words or less | Explicit anti-narration instruction ("Do NOT show your reasoning"); few-shot examples given directly |
| Crush | ≤50 characters, one line | No quotes/colons; explicitly no parsing step expected — "the entire text you return will be used as the title" |
| OpenCode | ≤50 chars per prompt, but **100-char hard cap in code** | A real prompt/code mismatch — the implementation's truncation ceiling is double what the prompt asks for |
| Claude Code | 3-7 words (main path) / 6 words (teleport) / 2-4 words kebab-case (`/rename`) | JSON-schema-constrained output for the main path; good/bad worked examples embedded in the prompt |

### 1c. A third kind of "summary" — per-turn recaps, distinct from titles and compaction summaries

Two leaked sources have a mandated end-of-turn recap of what the model
*just did* — easy to conflate with session-title generation or a
compaction summary since all three share the word "summary," but a
genuinely different thing from either: scoped to one turn's actions,
not the whole session, and produced every turn rather than once at
session start or once when context fills up.

- **Cursor's `<summary_spec>`** (2025-09-03 and CLI prompts): a
  mandated recap after substantive work, with explicit anti-heading
  rules ("Don't add headings like 'Summary:' or 'Update:'").
- **Replit's `<proposed_actions summary="...">` tag** (≤58 characters)
  and `report_progress`'s `summary` tool-parameter field — both
  per-turn action summaries, not conversation-title fields; worth
  flagging precisely so they aren't miscounted as evidence of session-
  title generation in the table above, which they aren't.

Neither of these two is a title mechanism or a compaction mechanism —
they're closer to `coding-agent-approaches.md`'s "communication style"
territory (what the model says to the user after acting), just specific
enough in format constraints to be worth distinguishing on their own.

## 2. Reasoning/thinking display

The native API mechanism (thinking/reasoning content blocks) is
consistent across sources in *shape* — every source has some config
surface controlling how much the model reasons, and some UI treatment
for whether/how that reasoning is shown. What differs sharply is the
**default visibility**.

| Default visibility | Sources |
|---|---|
| **Shown by default, collapsed** — the raw thinking text itself, not a summarized version | Claude Code (`AssistantThinkingMessage.tsx`: collapsed one-line hint by default, expandable to the model's actual unmodified thinking text; only the *most recent* thinking block stays expanded as a session scrolls, older ones auto-collapse), Copilot Chat (`ChatThinkingContentPart`, `Collapsed` mode is the VS Code-core default) |
| **Hidden by default, opt-in** | Gemini CLI (`ui.inlineThinkingMode` defaults to `"off"`), OpenCode (`showReasoningSummaries` defaults to `false`, shows only a shimmer + extracted heading when off), Codex CLI (the interactive TUI's `ReasoningSummaryCell` has a `transcript_only` flag — hidden from the *live* pane by default, shown only in the *exported transcript*; a further `hide_agent_reasoning` toggle can suppress it everywhere) |

**A lighter-weight fallback exists even when full display is off**:
Gemini CLI drives the status-row/spinner label from the current
thought's subject line regardless of the inline-display setting, so the
user always sees *some* indication of what the model is doing even with
full reasoning hidden — a middle ground between "show everything" and
"show nothing" that OpenCode's and Codex's binary toggles don't have.

### 2a. Codex's raw-vs-summary distinction is a genuine double layer

Worth calling out specifically: OpenAI's own Responses API already
returns a *summary* of reasoning, not raw chain-of-thought — that's an
API-level design choice upstream of any scaffold. Codex then draws its
**own** separate raw-vs-summary distinction on top of that: `reasoning_effort`
(how much the model reasons) and `model_reasoning_summary` (an enum —
`Auto`/`Concise`/`Detailed`/`None`) are independently configurable, and
`show_raw_agent_reasoning` is a third, separately-gated toggle for an
even-lower-level raw-content event. No other source surveyed has this
many independently configurable layers between "the model reasoned" and
"what the user actually sees."

### 2b. Redaction is sometimes the model provider's choice, not the scaffold's

Claude Code's `redacted_thinking` blocks (Anthropic's API-level
safety-redacted/encrypted reasoning content) render only as an opaque
placeholder — this is the model provider withholding content from the
scaffold entirely, not a display decision Claude Code itself makes.
Worth distinguishing from every other "hidden by default" row above,
where the scaffold *has* the content and chooses not to show it.

### 2c. A magic keyword to boost reasoning budget — one source, worth flagging for a meta-reason

Claude Code detects the literal word **"ultrathink"** typed anywhere in
a user message and boosts the thinking budget for that turn, with
dedicated UI highlighting as the user types it. (Note for anyone
reading this doc after the fact: this collection's own conversational
tooling uses the same keyword convention, which is what makes this
finding easy to verify firsthand rather than just take on faith.)

### 2d. A completed-reasoning-block micro-title — a second, smaller title-generation instance

Easy to miss, and distinct from session-title generation (§1): Copilot
Chat's collapsed thinking-block UI can carry an LLM-generated short
title once the block finishes streaming, alongside its completion
checkmark — a second, much narrower instance of "generate a short label
for this content," scoped to one reasoning block rather than a whole
session.

### 2e. Devin's `<think>` tool — a third category this doc's native-vs-prompted split doesn't capture

Every other finding in §2 is a native model-API reasoning mechanism
with a visibility *toggle* the scaffold controls. Devin's leaked
`<think>` tool is neither that nor ordinary prompted narration (§3) —
it's a **prompted tool call whose content is categorically invisible by
design**, not gated behind a setting: "Freely describe and reflect on
what you know so far... **The user will not see any of your thoughts
here**, so you can think freely." Three properties set it apart:

- **Structurally hidden, not defaulted-hidden** — nothing in the prompt
  describes a way to surface it; every other "hidden by default" row
  in the table above is a toggle on native reasoning content the
  scaffold *has* and chooses not to show (§2b makes the same
  distinction for Claude Code's provider-redacted content, for a
  different reason).
- **Mandatory at named checkpoints, not just available** — a numbered
  list of required trigger situations, one of which is a pre-completion
  verification checkpoint (see `leaked/devin/README.md`'s Self-
  verification section) — the same tool call serves double duty as
  reasoning mechanism and completion gate, a coupling not seen anywhere
  else in this survey.
- **No native-API config surface found** — no `reasoning_effort`/
  `thinking`-style parameter anywhere in the prompt, and it's visibly
  distinct from ordinary narration (which goes through a separate
  `<message_user>` command in the same prompt).

This is the same "private scratchpad, then a visible structured output"
shape `agent-context-compaction.md` documents for *compaction-specific*
internal tags elsewhere (Gemini CLI's `<scratchpad>`, Claude Code's
`<analysis>`) — Devin is the first source found in this collection
generalizing that shape to ordinary turn-by-turn reasoning across an
entire task, not just at compaction time.

**Caveat: this is specific to Devin's autonomous/background web
product, not "Devin" as a monolithic product.** A second, later-mirrored
capture — `leaked/devin/CLI Prompt.md`, "an interactive command line
agent from Cognition" — has no `<think>` tool at all: a full read found
no matching tag, tool, or hidden/visible narration split anywhere in its
306 lines. The CLI variant reasons in ordinary visible prose, the same
way most other CLI-style agents in this collection do, and its
"Verification" section (see `leaked/devin/README.md`'s CLI-variant
section) is prompted-only prose with no tool-call gate. When citing
Devin's `<think>` tool elsewhere, specify the background/web variant.

**A related near-miss, worth flagging so it isn't mistaken for a real
finding**: Cursor's `Agent Prompt 2.0.txt` contains `<reasoning>` tags,
but they're few-shot annotations inside `codebase_search` tool-usage
examples explaining *why a sample search query is good or bad* —
nothing to do with the model's own chain-of-thought or a display
mechanism. The tag name alone could mislead a keyword search; Cursor's
actual reasoning-adjacent content is ordinary prompted narration ("Use
your thinking to plan and iterate... plan your searches upfront in your
thinking"), the same narration-not-native-block pattern documented
throughout §3.

## 3. Narration: a genuinely separate mechanism from native reasoning display

Every source keeps these apart, and it's worth stating the distinction
explicitly since the vocabulary ("thinking," "reasoning") overlaps:

- **Native reasoning/thinking blocks** are a model-API-level
  mechanism, governed by the config surfaces in §2, rendered through a
  dedicated UI component with its own visibility toggle.
- **Prompted narration** — ordinary visible assistant prose the system
  prompt asks for, like "explain your intent in one sentence before
  tool calls" or general terseness/anti-preamble rules — is just
  regular assistant text with no special rendering path. Already
  substantially covered in `coding-agent-approaches.md`'s
  "communication style" material; the sources here just reconfirm the
  split. Concrete examples surfaced in this pass: Gemini CLI's "Explain
  Before Acting: Never call tools in silence... a concise, one-sentence
  explanation of your intent" paired with "No Chitchat"; Codex's "Communicate
  with the user by streaming thinking & responses, and by making &
  updating plans" (using "thinking" loosely here, unrelated to the
  `reasoning_effort` mechanism in the same prompt); OpenCode's
  inherited-per-provider narration rules (e.g. `beast.txt`'s "Always
  tell the user what you are going to do before making a tool call with
  a single concise sentence"); OpenHands's narrower, debugging-scoped
  instance ("Document your reasoning process" — confined to a
  repeated-failure TROUBLESHOOTING workflow, not a general narration
  rule); Aider's "Think step-by-step and explain the needed changes in
  a few short sentences."
- **A fourth narration mechanism, structurally distinct from all of the
  above**: Windsurf's (leaked) `toolSummary` argument is **required as
  the first parameter on every one of its 30 tools** — "Brief 2-5 word
  summary of what this tool is doing... you must specify this argument
  first over all other arguments." Every other narration instruction in
  this collection is free text the model chooses to emit in its message,
  sitting outside the tool call's own schema. Windsurf instead embeds
  the narration requirement directly into the tool call's JSON schema
  as a required field — the model cannot call a tool at all without
  populating a short action label as a structured argument. Call this
  **schema-embedded narration**: narration and the tool call collapse
  into one API-level artifact rather than two separate things (a
  narration message, then a tool call).
- **A fifth mechanism: a dedicated stateful tool that gates the
  communication channel itself**, found only in one of Google
  Antigravity's three captured prompt variants (leaked,
  `planning-mode.txt` — confirmed absent from both `Fast Prompt.txt`
  and `CLI Prompt.md`). The `task_boundary`/`notify_user` pair: while
  "in an active task," ordinary assistant messages become literally
  invisible to the user — "regular messages are invisible. You MUST
  use notify_user" — and `task_boundary`'s `TaskStatus` field is
  explicitly **prospective**, not retrospective: "should describe the
  NEXT STEPS, not the previous steps," the opposite framing from every
  other narration mechanism above (all of which narrate what the model
  is about to do or just did as ordinary prose). `task_boundary` also
  carries its own three-value `Mode` state machine (PLANNING/
  EXECUTION/VERIFICATION) baked into the tool schema — narration here
  isn't just a required field on an unrelated tool call (Windsurf's
  `toolSummary`) but a dedicated tool whose entire purpose is managing
  a structured narrative channel, with a hard rule about what other
  channels are allowed to say anything at all while it's active.

- **A sixth mechanism: a two-channel split with vendor-borrowed naming**,
  found in Amp's richer binary-string capture (`leaked/amp/amp-code.md`,
  not present in the two earlier YAML captures of the same product).
  Most modes instruct: "You have two ways of communicating with the
  users: Intermediary updates in `commentary` channel... Final responses
  in the `final` channel" — `commentary` is capped at 1-2 sentences and
  fires only on a meaningful discovery, tradeoff decision, blocker, or
  the start of a non-trivial edit ("Do not narrate routine searching,
  file reads, obvious next steps"); `final` is the concluding response.
  Structurally this is just prompted narration (§3, not a native-API
  block or a schema-embedded field) with a named-channel framing layered
  on top — but the channel names (`commentary`/`final`) are a direct
  match to OpenAI's Harmony/`gpt-oss` `analysis`/`commentary`/`final`
  taxonomy, worth flagging since Amp's own prompt states the underlying
  model here is Claude, not an OpenAI model — evidence of a scaffold
  borrowing another vendor's turn-output vocabulary rather than a
  model-native mechanism carrying over. **A grounding data point for
  this, from a leaked, differently-provenanced Codex capture**:
  `leaked/codex-supplement/gpt-5.6.md`/`codex-auto-review.md` (see
  `codex/README.md`'s Turn output section) confirm Codex itself uses
  the identical `commentary`/`final` split natively — "You have 2 ways
  of communicating with the users: Share intermediary updates in
  `commentary` channel... send a message to the `final` channel" —
  the first direct confirmation in this collection of where that
  vocabulary is native rather than borrowed, though notably this exact
  wording is absent from this collection's own live-sourced
  `codex/gpt_5_1_prompt.md`/`gpt_5_2_prompt.md`, so it's a newer
  addition even within Codex's own prompt history, not something every
  Codex capture in this collection shows.

- **A seventh mechanism: a dedicated, standalone narration *tool call*,
  distinct from both a required field on another tool (Windsurf) and a
  channel-name convention layered on ordinary prose (Amp)** — GitHub
  Copilot CLI (leaked): `report_intent` must be called "On your first
  tool-calling turn after each user message" and "Whenever you move on
  from doing one thing to another," with a hard co-occurrence
  constraint — "CRITICAL: Only ever call `report_intent` in parallel
  with other tool calls. Do NOT call it in isolation." Narration here
  is neither free prose nor a schema field on the tool doing the work;
  it's its own separate tool invocation, required to always accompany
  substantive action but forbidden from ever standing alone. A second,
  distinct rule layered on top governs the *style* of ordinary
  pre-tool-call narration with a specificity not found elsewhere in
  this survey: `preToolPreamble` bans first-person future-tense framing
  outright — "Do not use 'I will' statements like 'I will run' or 'I
  will install', instead use statements without self reference, e.g.
  'Running' or 'Installing'" — a grammatical-voice constraint on top of
  the usual "be brief" instruction.

- **An eighth mechanism: a rule constraining the *relationship* between
  narration and tool calls rather than narration's content, style, or
  channel** — Grok Build (leaked), `<task_completion_discipline>`'s
  rule 1, "Tool-call first, narration second": "Any past-tense or
  present-continuous prose describing an action ('I launched...', 'I'm
  now reading...', 'The subagent is working on...') MUST be paired with
  the corresponding tool call in the same assistant response. If you
  end a turn with such a sentence but no tool call, the action did not
  happen." Every mechanism above governs *whether/how much* to narrate;
  this one instead targets a specific failure mode — a model narrating
  an action in the past or present-continuous tense without the tool
  call that would actually perform it — and states outright that a
  narrated-but-uncalled action simply didn't happen. Closest existing
  analog is GitHub Copilot CLI's `report_intent` co-occurrence
  constraint (seventh mechanism, above), but that rule requires a
  *specific tool* to accompany action; Grok's rule instead constrains
  ordinary free-text narration's tense/timing relative to *any* tool
  call, with no dedicated narration tool of its own.

A model could in principle narrate heavily in prose while showing no
native reasoning content at all, or vice versa — the two axes are
independently configured in every source checked.

**A distinct, ninth-ish axis worth naming separately rather than folding
into narration: swappable *personality/tone*, not narration frequency
or channel.** A leaked, differently-provenanced Codex capture
(`leaked/codex-supplement/` — see that folder's own README and
`codex/README.md`'s Turn output section) reveals a `{{ personality }}`
template variable filled from named persona documents
(`personality_friendly.md`, `personality_pragmatic.md`), each
specifying not just tone but a distinct *escalation style* — how the
persona surfaces disagreement or risk to the user. This is orthogonal
to every mechanism above: narration mechanisms (§3) govern *when* and
*how often* the model speaks; native reasoning display (§2) governs
whether *thinking* is shown; this instead governs *which voice* speaks,
selected per model variant rather than per turn. No equivalent
swappable-persona-template finding exists anywhere else in this
collection's turn-output research — the closest analogs are Codex's own
single hardcoded "concise, direct, and friendly" personality paragraph
(one fixed point, not a template) and Amp's eleven launch-time identity
modes documented in `agent-subagent-architectures.md` (mode selection
at the *orchestrator-identity* level, not a `{{ personality }}` fill-in
layered on one shared prompt skeleton) — worth reading as a related but
structurally distinct axis, not the same finding restated.

## 4. Absences and unresolved findings

- **Gemini CLI's `update_topic` tool** is confirmed to exist and be
  callable by the model, but not confirmed to actually populate any
  persistent, user-visible session title — flagged as unresolved (§1)
  rather than counted as a confirmed title mechanism.
- **Codex Cloud's server-side title generation** is opaque from this
  repo's vantage point — the client-side absence is confirmed, but
  what (if anything) generates `task.title` on the backend is unknown.
- **Copilot Chat's title-generation behavior** (as opposed to its
  reasoning-display behavior, which is covered in depth) wasn't
  investigated in this pass.
- **Windsurf's compaction-adjacent `<memory_system>` finding**
  (persistent-memory externalization, `trajectory_search`) is
  documented in `agent-context-compaction.md`, not repeated here — it
  bears on recovery philosophy more than turn-output proper, even
  though it was surfaced during this doc's research pass.
- **Every "not found in captured files" entry in §1's title table is a
  capture-gap claim, not a confirmed design decision** — worth
  repeating here since it's easy to lose the distinction reading the
  table in isolation. Aider, OpenHands, and Pi's absences rest on
  reading every locally-available prompt file in full; the six leaked
  sources' absences rest on reading whatever got extracted, which is
  frequently partial by nature of how leaks happen.
- **Every source outside the ones listed in "Sources covered"** — the
  rest of this collection's ~35+ sources — hasn't been checked for
  either title generation or reasoning-display conventions at all.
  Given how often "not checked" has turned out to mean "actually quite
  sophisticated" elsewhere in this collection (Codex's sub-agents,
  OpenCode's Task tool, OpenHands's whole delegation system, Roo Code's
  Orchestrator mode), treat the absence of a source from this doc as
  exactly that — not checked — not as evidence the mechanism doesn't
  exist there.

---

## Design takeaways

- **Title generation splits cleanly into "pay for an extra LLM call" vs.
  "don't bother," and the two Cline-lineage sources (Cline, Roo Code)
  are the only confirmed "don't bother" cases** — both independently
  re-verified against their actual data schemas rather than assumed
  from the shared codebase history. Every other source with a confirmed
  mechanism pays for a separate (usually explicitly cheap-model) call.
- **Claude Code's three-generator fragmentation is a real design smell
  worth naming, not just a curiosity**: three separate prompts, three
  separate trigger conditions, one of them (the main session-title path)
  scoped so narrowly (remote/background sessions with no initial
  prompt) that ordinary interactive terminal sessions likely get no AI
  title at all under that specific mechanism. Contrast with OpenCode's
  single `title` agent triggered uniformly at the start of every first
  turn — a cleaner, more consistent design for the same underlying need.
- **Reasoning-display defaults split roughly down the middle, and the
  split looks like a real product-philosophy difference, not
  inconsistent implementation**: Claude Code and Copilot Chat default
  to showing collapsed-but-real reasoning; Gemini CLI, OpenCode, and
  Codex's interactive pane default to hiding it entirely. Both are
  defensible — showing it by default treats reasoning as useful
  debugging/trust-building signal; hiding it by default treats it as
  noise the average user doesn't want cluttering a terminal session.
- **Codex's layered raw/summary/effort configuration (§2a) is the most
  granular reasoning-visibility control surveyed**, mirroring the same
  "infrastructure over instruction" pattern found distinguishing Codex's
  sub-agent safety mechanisms in `agent-subagent-architectures.md` —
  multiple independent, code-level toggles rather than one blanket
  show/hide switch.
- **The "ultrathink" keyword convention (§2c) is a good reminder that
  this collection's own research process is itself running inside one
  of the systems it studies** — a rare case in this whole project where
  a documented pattern from another agent can be directly, immediately
  verified by the reader rather than taken on the strength of a
  research pass alone.
- **Narration and native reasoning display are consistently kept
  separate across every source checked**, despite overlapping
  vocabulary — a useful disambiguation for anyone reading prompt text
  elsewhere in this collection and seeing the word "thinking" used
  loosely (e.g. Codex's "streaming thinking & responses" line, which
  has nothing to do with its own `reasoning_effort` config a few
  sections later in the same prompt).
- **Devin's `<think>` tool (§2e) breaks the doc's own native-vs-prompted
  binary**, and is the single richest finding from this doc's second
  research pass: a prompted tool call that's categorically hidden by
  design (not a visibility toggle on native content), mandatory at
  named checkpoints, and doubles as a self-verification gate. Worth
  treating as a reminder that a two-category typology built from nine
  sources was always going to be incomplete — the tenth-plus source
  checked immediately produced something that didn't fit either bucket.
- **The "no title generation confirmed" pile grew from two sources
  (Cline, Roo Code) to ten** in the second pass, but the *reason*
  differs in a way worth keeping straight: Cline's and Roo Code's
  absence is schema-confirmed (no title field exists in the data
  model); the other eight (Aider, OpenHands, Pi, and five of the six
  leaked sources) are "not found in what this collection captured,"
  a meaningfully weaker claim given that most of those products'
  actual UIs visibly show named sessions. Treating all ten as
  equivalent "don't bother" design choices would overstate what's
  actually confirmed.
- **Windsurf's schema-embedded `toolSummary` (§3) suggests the
  "narration vs. tool call" framing this doc used going in was itself a
  simplification, and GitHub Copilot CLI's `report_intent` (§3) confirms
  it's a real spectrum, not a one-off**: most sources keep the two as
  genuinely separate artifacts (a narration message, then a tool call);
  Windsurf collapses them into a single required tool-schema field;
  Copilot CLI instead makes narration its *own* tool call, distinct from
  the work it narrates but mandated to always co-occur with it. Three
  different answers to "where in the API surface does the narration
  requirement live" — bolted onto an unrelated tool's schema, expressed
  as ordinary free text, or promoted to a tool of its own — none of them
  simply "how much narration to require," which is the axis this doc's
  typology started from.
- **Three genuinely different things all get called "summary" across
  this collection** (§1c): a session title (once per session), a
  compaction summary (once per context-fill event), and a per-turn
  action recap (every turn, found in Cursor's and Replit's leaked
  prompts). None of the three sources with a per-turn recap mechanism
  also has confirmed title generation — worth noting as a place where
  a keyword search for "summary" or "title" could easily produce a
  false positive if the three concepts aren't kept apart deliberately,
  exactly the confusion this section exists to prevent.
