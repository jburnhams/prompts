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

**Methodology note**: nine sources are covered, all via live-source
investigation except two (Crush, Goose) whose title-generation prompts
were already sitting in this collection unused for this specific
question. This is a narrower survey than `agent-tool-surfaces.md`/
`agent-subagent-architectures.md`/`agent-context-compaction.md` — it
covers exactly the sources investigated, not every source in the
collection; see "Absences" for what wasn't checked.

## Sources covered

Claude Code (leaked, via `leaked/claude-code/architecture-notes.md`),
Codex CLI, OpenCode, Gemini CLI, GitHub Copilot Chat, Cline, Roo Code,
Crush, Goose.

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
| **Not investigated in this pass** | Copilot Chat, and every source outside the nine covered here |

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
  a single concise sentence").

A model could in principle narrate heavily in prose while showing no
native reasoning content at all, or vice versa — the two axes are
independently configured in every source checked.

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
- **Every source outside these nine** — the rest of this collection's
  ~35+ sources — hasn't been checked for either title generation or
  reasoning-display conventions at all. Given how often "not checked"
  has turned out to mean "actually quite sophisticated" elsewhere in
  this collection (Codex's sub-agents, OpenCode's Task tool, OpenHands's
  whole delegation system, Roo Code's Orchestrator mode), treat the
  absence of a source from this doc as exactly that — not checked — not
  as evidence the mechanism doesn't exist there.

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
