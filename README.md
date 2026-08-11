# prompts

A collection of system prompts from real-world AI products/agents, for
analysis and comparison.

## Structure

Prompts are organized in folders by source (the tool/project they come from).
Each folder has its own `README.md` noting the license, where the files were
retrieved from (branch/tag + date), and what each file is.

**[→ `sources.md`](./sources.md)** — where the *code* behind those prompts
was read from: repo URLs, the specific paths that matter (they move — every
repo here has been restructured at least once), the commits read, and the
sparse-clone recipe for re-fetching any of them in a couple of minutes.
Start there before re-deriving where a harness keeps its tool definitions.

This is a first pass focused on **open-source coding and code-review
agents**, where the system prompt ships directly in the project's public
source code (as opposed to being reverse-engineered/leaked from a closed
product).

**[→ `agent-archetypes.md`](./agent-archetypes.md)** — start here for the
30,000-foot view: the ~35 agents/tools/skills/bots in this collection
sorted into six recognizable architectural archetypes (general-purpose
interactive assistant, benchmark-driven issue solver, minimalist
scaffold, multi-role pipeline, PR-review specialist, app/UI generator),
plus the two axes that explain most of the variance between them.

**[→ `code-review-approaches.md`](./code-review-approaches.md)** —
a synthesized comparison of every code/PR-review-specific source in this
collection, stage by stage (system prompt, diff format, context,
filtering, output format, delivery, safety), with links back to each
source for detail.

**[→ `coding-agent-approaches.md`](./coding-agent-approaches.md)** — the
companion doc, one level down: a comparison of the *full* coding-agent
system prompts themselves (identity, per-model variants, environment
injection, tool-use policy, code-editing format, planning, project-memory
files, safety, communication style), with particular focus on OpenHands,
OpenCode, Codex, Claude Code, and Cursor.

**[→ `agent-tool-surfaces.md`](./agent-tool-surfaces.md)** — a further
drill-down focused specifically on *what tools each scaffold actually
gives the model*: shell type/persistence, search tooling, code execution,
browser/web access, multimodal handling, async/background execution,
persistent memory & deployment, sandbox/isolation, and extensibility
(MCP/skills/dynamic tool sets), across all 25 sources with a documented
tool surface.

