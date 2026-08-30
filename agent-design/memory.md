# Memory, learnings, and improvement requests

What survives a run, where it lives, who writes it, and what a later run
does with it.

This document supersedes [`medium.md`](./medium.md) §6 on three points —
where the store lives, how a learning is captured, and what a learning is
addressed to — and leaves §6's run shape, envelope and safety rules
standing. It also adds a channel §6 did not have: what an agent does with
a finding it cannot act on and no future run can use.

Grounded in [`../agent-memory-learning.md`](../agent-memory-learning.md)
(the topic research, second code pass 2026-08-30) and
[`../agent-tool-implementations.md`](../agent-tool-implementations.md) §12
(the tool layer). Where a claim here rests on a single source, it says so.

---

## 0. Three channels, and why they are three

The single most common failure in the field's memory systems is putting
things in a store that nothing will ever retrieve. Sorting by **addressee**
separates them cleanly, and the three answers want different machinery:

| Channel | Addressee | Lifetime | Retrieval | Mechanism |
|---|---|---|---|---|
| **Learnings** | a future run | until superseded or invalidated | selected into the run's resolved context | §2–§5 |
| **Improvement requests** | a human who maintains the subject | until acted on or declined | never — a request is not context | §6 |
| **Output feedback** | us, about the agent's own quality | telemetry | never reaches a model | out of scope here; `medium.md` §3e |

The boundary that matters is the first two. A learning is something a
future run should *do differently*; a request is something *somebody else
should fix*. "The `edit` tool mangles CRLF files" is not a memory — no
future run can act on it, and storing it means every future run reads a
complaint it cannot resolve. It is a request against the harness.

DeepSeek Harness states the third row's rule as a contract and it is worth
adopting verbatim: its `/feedback` remarks and per-message ratings are
"signals about the output, **never input to it**… Neither kind of feedback
reaches the model" (`../agent-memory-learning.md` §12). Quality signal and
agent context are different pipes.

---

## 1. What changed from `medium.md` §6, and why

§6 resolved the hard question — who writes cross-run memory, and how it is
kept from poisoning future runs — and that resolution stands: a separate,
outcome-triggered run, no filesystem, one schema-validated write,
provenance stamped harness-side, and the human-owned conventions file never
a write target. Four things move.

| §6 as written | Now | Why |
|---|---|---|
| The store is "a memory store", substrate unspecified | The store is a **tier of the context service**, which is the code/git/artifact proxy | §2. The proxy already resolves refs across every repo and Artifactory, so it can key knowledge the same way it keys code — and can select dependency-scoped learnings without the harness or the model doing anything |
| `applies_to` is `"repo"` or a path prefix | A structured **subject**: repo, path, dependency coordinate, or tool | §4a. The two missing scopes in the whole field (`../agent-memory-learning.md` §1) become cheap once the store is keyed by ref |
| Capture happens in the learnings run, from artifacts | Capture happens **in session**, at the end of the originating run; the learnings run **promotes** | §3. The participant is the best witness and the worst judge — split the two |
| Learnings reach runs via a `<learnings>` envelope tag | Learnings arrive as `tier: "learned"` sections in the ordinary resolution | §5. "Informs, never vetoes" stops being a rule and becomes a `binding` value |

---

## 2. The store lives in the context service

### 2a. Why there

[`context-files.md`](./context-files.md) §1b already establishes the
service as a normalising cache over `(source repo, ref)` — every tier
reduces to that pair, which is what makes caching, invalidation and
reproducibility one mechanism instead of three. The service is in fact the
code/git/artifact proxy: it has all repositories and Artifactory, and
already resolves and identifies a ref across them.

That makes it the only component in the design that can answer the question
a memory store actually needs answered: **what is this fact about, and is
that thing present in the run I am resolving for?** Not "which directory
was I in when I learned it" — which is the only key any store in the field
has (`../agent-memory-learning.md` §1). Concretely:

- A learning about `com.example:http-client:4.2.1` is stored at that
  coordinate. When resolving for a run, the service reads the repo's
  manifest or lockfile **at the ref it is already resolving** and selects
  learnings for the dependencies actually present. Neither the harness nor
  the model participates.
- A learning about a repo or a path is stored at that repo and path, with
  the SHA it was verified at — and the service, having the repo, can tell
  whether that path has changed since (§5b).
