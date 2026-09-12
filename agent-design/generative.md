# What Forge takes from the generative-output research

[`../agent-generative-output.md`](../agent-generative-output.md) is a
drill-down on agents that make a *thing* — an image, a chart, a
dashboard, a prototype, a report someone reads. Forge does none of
that. It changes code and files findings.

This document exists because reading that pass against this design
turned up more that transfers than expected, and almost none of it is
about pictures. The transferable material is about **the boundary
between what the model authors and what the harness renders**, and
Forge crosses that boundary in four places it currently improvises:
`AddComment`'s body, `Complete`'s report, `AskUser`'s question, and the
suggestion-block degradation path. Every adoption below lands on one of
those four, or on a rule the whole surface obeys.

The rule of admission, applied throughout: **an item earns a place here
only if it changes a contract this design already has.** New tools,
new modes and new output genres are the roadmap's business
([`medium.md`](./medium.md), [`future.md`](./future.md)) and §4–§5 route
them there. Nothing in §2 adds a tool.

Two supersessions are recorded in §8, per
[`README.md`](./README.md)'s maintenance rules — neither is edited into
the document it replaces.

---

## 1. The one sentence the pass reduces to

`artifact-report`, on when to hand a destination a picture of a chart
rather than the numbers behind it:

> When the destination … renders live charts, hand it the rows (inline,
> or as an uploaded data file the chart cites) rather than a rendered
> PNG/SVG — a picture of a chart loses hover, data inspection and
> per-value comments.

Generalised, and adopted as a standing rule for every outward channel
Forge has:

> **The structured-representation rule.** Emit the most structured
> representation the destination can actually hold, and let the
> destination render. Where the destination cannot hold it, degrade one
> step and say so in the tool result.

The second clause is the one that keeps it honest, and it is not new to
this design — `AddComment` already does exactly that twice (anchor
validation falls back to a prefixed general comment; an unsupported
suggestion block falls back to a labelled fence, and the tool result
says which happened). What §1 adds is a *name* for the pattern and a
statement that it is general, so the next channel gets it by default
rather than by rediscovery.

Read against the existing surface, the rule sorts Forge's outputs into
a ladder, most structured first:

| Output | Most structured form the destination holds | One step down | Already implemented? |
|---|---|---|---|
| A fix that fully resolves a finding | committable suggestion block | labelled fenced code block | yes — `tools.md`, `AddComment.suggestion` |
| A finding's location | inline anchored comment | general comment prefixed `file:line` | yes — anchor validation |
| A review finding | the finding schema, rendered by the harness | Markdown the model wrote | yes — `formats.md` §4 |
| A plan | the plan schema in `Complete.report` | prose in `Complete.summary` | yes — `formats.md` §3c, §6 |
| A blocking question | **an option set with stable ids** | prose question | **no — §2d** |
| A long comment body | **a ref the harness renders or attaches** | inline Markdown | **no — §2a** |

The two gaps in that table are §2a and §2d. Everything else was already
right; it just did not know it was an instance of anything.

---

## 2. Adopted into v1

Five changes. None adds a tool; four are schema additions to existing
tools and one is a harness-side change to a gate that already exists.

### 2a. The ref rule applies to writes, not only reads

[`artifacts.md`](./artifacts.md) opens on two rules, and the second is
stated only for reads:

> **2. Bytes never enter context by default.** A non-write result that
> is non-trivial comes back as a **ref plus a preview of its shape.**

The research shows the same rule is needed in the other direction, and
shows the exact shape of the answer. `ArtifactData`'s write actions take
**either** an inline `data` object **or** a `file_path`, described as *"a
local JSON file whose top-level object is sent as the document — an
alternative to inline `data`, so a large document need not pass through
the conversation."* Its reads have the mirror image in `out_dir`, which
turns a multi-document read into a manifest of filenames the model can
then `Read` selectively.

Forge has one write path where this bites today. `AddComment.body` is a
required string, so a review summary comment carrying a twenty-row
findings table is authored token-by-token in the assistant turn, and
then sits in the transcript for the rest of the run. On a multi-stage
review that is the single largest thing the orchestrator writes.

**Change**: `AddComment` gains `body_ref`, and `body` becomes
conditionally required.