**[→ `agent-tool-implementations.md`](./agent-tool-implementations.md)** —
the layer below that one, and the first doc here grounded in **source code
rather than prompt text** (fetch paths and commits in
[`sources.md`](./sources.md)): for the universal primitives — read, list,
search, edit, write, run — how they are actually built across nine
harnesses. Covers the three-consumer structure of a tool (model text /
harness metadata / human rendering) that every mature implementation
converges on; tool-count granularity from Goose's five tools to Manus's 29,
with the same capability shown at three granularities (LSP: 1 vs 5 vs 8
tools) and the rule that predicts most of the field; parameter styles
including Claude Code's `Grep` taking JSON fields literally named `-A`/`-B`/
`-C` and Codex shipping `apply_patch` as a Lark-grammar freeform tool with
"do not wrap the patch in JSON" in its description; the advertise-strict/
accept-tolerant pattern (Cline parses `read_files` against a 13-branch
union behind one advertised shape); output formats (raw text for prose,
fields for facts, XML tags for framing) and why nobody JSON-encodes a file
body; a numeric comparison of every source's read/search/output caps, plus
the measured Claude Code experiment showing a hard error beats a truncated
success; errors written as instructions; the side channels attached to tool
results (JIT conventions injection, unchanged-file dedup, read-before-edit
gates); and the tool set as a runtime artifact — per-model-family schemas
(Gemini CLI), model-based tool routing (Cline), and deferred loading behind
a search tool (Claude Code, Codex). A later pass went one level deeper on
the single most-called tool, adding the first **vendor engineering
write-up** to this collection's source types (Command Code's read-tool
teardown, benchmarked across ten harnesses): the **three ceilings** a read
tool needs and the file shape each one is the only defence against;
recovery text as a closed catalogue typed as *notes rather than errors*;
the failures a model **provably cannot diagnose** (macOS's NFD-decomposed
filenames, narrow no-break spaces, curly-quote renames — byte-different,
pixel-identical) and the rule that sorts tool-side retry from model-side
suggestion; truncation claims you cannot honestly make yet at a stream
chunk boundary; a **production deadlock** in which a per-line clamp, a
read-before-write ledger and an unchanged-file dedup — each correct alone,
none of them calling another — lock a model into an infinite re-read loop,
and the "consume-on-hit" cache rule that stops a dedup stub pointing into
context that compaction has since eaten; and, as a method note, what it
means that the write-up's live probe of Claude Code and this collection's
reading of its leaked source **disagree** on two features (source-reading
establishes what was built; probing establishes what is switched on).
A further pass went one layer lower still, to the **wire format** — the
part below "what the schema says," added with [`omp/`](./omp) and its
author's two write-ups: how a tools array is actually rendered into the
prompt as text, why a scalar parameter is delimiter-matched and free
while an array or object forces escaped JSON into the same slot (which
puts a measured cost on the batch-`Read` shape this collection's own
design adopted), a harness that ships **eleven per-model-family tool-call
dialects** and can strip native structured tool calls altogether, and the
first benchmarked challenger to this doc's "`cat -n` won, unanimously"
finding — a line-anchored edit format whose per-file content hash is an
anchor the model *cites* instead of source text it must *reproduce*,
measured across 16 models, winning on 14 and losing on 2. The same pass
added the field's only published **tool-call repair catalogue** — the four
container/nullability malformations that reportedly account for ~90% of
"this open model can't do tool calls," the order they must be applied in
(parse a JSON-string array *before* wrapping a bare string, or
`'["a","b"]'` becomes `['["a","b"]']`: schema-valid, meaning lost), and
the architectural finding that repairs must run **after** validation
fails rather than as a pre-pass, because a pre-pass rewrites well-formed
inputs that merely look malformed — which is how a file write whose
content was legitimately JSON-shaped got silently corrupted. Two
independent teams, one open and one closed, land on the same thesis from
opposite directions: most of what reads as a model capability gap is
contract design. A follow-up pass then found the one thing all of that was
missing — **somebody actually ran the experiment**. Nous Research's Hermes
built an A/B eval for read-tool engineering choices, explicitly because the
vendor scorecard above got its column wrong, and its
`evals/readtool/` is the most rigorous artifact in this collection: nine
deterministic hostile fixtures, accuracy *and* cost metrics, three reps
with a stated ±3% noise floor, a frontier model and a strong open model on
purpose, and a per-feature ship/no-ship log with the caveats that
invalidate its own comparisons recorded next to the verdicts. It also found
a real gap in the blocklist reasoning: a name blocklist cannot see a FIFO
sitting inside the working tree, and the `stat`-based guard that can is
worth −79% tokens and −81% wall clock on that fixture with accuracy
unchanged — the shape of defect that survives in shipped harnesses
precisely because nothing fails.

**[→ `agent-tool-call-dialects.md`](./agent-tool-call-dialects.md)** — the
layer below *that* one, and the lowest in this collection: the **wire
format** under "the model called a tool." What crosses the wire is text —
a grammar rendered into the prompt by the provider's chat template and
scanned back out by a parser — which makes the tool channel a variable you
control on any model where you own the prompt. Covers why your schema is
documentation rather than enforcement; the five ways a call gets delimited
and why the tokenizer's `special: true`/`false` flag (Qwen3 and GLM
register their tool markers as *non*-special **so they survive decoding**
and a regex parser can find them) predicts parser behaviour; argument
encoding from GLM's `<arg_key>`/`<arg_value>` pairs that need no escaping
at all, through Gemma 4's string-delimiter *token*, to the JSON-blob
families where every structured parameter is a parse failure waiting to
happen; how tools get advertised (a `<tools>` block, a TypeScript
namespace, or prose); results correlated by ID versus by position, the
three different envelope roles a tool result can take, and the dialect
with **no error channel at all**, where prose is the only way an error can
be seen; and what implementing one costs — renderer *and* a deliberately
wider scanner, ID minting, streaming partial delimiters, history
conversion both ways. The practical answer to "how do you give tools to a
model with no function-calling support," and a caution that prompt-only
formats leak: Gemini's Pythonic syntax was reverse-engineered from
`MALFORMED_FUNCTION_CALL` bug reports.

