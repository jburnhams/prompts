# Keel: publish rules

The checks a JSON Schema can't express, run at validate and publish. Part of [Keel](./README.md). Section numbers are shared across Keel's files, so a reference like §7f means the same section everywhere; [the README](./README.md#files) lists which file holds each.

---

## 11. Publish rules

The checks a JSON Schema can't express. `:validate` and `:publish` run
them; `check.py` implements each one against the examples. The one part
it can't do is R13's comparison with a server's own input schema: the
example snapshots carry digests rather than schemas. That half runs at
publish against the real snapshot.

| Rule | Checks |
|---|---|
| R1 | every agent's grant names a declared group |
| R2 | every `mcp:<server>` tool names a server in `tools.servers` |
| R3 | the spawn graph names real agents |
| R4 | params: declared; `external`/`principal` bind only to inputs; config-bound params are constrained; grant-bearing fields take no params |
| R5 | `completion.form: text` has no report schema, completion checks, spinoffs or ending tools, and status `done` only |
| R6 | monitor handoffs name declared reasons; a template with HandOff reasons that no pipeline wires is a warning, since alone it has no HandOff |
| R7 | continuations (to `self` only, by schema): required params bound, carry inputs accept what is carried, spinoff edges have spinoffs enabled; `at` appears only on pipeline sinks; `approve` questions have an execute edge |
| R8 | `Expand` reveals only what the orchestrator is granted; `array_growth.bundle` is revealable; hidden groups have a reveal path (warning) |
| R9 | a read-only or absent workspace grants no `Edit`/`Write` |
| R10 | literal tiers are within `max_tier`; a clamped child above its parent is a warning |
| R11 | tool names, after aliasing, are unique per agent, including generated ending tools |
| R12 | no write tool (granted for any use, or called by a pipeline sink) on a service-credentialed server in anything users can run, unless the server has `entitlement_check: harness_policy` |
| R13 | argument overrides only narrow: a hidden argument is fixed, an enum is a subset of the server's, a maximum only goes down; a fixed `$param` is a config param of the template; other overrides on a fixed argument are a warning |
| R14 | tool uses: a built-in is used only as its catalogue allows; only the orchestrator is granted ending tools; each ending gives a declared status, and takes a report only if there is a report schema; no ending tool has an argument named `summary` or `report`; `complete: false` needs at least one ending tool |
| R16 | every prompt and report-schema ref resolves to a file in a configuration's registry; every report schema is a valid JSON Schema whose relative refs resolve |
| P1 | a pipeline's entry and edges name real stages; every `pipeline.params.x` it reads is declared |
| P2 | every exit an edge waits on (status, ending tool, HandOff reason) exists in that stage's template; every HandOff reason of every stage is wired |
| P3 | each edge's carry is accepted by the next stage's template |
| P4 | every route into every stage (the entry, and each incoming edge) binds that template's required params, and only params it declares |
| P5 | no stage runs above the pipeline's `max_tier` |
| P6 | every stage is reachable, the graph is acyclic, and the longest path is within `max_hops` |
| P7 | there is a principal type every stage allows |
| P8 | pipeline sinks call only tools the pipeline declares, on servers it declares; `at` names a real stage, and `settled` only a stage that settles |
| P9 | a sink calling a tool on a workspace-bound server names its stage with `at`, and that stage's checkout is retained for the stage |

At resolve time, before a run starts: tool snapshot drift, delegation
scope and consent digest, deployment tier ceiling, param values against
their constraints, and the provider's deferral capability against the
visibility plan.