- Version comparison replaces guesswork about staleness. A learning
  recorded at `4.2.1` offered to a run on `4.3.0` can be offered *with the
  version it was learned at stated*, which is a far better signal than a
  timestamp because it is comparable.

The org and team standards tiers are already knowledge stored at refs in
this same service. A learned tier is the same idea with a different author
and a lower binding.

### 2b. A learning is a section

Learnings come back in `sections[]` (`context-files.md` §1b) like anything
else:

```
{
  "id": "learned/8f21c0…",
  "tier": "learned",
  "binding": "default",          // always; see below
  "title": "Integration tests need a live Postgres, not the mock",
  "body": "<Markdown, inert>",
  "bytes": 410,
  "scope": ["testing"],           // feeds the existing `kinds` narrowing
  "applies_to": ["services/ingest/**"],
  "source": {
    "subject": { "kind": "path", "repo": "…", "path": "services/ingest" },
    "learned_at": { "ref": "<SHA verified at>", "pr": 4412, "run": "…" },
    "evidence": "…",
    "recorded_at": "<ISO-8601>"
  },
  "derivation": { "method": "learned", "pipeline_version": "…",
                  "reviewed_by_human": false }
}
```

Five properties fall out of reusing the section contract rather than
building a parallel channel, and each replaces something §6 had to specify
separately:

- **`binding` is always `default`, never `policy`.** §6f's
  "learnings inform, they never veto" stops being a prose rule the
  orchestrator must honour and becomes a value the existing precedence
  machinery enforces (`context-files.md` §1a). A learned section cannot
  outrank a human-authored one, cannot be non-negotiable, and cannot be
  made so by anything the learnings run writes.
- **`kinds` and `paths` narrowing apply for free** (`context-files.md`
  §1b, "Narrowing, later"), including the finding that a *plan* is a
  better selector than a dispatcher declaration. The plan that says which
  packages and concerns a change touches selects its learnings by the same
  query that selects its standards.
- **Budget, provenance, the nonce envelope and the run record already
  cover it** (§2, §3, §4, §10). "Which learning applied to this run" is
  answerable by the mechanism that already answers "which rule applied".
- **`derivation.reviewed_by_human` is already a field.** It becomes the
  machine/human marker, and a deployment that wants human review before a
  learning is served has a place to express it with no new concept.
- **Write protection is correct by construction.** `context-files.md`
  §10a protects every repo section's `source.path`. A learned section has
  no repo path, so there is nothing to protect — and nothing for a coding
  run to edit even if it wanted to.

### 2c. The cost, stated plainly

Adding a machine-written tier breaks a property the service currently has:
**a resolution is no longer a pure function of `(repo, ref, team)`.** Two
runs at the same ref, a day apart, can legitimately get different learned
sections. That is not a bug — it is the point — but three things must move
with it, or §10's "which rule applied" answerability quietly stops holding
for the new tier:

1. **The learned tier carries its own version in `resolved_for`.** The
   response's single `version` is a version of the *human* corpus at that
   ref; the learned tier needs a second, independently advancing one.
2. **The run record pins both.** A run is reproducible only if you can
   re-resolve exactly what it saw, and "the learned store as of then" has
   to be nameable.
3. **The cache key includes it.** Otherwise a cached resolution serves
   yesterday's learnings at today's version, which is the silent-staleness
   failure this design keeps refusing elsewhere.

The alternative — the harness merging a learned block into a resolution it
did not produce — was rejected: it puts assembly in two places, gives the
learned tier none of the five properties above, and makes the run record
answer half the question.

---

## 3. Writing: capture in session, promote on outcome

### 3a. Why not `Complete`

Checked against the collection: **no completion tool anywhere carries
learnings.** Trae's `finish` takes one `summary`; Jules's `submit` takes
branch, commit message, title and description; Cline's `submit_and_exit`
and OpenHands' finish are the same shape. Every one carries only what a
human needs to accept the work. The one product that ships both
capabilities keeps them in different tools — Jules has `submit` *and* a
separate `initiate_memory_recording()`.

The reason is the addressee, and it is the same reason §0 splits the
channels. `Complete`'s report says **what happened**, for a human and for
the next run's envelope; a learning says **what should change**, for a
store. Folding the second into the first would also make the run's terminal
tool the place where a run grades itself, at exactly the moment it is least
able to (§3b).

