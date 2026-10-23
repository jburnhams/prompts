# Models: start cheap and quick, grow on demand

**Status: proposal, revised 2026-10-22. Nothing here is adopted yet.** The
research is in [`../agent-multi-model.md`](../agent-multi-model.md) and
[`../agent-deferred-tool-loading.md`](../agent-deferred-tool-loading.md).
This file says what Forge would change, what it would leave alone, and what to
measure first. It extends `medium.md` §3d (per-role models for review) and
§3d-i (plan strong, implement cheap).

## 1. The constraint that decides the design

**The quick case is the product.** A user who asks "what was revenue last
month?" wants an answer in seconds, from a cheap model, with nothing else in
the way. A design that makes that user pay for triage, a handoff, a stage
boundary, or a big prompt will lose them, however good it is on hard tasks.

So the rule for every mechanism below is: **it must cost the quick case
nothing it can avoid.** No triage call before the first token. No fixed
multi-stage pipeline in front of a one-line question. No tool catalogue the
quick case does not need. Power is added by the run asking for it, or by the
harness noticing it is needed, and only then.

This reverses an earlier draft of this file, which made `explore` (cheap) →
`answer` (strong) the default analysis path. That path is right for a request
that clearly wants a report, and is kept as one landing (§4). It is the wrong
front door.

## 2. Positions

1. **Every analysis run starts on the economy tier with a minimal tool set and
   a short data overview.** If that is enough, it answers and the run ends.
2. **Two hatches, named for what each does to the run.** `Expand` widens
   what the run can see (more data sources, more tools) and the run
   continues. `HandOff` ends the run and passes the question to a stronger
   one, or to a report. Both are tools the cheap model can call, and the
   harness can also trigger them itself (§5).
3. **The cheap model is the router, not a separate classifier.** It already
   reads the request. If the request says "make me a report", it calls
   `HandOff(report_requested)` as its first action. No extra model call, no latency.
4. **Width grows inside the run; power grows at a run boundary.** More
   sources arrive as text in a tool result, which changes nothing the
   provider caches. A stronger model never replaces the model mid-run: it
   takes a new run, started by `HandOff` with a handoff. That boundary is
   also the one place a large run's tools array can change without losing
   its prompt cache (`agent-deferred-tool-loading.md` §5). Adding *tools*
   inside a cheap run is possible, once, under conditions (§4a).
5. **Tiers, not model names.** Config names `economy`, `standard`, `strong`;
   the deployment maps them to model IDs. Vendor features (the Anthropic
   advisor tool, OpenAI tool search) may implement a tier but no prompt or
   schema depends on them.
6. **Coding and review keep per-role tiers** (§7), because their stages are
   named and the quick case there is not a one-line question.

## 3. What the quick run carries

