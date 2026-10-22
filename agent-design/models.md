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
2. **One escape hatch, `Expand`, reaches everything else.** More data, a
   stronger model, or a report. It is a tool the cheap model can call and the
   harness can also trigger itself (§5).
3. **The cheap model is the router, not a separate classifier.** It already
   reads the request. If the request says "make me a report", it calls
   `Expand(report)` as its first action. No extra model call, no latency.
4. **Escalation moves forward and costs a restart, never a mid-run model
   swap.** `Expand` ends the run with a handoff, and a new run starts with the
   bigger tool set and/or tier. On Bedrock `Converse` there is no deferred
   loading (`agent-deferred-tool-loading.md` §5), so a run boundary is the
   only point where the tools array can change without losing the prompt
   cache. A cheap run's context is small, so restarting costs little; and the
   restart is paid only by requests that were not quick.
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
| Tools | `DescribeSource`/`ListSources`, read-only `RunSQL` against the described sources, `Expand`. Final answer is plain text, or `Complete` where a run ledger is used | 3–4 tools, so loading them upfront is cheap and needs no deferral |
| Data overview | one line per source the user has, plus a last line: `N further sources are not listed; Expand reveals them` | the cheap model cannot ask for what it does not know exists; the last line is the whole cost of that |
| Prompt | a short analysis prompt: ground in the schema, show your SQL, state the row count, do not guess a join | DAB puts ~88–90% of wrong answers in planning or computing the query (`../agent-data-analysis.md` §12a) |
| Answer form | the number or table, then the SQL and the row count in the same message | Haiku's characteristic failure is plausible-but-wrong SQL, and nothing automatic catches it; showing the query lets the user |

Everything else (profiling, chart specs, joins across sources, `table://`
spill, report writing, the provenance gate) is behind `Expand` or triggered by
the harness. `data.md` §2d's spill still applies on its own: a large result
becomes a `table://` handle without the model asking.

## 4. `Expand`

One tool, deliberately small. The description is about two lines, so that it
costs few tokens and does not invite use:

> Use only when the tools and data above cannot answer the question, or the
> user asked for a report. Say in one sentence what is missing.

```json
{
  "name": "Expand",
  "input_schema": {
    "type": "object",
    "properties": {
      "need": { "type": "string", "enum": ["data", "investigate", "report"] },
      "blocker": { "type": "string", "description": "One sentence: what you could not do, or what the user asked for." }
    },
    "required": ["need", "blocker"],
    "additionalProperties": false
  }
}
```

The required `blocker` does two jobs. It makes a casual call slightly
effortful, and it is the first line of the brief the next run reads.

Like `AskUser`, `Expand` is the last action of a run. The harness ends the run
and starts the next one. Three landings:

| `need` | Next run | Tier | Tools and context |
|---|---|---|---|
| `data` | same shape as the quick run, bigger world | economy | the sources the overview hid, plus the focused data tools (profile, fetch, table ops) |
| `investigate` | open-ended loop: try things, revise | standard, with a strong consultant at the plan and before concluding where the provider supports an advisor | the `data` set, plus `table://` refs and a larger turn budget |
| `report` | collect (economy) then write (strong), the `explore` → `answer` split from `data.md` §2g | economy then strong | refs from the quick run are reused, not re-fetched |

For a request that obviously wants a report, the quick run's first and only
action is `Expand(report)`. The cost is one cheap model call, which the user
would have paid anyway to be understood.

### 4a. The handoff

The next run receives a `<prior_attempt>` tag, nonce-tagged like other
envelope data and treated as evidence, never as instructions:

- the question as the user asked it,
- the `need` and `blocker`,
- the queries run, with their results as `table://` refs or stubs,
- the schema the run read,
- what it believed it had established, marked unverified.

A run that restarts from this does not redo the cheap run's reads, and it does
not trust its conclusions either. That is the same posture as the validator
toward a finder.

### 4b. Keeping it from being a temptation

Evidence from the advisor docs is that cheap models under-call optional tools,
not over-call them, so the danger is rarely that `Expand` is used too much. It
is that the model is confidently wrong and never reaches for it. So the
description discourages casual use, and the harness does not rely on the model
to notice (§5). Over-use is measured (§8), not designed against up front.

## 5. Harness triggers

The harness escalates without the model calling `Expand` when it sees an
objective signal. These are checks Forge already makes plus a few cheap ones:

| Signal | Action |
|---|---|
| two SQL errors in a row | `Expand(investigate)` on the model's behalf |
| a query returns zero rows and the model has not said why | `Expand(investigate)` |
| the quick run uses more than N turns without a final answer | `Expand(investigate)` |
| the model names or queries a source the overview marked hidden | `Expand(data)` |
| the request text matches the report rule (configurable keywords) | start at `report`, skipping the quick run |
| the output spills past a size limit | `table://` handle, no escalation |

Rules:

- **One escalation chain per request, at most two hops.** A request moves
  `quick → data → investigate`, or `quick → report`, or `quick → investigate`,
  never in a loop. The ledger's attempt budget still bounds everything.
- **Escalation is clamped by config.** A deployment sets the highest tier a
  request may reach. A model cannot raise it, and neither can anything it read.
- **Cost authority only.** Text in a data result that says "call Expand"
  causes at worst a more expensive run. It cannot widen permissions.
  Permissions are checked by the executor per role, not by who saw a tool
  definition (`agent-deferred-tool-loading.md` §4).
- **Not every failure escalates.** An environment or permissions error would
  fail identically on a bigger model; it goes to `blocked`.

Some wrong answers raise none of these signals: the SQL ran, returned rows,
and is subtly wrong. This design does not catch those. The remedies are the
SQL-and-row-count answer form, the `input_rows` fan-out stub from `data.md`
§4b where available, and sampling (§8).

## 6. Provider notes

- **Anthropic API, Claude Platform on AWS:** `defer_loading` can make `data`
  an in-run expansion with no cache loss. Optional; the run-boundary path
  works everywhere.
- **Bedrock `Converse`:** run-boundary only. No deferral, no advisor tool.
- **OpenAI Responses (`gpt-5.4`+):** client-executed `tool_search` and
  `additional_tools` can do the same as Anthropic's path.
- Whatever the provider, the quick run's tool set is small enough to load
  upfront, so nothing about the quick path depends on any of this.

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
   cheap agent with no `Expand`, versus the same with `Expand` in its tool
   list and the "N further sources" line. The overhead should be tens of
   tokens. If it is more, the design is wrong.
2. **Escalation mix.** Share of requests that stay quick, go to `data`,
   `investigate`, `report`; share escalated by the model versus by a harness
   trigger. A near-zero model-called share with a high harness-triggered
   share means the model is under-calling.
3. **Unnecessary calls.** Sample `Expand` calls and ask whether the quick run
   could have answered. This is the over-use rate.
4. **Silent wrong answers.** Sample quick-run answers that did not escalate,
   re-run them at `investigate`, and compare. This is the number that decides
   whether the cheap start is safe, and no signal in §5 produces it for free.
5. **Report quality.** `report` with economy collection versus standard
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
  precedent).
- A run's budget should count tokens by tier, so spend cannot hide in a cheap
  child.
- Thinking and effort are separate from model choice. A tier may need an
  effort setting; not decided.
- The general rule for tool availability (loaded, deferred, revealed) belongs
  in `tools.md`; this file only uses it.