`Complete`'s report stays what it is — and it is already the best
retrospective *input* in this design, which is the point: `verification[]`
carries commands and results, `judgment_calls` carries ambiguity resolved
and why. Codex spends most of a 569-line prompt inferring that from raw
rollouts (`../agent-memory-learning.md` §7). We have it as a schema.

### 3b. `Retrospect` — in-session capture

A tool available to coding and review runs after their work is done and
before `Complete`, producing **candidates, not learnings**.

```json
{
  "name": "Retrospect",
  "description": "Record one candidate learning from this run, before completing. Candidates are proposals, not memories: a later pass decides, with the outcome known, whether one becomes a learning. Recording nothing is the normal outcome.",
  "input_schema": {
    "type": "object",
    "properties": {
      "category": { "type": "string", "enum": ["repo_fact", "procedure", "failure_shield", "success_shield", "review_signal"] },
      "subject": { "$ref": "#/$defs/subject" },   // §4a — shared with ReportProblem
      "observation": { "type": "string", "description": "What was observed, in this run, as fact. Not what should be done about it." },
      "implication": { "type": "string", "description": "What a future run should do differently. One implication per call." },
      "evidence": { "type": "string", "description": "A command and its result from this run, a path plus the SHA read to confirm it, or a thread id and its outcome. A candidate whose evidence cannot be named is not recorded." },
      "confidence": { "type": "string", "enum": ["observed_once", "observed_repeatedly", "confirmed_by_human"] }
    },
    "required": ["category", "subject", "observation", "implication", "evidence", "confidence"],
    "additionalProperties": false
  }
}
```

Four deliberate choices:

- **`observation` and `implication` are separate fields**, not one
  `content` string. Every mature writer prompt in the field asks for
  evidence-first phrasing and none of them enforces it; two fields do.
  Claude Code gets the same effect by requiring a `**Why:**` and a
  `**How to apply:**` line and it is the highest-quality memory prose in
  the collection (`../agent-memory-learning.md` §2a).
- **`confidence` is stored here** and not in the final record. §6c argued
  against a confidence field on the grounds that nobody can act on it at
  read time — correct for a *learning*, wrong for a *candidate*, which
  exists precisely to be judged later. It is the recurrence signal, carried
  to the stage that can use it (§4b).
- **The tool is not terminal and does not gate `Complete`.** A run that
  records nothing completes normally; the final-turn nudge permits
  `Retrospect`, `ReportProblem` and `Complete`.
- **It is gated by a run digest** (§3d), so most runs are never prompted
  to reflect at all.

Precedent: Copilot CLI's `/subconscious run` (explicit, at session end),
Augment's documented "lightweight end-of-session ritual: batch pending
reviews at session end, when context is freshest", and Hermes's `/learn`,
which is explicit that the live agent does the work with the toolset it
already has — "there is no separate distillation engine and no model-tool
footprint" (`../agent-memory-learning.md` §2b2).

### 3c. The learnings run promotes; the transcript pass is the fallback

`medium.md` §6a's run shape is unchanged — outcome-triggered, no
filesystem, ref-pinned reads, one write tool. What changes is its input and
its job. It now receives the run's candidates in the envelope alongside the
existing blocks, and its job is **promotion**: decide, with the PR outcome
visible, which candidates became true.

This is the split both mature implementations shipped, arrived at from the
other end. Codex's Phase 1 is told to record preference *evidence* and "let
Phase 2 decide whether repeated signals add up to a stable user
preference." The reason to do the capture in-session rather than in Phase 1
is that we can: Codex's Phase 1 reads a rollout because it has nothing
better; we have the participant.

The division of labour, stated as the property that justifies it:

> The run that did the work is the best **witness** and the worst
> **judge**. It knows why the approach changed; it does not know whether
> the change was right. Capture where the evidence is; promote where the
> outcome is.

Codex states the judge half outright — an outcome where "only the assistant
claims success without validation" is labelled `uncertain`, and both mature
extractor prompts rank assistant messages below user messages and tool
output as evidence (`../agent-memory-learning.md` §2b).

**For runs with no candidates** — human-authored PRs, and our own runs from
before `Retrospect` — the learnings run falls back to the transcript,
processed with a lighter model, exactly as the four field consolidators do.
Two rules from `medium.md` §6 apply with full force here and nowhere else:
the transcript is the dirtiest input in the design, and the
data-not-instructions rule ships verbatim in the prompt. The fallback is
also where the cost is, which is another reason capture-in-session is worth
having: a run that captured its own candidates needs no transcript read at
all.