**[→ `agent-subagent-architectures.md`](./agent-subagent-architectures.md)**
— a companion drill-down on one specific tool-surface capability: when
and how a scaffold spawns another agent. Covers delegation triggers,
calling protocol (stateless tool-call vs. persistent addressable child
vs. shared-conversation handoff vs. async background process vs.
multi-party orchestration topologies), whether the sub-agent gets its
own system prompt, turn/output bounding, concurrency and write-safety,
and recursion limits, across the 21 sources with a documented sub-agent
mechanism — including Microsoft Agent Framework's five named
orchestration patterns (Sequential/Concurrent/Handoff/GroupChat/
Magentic), a structurally different N-party design found nowhere else
in the collection.

**[→ `agent-context-compaction.md`](./agent-context-compaction.md)** —
a further drill-down on how a scaffold survives running out of context
mid-task, across 21 sources: trigger model (proactive token-threshold
checks vs. reactive-on-API-error vs. manual commands vs. Cline's
model-proposes/user-approves third shape), prompt shape (free text vs.
structured templates vs. XML), single-mechanism vs. layered-pipeline
vs. pluggable-strategy vs. Cline's multiple-uncoordinated-mechanisms
architecture, incremental/anchored vs. from-scratch summarization,
recovery philosophy (is the discarded detail actually gone, down to
Cline's plain-deletion-no-summary floor and Windsurf's "externalize
before compaction happens" strategy via a persistent memory tool),
prompt-cache interaction, sub-agent isolation, and — compared in
detail — actual numeric token budgets (reserved buffers, summary
output caps, retention thresholds) across the sources that expose them.
A later pass added §9, which supplies the one thing the rest of the doc
had to take on faith — **a measurement of what compaction destroys**.
On a SQuAD-based benchmark against a verbatim-text ceiling, prose
compaction is a total loss of extractable fact on two of four frontier
models (Gemini answered `UNREADABLE` 240 times out of 240, Opus 209):
"the summaries preserve what you were doing, not what you knew." The
same source proposes a branch that is not on this doc's typology at all
— rendering the context into dense pixel-font bitmaps and carrying it as
*images*, which is lossless by construction and moves the cost from
fidelity to a decode tax — with a legibility cliff at 35–40 px² per
character and a vision-patch-alignment trick that drives decode
confidence from 0.39 to 1.00.

**[→ `agent-turn-output.md`](./agent-turn-output.md)** — a further
drill-down on what a single LLM turn actually produces, across 22
sources: session/task title generation (a dedicated cheap-model side
call vs. no generation at all vs. folded into the main model's own tool
calls — ten sources now confirmed or likely "don't bother," though only
Cline and Roo Code are schema-confirmed rather than just
capture-gapped), reasoning/thinking display defaults
(shown-collapsed-by-default vs. hidden-until-opted-in), Codex's
unusually layered raw/summary/effort reasoning-visibility controls,
Devin's `<think>` tool (a mandatory, categorically-hidden reasoning
mechanism that fits neither "native API block" nor "prompted
narration"), Windsurf's schema-embedded per-tool-call narration
requirement, and the recurring but easy-to-conflate distinction between
native model-API reasoning blocks and ordinary prompted narration text.
A later pass added §3a, which re-sorts the same sources by *what
narration contains* (the what vs. the why) and *how long it survives*
(dies with the transcript vs. durable artifact) — surfacing Gemini
CLI's `update_topic` as the best-specified why-focused mechanism
anywhere here (rate-limited to "every 3 to 10 turns," excluded from
trivial work, and triggered on "an unexpected event... that requires a
strategic detour"), Codex's matching `update_plan` `explanation`
requirement on mid-task plan changes, and Google Antigravity's four
durable markdown artifacts as the only case of the run narrative being
a file rather than chat prose. The same pass resolved this doc's
standing open question about `update_topic`: it is a progress-narration
channel, not a session-title generator.

**[→ `agent-self-verification.md`](./agent-self-verification.md)** — a
further drill-down on how (and whether) a scaffold checks its own work
before calling a task done, distinct from `code-review-approaches.md`
(which is about reviewing *someone else's* PR). Covers: the shared
"reproduce bug → fix → verify → edge cases → submit" workflow template
running through nearly every SWE-bench-lineage agent (SWE-agent,
mini-swe-agent, Live-SWE-agent, Augment SWE-bench Agent), deterministic
non-LLM completion gates (Roo Code's `AttemptCompletionTool`, SWE-agent's
templated `review_on_submit_m`), separate-LLM-call judge/reviewer
patterns and what happens on a failed verdict (SWE-agent's
`ScoreRetryLoop`/`ChooserRetryLoop`, Augment's o1 ensembler, Microsoft
Agent Framework's `with_judge()` nudge-not-restart pattern), the
"review-as-a-general-tool" conflation trap (Codex's `ReviewTask` and
OpenCode's `/review` command are general diff-review utilities, not
self-checks), hook-based user-configured gates (Claude Code's `Stop`
hooks — the one such mechanism actually shipped externally, alongside a
leaked internal-only adversarial verification subagent), and Jules's
per-action mandatory verification, hidden pre-commit tool, and
Playwright-screenshot-as-proof frontend verification — the most
granular self-review discipline found anywhere in this collection. A
second research pass roughly doubled the source count (20 sources
covered in depth) and surfaced two more patterns not in the original
typology: verification authority handed to the *human user* instead of
the model (Replit's automated-evidence-plus-confirmation tools, Warp's
inverted "ask before verifying" default) and "prompt-simulated"
gates that borrow deterministic-gate rhetoric — numbered steps, "no
exceptions" language — without any confirmed code-level enforcement
(Copilot Chat's `vscModelPrompts.tsx` "iron law" block, Factory/Droid's
PR-draft-state gate).

**[→ `agent-permissions-approval.md`](./agent-permissions-approval.md)**
— a further drill-down on how a scaffold decides whether an action
needs a human first, across 21 sources. This turned out to be the
richest single doc in the whole collection: Codex CLI's permission
architecture is not one mechanism but five cooperating subsystems
(a static command-safety classifier, a Starlark rule-engine DSL, an
LLM-based "Guardian" auto-reviewer running a separate cheaper/faster
model with its own risk taxonomy, a real OS-level sandbox on three
platforms, and a network-egress proxy), and Gemini CLI's "TOML policy
engine" turned out to include an opt-in second LLM ("Conseca") that
generates a least-privilege policy for the user's request and then
re-judges every subsequent tool call against it — an entire separate
model acting as judge over the first model's actions, layered on top
of (not replacing) a 5-tier admin/user/workspace/extension/default
priority engine. Claude Code's own leaked permission system has a
third, independently-converged instance of the same idea —
`yoloClassifier.ts`, a two-pass fast/slow LLM gate for its internal-only
`auto` mode — confirmed real via Anthropic's own public hooks docs but
also confirmed **ant-gated** (excluded from the externally-available
mode set), the same internal-only pattern this collection's
self-verification doc found for Claude Code's adversarial verification
subagent, now showing up a second time in an unrelated subsystem. Also
covers: static-vs-LLM risk classification
(OpenHands's genuinely pluggable choice between trusting the model's
own self-tag or a separate Dockerized static analyzer), scope/
persistence of a granted approval (five distinct tiers in Codex vs.
Roo Code's two, with no session-only cache at all), escalation
mechanisms (OpenCode's `doom_loop` circuit breaker on repeated
identical calls, Codex's mid-execution syscall-level interception),
sandbox/isolation as a complementary-not-substitute layer, and the
cross-cutting finding that most of this machinery is invisible to the
model's own system prompt — the harness gates the model, but rarely
tells it the rules.

**[→ `agent-git-vcs.md`](./agent-git-vcs.md)** — the last of the
planned drill-downs, across 25 sources: when (and whether) an agent
commits, checkpoint/undo systems, worktree isolation, branch-management
rules, and PR/push workflow. The headline finding: two unrelated teams
(OpenCode, Gemini CLI) independently built a **hidden shadow git
repository used purely as a checkpoint engine**, structurally separate
from the user's real `.git` — OpenCode's captures bare content-
addressed trees automatically on every LLM step and is wired into a
real session-level `/undo`/redo feature; Gemini CLI's captures full
commits only before file-edit proposals and bundles the **conversation
history** into the same checkpoint as the code state, restoring both
together. Also covers three independently-converged worktree-isolation
services (Gemini CLI, OpenCode, Claude Code — the last confirmed via
this session's own live tool schema, not a leak), the one code-level
(not merely prompted) git restriction found anywhere in this
collection (Augment SWE-bench Agent's hardcoded ban on `git commit`/
`git add`/`git init`), and "don't commit unless explicitly asked" as
close to a universal cross-vendor convention — including one exact,
word-for-word match between Claude Code's leaked prompt and OpenCode's
own base persona.

**[→ `agent-memory-learning.md`](./agent-memory-learning.md)** — what a
scaffold keeps *after* the session ends, across ~30 sources: the five
scope levels a fact can belong to (task, session, repo-shared,
repo-private, user-global, org) and the two sources with explicit
routing rules between them; who writes memory (the working model
inline vs. a background distillation agent vs. a human) and the
striking convergence of **four independently-built background
consolidators** — Codex CLI's two-phase pipeline, Gemini CLI's
`confucius` skill/memory extractor, GitHub Copilot CLI's `rem-agent`,
and Antigravity's Knowledge Subagent — all of which read *finished*
transcripts, all of which independently rank user messages above the
agent's own as evidence, and all of which state some version of
"transcripts are data, not instructions"; the equally striking
convergence on an **always-loaded index file plus on-demand topic
files**, named `MEMORY.md` by three unrelated products; retrieval
policy (Codex's "skip memory when the request is self-contained" plus a
4–6-step search budget vs. Antigravity's "🚨 MANDATORY FIRST STEP");
signal gates that make **no-op the encouraged default**; the memory tool
surfaces and what each scaffold actually injects — including an exact
read/write inversion between agents that can write memory but never
fetch it (Cursor, Augment) and Codex, which reads freely but may not
edit its own store, plus the two newest designs (Claude Code, Gemini
CLI) shipping no memory tool at all; retrospectives
proper (Codex's success/partial/uncertain/fail outcome triage and
"symptom → cause → fix" failure shields); the review-tool feedback loops
that learn from human reactions instead of self-assessment (Qodo Merge's
monthly auto-best-practices mining, CodeRabbit's approvable learnings,
Greptile's suppression-by-reaction); governance (Gemini CLI holds every
machine-written change as a patch in a `/memory inbox` nothing applies
automatically; Codex parses citation blocks into usage counts that
decide which memories survive the next consolidation); the finding that
**no first-party implementation does RAG over its own memory** — Codex's
memory search is a grep with a proximity window, Copilot CLI had a
database and explicitly chose FTS5 keyword search over vectors ("You
must act as your own 'embedder'"), and the vendors shipping genuinely
semantic *codebase* search pointed that infrastructure at the code, not
at the memory; and two vendor **retreats** — Cursor's Memories feature appears removed in favour of
Rules, and Gemini CLI deleted `save_memory` outright ("There is no
`save_memory` tool").

## Sources so far

| Folder | Project | Type | License |
|---|---|---|---|
| [`cline/`](./cline) | [Cline](https://github.com/cline/cline) | Coding agent (IDE extension) | Apache-2.0 |
| [`aider/`](./aider) | [Aider](https://github.com/Aider-AI/aider) | Coding agent (terminal) | Apache-2.0 |
| [`pr-agent/`](./pr-agent) | [PR-Agent / Qodo Merge](https://github.com/qodo-ai/pr-agent) | Code review agent | Apache-2.0 |
| [`swe-agent/`](./swe-agent) | [SWE-agent](https://github.com/SWE-agent/SWE-agent) | Coding agent (issue resolver) | MIT |
| [`openhands/`](./openhands) | [OpenHands](https://github.com/All-Hands-AI/OpenHands) | Coding agent (autonomous SWE) | MIT |
| [`opencode/`](./opencode) | [OpenCode](https://github.com/anomalyco/opencode) | Coding agent (terminal, multi-provider) | MIT |
| [`roocode/`](./roocode) | [Roo Code](https://github.com/RooCodeInc/Roo-Code) | Coding agent (VS Code extension, Cline fork) | Apache-2.0 |
| [`copilot-chat/`](./copilot-chat) | [GitHub Copilot Chat](https://github.com/microsoft/vscode-copilot-chat) | Coding agent (VS Code agent mode + CLI) | MIT |
| [`codex/`](./codex) | [Codex CLI](https://github.com/openai/codex) | Coding agent (OpenAI's terminal agent) | Apache-2.0 |
| [`goose/`](./goose) | [Goose](https://github.com/block/goose) | Coding agent (Block, CLI + desktop) | Apache-2.0 |
| [`crush/`](./crush) | [Crush](https://github.com/charmbracelet/crush) | Coding agent (Charm, terminal) | FSL-1.1-MIT |
| [`bolt/`](./bolt) | [Bolt.new](https://github.com/stackblitz/bolt.new) | AI app-building agent (browser) | MIT |
| [`gemini-cli/`](./gemini-cli) | [Gemini CLI](https://github.com/google-gemini/gemini-cli) | Coding agent (Google, terminal) | Apache-2.0 |
| [`augment-swebench-agent/`](./augment-swebench-agent) | [Augment SWE-bench Agent](https://github.com/augmentcode/augment-swebench-agent) | Coding agent (SWE-bench Verified baseline) | MIT |
| [`mini-swe-agent/`](./mini-swe-agent) | [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) | Coding agent ("the 100 line" SWE-bench baseline) | MIT |
| [`live-swe-agent/`](./live-swe-agent) | [Live-SWE-agent](https://github.com/OpenAutoCoder/live-swe-agent) | Coding agent (writes its own tools mid-task) | MIT |
| [`composio-swekit/`](./composio-swekit) | [Composio SWE-Kit](https://github.com/ComposioHQ/composio) | Coding agent + PR review, multi-role framework | Apache-2.0 |
| [`codeact-hyperlight/`](./codeact-hyperlight) | [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) | Tool-use pattern (CodeAct) + sandboxed execution, not a standalone agent | MIT |
| [`pi-agent/`](./pi-agent) | [Pi](https://github.com/badlogic/pi-mono) | Coding agent (minimal terminal harness) | MIT |
| [`zed/`](./zed) | [Zed](https://github.com/zed-industries/zed) | Coding agent (AI-native code editor's Agent Panel) | GPL-3.0-or-later / Apache-2.0 |
| [`omp/`](./omp) | [OMP / Oh My Pi](https://github.com/can1357/oh-my-pi) | Coding agent (terminal; fork of `pi-agent/` with LSP/DAP wired in) | MIT |

Note: Roo Code and Copilot Chat's source repos were both archived
(read-only) shortly before this collection was put together — files are
still retrievable, just no longer actively developed at those locations.

## Leaked / closed-source prompts

A second category, kept separate from the open-source folders above: prompts
from closed-source products, extracted by third parties rather than
published by the vendor. 34 sources so far — see
[`leaked/README.md`](./leaked/README.md) for the full list and caveats on
provenance and reliability. Most came in bulk from one community aggregator
repo; a few (Factory/Droid, Lumo, **Jules**, **GitHub Copilot CLI**,
**Grok Build**) from standalone gists/mirror-repo subfolders. Jules
(Google's async coding agent) is worth flagging specifically: its leaked
prompt has the most granular self-review discipline found anywhere in this
collection — mandatory verification after *every* file-modifying action
(not just before submission), plus a dedicated pre-commit tool, an explicit
code-review-request tool, and Playwright-generated screenshots as proof of
frontend verification. See [`leaked/jules/README.md`](./leaked/jules/README.md).
GitHub Copilot CLI — a distinct product from the already-covered
`copilot-chat/` VS Code extension — is worth flagging too: its two leaked
captures turn out to be the same underlying "Copilot CLI runtime" running
in two embedding contexts (standalone terminal vs. inside VS Code), with a
first-class SQL tool for todo tracking and cross-session memory not
matched by any other source in this collection. See
[`leaked/github-copilot-cli/README.md`](./leaked/github-copilot-cli/README.md).
Grok Build (xAI's coding CLI, this collection's first xAI coding-agent
coverage) is worth flagging for a different reason: several of its tool
descriptions and behavioral rules are near-verbatim matches to Claude
Code's own leaked tool descriptions (`Read`/`Edit`/`Write`, the Bash
tool's git-commit-safety guidance, even a shared worked example) — the
most literal cross-vendor prompt-text match found anywhere in this
collection. See [`leaked/grok-build/README.md`](./leaked/grok-build/README.md).

**Checked and no leak found (as of 2026-07-10)**: CodeRabbit, Greptile, and
Qodo's closed-source products (its open-source `pr-agent` is already
covered above). Worth re-checking later.

**Note on Lumo**: despite Proton's marketing and despite being filed under
a "Open Source prompts" folder in the aggregator repo it was sourced from,
Lumo is not actually open source — it stays in `leaked/` rather than
alongside Bolt and Gemini CLI above.

## Skills / plugins

A third category: Claude Code "skills"/plugins — small, self-contained
prompts that define a single slash command or subagent (e.g. "review my
uncommitted changes") rather than a whole standalone agent. Officially
published, but licensing varies (MIT to Anthropic's source-available
commercial terms) — see [`skills/README.md`](./skills/README.md).

| Folder | Publisher | Contents |
|---|---|---|
| [`skills/agent37/`](./skills/agent37) | agent37-platform | `local-review` (pre-commit review) |
| [`skills/anthropic/`](./skills/anthropic) | Anthropic | `code-review`, `pr-review-toolkit`, `security-guidance` |
| [`skills/turingmind/`](./skills/turingmind) | TuringMind AI | Pre-commit review, quick + deep modes |
| [`skills/bmad-code-review/`](./skills/bmad-code-review) | BMad Code, LLC | Code review as a 4-step state machine w/ pluggable review layers |
| [`skills/claude-code-cookbook/`](./skills/claude-code-cookbook) | wasabeef | PR review, auto-role-suggesting review, PR-fix |

Each of these documents its **scaffolding**, not just the prompt text —
how it constructs the diff/context, what else it pulls in, and how output
gets delivered — since that varies a lot between sources and matters as
much as the prompt wording itself. See
[`skills/README.md`](./skills/README.md) for details on where these came
from.

## GitHub PR bots

A fourth category: the automated bots/GitHub Actions vendors offer that
review PRs directly on GitHub (as opposed to `skills/`'s Claude-Code-only
commands, or the top-level folders' standalone CLI/IDE agents). See
[`github-pr-bots/README.md`](./github-pr-bots/README.md).

| Folder | Vendor | License |
|---|---|---|
| [`github-pr-bots/claude-code-action/`](./github-pr-bots/claude-code-action) | Anthropic | MIT |
| [`github-pr-bots/gemini-code-review/`](./github-pr-bots/gemini-code-review) | Google | Apache-2.0 |
| [`github-pr-bots/codex-review/`](./github-pr-bots/codex-review) | OpenAI | MIT (published reference impl., not the real hosted service — see README) |
| [`github-pr-bots/opencode-review/`](./github-pr-bots/opencode-review) | Anomaly (OpenCode) | MIT (defaults to the full "build" agent, not a review-specific one — see README) |

**Copilot: nothing found.** GitHub's actual hosted Copilot code-review bot
has no published prompt/diff-formatting logic anywhere — closed-source,
server-side. See `github-pr-bots/README.md` for what was checked.

## Papers

[`papers/inside-the-scaffold/`](./papers/inside-the-scaffold) — the PDF
itself (CC-BY 4.0), stored rather than just linked: *"Inside the Scaffold:
A Source-Code Taxonomy of Coding Agent Architectures"*
([arXiv:2604.03515](https://arxiv.org/abs/2604.03515)). Does complementary
analysis to this repo: instead of comparing prompt text, it compares the
*scaffold/architecture code* around 13 open-source coding agents (control
flow, tool interfaces, context management), grounded in specific file
paths and commit hashes. A good companion read to
[`coding-agent-approaches.md`](./coding-agent-approaches.md), and its
source list is where several "candidates for next pass" below came from.

## Candidates for next pass

Other open-source coding/review agents worth adding later: Continue.dev,
gpt-engineer, Plandex, bolt.diy (community multi-LLM fork of Bolt).
From the scaffold-taxonomy paper above: AutoCodeRover, Agentless,
Moatless Tools, DARS-Agent, Prometheus (all SWE-bench-family agents, same
category as `swe-agent/`/`mini-swe-agent/`/`live-swe-agent/`/
`augment-swebench-agent/` above). From Command Code's read-tool benchmark
(see [`sources.md`](./sources.md)): **Kilo Code**, **Hermes**, **OpenClaw**,
and **Command Code** itself — four harnesses this collection has no
coverage of, two of which (Kilo Code, Hermes) are credited with read-tool
features found nowhere in the sources read so far.
