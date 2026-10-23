# Lens on Keel

**Lens is a set of data-analysis use cases on [Keel](../keel/README.md)**:
answer a data question quickly, investigate it when that isn't enough,
and write it up as a report when that's what was asked. This folder
holds their templates, pipeline, triggers, prompts and report schemas.

Lens is what [`../data.md`](../data.md) §2g and [`../models.md`](../models.md)
designed as Forge's third entrypoint, `analyse`. It became its own set on
2026-10-23: the tools it uses are shared across use cases, not owned by
Forge. Like Forge, it adds no events, channels or tools of its own; it
uses Keel's and the shared servers (the warehouse server is in
[`../keel/examples/`](../keel/examples/warehouse.mcp-server.json)).

| File | What |
|---|---|
| [`lens.quick.template.json`](./lens.quick.template.json) | economy tier, four tools, `Expand` and `HandOff` (`../models.md` §3–§4) |
| [`lens.investigate.template.json`](./lens.investigate.template.json) | the `too_complex` stage: standard tier, every source, the full tool set |
| [`lens.report.template.json`](./lens.report.template.json) | the `report_requested` stage: collect on economy, write on strong |
| [`lens.pipeline.json`](./lens.pipeline.json) | quick → investigate / report, answering back to where the question came from |
| [`chat-data.trigger.json`](./chat-data.trigger.json) | `/data` in chat, as the invoking user |
| [`weekly-revenue.trigger.json`](./weekly-revenue.trigger.json), [`delegation.json`](./delegation.json) | a weekly question, under the owner's stored delegation |
| [`run-request.json`](./run-request.json) | a direct API request |
| [`prompts/`](./prompts) | the four prompts, derived from `../system-prompts.md` §8 |
| [`reports/`](./reports) | the answer and report-document schemas: every figure is a claim citing the query behind it |
| [`registry.json`](./registry.json) | which file each prompt and report-schema ref resolves to |

**Lens's choices, which Keel leaves open:** it starts every question on
the economy tier and grows only when the question needs it; it runs as
the person asking (`invoker` from chat, a stored delegation for
schedules); and its answer always carries the SQL and row count behind
each figure, because a cheap model's characteristic failure is a
plausible wrong query.