### 3d. The digest gate: most runs should produce nothing

Gemini CLI computes a model-free per-session digest — tool sequence,
touched paths, and whether a validation command passed, in ≤160 characters
— and routes on it, so "which of 50 sessions is worth reading" is answered
with no model call (`../agent-memory-learning.md` §2b). Codex does the
structural equivalent: whether Phase 2 runs at all is decided by **git
dirtiness of the memory workspace**, not by a database watermark.

We can do better than Gemini's version because it infers by regex what we
hold as a schema. The harness computes a digest from artifacts it already
has:

- `Complete.verification[]` — commands and results, no inference needed
- `Complete.judgment_calls` — ambiguity the run resolved
- `Narrate` entries with `kind: "detour"` (`medium.md` §2f) — an approach
  change, first-hand, at the moment it happened
- the changed-path set, and whether a verification failed and later passed

**No detour, no failed-then-passed verification, no judgment call → no
`Retrospect` prompt and no learnings run.** This is the cheapest cost lever
in the whole mechanism and it needs no model. The expected steady state is
that most PRs produce nothing, which is the field's own finding stated as
economics rather than as a prompt gate: Codex ("no-op is allowed and
preferred"), Gemini ("default to NO SKILL", 0–5 memory patches and 0–2
skills per run), DeepSeek ("days without a skill update are the workflow
behaving correctly, not a stall").

---

## 4. The record

### 4a. Subject: four kinds, one resolver

```
$defs.subject = {
  "oneOf": [
    { "kind": "repo",       "repo": "<id>" },
    { "kind": "path",       "repo": "<id>", "path": "<prefix>" },
    { "kind": "dependency", "coordinate": "<artifact coordinate>", "version": "<the version it was learned at>" },
    { "kind": "tool",       "tool": "<name>" }
  ]
}
```

- **`repo` / `path`** — as §6c's `applies_to`, unchanged in effect. A
  learning true of one service in a monorepo must not be recorded
  repo-wide.
- **`dependency`** — the axis no source in the field has. Resolved by the
  proxy against the manifest at the run's ref (§2a). `version` is
  mandatory: a learning about a library without the version it was learned
  at is not actionable, and the comparison is the staleness signal.
- **`tool`** — accepted by the schema and **routed to §6, not to the
  store**. A finding about our own tooling is a request, not a memory. The
  schema accepts it so the model has somewhere correct to put the thought;
  the harness converts it into a `ReportProblem` and tells the model it
  did.

### 4b. Categories, with structure and per-category gates

§6c's four categories become five, each with a required shape and its own
promotion gate:

| Category | Required structure | Promotion gate |
|---|---|---|
| `repo_fact` | observation + implication | `observed_repeatedly`, or `observed_once` with a pinned-SHA read as evidence |
| `procedure` | the command or sequence, and what it is for | must have run successfully in the originating run |
| `failure_shield` | **symptom → cause → what to do instead**, as three fields | the failure must have been observed *and* the alternative must have worked |
| `success_shield` | the approach, and what made it right here | the work must have merged, or the approach must have been explicitly accepted in review |
| `review_signal` | the finding, the thread outcome, and the follow-up diff verdict | a single occurrence qualifies (see below) |

Two additions worth arguing for.

**`success_shield` is new, and it is the one category we have better
evidence for than anyone.** Claude Code is the only source in the field that
records validated successes as well as corrections, and its stated reason is
a failure mode: an agent trained only on its own corrections "will avoid
past mistakes but drift away from approaches the user has already validated,
and may grow overly cautious" (`../agent-memory-learning.md` §2a). Its
evidence for a success is a user saying "yes exactly". Ours is a merged PR
with green verification and a review that did not object.

**`review_signal` drops the recurrence requirement, and only it.** The
field splits on this and both sides are right: a loop mining its own
trajectories has only frequency to distinguish durable from accidental, so
one occurrence is a data point; a loop whose evidence is a human verdict
that a diff demonstrably adopted has better evidence than any count.
DeepSeek states it — "a singleton may qualify; recurrence is not required" —
and its adoption test is exactly the one `medium.md` §6b already builds from
`<followup_diff>` (`../agent-memory-learning.md` §6, §8). So a `review_signal`
backed by a three-way thread verdict promotes on first sight, while a
`repo_fact` from our own run still waits for recurrence.

### 4c. `CreateMemory`, revised

The learnings run's single write, unchanged in posture from §6c —
schema-validated, harness-stamped provenance, no filesystem — with the
subject and category shapes above, `supersedes` retained, and two changes:

- **`keywords` is dropped.** It existed because retrieval was literal text
  matching against a flat block. Retrieval is now a query against the
  service by subject, `scope` and `paths`, and `scope` is the field the
  existing `kinds` narrowing already reads. A keyword list nobody queries
  is a field the model spends tokens inventing.
- **`evidence` gains structure where it can**: a `verified_at` SHA and,
  where the evidence is a file, the path. This is what makes §5b's
  mechanical staleness check possible, and it is free — the learnings run
  reads ref-pinned already.

Following Codex's `add_ad_hoc_note` (`../agent-tool-implementations.md`
§12c), the write is **create-only and rejects unknown fields**. A
correction is a new record with `supersedes` set, never an edit — which is
also DeepSeek's Agent Note rule, arrived at independently for records a
human will re-read years later: "a note is never edited into a different
decision" (`../agent-memory-learning.md` §9).