```jsonc
"body":     { "type": "string", "description": "Comment text, Markdown. Pass exactly one of body or body_ref." },
"body_ref": { "type": "string", "description": "A ref (artifacts.md §2) whose text is the comment body — use when the body is long or was produced by a tool rather than typed. Pass exactly one of body or body_ref." }
```

with a `oneOf` making exactly one of the two required, the same device
`suggestion`/`anchor` already uses for its conditional requirement.

Four constraints, all of which follow from rules this design already
has rather than from the source material:

1. **`body_ref` resolves through the same resolvers as `Read`.** No new
   scheme, no hostname from the model — `artifacts.md` §2a's closed
   scheme set is the whole security argument and this must not widen it.
2. **The harness echoes the resolved ref and the body's byte size in the
   tool result**, per `artifacts.md` §2c's echo-what-you-got discipline.
   A comment posted from a ref is a comment the model did not read back,
   so the result has to say what was posted.
3. **`suggestion: true` forbids `body_ref`.** A suggestion block commits
   its contents verbatim into someone's codebase; the existing
   description already forbids prose inside it, and a body the model
   never had in context is exactly the case where that rule cannot be
   checked. Schema-enforced, alongside the existing `anchor` condition.
4. **Above a configured byte threshold the harness attaches rather than
   inlines**, posting a short comment that names the attachment — and
   says so in the tool result. This is §1's degrade-and-say-so clause,
   and it is the reason `body_ref` is worth having beyond token savings:
   a 200 KB comment is bad for the *human* too.

`Complete.report` does **not** get the same treatment. It is a
structured object the harness renders, not a blob, and its size is
bounded by the finding schema; adding a ref there would create a second
way to say the same thing for no gain. Noted because it is the obvious
next move and it is wrong.

### 2b. A closed refusal vocabulary on every validating write path

The sharpest single artefact in the pass is `artifact-components`'
publish contract, which states its security policy as an **error
catalogue**: `script-not-blessed`, `unknown-data-island`,
`island-sentinel-ambiguity`, `banner-state-mismatch`. A model that gets
`unknown-data-island` back knows precisely which of two components to
drop. A model that gets "publish failed" learns nothing and retries the
same bytes.

This design already believes the underlying principle —
[`../agent-tool-implementations.md`](../agent-tool-implementations.md)'s
"errors written as instructions" is cited in `tools.md`, and several
tool results already degrade visibly with a prose explanation. What is
missing is that the explanations are **prose**, so nothing downstream
can branch on them and two runs describing the same refusal describe it
differently.

**Change**: every tool result that reports a harness-side refusal,
fallback or degradation carries a `refusal` field alongside its prose,
drawn from a closed vocabulary. The prose stays — it is what steers the
model — and the code is what the ledger, the eval harness and the
learned-memory tier can count.

The v1 vocabulary is small, because it enumerates refusals that already
exist rather than inventing any:

| Code | Raised by | Today's behaviour |
|---|---|---|
| `anchor-not-commentable` | `AddComment` | posts as a general comment prefixed `file:line` |
| `suggestion-unsupported` | `AddComment` | posts as a labelled fenced code block |
| `body-attached` | `AddComment` | body exceeded the inline threshold (§2a) |
| `head-moved` | `AddComment` | posts anchored to the reviewed commit (`review.md` §8) |
| `git-write-blocked` | `Bash` | the git-write blocklist refused the command |
| `edit-match-not-unique` | `Edit` | the `old_string` matched more than once |
| `edit-match-not-found` | `Edit` | the `old_string` matched nothing |
| `ref-unauthorised` | `Read`/`Grep` | the resolver refused; distinct from not-found (`artifacts.md` §2a) |
| `payload-spilled` | any read | the result exceeded the cap and came back as a ref (`artifacts.md` §4) |
| `tool-not-registered` | any | called a tool this run's mode does not wire |

Three rules govern it, and they are the part worth arguing about:

- **Closed set, versioned with the tool surface.** A new code is a
  schema change. An open string field would become a second, worse prose
  channel within a month.
- **A code names what the harness did, never what the model should do
  next.** `anchor-not-commentable` says the anchor was not commentable;
  the prose says the comment was posted as a general comment instead.
  Codes that encode remedies go stale against the harness that raises
  them.
- **Success is not coded.** There is no `ok`. A `refusal` field present
  at all means something did not happen as asked, which makes "did this
  run hit any degradation" a field test rather than a text search.

