# Models: one model per stage, chosen by config, not by a model

**Status: proposal, written 2026-10-22. Nothing here is adopted yet.** The
research is in [`../agent-multi-model.md`](../agent-multi-model.md). This
file says what Forge would change, what it would leave alone, and what to
measure first. It extends `medium.md` §3d (per-role models for review) and
§3d-i (plan strong, implement cheap) to the `analyse` entrypoint and to
mid-run escalation.

## 1. Position

1. **The model is a property of a run's stage, set in job config.** Not of a
   turn, not of a prompt, and not decided by a model.
2. **No router.** Forge's stages are named (`plan`, `implement`, `explore`,
   `answer`, `reviewer`, `validator`), so the stage is already the routing
   signal and costs nothing. Cursor's and Copilot's routers exist because a
   free-form chat turn has no stage label.
3. **Escalation is a ledger rule, not a feeling.** A run that ends in a
   specific, countable failure state may be retried one tier up. That is the
   same shape as `orchestration.md` §7's other health rules.
4. **Model-agnostic.** A stage names a *tier* (`economy`, `standard`,
   `strong`); the deployment maps tiers to model IDs. Vendor features such as
   the Anthropic advisor tool are optional accelerators behind a tier, never
   required by a prompt.

## 2. The analysis case: `explore` cheap, `answer` strong

This is the user's scenario, and the seam already exists (`data.md` §2g).

```
explore (economy tier)                 answer (strong tier)
read-only, mints table:// refs   ──►   reads the handoff, re-queries
ends with a structured finding         read-only if it doubts a number,
                                       writes the report, passes the gate
```

What changes:

- **`tiers` per mode** in the analysis job config:
  `explore: economy`, `answer: strong`. Default both to the deployment's
  current model so nothing changes until someone opts in.
- **A handoff envelope.** `answer` already receives the task envelope; add an
  `<exploration>` tag carrying the `explore` run's `Complete` payload: the
  question as understood, the refs minted (with their stubs), the queries run
  (`produced_by`), caveats, and what it did **not** manage to check. The tag
  is data under the existing nonce-tagging rule; the answer run treats it as
  evidence to verify, not as instruction or fact.
- **`explore` is told what it is for.** Its prompt gains one rule: *retrieve
  and describe; do not conclude.* It may profile, run the queries the task
  names and note anomalies. It must not state a headline number as an
  answer, because the strong stage owns the claim. This follows
  `agent-multi-model.md` §6: the cheap tier is safe on mechanical steps and
  unsafe on deciding what to compute (DAB: ~88–90% of wrong answers are in
  planning or computing).
- **`answer` may re-query.** It keeps the read-only `table://` selectors and
  SQL (`data.md` §2c). A writer that cannot check a number can only repeat
  it. The strong tier's job includes recomputing any figure that appears in
  the report headline.
- **Provenance gate unchanged** (`data.md` §2f). It does not care which tier
  made a ref, only that it resolves and traces to a query. This is the
  property that makes mixed tiers safe to ship.

When `explore` has to do real analysis (a join the task did not specify, a
metric definition), the right outcome is for it to **stop and say so in the
handoff**, and for the dispatcher to run the strong tier for that part. Do
not make the cheap tier guess.

### 2a. Dynamic delegation inside a run

For a coding or `answer` run that wants a cheap helper mid-run (scan 40 files,
profile five tables), the existing `Task` tool gets one field:

```json
"tier": { "type": "string", "enum": ["economy", "standard", "strong"],
          "description": "Capability tier for this sub-agent. Omit to use the sub-agent type's default. Use economy for retrieval and profiling; use strong when the result decides what the report claims." }
```

