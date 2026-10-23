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
| R1 | every agent's grant, including `kind_grants`, names a declared group |
| R2 | every `mcp:<server>` tool names a server in `tools.servers` |
| R3 | the spawn graph names real agents; `kind_grants` and `kind_scope` keys are in `spawn_kinds` |
| R4 | params: declared; `external`/`principal` bind only to inputs; config-bound params are constrained; grant-bearing fields take no params |
| R5 | `completion.form: text` has no report schema, completion checks, spinoffs or finishers, and status `done` only |
| R6 | monitor handoffs name declared reasons; a template with HandOff reasons that no pipeline wires is a warning, since alone it has no HandOff |
| R7 | continuations (to `self` only, by schema): required params bound, carry inputs accept what is carried, spinoff edges have spinoffs enabled; `at` appears only on pipeline sinks; `approve` questions have an execute edge |
| R8 | `Expand` reveals only what the orchestrator is granted; `array_growth.bundle` is revealable; hidden groups have a reveal path (warning) |
| R9 | a read-only or absent workspace grants no `Edit`/`Write` |
| R10 | literal tiers are within `max_tier`; a clamped child above its parent is a warning |
| R11 | tool names, after aliasing, are unique per agent, including finisher names and generated tools |
| R12 | no write tool (granted, wrapped by a finisher, or called by a pipeline sink) on a service-credentialed server in anything users can run, unless the server has `entitlement_check: harness_policy` |
| R13 | argument overrides only narrow: a hidden argument is fixed, an enum is a subset of the server's, a maximum only goes down; a fixed `$param` is a config param of the template; other overrides on a fixed argument are a warning |
| R14 | finishers: `complete: false` needs at least one; each ends with a declared status; `report` needs a report schema; the wrapped tool is declared |
| R15 | if any agent can reach `action/open_pull_request` (granted or through a finisher), the checkout is writable with `git_writes: via_action`; `via_action` with no agent able to reach it is an error |
| R16 | every prompt and report-schema ref resolves in a configuration's registry; every report schema is a valid JSON Schema whose relative refs resolve; a prompt still marked a draft fragment is a warning |
| P1 | a pipeline's entry and edges name real stages; every `pipeline.params.x` it reads is declared |
| P2 | every exit an edge waits on (status, finisher, HandOff reason) exists in that stage's template; every HandOff reason of every stage is wired |
| P3 | each edge's carry is accepted by the next stage's template |
| P4 | every route into every stage (the entry, and each incoming edge) binds that template's required params, and only params it declares |
| P5 | no stage runs above the pipeline's `max_tier` |
| P6 | every stage is reachable, the graph is acyclic, and the longest path is within `max_hops` |
| P7 | there is a principal type every stage allows |
| P8 | pipeline sinks call only tools the pipeline declares, on servers it declares; `at` names a real stage, and `settled` only a stage that settles |
| P9 | a sink calling `action/open_pull_request` names its stage with `at`, and that stage's checkout is writable and retained for the stage |

At resolve time, before a run starts: tool snapshot drift, delegation
scope and consent digest, deployment tier ceiling, param values against
their constraints, and the provider's deferral capability against the
visibility plan.