The immediate payoff is in [`eval.md`](./eval.md): "how often does anchor
derivation fail on this fixture set" becomes a count instead of a
regex over transcripts. The second payoff is in
[`memory.md`](./memory.md), whose capture-in-session step currently has
to recognise a problem from prose.

### 2c. The completion gate gets a computed half

`dataviz` ships `scripts/validate_palette.py` and a byte-equivalent
`.js`: given a palette, a mode and a surface colour, it computes — *"never
eyeballs"* — OKLCH lightness bands, a chroma floor, OKLab ΔE between
slots under Machado–Oliveira–Fernandes (2009) severity-1.0 protan/deutan
simulation, a normal-vision worst-pair floor, and WCAG contrast. It
distinguishes hard FAIL from WARN bands, exits non-zero only on FAIL,
**documents the two checks it cannot make from hex values alone**, and
names the calibration swap that would silently invalidate its
thresholds.

The generalisation is not about colour: **find the part of a judgement
that is arithmetic, and ship it as an exit code.**

Forge already has the right place to put one. `tools.md`'s `Complete`
gate — the first `Complete(status: "done")` in `implement` mode returns
a fixed checklist instead of ending the run — is deterministic in
*firing* but entirely prompted in *content*: three things to go and
check, with nothing checking them. Half of that checklist is arithmetic
the harness can do before the model is asked anything.

**Change**: the checklist the gate returns is prefixed by a **computed
findings block**, and the prompted questions are narrowed to what the
computation cannot reach.

Computed, from state the harness already holds:

| Check | Computed from | Severity |
|---|---|---|
| Untracked or modified paths outside the run's `paths` scope | `git status` against the envelope's scope | **FAIL** |
| Files written outside the working tree and the scratch directory | write-path log | **FAIL** |
| Scratch-directory paths referenced from a tracked file | grep of the diff for the scratch prefix | **FAIL** |
| Placeholder tokens introduced by this run's diff (`TODO`, `FIXME`, `XXX`, `lorem`, `<<<<<<<`) | the diff, added lines only | WARN |
| Verification commands claimed in `report` that this run never executed in `Bash` | transcript tool-call log | **FAIL** |
| Diff touches the conventions file | `context-files.md`'s structural write protection | WARN |

Still prompted, because nothing above reaches them: *did the change do
what the ticket asked*, *are the verification commands the right ones*,
*is anything you changed unintended even though it is in scope*.

Four properties carried over deliberately from the validator:

1. **FAIL and WARN are different things.** A FAIL blocks the second
   `Complete` until it is resolved or explicitly overridden in the
   report; a WARN is reported and does not block. The validator's
   reasoning applies exactly — some problems are compensable and some
   are not, and collapsing the two produces a gate people route around.
2. **The block lists what it did *not* check.** One line, fixed text,
   naming the prompted half. A gate that presents a clean computed
   result with no coverage statement reads as "verified" and is the
   failure mode `agent-self-verification.md` catalogues.
