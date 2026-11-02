# Keel: memory, notes and consolidation

Where a run can keep things, who can read them later, who checks what is
written, and how a store is tidied between runs. Part of
[Keel](./README.md). Section numbers are shared across Keel's files, so a
reference like §7f means the same section everywhere.

**Status: proposal, 2026-11-02. Nothing in the schemas, the API or the
publish rules has changed yet.** This file says what would change and
why; §16h sketches the resources, fields, tools and rules it would add
if accepted.

Grounded in [`../../agent-memory-learning.md`](../../agent-memory-learning.md)
(the field research; §14 and §15 were added for this proposal, §15
after the survey was widened to always-running agents) and built on
Forge's [`../memory.md`](../memory.md), which it does not replace (§16a).

---

## 16. Memory

### 16a. What exists, and the gap

Forge already has a memory design, written before Keel was named:
[`../memory.md`](../memory.md). It splits what survives a run by who it
is addressed to: **learnings** for a future run, **improvement requests**
for a human (`ReportProblem`), and output feedback for us. Learnings are
captured in session (`Retrospect`), promoted by an outcome-triggered
learnings run, and served by the **context service** as a `learned` tier
keyed by subject: repo, path, dependency coordinate. That design stands.
It is the right home for knowledge about **code at a ref**, because the
context service holds the code and can tell when a learning's evidence
has moved.

Keel has no memory concept at all. `taxonomy.md` mentions the learned
tier once, inside "Conventions". That leaves four things with nowhere to
live:

| Need | Example | Why the context service is the wrong home |
|---|---|---|
| Notes that outlive one attempt but not the work | "Tried the Gradle daemon fix, it didn't help" on stage 2 of a pipeline, read by the retry | Not about code at a ref, and gone when the pipeline run settles |
| What a **user** has told an agent | Lens: "when I say *year* I mean the fiscal year" | Keyed by person, not by repo; private |
| What a **team** has learned | Lens: "`active_users` excludes service accounts; use `dim_user.is_human`" | Keyed by RBAC team; may span many repos or none |
| How to use a **tool group** | "`Maven` with goal `verify` needs `-Pci` on the shared runners" | Keyed by the saved tool group, read by every template that grants it |

Lens has no repository at all for most runs, so for Lens the context
service's learned tier holds nothing. These are the gaps this section
fills, as generic Keel resources that Forge and Lens configure.

### 16b. What the field does, in one table

The detail is in [`../../agent-memory-learning.md`](../../agent-memory-learning.md)
§1–§15. The decisions below rest on these rows. Rows marked *(rev.)*
changed when the survey was widened to always-running agents
(OpenClaw, Hermes) and memory-first systems (Letta, mem0, Zep,
Generative Agents) on 2026-11-02.

| Question | Field answer | Sources |
|---|---|---|
| Substrate | Markdown files with frontmatter, a small always-loaded **index** pointing at on-demand detail files | Claude Code, Codex, Gemini CLI, OpenHands SDK, Antigravity (§4) |
| Retrieval *(rev.)* | **Two layers.** A small curated core is injected and read with file tools and grep, everywhere. A large episodic layer (daily notes, transcripts, archival memory) is searched: hybrid vector + BM25 with recency and importance (OpenClaw), FTS5 only (Hermes), vectors or graphs (Letta, mem0, Zep). Coding harnesses have no episodic layer, which is why they never needed search | §4, §15 |
| Recall cost lanes | Rule-matched trigger phrases with no model call; a recall sub-agent only for questions about the past | OpenClaw (§15) |
| Selection when the index is too big | A cheap model picks ≤5 files from name + description, with restraint rules | Claude Code `findRelevantMemories` (§5, §13) |
| Levels | Session, private project, shared project, user, org, per-sub-agent | Gemini CLI routing table, Claude Code types → scope (§1) |
| Platform shape | Several stores per session, each attached `read_only` or `read_write`, mounted as directories, versioned | Managed Agents memory stores (§14) |
| Who writes | The working model; a background consolidator; or a human | §2 |
| Moderation | Human inbox (Gemini), visible after the fact (Claude Code), agent-owned (Codex). Secret scanning at the write tool only in Claude Code | §9 |
| Injection *(rev.)* | Every consolidator says "data, not instructions"; Managed Agents ties write access to input trust; OpenHands labels the index `UNTRUSTED_CONTENT`. OpenClaw makes **provenance** the boundary: closed origin classes in fields the model cannot write, taint that propagates, quarantine by tier, and no reliance on content scanning. Hermes scans content | §10, §14, §15 |
| Noise *(rev.)* | In always-on agents, most auto-captured memories restate runtime instructions, heartbeat output or recalled memory. Fixed by gating on session kind and marking recalled content | OpenClaw (§15) |
| Prospective memory | Intentions ("remind me", "when X comes up") compiled into cron jobs and rule tables with expiry and fire budgets, not prose | OpenClaw (§15) |
| Consolidation *(rev.)* | A separate run over the store and recent sessions, triggered by a count of sessions or dirtiness, mostly a no-op. OpenClaw promotes by recall frequency across distinct queries, with fixed gates before the model and the model choosing operations rather than writing prose (as mem0 does) | Claude Code dream, Codex Phase 2, OpenClaw dreaming, Letta sleep-time, Generative Agents reflection (§2b, §13, §14, §15) |
| Forgetting | Usage-ranked eviction (Codex citations), index budget pressure, delete-on-contradiction, a mass-deletion guard; supersession with validity intervals (Zep); forgetting by source session, following lineage (OpenClaw) | §9, §13, §15 |

