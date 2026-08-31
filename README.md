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
source for detail. A later pass added the first source in this collection
that treats **where review criteria come from** as a pipeline stage of
its own ([`deepseek-harness/`](./deepseek-harness), §11): a repo-resident
review skill rewritten periodically from mined human review comments,
where adoption is proven by comparing two PR-specific patch snapshots
rather than by merge status or a "fixed" reply, two independently
configured reviewer adapters must agree before anything reaches a draft,
bot findings are excluded from the learning source by contract, the mined
comments are handled as untrusted input behind a nonce-tagged wrapper,
and a human promotes the candidate under written instructions not to
defer to the reviewers. Its published acceptance run is the finding:
426 human feedback items over 62 merged PRs produced **zero** rule
changes, which the operator doc frames as the workflow working —
the hard part of learning from human review is refusing to extract.

**[→ `openclaw/`](./openclaw)** — OpenClaw 2.0 (`v2026.8.1`, MIT, read
2026-08-31): a messaging **gateway with a personal assistant in it** that
grew a coding agent as one of its surfaces, and by far the largest source
here (35,739 files, 159 plugins, 747 doc pages). The inversion is what
makes it interesting — a coding turn is one mode among many, so the prompt
is assembled per *surface* from ~60 runtime parameters with a **declared
cache boundary inside its own text**
(`<!-- OPENCLAW_CACHE_BOUNDARY -->`), section placement argued as a
caching decision, and three named sections a provider plugin may replace.
The team-coding answer is **Workboard**: a bundled, disabled-by-default
board of claimable cards with claim tokens (redacted in every projection,
handed out once, and *not* required by the recovery paths), heartbeats
with a staleness diagnostic, a completion contract whose violation is a
first-class card event, a dependency DAG that renders each done parent's
result summary into the child's brief, per-assignee recent-work memory
scoped to a board, and a dispatcher that starts one card per owner per
pass — a Kanban WIP limit applied to agents. Its worker prompt is six
lines. Alongside it, **Swarm** takes the field's strongest position on
orchestration — *"There is no graph DSL and no separate workflow format.
The program is the orchestration"* — with `Promise.all`/`while`/
`Promise.race` as the control flow, JSON-Schema-validated child results
with one corrective nudge, and collector approvals that **fail closed into
data the program can branch on**. Other firsts: an **allow-or-escalate**
model in the exec-approval path (it cannot deny, so a compromised reviewer
degrades to asking a human); **compaction that fails closed** after
auditing five required headings in the post-budget text, protecting
pending asks and exact identifiers from truncation; memory consolidation
where the model **places but may not write** ("never author replacement
prose") and must emit a per-candidate operation record; a learning pass
grounded in an **authoritative runtime receipt** of which skills actually
fired; worktree cleanup that snapshots into `refs/openclaw/snapshots/<id>`
and removes only when provably lossless; and a review prompt that reasons
about **`git blame` epistemics**. It also sharpens
`agent-context-file-loading.md`'s clean negative: OpenClaw ships a
general-purpose `<untrusted-text>` escaping wrapper and uses it for
sub-agent results, attachments and operator `/compact` text — but still
injects `AGENTS.md`/`SOUL.md`/`MEMORY.md` raw, so the gap is now a
*choice* rather than an absence.

**[→ `deepseek-harness/`](./deepseek-harness)** — DeepSeek AI's
open-source agent harness (MIT, developer preview, read 2026-08-14), and
a different *kind* of source from the rest of the collection: no file in
it contains a system prompt, because the prompt is assembled per request
from per-plugin sections, so what is stored here are the assembled
**snapshots the repo checks in as test expectations** — which is itself
the finding, since prompt wording is treated as behavior under test.
Alongside them, the repo's own agent-facing process corpus: `AGENTS.md`
under a word-budget gate, five of its eleven skills, an eight-class
taxonomy of **chain-of-thought leakage** in committed prose (with the
four overcorrection traps that shipped and were caught in review), a
decision-memory tree whose lifecycle is encoded in the file path and
whose archive is cryptographically frozen, and a machine-enforced
**"Model Experience"** section required in every package README
declaring what the model sees, what it costs in tokens, and what
invalidates KV cache — the only instance here of a repository gating
that disclosure per component. Its **Code Mode** advertises every tool
as a compiling `.d.ts` with declared return types and asks for a program
rather than a call, which is what lets it say the sentence the rest of
this collection's context-management docs are circling: intermediate
tool results never enter the conversation.

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
tool surface. Its §4–§5 (browser access, multimodal) are largely
**superseded** by the source-grounded pass in
[`agent-vision-multimodal.md`](./agent-vision-multimodal.md).

**[→ `agent-vision-multimodal.md`](./agent-vision-multimodal.md)** — the
drill-down that overturned that section: how agents actually get pixels in
front of a model, read from source across twelve harnesses plus the leaked
corpus. Reading code rather than prompts falsified the earlier "multimodal
is the thinnest capability here" verdict — Goose, Crush, Zed, OpenHands and
Gemini CLI all handle images through tools no captured prompt names, and
Gemini CLI ships a whole browser sub-agent. Organised around the four
questions a harness answers independently (entry, transport, admission,
lifetime) and the pixel-first/text-first split. Findings that recur: the
**image-in-a-tool-result bug** — Chat Completions cannot carry one, the
converter `JSON.stringify`s it, and the model "treats it as ~50KB of opaque
text and hallucinates the image's actual contents," a failure that never
errors — with Cline's middleware fix and SWE-agent's opposite answer
(base64 through stdout, promoted to image blocks by a history processor);
five independent implementations of capability-gated degradation whose
**placeholder strings differ in whether the model can act on them**, and
the rule that emerges (strip at request-build time, keep the real image in
history, so a model switch restores sight); resize budgets tabulated
(patches as well as pixels in Codex, a ceiling that drops from 8000px to
2000px past twenty images in OpenHands), and the coordinate-drift problem
with three shipped answers — state the scale factor in-band, fix the
viewport, or draw a red crosshair into the screenshot. §8 is the
under-served question: only Codex prices images and keeps them atomic
through compaction (with `retained_image_count` as the field's only
retention metric), and only Gemini CLI **evicts a stale visual observation**
— a type-aware supersession rule with a lifetime of one, which generalises
and nobody has generalised. §10 names the strongest convergent pattern:
three harnesses independently put the screenshot in front of a *different*
model and return only text (Gemini CLI defangs its computer-use delegate by
excluding its action functions; OpenHands's tool refuses to register when no
sighted profile exists). §11 covers screenshots as verification evidence —
Jules gating task completion on a `screenshot_path` parameter, Antigravity's
auto-recorded WebP walkthroughs, and Codex's three-valued
`Disabled`/`TextOnly`/`Multimodal` mode deciding whether the *reviewer*
gets to see — and §12 the injection surface a text scanner cannot cover.

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
precisely because nothing fails. A final pass closed the two loose ends
with the collection's first **independent** benchmark: JetBrains's
Diff-XYZ, which separates *generating* an edit from *reading* one and
finds they want opposite formats — search-replace scores 0.95 on diff
generation and 0.57 on apply, unified-diff variants 0.92–0.93 on apply
and 0.06 on generation — so "which edit format is best" is the wrong
question for an agent that does both jobs, and the model-size interaction
both vendor benchmarks reported turns up here independently. Reading
Kilo Code's actual clamp then produced a better answer than the one this
collection had adopted: compose the ceilings so the byte budget only ever
decides whether a *whole* line fits, and mid-codepoint truncation and the
resume off-by-one both stop existing. A final look at the academic
literature added §4a2 and a warning to go with it — Diff-XYZ's roster is
entirely superseded, and an April 2026 **audit** of the only two
benchmarks that evaluate instructed code editing with human instructions
and tests finds both are over 90% Python with zero TypeScript, invert the
real domain mix, contain no documentation or maintenance edits, and carry
oracles so thin that 59% of EDIT-Bench's low-coverage suites cannot detect
changes made *outside* the edit region, which is exactly the failure mode
an unsupervised agent has. The synthesis is deflating and worth stating:
there is no public evidence base good enough to pick an edit format from,
and what every credible actor in this space actually did was build their
own eval on their own harness. A 2026-08-30 pass added §12 on a tool
family the doc's four questions don't reach — **memory tools** — and its
finding is that nobody built the database the name implies: every
implementation is the ordinary file tools pointed at a different
directory (Claude Code, Gemini CLI) or a read/list/search family scoped to
one root (Codex's namespaced `memories.*`, Goose's MCP server), so the
engineering lands in the path predicate that runs before any I/O, the
single create-only write whose schema refuses an update verb, and the
guards that run before the bytes do — including the collection's only
*content* guard on a write path, a curated gitleaks subset that blocks a
secret from reaching a team-shared memory file, running inside
`FileWriteTool`'s own validation. It also records a bug class this family
invites, in shipped code: Goose keys retrieved memories by their tag
string, so two entries with the same tags silently collapse into one at
read time — nothing about either the write path or the read path is wrong
in isolation.

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

**[→ `agent-tool-result-transport.md`](./agent-tool-result-transport.md)** —
one layer to the *side* of those three, and the first doc here about MCP as
a **result transport** rather than as an extensibility checkbox: what
happens to a tool result between the process that produced it and the
model's context. Opens by disentangling the escaping folklore into three
layers — the JSON-RPC transport (decoded before tokenisation, **free**),
the provider's own rendering (Anthropic passes a raw string, Gemini's
`FunctionResponse` is a Struct and *does* escape, the in-band dialects
write raw text), and the payload the tool itself built — with the cost of
each **measured**: single-level escaping is 1.11× on prose and 1.22× on
quote-and-tab-heavy code, double-encoding 1.48×, base64 2.58–3.61×, and —
the number that settles the design question — a line-number prefix costs
1.13×, i.e. the *same* as escaping, while preserving the byte-exact match
escaping destroys. The core finding is a gap in the spec: **MCP specifies
the shape of a result and not its projection into model context**, so
every client invents one, and the seven compared here — six of them
read from source — disagree completely.
OpenCode ships two deliberately opposite projections in one codebase
(`content`-first for a model, `structuredContent`-first for its Code Mode
program) and the only binary handling in the field that routes images and
blobs to a separate attachment channel while leaving a *stub* in the text;
Roo Code passes text raw but `JSON.stringify`s embedded resources, strips
`blob` fields and drops `resource_link`, `audio` and `structuredContent`
**silently**; Cline's SDK types an MCP result as `unknown` and
`JSON.stringify`s the whole envelope into the conversation; ADK's Java and
Python bindings ship two incompatible projections of the same protocol in
the same release train. Also: the spec's own duplication trap (servers
SHOULD serialise `structuredContent` into a text block too, so any client
forwarding both pays twice — 284 vs 189 tokens on SEP-1624's own example);
the 146 KB PNG that cost **106,356 tokens instead of 39,199** because a
client stringified base64 it was already rendering natively; and, for
payloads that shouldn't be in context at all, the **six decisions an
artifact system forces** — minting, opaque-vs-legible naming, what the
stub says (shape, never contents), an operation set that *reduces* rather
than defers, expiry-as-recoverable-error, and whether a load is permanent
— synthesised across six independent arrivals at the same pattern: MCP
`2026-07-28`'s new "Stateful Tools" guidance (sessions were removed from
the protocol, and server-minted handles passed as ordinary tool arguments
are the sanctioned replacement), `resource_link`, the tasks extension,
Claude Code persisting oversized MCP results to disk and replacing them
with a file reference, OMP's `artifact://` reusing the file selector
grammar so the operation set costs zero new tools, and ADK's versioned
`ArtifactService` whose loads are appended to *one request* rather than to
history. Closes with the protocol's unused answer to "return this to the
user" — `annotations.audience`, `_meta`, and MCP Apps (`ui://`, stable
2026-01-26) — and the rule that generalises it: **audience is a property
of a content block, not of a tool call.**

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

