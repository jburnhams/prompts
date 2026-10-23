# Forge on Keel

**Forge is a set of use cases on [Keel](../keel/README.md)**: plan a
ticket, implement it, review a PR, and fix what review found. This
folder holds their templates, pipelines and triggers. The rest of
[`agent-design/`](../README.md) describes how those use cases behave:
prompts, tool contracts, formats. Forge adds no events, channels,
actions or checks of its own. It uses Keel's, which every other use
case shares. Each choice below is Forge's, made with what Keel provides.

| File | What |
|---|---|
| [`forge.coding.template.json`](./forge.coding.template.json) | base template (`runnable: false`): what plan and implement share |
| [`forge.plan.template.json`](./forge.plan.template.json), [`forge.implement.template.json`](./forge.implement.template.json) | sibling templates; neither is a mode of the other |
| [`forge.review.template.json`](./forge.review.template.json) | multi-stage review |
| [`jira-plan-implement.pipeline.json`](./jira-plan-implement.pipeline.json), [`jira-assigned.trigger.json`](./jira-assigned.trigger.json) | plan → approved → implement, started by a Jira assignment |
| [`pr-review-fix.pipeline.json`](./pr-review-fix.pipeline.json), [`pr-review.trigger.json`](./pr-review.trigger.json) | review a PR, then fix what its author approves |
| [`prompts/`](./prompts) | Forge's prompts as registered text, derived from `../system-prompts.md`: plan, implement, the delegate, the review orchestrator, the reviewer (core and wrapper together), the validator |
| [`reports/`](./reports) | Forge's report schemas, from `../formats.md` §3–§4 and `../risk.md` §2 |
| [`registry.json`](./registry.json) | which file each prompt and report-schema ref resolves to |

**Forge's choices, which Keel leaves open:**

- **Who opens the PR.** `forge.implement` run alone leaves its working
  tree for an external committer, which links the PR back. Inside
  `jira.plan-implement`, the pipeline opens it with
  `action/open_pull_request` after implement ends. Neither Forge
  template lets its agents push (`git_writes: none`).
- **Plan approval** is gated and bound to the plan's hash, rather than
  auto-chained.
- **Review runs as the service identity**; plan and implement run as the
  person who assigned the ticket, under their delegation.

Forge's own documents still use some older words (mode, job, lens,
landing, ledger, `Task.role`). [`../keel/taxonomy.md`](../keel/taxonomy.md)
§10 maps each to the Keel term.

---

## What maps to what

The files are the mapping, and [`../keel/check.py`](../keel/check.py) passes on them:

| Forge | Keel |
|---|---|
| coding `implement` | [`forge.implement`](./forge.implement.template.json) |
| what Forge calls the coding modes | three templates: the base [`forge.coding`](./forge.coding.template.json) (`runnable: false`) and its siblings [`forge.plan`](./forge.plan.template.json) (read-only, `jira.comment` granted, `require_tool_called: AddComment`, strong tier) and `forge.implement` |
| plan → implement handoff | pipeline [`jira.plan-implement`](./jira-plan-implement.pipeline.json), edge gated on `plan_hash` |
| review, multi-stage | [`forge.review`](./forge.review.template.json): `reviewer` with `spawn_kinds` and `kind_grants.visual = [vision]`, `validator` at `strong` with `clamp_to_parent: false`, attention tier as a `commit_status` sink |
| review → fix | pipeline [`pr.review-fix`](./pr-review-fix.pipeline.json), approval by the PR author |
| the `analyse` entrypoint: quick run and the stages it hands off to | pipeline [`analysis`](../keel/examples/analysis.pipeline.json): [`analysis.quick`](../keel/examples/analysis.quick.template.json) → [`analysis.investigate`](../keel/examples/analysis.investigate.template.json) / [`analysis.report`](../keel/examples/analysis.report.template.json) |
| "the job declares the tools; each sub-agent gets a subset" | `tools.groups` + `agents.*.grant`, R1 |
| `AddComment` absent in `implement` | declared in `tools.groups`, not granted to the orchestrator |
| AskUser `approve` → fresh execute run | continuation `execute_approved`, `carry: [approved_action, resumed_answer]`, no transcript |
| run ledger (`../orchestration.md`) | the pipeline run ([`keel/pipelines.md`](../keel/pipelines.md) §7f): stage attempts and retry policy, `waiting_on`, `settle` for the PR, child runs for spinoffs |
| tier map (`../models.md` §10 open point) | [`deployment.json`](../keel/examples/deployment.json) |