### 16c. Notes, memory and consolidation are three things

People use "memory" for all three. They have different lifetimes and
want different machinery.

| | **Notes** | **Memory** | **Consolidation** |
|---|---|---|---|
| What | Working state the agent writes for itself | Durable knowledge for later runs | Tidying a store between runs |
| Lifetime | The pipeline run | Until superseded, evicted or deleted | One run |
| Written by | The working agent, directly | Proposals from working runs; direct only at low blast radius (§16f) | A consolidation run (§16g) |
| Keel resource | A store at level `run` (episodic only) | A `MemoryStore` at level `user`, `team`, `tool_group` or `global`, each with a curated and an episodic layer (§16e) | A template extending `keel.consolidate` |
| Precedent | OpenHands and OpenClaw daily logs, Claude Code `sessions/`, Copilot CLI `context_board` | Every row of §16b | Claude Code dream, Codex Phase 2, OpenClaw dreaming |

**Notes are not a carry.** A carry (`run-spec.md` §3) is written by the
harness from an outcome: a plan, findings, an interrupted attempt. Notes
are written by the agent while it works, in its own words. The two
compose: on a retry after `infra_failure`, the interrupted-attempt carry
says what happened and the notes say what the dead attempt had already
ruled out. A transcript is still never carried.

### 16d. Levels

One `MemoryStore` resource, with a `level` that fixes who owns it, who can
read it and the most a run may do to it. Five levels, the five the brief
asked for, plus the existing learned tier for completeness.

| Level | Owner (RBAC) | Who reads | Most a run may do | Default retention | Typical content |
|---|---|---|---|---|---|
| `run` | the pipeline run | every stage, retry and resume of that pipeline run | `read_write` | deleted when the pipeline run settles, unless a stage promotes a note | approaches tried, dead ends, partial findings |
| `user` | the principal it names | runs acting for that principal (`principal`, not `actor`) | `read_write` in an interactive run; `propose` otherwise (§16f) | until deleted; the user can see, edit and delete all of it | preferences, definitions, recurring corrections |
| `team` | an RBAC team | runs whose principal is on that team, or service runs a team owns | `propose` | until superseded or evicted | shared facts, metric definitions, workarounds |
| `tool_group` | the saved tool group's owners | runs whose grant includes that group (any version ≥ the one the entry names) | `propose` | until the group's next major version, then re-checked | gotchas and warnings about those tools |
| `global` | operators | every run in the deployment | `read_only` | — | org-wide facts too small to be a conventions section |
| *(learned tier)* | *the context service* | *runs resolved at that ref* | *none; Forge's learnings run writes it* | *Forge `../memory.md` §5b* | *knowledge about code at a ref* |

Seven decisions behind the table.