---

## 5. Reading

### 5a. Learnings arrive in the resolution

No `<learnings>` envelope tag, no read tool, no detail tier. Learned
sections arrive in `sections[]` with everything else, subject to the same
budget (`context-files.md` §2), the same nonce envelope (§4), the same
inlining rules (§8) and the same run record (§10). Three properties from
§6d survive intact and are now free:

- **The cap is enforced, not requested** — the budget mechanism already
  errors rather than truncating silently.
- **An empty learned tier injects nothing** — no tag, no instructions, no
  heading, matching Codex's read-path builder returning `None` on an empty
  store. A cold repo pays nothing for a capability with no content behind
  it.
- **The handling policy ships with the content**, not in the system
  prompt, so prompts are identical whether or not a repo has learnings.

**Sub-agents inherit learned sections exactly as they inherit conventions**
(`context-files.md` §8a) — with the one exception `medium.md` §6f already
establishes and this document keeps: **the validator does not receive
them.** Validator independence is what makes confirmation worth anything;
a learning is precisely the kind of prior argument it must re-derive
without. That exclusion is now expressible as a resolution parameter rather
than as an assembly rule.

A note on per-role scoping: Claude Code stores memory per sub-agent type
(`agent-memory/<agentType>/`, three scopes, its own `MEMORY.md`) and it is
a good fit for our fixed review roles — a `security` finder accumulating its
own `review_signal`s. It needs no new mechanism: `scope` on the section and
the lens name on the request is the same `kinds` narrowing the fan-out
already uses. Worth doing when there is enough signal per role to be worth
separating, not before.

### 5b. Staleness, computed rather than declared

Two mechanisms, both cheap, and the second is available to us and to nobody
else in the field.

**Age in words, not timestamps.** Claude Code computes elapsed days from
`mtime` and renders `"47 days ago"`, with the reasoning in the source:
"models are poor at date arithmetic — a raw ISO timestamp doesn't trigger
staleness reasoning the way '47 days ago' does." It suppresses the note
entirely below two days, because a warning on a fresh memory is noise. The
motivating report is worth keeping in mind when deciding whether this is
worth the tokens: stale `file:line` citations asserted as fact, where **the
citation made the stale claim sound more authoritative, not less**
(`../agent-memory-learning.md` §9).

**Evidence drift, from the ref.** Every record carries the SHA it was
verified at, and the service has the repository. So it can answer, for
free, at resolution time:

- for a `path` subject: has anything under that path changed between
  `verified_at` and the run's ref?
- for a `dependency` subject: is the version resolved for this run the
  version it was learned at?

A learning whose evidence has not moved is served plain. One whose evidence
has moved is served with that stated: *"recorded against
`services/ingest/loader.py` at `a1b2c3d`; that path has changed since."*
This is the staleness problem solved with a comparison instead of a
heuristic, and it exists only because the store is keyed by ref in a service
that holds the code. It also gives the consolidation pass (§6e of
`medium.md`) a mechanical re-check target rather than a model's judgment
about what looks old.

---

## 6. `ReportProblem` — the improvement-request channel

### 6a. What it is for