| Part | Content | Why this much |
|---|---|---|
| Tier | economy | speed and cost |
| Tools | `DescribeSource`, read-only `RunSQL` against the described sources, `Expand`, `HandOff` (listed last). Final answer is plain text, or `Complete` where a run ledger is used | four tools, so loading them upfront is cheap and needs no deferral (Anthropic's guidance is 3–5 non-deferred) |
| Data overview | one line per source the user has, plus a last line: `N further sources are not listed here. If the question needs one, call Expand.` | the cheap model cannot ask for what it does not know exists; the last line is the whole cost of that |
| Prompt | a short analysis prompt: ground in the schema, show your SQL, state the row count, do not guess a join | DAB puts ~88–90% of wrong answers in planning or computing the query (`../agent-data-analysis.md` §12a) |
| Answer form | the number or table, then the SQL and the row count in the same message | Haiku's characteristic failure is plausible-but-wrong SQL, and nothing automatic catches it; showing the query lets the user |

Everything else (the rest of the sources, profiling and chart tools, joins
across sources, report writing, the provenance gate) is behind `Expand` or
`HandOff`, or triggered by the harness. `data.md` §2d's spill still applies on its own: a large result
becomes a `table://` handle without the model asking.

## 4. The two hatches

The quick agent has two tools for getting more than it started with. They
differ in what they do to the run, and the cheap model's choice is meant to be
a plain question: *do I need to see more, or does this need someone else?*
This section covers both tools and, more than that, **how the cheap model is
presented with them**: whether they are used when they should be, and not
when they should not, depends on that more than on any rule elsewhere.

### 4a. `Expand`: look further, keep going

```json
{
  "name": "Expand",
  "input_schema": {
    "type": "object",
    "properties": {
      "keywords": { "type": "string", "maxLength": 100, "description": "Optional. Words to narrow what is shown." }
    },
    "additionalProperties": false
  }
}
```

Description (about 35 words):

> Shows data sources and tools that exist for this user but are not listed.
> Use it when the question needs something the listed sources do not hold.
> Your run continues. Optional keywords narrow the result.

The result lists up to a configured number of matches (default 8), one per
item, in the same format as the data overview: name, grain, key columns, and
how to use it (`query with RunSQL, source=...` or `tool X is now available`).
If nothing matches it says so and points at `HandOff(too_complex)`. Source
descriptions come from source metadata, so they are untrusted text and are
framed as data like any other result.

**What `Expand` can show is what the user is already granted.** The hidden set
is granted-but-not-listed. A source the user cannot reach is never listed and
never revealed, and the executor checks the grant on every query whether or
not the source was shown (`tools.md`, "Granted, registered, visible").
`Expand` changes visibility, never authority.

Three kinds of widening, delivered three ways:

| What is revealed | Delivered as | Cache effect |
|---|---|---|
| A SQL-reachable source | text in the `Expand` result. `RunSQL` already accepts any granted source name; the executor checks the grant | none: messages only, any provider |
| A tool, on a provider with deferred loading | a `tool_reference` or `additional_tools` item | none |
| A tool, on a provider without it (Bedrock `Converse`) | the tools array grows **once**, at this call, to a fixed bundle (profile, fetch, table ops) | one cache miss on the prefix at that point |

The one growth is a deliberate exception to "the tools array is fixed for a
run" (`tools.md`), allowed only when all of these hold: the provider has no
deferral, the run is on the economy tier, and the cached prefix is below a
configured size (a guess to set from measurement; the prefix of a quick run is
a few hundred to a few thousand tokens, so the loss is a small absolute
cost). Note that provider cache minimums are low on current models (512
tokens on the newest Anthropic models; Bedrock publishes its own), so do not
count on a quick run being too small to cache. When any condition fails, the
result says the extra tools need a longer run and names `HandOff(too_complex)`;
sources are still revealed because they cost no array change. The bundle is
fixed in advance, so the array grows at most once per run.

`Expand` is the cheap widening, so it carries no cost warning. Its real cost
is clutter: more sources and tools lower selection accuracy (Anthropic puts
the drop at over 30–50 tools), which is why the result is capped and takes
keywords.

### 4b. `HandOff`: pass it on

```json
{
  "name": "HandOff",
  "input_schema": {
    "type": "object",
    "properties": {
      "reason": { "type": "string", "enum": ["too_complex", "report_requested"] },
      "why": { "type": "string", "maxLength": 300, "description": "One sentence: what you could not do, or what the user asked for." }
    },
    "required": ["reason", "why"],
    "additionalProperties": false
  }
}
```

Description (about 50 words, and the whole of what the tool says about
itself):

> Ends your run and passes the question to a run with wider access and more
> time. The user will wait longer, so use it only in the situations your
> instructions list, not for a detail you can state as an assumption. Nothing
> you write after calling it is shown.

Like `Complete` and `AskUser`, `HandOff` is the last action of a run. The
harness ends the run and starts the next one. The reason names the situation;
the harness chooses the landing:

| `reason` | Landing run | Tier | Tools and context |
|---|---|---|---|
| `too_complex` | `investigate`: an open-ended loop, try things, revise | standard, with a strong consultant at the plan and before concluding where the provider supports an advisor | every source and the full focused tool set from the start, `table://` refs, a larger turn budget |
| `report_requested` | `report`: collect (economy) then write (strong), the `explore` → `answer` split from `data.md` §2g | economy then strong | refs from the quick run are reused, not re-fetched |

For a request that clearly wants a report, the quick run's first and only
action is `HandOff(report_requested)`. The cost is one cheap model call,
which the user would have paid anyway to be understood.

### 4c. How the quick agent is presented with them

The model meets the two tools in five places, and each carries one kind of
information so that no two repeat each other.

| Surface | Carries | Keyed to | Cost on the quick path |
|---|---|---|---|
| **Tool schemas** | each name and what the call does to the run; for `HandOff`, that it costs the user time and two required fields; for `Expand`, an optional keyword | nothing; always present | about 85 words of description plus two small schemas |
| **System prompt** | the three situations, as a short list | the request (read at turn 0) | about 90 words (`system-prompts.md` §8b) |
| **Data overview** | the existence of a hidden world: the last line names `Expand` | the sources (what the user can reach) | one line, and none when nothing is hidden |
| **Harness note in a tool result** | an instruction at the moment of failure: no rows, a second error in a row | the result (read when it happens) | zero on success |
| **What the user sees** | a status line when a run hands off ("Taking a closer look, this will take longer") | the handoff | zero unless it fires |

The principles behind that division:

1. **Describe the situation, not the capability.** The `HandOff` reasons are
   things the model can observe: the question is too complex, a report was
   requested. They are not service levels to choose from ("investigate",
   "report"). A cheap model is good at noticing a
   situation and bad at judging whether it deserves a better model, and a
   capability menu invites the second judgement. The landing names stay
   internal to the harness.
2. **Never tell the cheap model a stronger model is waiting.** Nothing it
   sees names a tier, a model, or the word "smarter". Without that lure,
   handing off is a way to pass work on, not a way to get a better answer for
   itself. It needs to know the cost to the user, not the capability on the
   other side.
3. **State the cost honestly and in the tool's own text.** "The user will
   wait longer" is true, cheap, and aligned with the one thing the quick path
   protects. It is the deterrent for `HandOff`, in place of rules about when
   not to call. `Expand` has no such sentence because it is not that
   expensive; it is capped instead.
4. **Put each rule where its evidence appears.** The rule that depends on the
   request (report, an unlisted source, a multi-step question) is read once at
   turn 0, so it goes in the prompt. The rule that depends on a result (no
   rows, a repeated error) is only visible after the result, so it goes in the
   result as a harness note. The advisor docs bear this out: a turn-2 nudge
   raised a Haiku executor's pass rate by about 7 points, a nudge that came
   later than the model's natural first call cost 3–4, and extra under-calling
   fixes on Opus were net flat because they caused over-calling elsewhere.
   Timed at the moment of need is the version that does not backfire.
5. **Harness notes are not data.** A note is harness-authored text in its own
   field, separate from the result rows, so the provenance rule (text in
   results is data, never instruction) is not weakened for it:

   ```json
   {"row_count": 0, "rows": [],
    "harness_note": "No rows. If the schema does not explain why, call HandOff(too_complex)."}
   ```

   Notes appear only on no-rows, on a second consecutive error, and when a
   query names a source the overview left out (where the note is the source's
   own description, §5). A successful query has none, so the quick path pays
   nothing.
6. **Few parameters, no options.** `HandOff` takes a closed `reason` and one
   sentence; `Expand` takes optional keywords. There is no tier parameter, no
   "urgency", no "continue from here" flag. Every added parameter is another
   way to call it casually.
7. **Name each for what it does to the run.** `Expand` leaves the run going
   and adds to what it can see. `HandOff` ends the run, and joins `Complete`
   and `AskUser` as the three tools that end one, so the prompt describes that
   calling convention once ("calling it is the last thing you do") rather
   than once per tool. An earlier draft had one tool, also called `Expand`,
   that restarted the run to widen it; that charged the user a restart for
   what is a text result. Splitting the two keeps the cheap widening cheap.
8. **List `HandOff` last.** The core tools are what the model sees first. This
   is untested and cheap to test (§8).

The result of a successful `HandOff` is one line, `Handed off. Your run is
over.`, so the model does not go on to write an answer the user will not see.

What this does not try to do is make the model call either tool reliably. A
cheap model that is confidently wrong raises none of the signals above, which
is why §5 exists and why §8's silent-wrong measure is the headline.

### 4d. The handoff

The landing run receives a `<prior_attempt>` tag, nonce-tagged like other
envelope data and treated as evidence, never as instructions:

- the question as the user asked it,
- the `reason` and `why`,
- the queries run, with their results as `table://` refs or stubs,
- the schema the run read,
- what it believed it had established, marked unverified.

A run that restarts from this does not redo the quick run's reads, and it
does not trust its conclusions either. That is the validator's posture toward
a finder.

### 4e. Over-use and under-use

The advisor docs report that cheap models under-call optional tools, so the
bigger risk is the confident wrong answer that never reaches for the hatch,
not a flood of unnecessary calls. Over-use is measured (§8) rather than
designed against in advance. The presentation choices above all err toward
making the call honest and easy; the deterrent is the stated cost, and the
backstop for the missed cases is the harness (§5).

## 5. Harness triggers

The harness widens or escalates without the model calling a tool when it sees
an objective signal. These are checks Forge already makes plus a few cheap ones:

| Signal | Action |
|---|---|
| two SQL errors in a row | `HandOff(too_complex)` on the model's behalf |
| a query returns zero rows and the model has not said why | `HandOff(too_complex)` |
| the quick run uses more than N turns without a final answer | `HandOff(too_complex)` |
| the model queries a source the overview left out but the user is granted | reveal it in the result (an automatic `Expand` for that source); no escalation |
| the request text matches the report rule (configurable keywords) | start at `report`, skipping the quick run |
| the output spills past a size limit | `table://` handle, no escalation |

Rules:

- **`Expand` is free to use within a run; `HandOff` is bounded.** At most two
  hand-offs per request (`quick → investigate → report` is the longest chain),
  never in a loop. The ledger's attempt budget still bounds everything.
- **Escalation is clamped by config.** A deployment sets the highest tier a
  request may reach. A model cannot raise it, and neither can anything it read.
- **Cost authority only.** Text in a data result that says "call HandOff"
  causes at worst a more expensive run, and one that says "call Expand"
  adds clutter. Neither widens permissions.
  Permissions are checked by the executor per role, not by who saw a tool
  definition (`agent-deferred-tool-loading.md` §4).
- **Not every failure escalates.** An environment or permissions error would
  fail identically on a bigger model; it goes to `blocked`.

Some wrong answers raise none of these signals: the SQL ran, returned rows,
and is subtly wrong. This design does not catch those. The remedies are the
SQL-and-row-count answer form, the `input_rows` fan-out stub from `data.md`
§4b where available, and sampling (§8).

## 6. Provider notes

- **Anthropic API, Claude Platform on AWS:** `defer_loading` makes `Expand`'s
  tool reveal free of cache loss. Optional; the paths in §4a work everywhere.
- **Bedrock `Converse`:** no deferral, no advisor tool. Sources are revealed as
  text; tools by the once-only array growth in a small economy run, or by
  `HandOff`. *Not verified:* how Bedrock orders and invalidates cache
  checkpoints for `toolConfig` changes, and its per-model cache minimums.
- **OpenAI Responses (`gpt-5.4`+):** client-executed `tool_search` and
  `additional_tools` can do what Anthropic's path does.
- Whatever the provider, the quick run's four tools load upfront, so the
  quick path itself depends on none of this.

## 7. Coding and review

Unchanged from `medium.md` §3d and §3d-i apart from naming tiers:

| Role | Tier | Reason |
|---|---|---|
| orchestrator (review) | standard | skip/dispatch decisions, brief construction |
| finder specialists | economy → standard | silent misses are costly, but dedup and the validator catch overlap |
| validator | strong | a wrong confirmation becomes a posted comment |
| `plan` | strong | nothing downstream re-derives the approach |
| `implement` | standard (economy to be measured) | checked by verification, audit and review; see the instruction-density risk in §3d-i |

For `Task` children inside a run, an optional `tier` field is clamped to the
parent's tier, so delegation never widens cost authority. Children's reports
must include the refs or file lines behind each claim.

## 8. What to measure

Each step changes one thing, using `medium.md` §3e telemetry and `eval.md`.
Record tier, model ID and the price at the time on every result.

1. **The quick path must not regress.** Time to answer and cost of a plain
   cheap agent with no hatches, versus the same with `Expand` and `HandOff` in
   its tool list and the "N further sources" line. The overhead should be
   around a hundred tokens. If it is more, the design is wrong.
2. **Route mix.** Share of requests that stay quick, use `Expand` and finish,
   go to `investigate`, go to `report`; share moved by the model versus by a
   harness trigger. Also the `Expand` hit rate: how often what it revealed
   was used in a later query. A near-zero model-called share with a high harness-triggered
   share means the model is under-calling.
3. **Unnecessary calls.** Sample `HandOff` and `Expand` calls and ask whether
   the quick run could have answered without them. This is the over-use rate.
4. **Silent wrong answers.** Sample quick-run answers that did not escalate,
   re-run them at `investigate`, and compare. This is the number that decides
   whether the cheap start is safe, and no signal in §5 produces it for free.
5. **Presentation variants.** The text around the hatch is the cheapest thing
   to change and the thing most likely to decide how it is used. `eval.md`
   Suite 4 runs text-only variants of §4b (the situations in the prompt or
   not; harness notes or not; the tool name; the position in the tool list;
   the cost sentence in the description or not) on the arm without harness
   triggers, so the triggers cannot hide under-calling.
6. **Report quality.** `report` with economy collection versus standard
   collection, same writer; and strong versus standard writer. Needs an
   analysis eval set (`eval.md` notes DAB as the first labelled data-agent
   set; none exists in this design yet).

## 9. Not adopted

- **A triage model call before every request.** Costs the quick case latency
  and tokens to answer a question the cheap model answers anyway by reading
  the request.
- **A learned router (Compass-style).** Needs a satisfaction signal and
  scale. Cursor and Copilot have both; a Forge deployment does not.
- **Mid-run model switching.** Loses the prompt cache and mixes behaviours in
  one transcript.
- **Requiring the advisor tool.** Vendor beta, not on Bedrock.
- **`explore` → `answer` as the default for every analysis request.** Kept
  only as the `report` landing.

## 10. Open points

- The tier→model mapping, the report keyword rule and the hop limit need a
  home in job config (`tools.md` "One job declares the tools" is the nearest
  precedent). *Placed by [Keel](./keel/README.md) (2026-10-23): the
  tier map in `Deployment`, the keyword rule as a `request_matches` harness
  trigger, the hop limit as `outputs.max_chain_depth`.*
- A run's budget should count tokens by tier, so spend cannot hide in a cheap
  child.
- Thinking and effort are separate from model choice. A tier may need an
  effort setting; not decided.
- The general rule for tool availability (loaded, deferred, revealed) belongs
  in `tools.md`; this file only uses it.