1. **Exactly one level per fact.** Gemini CLI's rule, and Claude Code's
   dream enforces it the other way round ("If a personal memory restates
   a team memory, delete the personal one"). A consolidation run that
   finds the same fact at two levels keeps the wider one and deletes the
   narrower (§16g).
2. **`global` is never written by a run.** Org-wide standing
   instructions already exist as the conventions corpus, which humans
   author. `global` memory is for facts, not rules ("the warehouse is
   read-only between 02:00 and 03:00 UTC"), and only operators write it.
   Without this line, `global` becomes a second conventions corpus that
   nobody reviews, and Forge's conventions specialist would review real
   PRs against it (Forge `../memory.md` §7).
3. **`tool_group` is keyed by the saved group, not by the tool.** A tool
   has no owner in Keel; a `SavedToolGroup` has one, a version and a
   grant (`tools-and-agents.md` §4b). Keying by group means a run sees
   memory about exactly the tools it was granted, and it gives the
   memory an owner who can moderate it. An entry names the group version
   it was learned at; a new major version marks it for re-check, the way
   Forge's dependency subject compares versions.
4. **`tool_group` holds workarounds; defects still go to `ReportProblem`.**
   This answers Forge `../memory.md` §9's open question. A defect is a
   request to the group's owners and never context. A workaround a human
   has accepted is useful context until the defect is fixed. So a
   `ReportProblem` against a tool can carry a proposed workaround, and
   the group's owners can accept it into the `tool_group` store when
   they triage the report. It expires when they close the report as
   fixed.
5. **`user` memory follows the principal, never the actor.** A Forge run
   started by Alice's Jira assignment reads Alice's store. A review run
   with a service principal has no user store at all. A run started by a
   delegation reads the delegating user's store only if the delegation's
   consent included memory (§16h, rule M4).
6. **`team` is an RBAC team, not a repo.** Repo-keyed knowledge belongs
   in the context service (§16a). A team store is for knowledge that
   follows people: Lens's metric definitions, a team's release calendar,
   which on-call channel to use.
7. **Per-agent memory is a path, not a level.** Claude Code keeps memory
   per sub-agent type, and Forge's review specialists could use it
   ("the security finder's own signals"). In Keel it is a subdirectory
   of a store (`agents/<agent name>/`) that only that agent reads, set
   by `agents.<a>.memory.path`. It needs no new level and no new
   owner.

### 16e. Substrate and retrieval: files for curated memory, search for episodic

*Revised 2026-11-02 after widening the survey to always-running agents
(`../../agent-memory-learning.md` §15). The first draft said "no
embeddings" outright. That was right for curated memory and wrong for
the episodic layer.*

**Every durable store has two layers.** Every always-running and
memory-first system in the survey separates them: OpenClaw (`MEMORY.md`
and `USER.md` against daily notes and transcripts), Hermes (two capped
files against `session_search`), Letta (core blocks against archival
memory), OpenHands (`MEMORY.md` against daily logs).

| Layer | What | Size | Written by | Reaches a run by |
|---|---|---|---|---|
| **Curated** | the index and its documents: facts, preferences, definitions, workarounds | small and capped (§16f step 1) | proposals and consolidation; direct only where §16d allows | injection at turn 0, file reads, grep |
| **Episodic** | dated, append-only notes (`episodes/YYYY-MM-DD.md`) and harness-written run summaries | grows without a cap until retention removes it | the working agent appends; the harness appends a run summary | search only, never injected |

A `run` store is all episodic. `global` is all curated. `user`, `team`
and `tool_group` have both. The episodic layer is what a long-lived
Lens user or a persistent assistant accumulates over months. Curated
memory is what survives consolidation out of it (§16g).

**Decision: curated memory is path-addressed Markdown, retrieved by
injection, file reads and grep, with no vector index.** The reasons stand
from the coding-agent sources (`../../agent-memory-learning.md` §4), and
the always-running agents agree for this layer:

- **It is small by construction.** A capped index and a few hundred
  documents. Grep is exact and instant, and there is no index to rebuild
  when a person edits a file by hand.
- **Scope wants an exact filter.** "Only Alice's" and "only for tool group
  `java.coding` ≥ 3" are access checks, not similarity questions.
- **People must be able to read and correct it.** Every moderation step
  in §16f ends with a person reading a document.
- **It is injected anyway.** What is always in context needs no
  retrieval.

**Decision: the episodic layer is searched through a derived index,
keyword always and vector optional.** The files stay the source of
truth; the index is built from them and can be rebuilt from them at any
time (OpenClaw's `memory reset` / `memory index`). Concretely:

- **Keyword search (BM25 or FTS5) is always on.** Hermes ships episodic
  recall with keyword search alone, and IDs, error strings and config
  keys need exact matches whatever else runs.
- **Vector similarity is a deployment option**, merged with keyword
  scores as OpenClaw does: keyword scores scaled so the best keyword
  match earns at most the best semantic score, then **relevance × recency
  decay × importance**, then MMR for diversity. Daily notes decay (a
  30-day half-life is OpenClaw's default); curated documents do not.
  If the embedding provider fails, search falls back to keyword-only and
  says so; it never fails the call.
- **Access filters run before ranking.** The candidate set is restricted
  to the stores the run may read *before* the result limit applies
  (OpenClaw: "scope restrict[s] candidates before the result limit").
  Ranking first and filtering after would let one user's notes push
  another's out of the window, or leak through scores.
- **Untrusted-origin chunks are searchable but quarantined** (§16f):
  results carry their origin, and the harness wraps untrusted ones in
  the untrusted-data envelope.

So the first draft's "no vector store" now reads **"no vector store for
curated memory, and no embedding index as a source of truth anywhere"**.
A wiki, a runbook library or an incident archive is still not memory. It
is a knowledge base and reaches a run as an MCP tool in a tool group,
with its own owner.

**How a run reads memory.** Four ways, from cheapest to dearest.

1. **The curated index is injected.** Each store has an index document
   (`MEMORY.md`, one line per entry, ≤150 characters a line). The
   harness renders the indexes of a run's stores into one generated
   block in the opening message, **narrowest level last** (OpenHands:
   "the later position gets more model attention"), each under a header
   naming its level, its fill (`[67% — 134/200 lines]`, as Hermes shows)
   and whether the run can write it. The block is nonce-wrapped and
   labelled as unverified data. Over budget, the harness drops whole
   lines from the oldest end and says so. An empty store injects
   nothing. **The block is frozen for the run**: a write during the run
   is visible to later runs, not re-injected into this one (Hermes's
   frozen snapshot, which also keeps the provider's prompt cache).
2. **Rule-matched entries are injected.** A curated entry may carry up to
   three short trigger phrases. Before turn 0 the harness matches them
   against the starting query with keyword and, if configured, vector
   similarity, and injects up to three matching documents whole. No
   model call. Only curated, non-untrusted entries qualify (OpenClaw's
   lane one).
3. **Documents are read and the episodic layer is searched by tool.**
   With a workspace, curated documents are mounted read-only or
   read-write at `/memory/<level>/` and the ordinary `Read`, `Grep` and
   `List` reach them; a write tool against a read-only mount is refused
   at the executor. `MemorySearch` (§16h) searches the episodic layer
   and curated documents of every store the run can read. With
   `workspace: none`, the built-in memory tools do both.
4. **A selector, when the index is too big.** If the combined indexes
   exceed the budget, `selector: model` runs an economy-tier side query
   before turn 0 that picks up to five documents from their names and
   descriptions, under Claude Code's restraint rules: only documents it
   is certain will help; match on what the task is about, not on
   keywords shared with a user profile; skip reference for tools already
   in use, but **keep warnings about them**. An outage selects nothing
   and never fails the run.

OpenClaw's fifth lane, a blocking recall sub-agent for questions about
the past, is a template choice in Keel: a sub-agent granted only
`MemorySearch` and `MemoryRead`, which a conversational template can
spawn. It needs no platform feature.

**Staleness is computed, not declared.** Each injected entry carries its
age in words ("written 47 days ago", nothing under two days), and a
`tool_group` entry learned at an older group version says so. Forge
`../memory.md` §5b has the reasoning; Keel applies it to every level.

### 16f. Writing, validation and moderation

The rule that decides everything here: **the wider a store's readership,
the less a run may write to it directly.** A bad note costs one pipeline
run. A bad team memory is read by every colleague's agent until someone
notices.

**Three write modes**, set per store attachment:

| Mode | What a write does | Default for |
|---|---|---|
| `read_write` | creates a new version of the document now | `run`; `user` in an interactive run |
| `propose` | creates a **proposal**, which a consolidation run or a moderator turns into a version, or rejects | `user` in a hands-off run; `team`; `tool_group` |
| `read_only` | refused at the executor | `global`; any store on an agent marked `memory: none` |

`propose` is how Gemini CLI's inbox and Forge's `Retrospect` candidates
generalise. The model makes the same call either way; the harness
returns *"proposed; a reviewer will decide"* instead of *"written"*, so
the model does not assume the fact is now in memory.

**Provenance is the boundary; content checks are the second line.**
*Revised 2026-11-02.* The first draft led with content checks and put
lineage last. OpenClaw's architecture argues the other way, with a
production audit behind it: "Content-level scanning of memory cannot
catch poisoned facts reliably, so OpenClaw enforces provenance at write
time and gates promotion structurally instead of trying to detect bad
memories later." A poisoned fact ("the deploy key lives at …") looks
like any other fact. What gives it away is where it came from.

Every write and every proposal is stamped by the harness, in fields the
model cannot set (OpenClaw: "Origin labels live in SQLite columns
written by classification code, never parsed out of memory text"):

| Field | Values | Set from |
|---|---|---|
| `origin` | `principal` (the principal's own words: the starting query from a live user, a chat message, an `AskUser` answer), `agent` (the agent's own conclusion with only `principal`, `config` and `harness` inputs in context), `untrusted` (anything after a ticket body, PR comment, fetched page, MCP result or other non-principal input entered the context), `system` (template text, trigger preambles, harness notes) | the trust of every input and tool result the writing agent had seen, at the moment of the write. Unknown is never `principal` |
| `run_kind` | `interactive`, `event`, `schedule`, `continuation`, `consolidation`, `sub_agent` | the trigger and the agent |
| `observed_at`, `supersedes` | a time; an entry id | the harness clock; the write |

Taint clears the way OpenClaw's does: on the next `principal` message.
In an interactive run that is the user's next chat message, so a Lens
user who says "when I say *year* I mean the fiscal year" after a
warehouse query has been answered still writes with `principal` origin.
In a hands-off run there is no next user message, so taint lasts until
the run ends: a Forge run that read a ticket stays `untrusted` for the
rest of the run.

Four structural rules use these fields. Each is enforced by the harness,
not asked of the model:

1. **Run-kind gating.** Runs started by a `schedule` trigger or a
   monitor, and `system`-origin content anywhere, produce no curated
   writes or proposals unless the template sets `memory.capture: true`.
   They may write episodic notes. OpenClaw's audit found that "the
   overwhelming majority of auto-captured memories [were] restatements of
   runtime instructions, heartbeat noise, and recall feedback loops", and
   a weekly Lens report on a schedule would produce exactly that.
2. **Recall-loop prevention.** The harness knows what it injected and
   what `MemoryRead` and `MemorySearch` returned. A proposal whose body
   restates retrieved memory is dropped as a duplicate. "A fact recalled
   one hundred times stays one fact."
3. **Quarantine by origin.** `untrusted` content may go to the episodic
   layer and is searchable there, but can never be written directly to a
   curated layer at `team`, `tool_group` or `global`, and consolidation
   never promotes it (§16g). At `user` level, an `untrusted`-origin
   write to the curated layer becomes a proposal even on a `read_write`
   attachment. Rule M2 catches the static case at publish; this catches
   the tool result that arrives mid-run.
4. **Least-trusted wins.** A document or proposal assembled from several
   sources takes the lowest origin among them, so "untrusted content
   cannot ride a trusted file hash".

**Then validation runs on every write and every proposal, in this
order.** Each step is a harness check (`tools-and-agents.md` §4d), so no
grant can remove it. A refusal comes back as a tool error that states
the rule, per the errors-are-prompts posture.

1. **Shape.** Frontmatter with `name`, `description` (one line; it is
   what the selector reads), and a `kind` from the store's declared
   list. Paths are normalised and confined to the store root before any
   I/O (`..`, absolute paths, reserved names rejected). One curated
   document is at most 4 KB, and the index at most a declared number of
   lines. A write that would push the index over its cap is refused with
   the cap, the current size, the entries it holds and how much must be
   freed. The agent then retries as one batch that frees space and adds
   the entry (Claude Code and Hermes both do this; Hermes's message names
   the exact number of characters to free).
2. **Concurrency.** Every update names the version it read (`if_version`,
   or `new` for a document that must not yet exist). A conflict returns
   the current content so the model can merge and retry. Claude Code
   and Managed Agents both landed here, and Hermes, which has no such
   check, has to tell its users never to run two agents on one store.
3. **Secrets.** A scanner over distinctive-prefix credential patterns,
   on every level and both layers. Claude Code's team-memory guard,
   widened.
4. **Personal data.** On `team`, `tool_group` and `global`, a classifier
   for personal data about anyone other than the principal. A team
   memory that says "Bob is slow to review" is refused. On `user` it is
   the principal's own data and allowed.
5. **Instruction shape and invisible text.** A body that addresses the
   agent ("ignore", "always run", "you must"), contains tool-call or tag
   syntax, invisible Unicode, or a link to a host outside the
   deployment's allowlist is forced to `propose` and flagged at `team`,
   `tool_group` and `global`. At `user` level it is allowed, because
   people do write "always show me the SQL". Hermes scans for these
   patterns and refuses; Keel routes to a person instead, because
   provenance has already done the structural work and a false positive
   should cost a review, not a lost fact.

**Moderation of proposals.** A proposal is a document diff with its
origin and run kind, the evidence the model gave, and the run it came from. Three
ways it can be decided, chosen per store:

| Policy | Who decides | When to use it |
|---|---|---|
| `human` | the store's owners, in a queue | `tool_group`, and `team` stores whose readers act on what they read (Forge implement, Lens answer) |
| `consolidation` | the store's consolidation run (§16g), against gates the store declares | `user` stores in hands-off use; `team` stores read only by low-stakes agents |
| `consolidation_then_human` | the consolidation run filters and merges; people approve what survives | the default for `team` |

Whatever decides, three rules hold:

- **Outcome beats self-report.** A proposal from a run whose outcome
  was `done` with passing checks is stronger evidence than one from a
  run that ended `blocked`. Forge `../memory.md` §3c's "witness, not
  judge" applies at every level: the run that wrote the proposal does
  not decide it.
- **A rejection is kept.** Rejected proposals stay, with the reason, so
  the same proposal from the next run can be matched and dropped
  without a person seeing it twice.
- **Wording is held to evidence.** A fact seen once is written as "seen
  once, on <date>, in <run>" and not as a rule (Forge `../memory.md`
  §4b-i). A moderator may accept a proposal and narrow its wording; the
  version history shows both.

**Audit, correction and deletion.** Every write is an immutable version
attributed to its run and principal; versions survive deletion of the
document. A version can be **redacted**: its content scrubbed, its
who-and-when kept (Managed Agents). That is how a leaked secret that got
past the scanner is removed, and how a user's request to delete their
data is met: delete the `user` store's documents and redact their
versions. Deletion has a rate limit: a run or a consolidation that
deletes more than a set number of documents in one cycle has the extra
deletions withheld and reported, Claude Code's mass-deletion guard,
because a sudden large delete is far more often an accident than a
decision.

### 16g. Consolidation ("dreaming")

**Decision: consolidation is an ordinary Keel template, not a
subsystem.** Keel already has everything a dream needs: templates,
triggers, grants, harness checks, run records and gates. A base template,
`keel.consolidate` (`runnable: false`), fixes what is common, and each
use case extends it per store level.

**When it runs.** A trigger on `memory.store_changed` **or**
`memory.proposal_created`, with a CEL condition, so the gate is a count,
not a clock:

- at least *N* pending proposals, or at least *N* runs that read or wrote
  the store since the last consolidation (Claude Code's "sessions since
  last consolidation"); and
- the store is **dirty**: its documents *or its proposal queue* have
  changed since the last successful consolidation (Codex's dirtiness
  gate, widened). On a store whose working runs only `propose`, new
  proposals create no document versions, so a gate on documents alone
  would never let the queue be processed. A store with no new versions
  and no new proposals never consolidates.

A schedule is allowed as a backstop, never as the main trigger, and it
uses the same dirtiness test. Most
consolidation runs should end `skipped`: "nothing changed" is the
normal outcome, and the completion contract has it as a status.

**What it is given** (inputs, all harness-built):

- the store's **diff since the last successful consolidation**, as Codex
  feeds its Phase 2 a git diff, so a person's hand edit shows up as an
  edit to respect, not as noise;
- the pending proposals, each with origin, run kind, evidence and
  source-run outcome;
- **promotion candidates from the episodic layer**: passages that
  `MemorySearch` returned to at least *N* runs for at least *M* distinct
  queries since the last consolidation, with their origins (below);
- per-document **usage**: how many runs had it injected or read it, and
  when last, from run records. Codex needs the model to emit citations
  to get this; Keel has it already because every read goes through the
  harness;
- for `team` and `tool_group`, the relevant conventions sections, for
  reconciliation;
- **digests** of the source runs (Forge `../memory.md` §3d), not their
  transcripts. A grep tool over transcripts is grantable for the narrow
  "what was the error message" question, read-only, and the prompt says
  to search for what it already suspects matters, never to read whole.

**What it may do.** Its grant is the built-in memory tools on **this one
store**, plus the read-only transcript grep. Its access is not a working
run's attachment and is not bounded by §16d's level maximum: it is the
store's **consolidator** access, held only by the template the store
names in `consolidation.template` (rule M1's one exception). What that
access does depends on the store's `moderation`: under `consolidation`
its writes are versions; under `consolidation_then_human` they are one
gated proposal batch; under `human` the store has no consolidator, and
proposals wait in the moderation queue. No
workspace, no network, no `Task`, no other store. Its effective
authority is the store owner's, through a service principal the owners
control; it never runs as a user, so it can't reach anything a
user-scoped run could.

**What it is told to do**, in Claude Code's four phases, with the rules
the field learned the hard way:

1. **Orient.** Read the index and skim the documents, so it improves
   them rather than adding near-duplicates.
2. **Gather.** In order: documents that the diff or usage data show have
   drifted; proposals; then, only if needed, a narrow transcript grep.
3. **Consolidate.** Merge proposals and promotion candidates into
   existing documents rather than adding new ones. Convert relative
   dates to absolute. When a fact is contradicted by newer evidence,
   **supersede** it: the old entry gets `valid_until` and a pointer to
   the new one, and stays in the version history (Zep's validity
   intervals, DeepSeek's "never edited into a different decision").
   Delete only what is superseded and unused.
4. **Prune and index.** Keep the index under its cap, one line per
   entry. Drop entries unused for longer than the store's
   `max_unused_days`; usage decides, not the model's sense of what looks
   old.

**Promotion from the episodic layer is decided by code, then by the
model.** *Added 2026-11-02, from OpenClaw's deep phase.* Fixed gates
run first: a candidate passage must have been retrieved by at least *N*
runs, for at least *M* distinct queries (`min_recall_runs`,
`min_unique_queries`), and must not have `untrusted` or `system` origin.
That removal is structural, not a score penalty, so no amount of recall
promotes an untrusted passage. Only then does the model see it, and the
model returns **operations, not prose**: add, merge into entry *x*,
supersede entry *y*, or drop. The harness applies them using the
candidate's own text and source reference, which is OpenClaw's design
and mem0's ADD / UPDATE / DELETE / NOOP. Three checks gate the result
before it is written: it loses no more than a set fraction of prior
entries (`max_prior_entry_loss`), it cites every promoted candidate's
source (`episodes/2026-10-30.md#L12-L18`), and it fits the index cap.
The previous index is kept as a version, so every consolidation can be
undone. This is the "writer that may place but may not author" of
`../../agent-memory-learning.md` §6, made the default.

And five rules that apply at shared levels:

- **Never move a fact between levels.** Promotion from `user` to `team`
  is a person's decision (Claude Code: "a deliberate choice the user
  makes"). The consolidation run may propose it to the team store's
  moderators; it may not write it.
- **Be conservative pruning shared stores.** "Do not delete a team
  memory just because you don't recognize it … A stale team memory costs
  little; deleting a teammate's load-bearing note costs a lot."
- **Never edit conventions.** When a memory contradicts a conventions
  section, the section wins by default. When the memory is clearly
  newer and corrects it, annotate the memory and raise a `ReportProblem`
  against the section's id for its owner (Forge `../memory.md` §6c).
  The "user corrected me" framing of a memory is not evidence that it
  is newer.
- **Treat the existing store as untrusted too.** OpenClaw's rule: prior
  memory is data, not instructions, because an injection that got in
  once is read by every consolidation after. Promoted entries keep the
  origins of everything they were built from, so forgetting a source
  (§16f) can still find them.
- **A team or tool-group consolidation's output is a proposal batch**
  under `consolidation_then_human`, gated like any other Keel gate
  (`outputs.md` §7d): one review of the whole diff, not one per entry.

**Models.** Economy tier for the `run` and `user` levels, standard for
`team` and `tool_group`. Letta's community guidance ("consolidation, not
complex reasoning") supports the cheap tier for the narrow levels; the
shared levels carry more risk per mistake.

### 16h. The spec, sketched

Shapes only; field names are proposals. Nothing below is in
`schemas/` yet.

**`MemoryStore`** (registry resource):

```json
{
  "name": "lens.team.growth",
  "level": "team",
  "owner": { "team": "growth-analytics" },
  "description": "Metric definitions and data quirks the Growth team's analysts have confirmed.",
  "kinds": ["definition", "quirk", "preference", "workaround"],
  "limits": { "doc_bytes": 4096, "index_lines": 200, "max_docs": 2000 },
  "moderation": "consolidation_then_human",
  "consolidation": { "template": "lens.consolidate.team", "min_pending": 5, "min_runs": 20 },
  "retention": { "max_unused_days": 180, "versions_days": 90 },
  "delete_rate": { "per_cycle": 10 },
  "episodic": { "search": "hybrid", "recency_half_life_days": 30, "retention_days": 365 },
  "promotion": { "min_recall_runs": 3, "min_unique_queries": 2, "max_prior_entry_loss": 0.1 }
}
```

`episodic.search` is `keyword` or `hybrid`; `hybrid` needs the
deployment to name an embedding provider, and falls back to `keyword`
when it is unavailable. `promotion` holds the fixed gates of §16g.

`run` and `user` stores are not registered one by one: Keel creates a
`run` store per pipeline run and a `user` store per principal on first
use, from a deployment-level default.

**`memory`** in a `RunSpec`:

```json
"memory": {
  "stores": [
    { "level": "run",  "access": "read_write" },
    { "level": "user", "access": "propose", "inject": "index" },
    { "level": "team", "store": "lens.team.growth", "access": "propose",
      "inject": "index", "instructions": "Check definitions before writing SQL." },
    { "level": "tool_group", "group": "warehouse", "access": "read_only", "inject": "index" },
    { "level": "global", "access": "read_only", "inject": "index" }
  ],
  "budget_bytes": 6000,
  "selector": "model",
  "triggers": true,
  "capture": false,
  "agents": { "validator": { "memory": "none" } }
}
```

- `store` and `group` are **not bindable**: a store reference grants
  read access, and grant-bearing fields take no params (`run-spec.md`
  §6). The `user` store is always the principal's and is never named.
- `access` is a ceiling for working runs. (A store's own consolidation
  template is the exception, §16g.) The effective mode is the narrowest of this
  field, the level's maximum (§16d), the principal's RBAC permission on
  the store, the delegation's memory consent, and the quarantine rule
  (§16f).
- `instructions` (≤ 1,000 characters) is rendered beside that store's
  index, as Managed Agents does; it comes from the template, so it is
  `config` trust.
- `triggers: true` turns on rule-matched injection (§16e, way 2).
- `capture` defaults to `true` for `interactive` and `event` runs and
  `false` for `schedule` runs and monitors (§16f, run-kind gating). A
  template sets it explicitly to override.
- An agent with `memory: none` gets no block and no tools. Forge keeps
  its validator independent this way (Forge `../memory.md` §5a).

**Built-in tools**, registered when a run has a store and no workspace
mount for it (and always for `propose` stores, since a file write can't
express a proposal):

| Tool | Does | Notes |
|---|---|---|
| `MemoryList` | no args: the run's stores, each with level, access and index path; with a store: paths, sizes, ages | never content; the set is fixed for the run |
| `MemoryRead` | one document's content and version | records the read for usage |
| `MemoryWrite` | replace a whole document, with `if_version` | at `propose`, returns "proposed" and the proposal id |
| `MemoryDelete` | delete one document, with `if_version` | counts against the delete rate |
| `MemoryNote` | append a dated entry to a store's episodic layer | allowed at `propose` too: episodic notes are not curated memory, and they keep their origin |
| `MemorySearch` | search the episodic layer and curated documents of every readable store; returns snippets with path, line range, store, age and origin | access filter before ranking; untrusted results wrapped; records the query for promotion counts |

`Retrospect` stays Forge's, and becomes a thin wrapper: a `Retrospect`
call is a `MemoryWrite` at `propose` to the store its `category` routes
to, with Forge's structured fields as the body.

**Events, for triggers**: `memory.proposal_created`,
`memory.store_changed`, `memory.proposal_decided`.

**API**: stores, documents, versions (list, read, redact), proposals
(list, accept with optional edit, reject with reason), as resources
alongside the rest of `api.md`.

**Publish rules** (`rules.md` §11), numbered here until accepted:

| Rule | Rejects |
|---|---|
| M1 | an `access` wider than the level's maximum in §16d: `read_write` on a `team`, `tool_group` or `global` store, or anything but `read_only` on `global`. **Exception:** a template extending `keel.consolidate` that the store names in `consolidation.template` gets consolidator access to that store only, which writes versions or a gated proposal batch per the store's `moderation` (§16g). A store with `moderation: human` may name no consolidation template |
| M2 | `access: read_write` on a `user` store in a template with any input that is not `principal`, `config` or `harness` (Managed Agents' warning as a rule; at wider levels M1 already forbids `read_write`) |
| M3 | a `tool_group` attachment naming a group the template does not grant |
| M4 | a template a delegation may run that attaches the `user` store, unless the template declares memory in its consent digest (so re-consent is required when it changes) |
| M5 | `capture: true` on a template started only by `schedule` triggers, unless every input is `principal`, `config` or `harness` |

### 16i. How Forge and Lens would use it

**Forge.** Little changes, which is the point.

- The context service's learned tier stays the home for repo, path and
  dependency learnings. `Retrospect` candidates with those subjects
  still route there through the learnings run.
- `forge.coding` attaches a `run` store, so plan, implement and their
  retries share notes. The implement prompt says what belongs there:
  approaches tried and why they failed, and nothing a carry already
  holds.
- Each template attaches the `tool_group` stores for the groups it
  grants, read-only. `ReportProblem` gains an optional `workaround`
  proposal for the group's owners (§16d.4).
- Forge's runs are hands-off and read tickets, PR comments and MCP
  results, so their `user` and `team` access is `propose` by rule M2.
- The review validator is `memory: none`.

**Lens.** This is where memory pays.

- `lens.quick` and `lens.investigate` attach the `user` store
  (`read_write` when the run started from a chat message the user is
  waiting on, `propose` for scheduled reports), and the team store of
  the principal's team at `propose`.
- The opening message's index gives the quick tier a user's definitions
  before it writes a query, which is the miss that most often sends a
  quick answer up to `lens.investigate`.
- A team store moderated `consolidation_then_human` is where an
  analyst's confirmed metric definition becomes every analyst's.

**A persistent assistant on Keel.** *Added 2026-11-02.* Keel has no
always-running process, and it does not need one to host the
OpenClaw and Hermes pattern. A persistent assistant is a chat trigger
(`run_as: invoker`) plus a `user` store whose episodic layer collects
`MemoryNote`s and harness-written run summaries, a heartbeat as a
`schedule` trigger with `capture: false`, and a `keel.consolidate`
template on that store. Hermes's lesson about session boundaries is
built in: each Keel run is a session, so the frozen curated snapshot
refreshes on every run rather than when a user remembers to type
`/new`.

### 16j. What stays out

- **No vector store for curated memory, and no embedding index as a
  source of truth.** Embeddings are allowed only as a derived, rebuildable
  index over the episodic layer, with keyword search always available
  (§16e).
- **No prospective memory.** "Remind me Friday" and "when the release
  comes up, mention the changelog" are not facts to store. They are
  triggers: a `schedule` trigger, or an event trigger with a condition,
  an expiry and a fire budget, created on the user's behalf through the
  trigger API with their delegation. OpenClaw's reason: "storing
  intentions as prose in a memory file is the least reliable design
  available".
- **No memory in a carry.** Carries stay harness-written outcome records.
- **No direct machine writes to shared levels, and none from untrusted
  contexts at any curated level.** Rules M1 and M2, and §16f's
  quarantine rule.
- **No memory as policy.** Memory is injected as data and can never
  outrank a conventions section or a harness check. Forge's
  "informs, never vetoes" holds at every level.
- **No cross-level promotion by a machine.** §16g.
- **No consolidation of `run` stores.** They are deleted when the
  pipeline run settles. A note worth keeping is proposed to a wider
  store by the run that wrote it, while it still has the evidence.

### 16k. Build order

1. **`run` stores and the four built-in tools**, `read_write` only. No
   moderation, no consolidation, no new risk: notes live and die with a
   pipeline run. This alone fixes "the retry repeated what the first
   attempt ruled out".
2. **Validation steps 1–3 and the version history**, on every store,
   before any store outlives a run.
3. **`user` stores**, `read_write` for interactive Lens runs only.
   Users can see and delete everything. Measures whether people value
   it before building anything shared.
4. **Provenance stamping, proposals and the human moderation queue**, then `team`
   and `tool_group` stores behind them.
5. **The episodic layer with keyword search** (`MemoryNote`,
   `MemorySearch`, `episodic.search: keyword`), and run-kind gating.
6. **`keel.consolidate`** and the `memory.store_changed` trigger, first
   for `user` stores (low risk), then `team` under
   `consolidation_then_human`. Promotion from the episodic layer needs
   step 5's recall counts.
7. **Hybrid search**, when an `../eval.md` case on real episodic stores
   shows keyword search missing what a user asked about (a different
   wording, another language). Hermes ships without it; OpenClaw ships
   with it on by default. Measure before choosing.
8. **The selector** and **rule-matched triggers**, only when some
   store's index stops fitting its budget.

### 16l. Open questions

- **Personal-data classifier (§16f step 4).** Which classifier, and
  what its false-positive rate does to the team proposal queue. Without
  it, step 4 is a prompt rule, and the moderators carry the risk.
- **Interactive vs hands-off for `user` writes.** §16d uses "a run started
  by a live user message" as the test. A Lens chat run that hands off to
  `lens.investigate` keeps the user waiting, so the investigate stage
  probably counts as interactive. It needs a definition in
  `triggers-and-runs.md` rather than one per use case.
- **Team membership changes.** When a person leaves a team, their past
  writes stay (they were moderated), but should their open proposals be
  dropped? Probably yes; not yet argued.
- **Keyword or hybrid by default (§16k step 7).** The two always-running
  agents disagree, and neither publishes a comparison. LongMemEval
  (arXiv:2410.10813) is the obvious public benchmark for the episodic
  layer.
- **Episodic retention and the right to be forgotten.** A year of a
  user's notes is personal data. OpenClaw's `memory forget --session`
  removes everything derived from a session by following lineage, and
  says what it cannot reach. Keel would need the same, plus redaction of
  the derived search index, before `retention_days` is longer than a
  few months.
- **Cross-deployment portability.** Claude Code ships agent-memory
  snapshots with sub-agent definitions. A published template could ship
  a seed `tool_group` store the same way. Useful for a shared Java tool
  group; not needed for v1.
