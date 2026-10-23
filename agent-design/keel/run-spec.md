# Keel: the run spec, templates and params

What defines a run, and how a template makes it reusable. Part of [Keel](./README.md). Section numbers are shared across Keel's files, so a reference like §7f means the same section everywhere; [the README](./README.md#files) lists which file holds each.

---

## 3. The RunSpec

Schema: [`run-spec.schema.json`](./schemas/run-spec.schema.json).
It was called `AgentSpec` until "agent" came to mean one model context
inside a run ([`taxonomy.md`](./taxonomy.md)).
The fields, with the reason each is shaped the way it is:

- **`model`**: `tier`, optional `effort`, and `max_tier`. The ceiling
  applies to this run and to every continuation from it, so a handoff
  chain can't climb above it (`../models.md` §5, "escalation is clamped by
  config"). `max_tier` is never bindable.
- **`system_prompt`**: `base` is a versioned prompt ref (or inline text).
  `omit_sections` is subtraction by heading, the only variation the
  README's per-model-prompt decision allows. `generated` lists the
  harness blocks (`env`, `capabilities`, `git_status`, `repo_context`,
  `data_overview`), in order. No field accepts a param (§6).

  **Where each part is rendered.** The system prompt holds only what is
  the same for every run of the template version: the base text and the
  `capabilities` block, which is computed from the tools array and so is
  fixed per version too. Everything that varies per run goes into the
  **opening user message**, in this order: the other generated blocks
  (`env`, `git_status`, `repo_context`, `data_overview`), then the
  inputs. Anything that changes during the run (a revealed tool, a
  harness note, a nudge) is appended as a message, never written into
  what was already sent. A prompt's text therefore has no placeholders.
  It refers to "the first message" for its task. For a sub-agent, the
  opening message is its `<scope>` block (from the sub-agent's `scope`)
  followed by the spawner's brief. This is what makes the
  shared cache prefix in §6 true, and it is the shape Anthropic's API
  guidance gives for harnesses: freeze the rendered system prompt and
  announce per-session facts in the first user turn, then send deltas.
  Forge's original prompts (`../system-prompts.md`) put `{{ENV_BLOCK}}`
  and `{{TASK_ENVELOPE}}` inside the system prompt. Its Keel prompts
  (`../forge-on-keel/prompts/`) don't.
- **`inputs[]`**: the task envelope as an ordered list of tagged blocks.
  Each one has a `kind`, a `source` and a `trust`. There are four kinds
  of source:
  - `param`: the starting query, a manual instruction.
  - `fetch`: pre-fetched through a declared tool before turn 0, like
    the ticket in `../formats.md` §1a.
  - `carry`: filled only by a continuation or a resume: plan, prior
    attempt, approved action, resumed answer, findings.
  - `builder`: a harness component, such as the review diff builder or
    the comment-thread model.

  Anything not authored by `harness` or `config` is sanitised and
  nonce-wrapped.
- **`context`**: the context-service resolution (`tiers`, `team`,
  `paths`, `topics`, `at: base_sha` for review) and, for data
  analysis, the data overview. A failed resolution means the run doesn't start, as
  `../context-files.md` §1b already says.
- **`workspace`**: `none`, or `checkout`. `writable: false` registers no
  write tools for any agent, whatever the grants say (rule R9 rejects
  the contradiction at publish). `retain: stage` keeps the checkout
  until the stage settles, so a pipeline sink's workspace-bound tool can
  still act on it after the run (§7g).
- **`tools`**: the job's declaration (§4).
- **`agents`**: `orchestrator` plus named sub-agents (§4c).
- **`human`**, **`completion`**, **`hatches`**: these generate tools (§5).
- **`monitors[]`**: `../models.md` §5's "harness triggers" table as data,
  renamed so that "trigger" only ever means what starts a run. Each is a
  signal (consecutive errors on a tool, zero rows, turns without an
  answer, an unlisted source named, a request matching keywords) and an
  action (hand off, reveal a group, add a harness note, skip to a
  landing before turn 0).
- **`budgets`**: crossing `turns` or `context_high_water_tokens` triggers
  the final-turn nudge. `tokens_by_tier` counts the run and its children
  together, so spend can't hide in a cheap child (`../models.md` §10).
- **`outputs`**: sinks and continuations (§7).
- **`authority`**: who the run may act for (§8).
- **`concurrency`**: from `../orchestration.md` §4; held through a stage's
  settle wait (§7f).
- **`stage_defaults`**: the template's default `retry` and `settle` when
  it runs as a stage, alone or in a pipeline that leaves them unset
  (§7f).

### 3e. Deployment

[`deployment.schema.json`](./schemas/deployment.schema.json).
The tier map, provider capabilities (`deferred_tools: native | client |
none`, cache minimum, advisor), the global `max_tier`, default budgets,
and checks added to every template that no template can remove. This is
where `../models.md` §10's open point ("the tier→model mapping … needs a
home") lands. It isn't in the template, because the same template should
run on Bedrock and on the Anthropic API without a new version.

---

## 6. Templates and params

Schema: [`template.schema.json`](./schemas/template.schema.json).

A template is `{name, version, params, spec}`, optionally `extends` one
published parent. Versions are numbered. Drafts are mutable. Publishing
does all of this:

- flattens `extends` (objects deep-merge, arrays replace, `null`
  deletes);
- expands tool wildcards against pinned snapshots;
- resolves `version: "pinned"` continuation targets to concrete
  versions;
- generates harness tools per agent;
- runs the rules in §11;
- computes three digests: the spec, the fixed prompt text per agent,
  and each server snapshot.

After that the version never changes.

**Params are typed, and their `trust` decides where they may bind.**
Placeholders are structural (`{"$param": "issue_key"}`), allowed only in
fields the schema marks bindable. There's no string interpolation
anywhere.

| `trust` | Typical source | May bind to | Must be |
|---|---|---|---|
| `external` | event text, a PR title | an input (`inputs[].source.param`) only | — |
| `principal` | the user's question, a manual instruction | an input only | — |
| `config` | an issue key, a repo, a branch, a tier, a budget, a kinds list | config slots: workspace, context paths/kinds, model tier, budgets | constrained: `enum`, `pattern`, `subset_of`, `maximum` or `max_tier` |

Not bindable at all: `system_prompt`, `tools`, `agents`, `completion`,
`hatches`, `authority`, `monitors`, `model.max_tier`. That is
R4. It's the reason "params narrow, never widen" holds: every
config-bound param has a declared ceiling, and the fields that grant
anything take no params.

**Two consequences worth wanting:**

- **One cacheable prefix per template version.** Params never reach
  the system prompt, per-run blocks go into the opening message (§3),
  and the tools array per agent is fixed at publish (up to the
  deployment's tier map). So every run of a version shares the same
  tools-plus-system prefix, and the cache is shared across runs, not
  just within one. `Template.resolved.prompt_digest` names it.

**Prompts and report schemas are registry entries.** Both are referenced
as `{name, version}` and are immutable once created
(`POST /v1/prompts/{name}/versions`). A configuration kept in a folder
lists the entries it uses in a `registry.json`
([`schemas/registry.schema.json`](./schemas/registry.schema.json)):
each ref maps to a file in the folder. Rule R16 checks
every ref in every template resolves, and that every report schema is a
valid JSON Schema.
- **`:render`** shows exactly what a model would be given for a set of
  params (tools array, visibility, rendered prompt, envelope with
  placeholder nonces) without running anything. It's what you diff when
  someone asks why a run behaved the way it did.

**Ad-hoc runs** (use case 0a's "just run it"): `POST /v1/runs` with
`adhoc: {params, spec}` instead of `template`. The harness publishes the
body as `adhoc.<digest>`, a content-addressed version (the same body is
the same version and shares its prompt cache), runs every rule, then
runs it. The body can reference saved tool groups and saved prompts like
any template. It needs a `runs:adhoc` permission, because it skips the
review a named template gets. It never skips a rule.