A hands-off agent that hits a broken tool, a misleading tool description, a
dependency whose documented behaviour is wrong, or a conventions section
that contradicts the code has, in this design as it stands, exactly two
options: work around it silently, or write a sentence in a report that
nobody reads twice. `AskUser` is reserved for blocking ambiguity *in the
task*, and correctly so. Neither produces a durable record and neither
reaches the person who maintains the thing.

Devin's `report_environment_issue` is the only first-class precedent in the
field, and the shape it settled on is the one that survives an unsupervised
run: **report and continue.** "Use this to report issues with your dev
environment as a reminder to the user so that they can fix it… It is
critical that you use this command whenever you encounter an environment
issue," paired with the main prompt's "Then, find a way to continue your
work without fixing the environment issues… **Do not try to fix environment
issues on your own**" (`../agent-memory-learning.md` §12).

```json
{
  "name": "ReportProblem",
  "description": "Report a defect or a missing capability in something you cannot fix and a future run cannot work around: the harness or a tool, a dependency, a conventions section, or this repository's setup. Reporting is not blocking unless you set priority to blocker. After reporting anything less than blocker, continue the task — work around the problem rather than fixing it.",
  "input_schema": {
    "type": "object",
    "properties": {
      "subject": { "$ref": "#/$defs/subject" },
      "priority": { "type": "string", "enum": ["note", "impairment", "blocker"],
        "description": "note: worth someone knowing, cost you nothing. impairment: you worked around it and the workaround cost turns or quality. blocker: you cannot complete the task and no workaround exists." },
      "problem": { "type": "string", "description": "What is wrong, as observed. Include the exact input and the exact result." },
      "expected": { "type": "string", "description": "What you expected instead, and why." },
      "workaround": { "type": "string", "description": "What you did instead. Required unless priority is blocker; at blocker it must be absent, since the claim is that no workaround exists." },
      "evidence": { "type": "string", "description": "The tool call and its result, the command and its output, or the section id and the code that contradicts it." }
    },
    "required": ["subject", "priority", "problem", "expected", "evidence"],
    "additionalProperties": false
  }
}
```

The `workaround` conditional is **enforced by the tool, not by the
schema** — `required` cannot express "present at two of three enum values
and absent at the third" without an `if`/`then` construction that several
model families render badly (`../agent-tool-implementations.md` §3a). The
rejection message states the rule, per the errors-are-prompts posture
(`../agent-tool-implementations.md` §7):
*"`blocker` asserts that no workaround exists, so `workaround` must be
omitted. If you worked around it, this is an `impairment`."* That wording
is doing real work — it is the guard against "this was hard" becoming
"this was blocked".

Callable at any point in a run, by any entrypoint, including sub-agents.
Unlike `Retrospect` it is not end-of-run: the moment of failure is when the
evidence exists.

**Naming**: `ReportProblem` rather than `Feedback` deliberately. DeepSeek
uses "feedback" for the human→vendor signal that by contract never reaches
the model; using the same word for the agent→maintainer direction would
blur exactly the distinction §0 is drawing. `RaiseIssue` was rejected for
colliding with `WriteJira`.

### 6b. `blocker` suspends, and it reuses machinery that exists

At `blocker`, `ReportProblem` is **terminal**, and the task suspends with a
wake predicate on the report's resolution — one more predicate kind
alongside `medium.md` §4c's `jira` / `build` / `pr` / `timer`. Suspension
mechanics carry over from `formats.md` §5 unchanged: no `Complete`, the
harness records the envelope, transcript and wake condition, and the
resumed run receives a `<resumed_event>` describing what was fixed. §4c's
suspension-cycle cap and maximum park duration apply, and matter more here:
a task parked on a defect nobody triages must eventually fail honestly back
to a human rather than sleep forever.

Two guards, both from §4c's own stance:

- **Prefer being woken over waiting.** If a fresh run could redo the work
  once the defect is fixed, the right answer is a trigger and an honest
  failure, not a suspension. Suspension is for when *this* task's
  accumulated context must survive the fix — a half-done migration that
  hit a tool defect at file 40 of 60. The prompt must say this, or every
  hard run ends in a lazy blocker.
- **`blocker` requires that no workaround exists**, which is why
  `workaround` is required at the other two levels and forbidden-by-absence
  at this one. The schema makes the claim explicit rather than letting
  "this is hard" become "this is blocked".

### 6c. Requests are not context