- Defaults come from config per `subagent_type` (`general-purpose` defaults to
  the parent's tier; `reviewer`/`validator` per §3). A parent **cannot pick a
  tier above its own** (the harness clamps), so delegation never widens cost
  authority; compare `agent-subagent-architectures.md` §7d on authority.
- A deployment may pin a tier with a force switch, as Claude Code's
  `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` does.
- The sub-agent's report format for `economy` children must include the refs
  or file/line evidence behind each statement, not just conclusions. This is
  the same rule as the review `Task` notes: a report is a candidate until
  checked.

## 3. Review and coding

These are `medium.md` §3d and §3d-i unchanged except for naming tiers:

| Role | Tier | Reason |
|---|---|---|
| orchestrator (review) | standard | skip/dispatch decisions, brief construction |
| finder specialists | economy → standard | silent misses are costly, but dedup + validator catch overlap |
| validator | strong | a wrong confirmation becomes a posted comment |
| `plan` | strong | nothing downstream re-derives the approach |
| `implement` | standard (economy to be measured) | checked by verification, audit and review; but see the instruction-density risk in §3d-i |
| `explore` | economy | mechanical retrieval |
| `answer` | strong | owns the claim |

## 4. Escalation

A small addition to `orchestration.md` §7:

| Check | Condition | Action |
|---|---|---|
| `tier_escalate` | last attempt ended `Complete(budget_exhausted)` or the completion audit/gate failed on an `economy` or `standard` stage | next attempt runs one tier up; recorded as `escalated_from` on the attempt |

Rules to keep it from becoming an unbounded cost source:

- One escalation per task; the ledger's `max_attempts` still bounds everything.
- Escalation is triggered only by **objective** signals Forge already
  produces (`budget_exhausted`, a failed gate, a failed `verification`
  entry). No model is asked whether it was clever enough. This is the
  FrugalGPT cascade with the confidence signal replaced by checks that exist.
- Not every failure escalates. `blocked` (needs a human) and `failed` for
  tool or environment reasons would fail identically on a bigger model.
- Data analysis has few objective failure signals. The provenance gate catches
  unsupported numbers but not wrong ones, so escalation there depends on the
  gate and the audit; it is weaker than in coding. That is the reason the
  strong tier is the default for `answer`, rather than a cascade starting
  cheap.

## 5. Not adopted, and why

- **A model router (Compass-style).** Needs a satisfaction signal and a human
  to absorb mis-routes; Forge has neither, and the stage already carries the
  information. Also adds a model call to a dispatcher that is deliberately
  non-model (`orchestration.md` §8).
- **Mid-run model switching.** Loses the prompt cache and mixes behaviours in
  one transcript. Switch at stage or task boundaries only.
- **Requiring the Anthropic advisor tool.** Useful for a cheap `implement`
  that needs occasional strong planning, and it sees the whole transcript,
  which a separate `plan` run does not. But it is a vendor beta, absent from
  Bedrock, Google-managed Vertex and Foundry, and its result may be redacted
  from the client, so logs would lack the advice. **Allowed as an
  implementation of the `standard` tier** where the deployment has it; no
  prompt or schema depends on it. Revisit when measuring cheap `implement`
  (§6), since it is the obvious thing to compare against a separate `plan`
  run.
- **Cheap model summarising for the strong one inside a run.** Compaction
  already exists as a lever (`formats.md` §7); mixing tiers there adds a
  faithfulness risk with no seam to check it.

## 6. What to measure before turning anything on

Everything defaults to today's model. Each step changes one thing and has a
number that decides it, using the finding-outcome telemetry of `medium.md`
§3e and `eval.md`:

1. `analyse`: `explore` on economy vs standard, same `answer`. Metric:
   report correctness on a DAB-style set (`eval.md` Suite 3 notes DAB as the first labelled data-agent set; no analysis suite exists yet), plus
   *handoff loss* — facts present in the `explore` refs that never reach the
   report, and wrong facts that do.
2. `analyse`: `answer` on strong vs standard, same `explore`. Does the
   stronger writer catch an `explore` error by re-querying?
3. Review: validator strong vs standard, with findings-per-run and
   post-resolution rates as in §3d.
4. Escalation: fraction of `economy` attempts that escalate and the cost of
   those attempts, against running the stronger tier first. If most economy
   runs escalate, the economy tier is a net cost.

Record in each result the tier, the model ID and its price at the time, so
runs stay comparable when model names change.

## 7. Open points

- The tier→model mapping needs a home in the job config
  (`tools.md` "One job declares the tools" is the nearest precedent).
- Cost accounting: a run's budget should count tokens by tier. OpenHands
  charges delegated vision calls to the run budget; the same rule applies
  here so spend cannot hide in a cheap child.
- Thinking/effort is separate from model: Claude Code sub-agents inherit the
  parent's setting, Codex sets effort per role. A tier may need an effort
  setting too; not decided.