3. **No model call.** The existing gate's whole argument
   (`agent-self-verification.md` §2, SWE-agent's `review_on_submit_m`)
   is that a mechanical gate cannot be talked out of firing. Adding an
   LLM judge here would forfeit that.
4. **The placeholder check is added-lines-only.** A `TODO` the run did
   not write is not this run's finding. The dataviz validator's
   `--pairs adjacent` default is the same instinct: scope the check to
   what the decision actually turns on, and make the wider scope opt-in.

This does not change when the gate fires, what statuses skip it, or the
reset rule after `Edit`/`Write`/`Bash`. It changes only what the gate
*returns*.

### 2d. `AskUser` posts a decision record, not a prose question

The `workshop` skill runs a decision loop through a published document:
choices are rendered as option rows, a confirmed choice republishes the
page, and the session reads the answer back through a named schema
(`read_page_data`, schema `workshop-decisions`) rather than by parsing
prose. The structural insight is not the page. It is that **the question
and the answer share a schema, so the resume path does not have to
interpret free text.**

That is a direct hit on a real weakness in
[`formats.md`](./formats.md) §5. Today `AskUser` takes an optional
`options` array of plain strings; the harness formats the whole thing
into a comment; a reply lands; the harness appends the reply text
verbatim as `<resumed_answer>`. Forge then reads prose and infers which
option — if any — the human meant. Three failure modes follow from that
and all three are avoidable: a reply that names an option by a different
phrase, a reply that answers a different question than the one asked,
and a reply that arrives after the plan it was about has moved on.

**Change**, in three parts.

**(i) Options get stable ids.** `AskUser.options` becomes an array of
objects rather than strings:

```jsonc
"options": {
  "type": "array", "minItems": 2, "maxItems": 4,
  "items": {
    "type": "object",
    "properties": {
      "id":    { "type": "string", "description": "Short stable id, kebab-case. Quoted back by the harness and matched against the reply." },
      "label": { "type": "string", "description": "The choice, one line." },
      "implication": { "type": "string", "description": "Optional: what picking this changes about the work." }
    },
    "required": ["id", "label"], "additionalProperties": false
  },
  "description": "Optional: 2-4 concrete choices, if the question reduces to one. Omit for an open-ended question."
}
```

The harness renders them as a numbered list with the ids visible, so a
human can reply `plan-b`, `2`, or a sentence, and the first two resolve
without interpretation.

**(ii) The resume envelope carries a resolution, not just text.**
`<resumed_answer>` gains two attributes the harness fills:

```xml
<resumed_answer option_id="keep-legacy-endpoint" match="exact">
  Keep the legacy endpoint for now — we have two customers on it.
</resumed_answer>
```

`match` is a closed enum: `exact` (the reply named an id or its number),
`inferred` (the harness matched prose to an option with a documented
rule), `none` (no option matched — open-ended reply, or the human
answered something else). The reply text is *always* carried in full
regardless; the attributes are an aid, never a replacement, because a
human who picks option 2 and then explains a constraint has said two
things and only one of them is an id.

`match="none"` is the important value, not `exact`. It is the signal
that says *the human did not answer the question you asked*, which is
precisely the case `formats.md` §5 step 4 already anticipates ("a
non-answer, a deflection, a reply that raises a new question") and
currently leaves Forge to detect by reading.

**(iii) The question carries the draft, when there is one.** This is the
`workshop` lesson proper: the page the reader decides on *is* the
evolving plan, so the decision is never asked in a vacuum. For Forge, in
`plan` mode, an `AskUser` whose answer changes a plan Forge has already
partly formed posts **that plan so far** alongside the question — as a
`body_ref` attachment (§2a) when it is long. New optional field:

```jsonc
"draft_ref": { "type": "string", "description": "Optional, plan mode: a ref to the plan-so-far, posted with the question so the human decides against the actual draft rather than a summary of it." }
```

A human asked "should the migration be online or offline?" with the
seven-step plan attached answers a different and much better question
than one asked cold. The cost is one attachment; the benefit is the
thing `workshop` is built entirely around.

Not adopted from `workshop`: the round-trip republish, the decision
island, and the "start building" affordance. Those need a page runtime
Forge does not have and §4 routes to the roadmap.

### 2e. Skills, if they ever arrive, execute rather than read

[`context-files.md`](./context-files.md) §12 covers the programmatic
context channels v1 deliberately does without — MCP server
`instructions`, skills, hooks, plugins — and states four rules for
whichever of them is added later. The pass supplies a fifth, from
`webapp-testing`:

> Always run scripts with `--help` first … DO NOT read the source until
> you try running the script first and find that a customized solution is
> absolutely necessary. These scripts can be very large and thus pollute
> your context window. They exist to be called directly as **black-box
> scripts** rather than ingested into your context window.

**Fifth rule, added to `context-files.md` §12**: *a skill's instructions
are read; a skill's code is executed.* A bundled asset is addressed by
path and invoked; it is never `Read` into context to find out what it
does, and the skill's own text is responsible for saying what it does
and what its interface is.

This is what makes the size of a skill irrelevant to its context cost,
and the evidence is concrete: the `pptx` skill is ~1.1 MB, almost all of
it ISO-IEC 29500-4 XSD schemas and ~875-line validators, and none of it
is meant to be read by the model. `paint` bundles a 1,469-line toolkit
and points the model at a 66-line reference instead, adding *"Do not
paste either into the conversation."*

The rule has a corollary worth writing down next to it, because it is
what makes the rule safe rather than merely cheap: **an executable a
model invokes without reading is a trust decision, so it is subject to
the same provenance rules as any other instruction channel.** §12's
existing rules about where a channel's content may come from apply to
the binary, not just to the prose.

---

## 3. One rule to state once, not five times

§1's structured-representation rule is written into
[`formats.md`](./formats.md) §8, next to the tool-result shape, as a
single paragraph, and the four places that already implement it
(suggestion fallback, anchor fallback, finding schema, plan schema)
gain a one-line back-reference rather than restating it.

The reason for stating it centrally rather than per-tool is the reason
`tools.md`'s granularity rule is stated centrally: the next channel
Forge grows — a CI summary, a responder reply, a published briefing —
should inherit the rule without anyone deciding to apply it. Four
independent implementations of one rule is how a design ends up with
four slightly different behaviours.

---

## 4. Promoted to `medium.md`: the published briefing

One roadmap item, with a real trigger rather than a speculative one.

**What.** A `Publish` tool and one page type: a **review briefing** — a
shareable page carrying the review's bottom line, the findings grouped
by severity, the reviewer judgment calls, and the diff regions to look
at. `artifact-pr-review` is a worked instance of exactly this genre,
down to the shape (*"what the PR changes and why, what needs the
reviewer's judgment, and where to look — readable in two minutes without
opening the diff"*).

**Why it is not v1.** It is a new outward channel with a new runtime,
and this design's leanness rule says a channel earns its place from a
deployment need. The need is visible but not yet present: a
multi-stage review that produces thirty findings across nine files
currently reaches a human as thirty comments, and the synthesis exists
only in `Complete.summary`, which the harness may or may not post
anywhere.

**The trigger to watch**, stated so it can be recognised rather than
argued: the first deployment where review output is read somewhere other
than the PR itself — a weekly quality review, a release readiness check,
anything that reads across PRs.

**What the design already fixes if it is built.** Four things, all from
the pass, so this item is a sketch rather than a blank page:

1. **Template-fill with FIXED and VARIABLE regions, creation-only.** The
   `artifact-*` family's five-step recipe: read the template, replace
   each named slot, adapt beyond the slots, self-check mechanically,
   publish. The non-obvious half is *creation-only* — *"When editing an
   existing dashboard artifact, work with its current HTML directly —
   don't re-read or re-apply this template"* — which is what stops an
   edit silently reverting a customised page to the template. A
   hands-off agent gets one generation, so the template is doing the
   work an iterative loop would otherwise do.
2. **Body fragments, not documents.** The skeleton is the harness's;
   the model fills a fragment and therefore cannot get the document
   scaffolding, the theme handling or the CSP wrong.
3. **Named refusal codes on publish** — §2b's vocabulary extends rather
   than restarts.
4. **The honesty rules travel with the genre.** `artifact-pr-review`'s
   provenance note is the one to copy verbatim into the brief: in the
   internal prototype it was ported from, state signals were *"computed
   deterministically by a backend; this skill has no backend, so the
   page must never present inferred state as computed state."* A
   briefing that renders a model's judgement in the same visual language
   as a measured signal is lying by layout, and Forge's findings are
   overwhelmingly the former.

---

## 5. Tracked in `future.md`

Three items, each with the measurement or dependency that would move it.

**5a. The `content` / `structuredContent` split.** MCP Apps (SEP-1865)
is the right answer to the whole payload-projection problem — the tool
result carries a model-facing `content` and a renderer-facing
`structuredContent` that the spec says is *"not added to model
context"* — and it is the first time the protocol specifies the
projection that
[`../agent-tool-result-transport.md`](../agent-tool-result-transport.md)
found every client inventing. It is blocked on a version ceiling this
design has already measured: [`adk.md`](./adk.md) §0 records that
ADK-Java pins MCP SDK `1.1.2` and that `ProtocolVersions.java` declares
no `MCP_2026_07_28` constant at all, in either the 1.x or 2.x line.
**Moves when**: the Java SDK ships the constant and ADK's pom advances
past it.

The idea worth stealing *before* that, and cheaply, is
`visibility: ["app"]` — a tool the renderer may call that the host
**MUST NOT** put in the model's tool list. Forge's equivalent question
is whether a published briefing's own refresh path needs to be a tool
Forge can see. It does not, and saying so now is free.

**5b. A local preview before an outward write.** The shipped Claude Code
binary contains an `Artifact` action the live tool schema does not
expose: `preview`, which *"renders that one page file locally the way
publish wraps it, in light and dark themes at desktop and phone widths,
and returns the screenshots with a mechanical checklist of layout and
load problems."* Note the pairing — screenshots **and** a mechanical
checklist, so the model is not the only judge — and that it states its
own blind spot (capability calls fail in preview; check them after
publishing).

Forge has no page to preview, but the pattern generalises to any
outward write with a rendering step: **render it the way the destination
will, locally, and return the render plus a computed checklist, before
committing to the side effect.** The nearest v1 candidate is
`AddComment`'s Markdown → ADF conversion, which today is a
harness-side concern Forge never sees the output of. **Moves when**:
`eval.md` shows conversion-fidelity failures are real rather than
theoretical.

This is also the pass's third independent sighting of this collection's
**built-but-not-switched-on** pattern in Claude Code, after
`yoloClassifier` (`agent-permissions-approval.md`) and the adversarial
verification subagent (`agent-self-verification.md`). The methodological
note from `agent-tool-implementations.md` holds: source-reading
establishes what was built; probing establishes what is switched on.

**5c. The verified-lane / free-lane split.** `artifact-components`
prices its own escape hatch: a component using its own data island
publishes in the ordinary lane where custom scripts are allowed and the
verifier's constraints do not apply — *"but the session's
`read_page_data` workshop-decisions schema does not read such an island,
so decisions recorded there need their own read-back path."* Two lanes,
with the cost of the loose one stated rather than implied. If Forge ever
publishes anything, it needs the same split and the same honesty about
it. **Moves when**: §4 ships.

---

## 6. Considered and rejected

**In-band delimiters for artefact delivery.** The `:::artifact{…}` /
`<boltArtifact>` lane, where the payload rides inside the assistant
message and the host scans it out. Rejected on three counts, all
observable in the sources rather than predicted: the payload is charged
to context twice (authored, then carried in history); the delimiter
grammar is load-bearing enough that LibreChat ships an entire *"Common
mistakes to avoid: Don't split the opening `:::` line; Don't add extra
backticks outside the artifact structure; Don't omit the closing
`:::`"* block — and only to its OpenAI-family models, not its Anthropic
ones, which is a per-model-family dialect split in an *output* format;
and the failure mode is a half-rendered artefact rather than an error.
§2a's `body_ref` is the same capability with none of that, because a
ref is a name and a name has no fence.

**A prompted fake user turn to force a revision pass.**
`canvas-design`'s final step fabricates a user utterance —
*"**IMPORTANT**: The user ALREADY said 'It isn't perfect enough…'"* — to
force a second pass, then constrains that pass to refine rather than
add. The underlying observation is correct and matches this design's own
research: a one-pass generative agent stops at "acceptable." The
mechanism is not adopted. Forge's transcript is evidence a human reads
and the ledger stores; putting words in the user's mouth inside it
corrupts the record for a gain that §2c's gate achieves honestly — a
mandatory second pass whose move set is narrower than the first's, which
is exactly what the `Complete` checklist already is.

**A diffusion-model image tool.** Recorded not because it was
tempting but because the pass makes the boundary unusually legible.
Anthropic's nine published creative skills contain **zero**
image-model calls and draw everything by writing a program; every
app-builder in `leaked/` ships a diffusion tool and no drawing toolkit.
The split is not about capability, it is about whether the image is
*content* (a hero photo — a plausible picture is the requirement) or
*information* (a chart, a diagram — a specific arrangement of specific
elements is the requirement). Everything Forge could ever want to draw
is the second kind, so the route is code, and the route to code it
already has is `Bash`. There is nothing to add.

**Per-page-type skills as a v1 structure.** Anthropic has at least
fourteen output genres each with its own skill, template, slot table and
honesty rules. That is a bet that most requests fall into a small number
of genres and that a genre's accumulated rules beat generality — and it
is a good bet for a *hands-off* agent, which gets one generation. Forge
has exactly two genres today (a review finding, a plan) and both are
already schemas with harness-side rendering, which is the same idea at
the right scale. Revisit only if §4 ships and a second page type
follows.

---

## 7. What this document does not change

Stated explicitly so the absences read as decisions:

- **No new tool.** The v1 surface stays at 11.
- **No new mode, no new run source, no new sub-agent type.**
- **No change to the completion gate's trigger, reset rule, or status
  semantics** — only to what it returns (§2c).
- **No change to `Complete.report`'s shape.** §2a's ref channel is
  `AddComment`-only, deliberately (§2a, closing note).
- **No change to `artifacts.md`'s scheme set.** `body_ref` resolves
  through the existing closed set; adding a scheme to serve an outward
  write would forfeit the property that makes the namespace safe.
- **No page runtime, no publish path, no `window.*`-style capability
  model.** §4 and §5c hold the whole of that, behind a named trigger.

---

## 8. Supersessions and decision rows

Per [`README.md`](./README.md)'s maintenance rules, a decision is never
edited into a different decision.

**Superseded.** Two, both narrow:

1. **`tools.md`, `AddComment.body` required.** Superseded by §2a:
   exactly one of `body` / `body_ref`. The original decision — one
   Markdown string, harness converts to the platform's native format —
   stands entirely; what changes is where the string comes from.
2. **`formats.md` §5, `<resumed_answer>` as bare text.** Superseded by
   §2d(ii): the tag gains `option_id` and `match`, and the reply text is
   still carried verbatim. The suspend/resume mechanics, the comment-id
   keying, the no-`Complete`-on-suspension rule and the budget
   interaction are all unchanged.

**Decision rows to add to `README.md`'s log**, in that table's format:

| Decision | Chosen | Rejected alternative(s) | Rationale |
|---|---|---|---|
| Long outward payloads | `AddComment` takes `body` **or** `body_ref`, a ref through `artifacts.md`'s existing closed scheme set; above a threshold the harness attaches and says so | Inline-only (today's v1); a general `Publish` tool; extending the ref channel to `Complete.report` | `artifacts.md`'s "bytes never enter context" was stated only for reads. `ArtifactData`'s `data`-or-`file_path` pair is the worked precedent, described in its own schema as existing "so a large document need not pass through the conversation." `Complete.report` is excluded because it is a bounded structured object, not a blob — a ref there is a second way to say one thing |
| Degradation reporting | A closed `refusal` code alongside the existing prose on every harness-side refusal or fallback; no `ok` code | Prose only (today's v1); an open string field; a per-tool ad-hoc shape | The prose steers the model and stays. The code is what `eval.md` counts and `memory.md` keys on, and neither can branch on a sentence. `artifact-components`' publish verifier is the precedent: a security policy stated as a catalogue a model can program against. Open strings become a second prose channel |
| The `implement` completion gate | The fixed checklist is prefixed by a **computed findings block** with FAIL/WARN severities and a fixed line naming what it did not check | Keeping the checklist entirely prompted; adding an LLM judge to the gate; computing everything and dropping the prompted half | `dataviz`'s `validate_palette.py` is the model: compute what is arithmetic, separate compensable from non-compensable, and document the coverage gap. The gate's existing argument (SWE-agent's `review_on_submit_m`, `agent-self-verification.md` §2) is that a mechanical gate cannot be talked out of firing, which an LLM judge would forfeit |
| `AskUser` shape | Options become `{id, label, implication?}`; `<resumed_answer>` gains `option_id` + a three-value `match` enum; plan-mode questions may carry `draft_ref` | Plain-string options (today's v1); free-text parsing on resume; a full workshop-style republish loop | The `workshop` skill's structural claim is that the question and the answer share a schema, so resume does not interpret prose. `match="none"` is the valuable value — it detects the non-answer `formats.md` §5 already anticipates but leaves Forge to spot by reading. The republish loop needs a page runtime; §4 holds it |
| Skills, if added later | Fifth rule for `context-files.md` §12: a skill's instructions are read, its code is executed and never `Read` into context — and the executable is a trust decision under §12's existing provenance rules | Treating bundled code as ordinary readable context | `webapp-testing` states it directly ("black-box scripts rather than ingested into your context window"); the `pptx` skill's ~1.1 MB of XSD and validators is the evidence that skill size is only irrelevant to context cost if this rule holds |
| Artefact delivery channel | Refs and schemas; **never** an in-band delimiter grammar in the assistant message | `:::artifact{…}`-style directives (LibreChat, Claude.ai's original prompt); `<boltArtifact>` tags | Charges the payload to context twice; the delimiter grammar is load-bearing enough to need a per-model-family error-recovery block in the prompt (LibreChat ships one to OpenAI-family models only); failure renders half an artefact instead of erroring |