A report is never retrieved by a future run, never enters a resolution, and
never becomes a learned section. It goes to a queue a human triages. The
only path from a report into any future run's context is a **human
promoting it** — into the harness (fix the tool), into the corpus (edit the
conventions section), or into a tracker (`WriteJira` already exists for the
cases where that is the right destination).

That closes a hole `context-files.md` §10a leaves open. §10a makes `Edit`
and `Write` refuse against a conventions path, which is right, and leaves a
run that concludes a convention is *wrong* with only `AskUser` and its
report. A `ReportProblem` against a section id is the sanctioned way to say
so — durable, addressed to the section's owner, and with no write path to
the section itself.

It also gives us the mechanism DeepSeek's evidence says matters most.
`../agent-memory-learning.md` §8: mining human review comments produced
**zero** rule changes across 426 feedback items, while every actual change
to the review criteria arrived in the ordinary PR that established the
convention — written by the person who knew, able to *replace* a rule
rather than only append one. A promoted `ReportProblem` is that path with
an agent as the reporter and a human as the author.

---

## 7. What stays out

- **No vector store.** Unchanged and now better evidenced: no first-party
  implementation in the field retrieves memory by embedding similarity, and
  the two with the deepest stores use grep and a small model respectively
  (`../agent-memory-learning.md` §4).
- **No memory tool on working runs.** Three products have removed one and
  none has added one (`../agent-tool-implementations.md` §12a). Working
  runs read learnings as context and write candidates through
  `Retrospect`; they never search or edit the store.
- **No suppression.** `medium.md` §6f's informs-never-vetoes stands, now
  enforced by `binding`. Revisit only with §3e outcome data, per
  `future.md`.
- **Learnings never reach the validator.** §5a.
- **The machine store never becomes the conventions corpus.** A learned
  section is `tier: "learned"`, `binding: "default"`,
  `reviewed_by_human: false`, and no write path promotes it. Note this is
  now a *contested* position rather than the field's consensus: Claude Code
  writes machine-authored memory to a team-shared, org+repo-scoped store
  with no review queue, guarded only against secrets
  (`../agent-memory-learning.md` §9). The reason to hold the line here is
  specific rather than general caution — the conventions corpus is the
  authority a `conventions` review specialist reviews *against*, so a
  machine-written entry reaching it would not merely bias a future run, it
  would generate review comments on a real PR.
- **No `confidence` on the stored record.** §4b keeps it on the candidate,
  where something acts on it.

---

## 8. Build order

Each step is useful alone, and each is a prerequisite for the next.

1. **`ReportProblem` at `note` / `impairment`.** No store, no learnings
   run, no service change — a tool and a queue. It is the cheapest item
   here and it starts producing the signal that tells us what to build
   next: if the queue fills with tool defects, that is harness work, not
   memory work.
2. **The run digest** (§3d), computed from artifacts that already exist.
   Needed by everything after this, and independently useful as run
   telemetry.
3. **`Retrospect`**, gated by the digest. Candidates accumulate with no
   read path yet — which is safe, and gives a corpus to design the
   promotion gates against rather than guessing at them.
4. **The learned tier in the service**, read path first: promotion by hand
   from the candidate pool, so the read path is exercised and budgeted
   before anything writes to it automatically.
5. **The learnings run** (`medium.md` §6a) as the automatic promoter,
   which needs §3e finding-outcome telemetry for the review half.
6. **`blocker` suspension**, which needs `medium.md` §4c's generalized
   wake predicates.
7. **Consolidation** (`medium.md` §6e). Last, deliberately: DeepSeek's
   evidence is that the human-promoted path produced 100% of the value in
   the one repository observed running both, and an automatic consolidator
   over a store that is not yet growing is machinery with nothing to do.

## 9. Open questions

- **Learned-tier versioning and cache invalidation** (§2c) is specified as
  a requirement, not a design. It is the one piece here that genuinely
  belongs to the service rather than to this document.
- **Per-role learning scopes** (§5a) — worth doing when there is enough
  per-lens signal to separate; the mechanism is already available.
- **Whether a promoted `ReportProblem` should be able to become a learned
  section** — i.e. whether a human triaging "the `edit` tool mangles CRLF"
  can publish a *workaround* as a `tool`-subject learning rather than
  waiting for the fix. It would be useful and it reopens the boundary §0
  draws, so it needs an argument rather than a default.
- **Suppression**, still open, still gated on §3e outcome data.