A second pass (2026-08-30) read five of those systems as **source**
rather than as prompt text and changed several conclusions. It added the
collection's fullest machine-written-memory specification, from the
leaked Claude Code source's `src/memdir/`: a four-type taxonomy whose
`<scope>` line routes each type to a private or a **team-shared** store,
a rule to record validated *successes* as well as corrections (because a
failure-only store "may grow overly cautious"), staleness computed from
`mtime` and rendered in words at read time ("models are poor at date
arithmetic"), retrieval by a **cheap model acting as the selector** —
≤5 files chosen from a manifest, hallucinated filenames dropped, and
reference docs for a tool already in use suppressed while its *warnings*
are not — memory scoped per **sub-agent type** and shippable as a
snapshot, and several paragraphs carrying **eval results in code
comments** (a section that scored 3/3 with its own header and 0/3 as a
bullet with identical text). That team-shared store contradicts what the
first pass had recorded as the field's cleanest rule — Gemini CLI's "an
extractor may never patch the file your team commits" — and ships a
gitleaks-derived secret scanner inside `FileWriteTool`'s validation
instead of a review queue. The same pass found Gemini CLI computing a
**model-free session digest** (tool sequence, touched paths, and whether
tests passed, in ≤160 characters) that decides which transcripts an
extractor bothers to read; Codex deciding whether to consolidate at all
from **git dirtiness** rather than a database watermark; Goose loading
only its *global* memories into the prompt while a tag-keyed map silently
collapses same-tagged entries at read time; a third retreat (Cline's
`new_rule` tool is now a settings-UI button); and, in DeepSeek Harness,
the sharpest single datum in the topic — its review-criteria mining loop
has produced **zero** rule changes from 426 human feedback items, while
`git log` shows every actual rule change arriving in the ordinary PR that
established the convention it governs. The doc closes with a channel it
argues is missing almost everywhere: **improvement requests** — what an
agent does with a finding about a broken tool, a misleading library, or
the harness itself, which is neither a memory (nothing retrieves it) nor
a question (nothing blocks). Devin's `report_environment_issue` is the
only first-class instance; DeepSeek routes the same signal the opposite
way, with feedback that by contract "never reaches the model".

**[→ `agent-context-file-loading.md`](./agent-context-file-loading.md)** —
the read side of the same files `agent-memory-learning.md` covers the
writing of: **how a repo's `AGENTS.md`/`CLAUDE.md`/`GEMINI.md` actually
becomes prompt bytes**, read from eleven loaders' source rather than
their docs (fetch paths and commits in [`sources.md`](./sources.md)).
The nine questions every loader answers differently — filenames,
walk boundaries, collision (first-match vs. load-all, and how a repo
with both `AGENTS.md` and `CLAUDE.md` gets three different answers with
no indication which fired), ordering, dedup, transformation, imports,
envelope, injection point. The findings that recur: **everyone
concatenates root-first**, so every "sub-directory rules win" claim in
the field is carried by nothing but position in the text — Gemini CLI
states that claim twice and satisfies it once, and Crush's precedence is
alphabetical by accident (`slices.Sort` over the merged default and
user-configured path lists). Five different dedup keys, only one of them
— Gemini CLI's `dev:ino` — actually correct on a case-insensitive
filesystem. A comparison of the four `@import` expanders on every safety
axis, where only Goose bounds *total* cost (64 operations / 1 MiB /
128 KB parse input), only Goose filters imports through the repo's own
`.gitignore` so a committed hints file can't inline a `.env`, only
Claude Code gates escaping the repo behind a one-time human approval,
and OpenCode will fetch instruction text over **HTTPS** with no
approval, cache, or integrity check. A clean negative result on
templating — **nobody evaluates the context file as a template**, in any
of the eleven — and a much less comfortable one on escaping: **nobody
escapes the body either**, so a file containing `</INSTRUCTIONS>`,
`</file>` or `# Rules from …` forges its own envelope; Zed's
six-backtick fence is the only containment attempt in the field. The
three incompatible postures on authority, quoted: Claude Code's "These
instructions OVERRIDE any default behavior and you MUST follow them
exactly as written", Gemini CLI's ceiling ("cannot override Core
Mandates regarding safety, security, and agent integrity"), and
OpenHands alone shipping an `<UNTRUSTED_CONTENT>` banner plus a
*capability scope* ("coding style, project conventions, and
documentation guidance only") — applied to its own memory files too,
because "anyone with access to the workspace or repository can edit or
commit them". Claude Code's delivery mechanism contains the
contradiction in miniature: one `<system-reminder>` user message whose
outer wrapper hedges ("may or may not be relevant... you should not
respond to this context") around an inner payload that says the same
bytes must be obeyed exactly. Plus: six distinct JIT triggers (Goose
derives context loads from **shell argv**; Cline from path-shaped tokens
scraped out of the user's own prose); Codex's 32 KiB shared budget that
byte-truncates mid-file and tells the model nothing; Codex's cache keyed
on environment selection rather than mtime, so **editing `AGENTS.md`
mid-session doesn't reload it**; the two harnesses that place the file
deliberately with respect to the prompt cache (OpenHands' `CacheTier`,
Aider's read-only-file channel) and the nine that don't; and the
**revision question** for CI — no loader anywhere is revision-aware or
records the SHA a rule came from, Codex's reference review workflow
checks out `refs/pull/N/merge` so **a PR that edits `AGENTS.md` changes
the rules used to review that same PR**, Gemini's is a `workflow_call`
whose comment-triggered path reads `GEMINI.md` from `main` while the
diff comes from the API, both vendors' workflows statically disable the
folder-trust gate that would otherwise refuse to load these files at
all, and Claude's action runs a bidi-override-stripping sanitizer over
every PR comment while applying none of it to the `CLAUDE.md` the same
prompt tells the model to follow. Aider is included as the deliberate
null case — no loader at all, conventions passed by `--read`, which buys
edit-protection and cache-stability for free. A later section (§12a)
covers the **programmatic** channels the file loaders can't answer for —
MCP server `instructions`, skills, hooks and plugins — and finds the
governance running backwards: Claude Code diffs newly-connected MCP
servers against prior attachments in the conversation's own history and
announces only the delta, because the alternative is a constant literally
named `DANGEROUS_uncachedSystemPromptSection` ("rebuilt every turn;
cache-busts on late connect"); Codex assembles its prompt from 45 typed
fragments and assigns third-party *content* the `user` role while
harness-authored framing gets `developer` — but gives a plugin's own text
and a hook's stdout a `developer` message with an **empty marker pair**,
i.e. higher in the instruction hierarchy than `AGENTS.md` and with no
envelope at all; and Codex's `dynamic_skill_selector/` holds **eleven**
competing retrieval implementations (fielded BM25, character n-grams,
routing cards, LRU hybrids, RRF fusion) behind a trait documented as
running "in shadow mode on every turn... without changing the
model-visible catalog" — the most developed retrieval-over-instructions
machinery in the collection, deliberately not shipped, by the same vendor
whose *memory* search is a grep. Across all eleven, **nobody generates
repository context programmatically**: skills are progressive disclosure
of static files, not construction.

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
(see [`sources.md`](./sources.md)): **Kilo Code**, **Hermes** and
**Command Code** itself — three harnesses this collection has no coverage
of, two of which (Kilo Code, Hermes) are credited with read-tool features
found nowhere in the sources read so far. The fourth, **OpenClaw**, has
since been read and has its own folder above.
