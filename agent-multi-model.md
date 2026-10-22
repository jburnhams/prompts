# Using more than one model in a run: delegation, staging, advice and routing

Written 2026-10-22. Question behind it: **a data-analysis task wants a cheap
model (Haiku-class) to do the tool calling and collect the data, and a strong
model (Opus-class) to write the report. Is that a sub-agent, a single call, or
two stages? How do other harnesses mix models, and do any use a cheap model to
decide which model to use?** What Forge should do about it is in
[`agent-design/models.md`](./agent-design/models.md).

Sources: this collection's existing reads (cited by file), plus four web
sources read on 2026-10-22: Anthropic's [advisor tool
docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool),
Claude Code's [sub-agent docs](https://code.claude.com/docs/en/sub-agents),
Cursor's [router write-up](https://cursor.com/blog/how-cursor-router-works),
and GitHub's [Copilot CLI auto-selection
changelog](https://github.blog/changelog/2026-06-30-copilot-cli-auto-model-selection-routes-based-on-task/).
Where a source is silent the text says so rather than guessing.

## 1. The short answer

All three of your options exist in the field, and they are different mechanisms
with different costs. There is also a fourth you did not list.

| Pattern | Who is in charge | Who sees what | Where it lives |
|---|---|---|---|
| **A. Strong model delegates down** (sub-agent) | Strong model is the parent and calls a cheap child | Child sees only its brief; parent sees only the child's final report | Claude Code `Task` with `model: haiku`, Copilot CLI per-agent pins, Amp |
| **B. Two stages** (cheap collects, then a fresh strong call writes) | Harness code sequences them | Stage 2 sees stage 1's *output*, not its transcript | Aider architect/editor, Forge's `plan`→`implement` and `explore`→`answer` |
| **C. Cheap model leads, strong model advises** | Cheap model is the loop; strong model is a tool it can call | Advisor sees the executor's **whole transcript**; executor sees only advice text | Anthropic advisor tool (API beta, April 2026) |
| **D. A router picks the model per turn** | A classifier outside the loop | Each turn goes to one model; history carries over | Cursor Router, Copilot Auto |

For your example, pattern B is the natural fit and A is the common
implementation of it when no harness sequences stages. C is the reverse of what
you described and suits a different job (§4). D answers a different question
("which model for this turn") and is not needed once the stages are explicit.

## 2. Pattern A: sub-agents with a model pin

Every harness here that has sub-agents lets the model be set per sub-agent;
the question is who sets it.

- **Claude Code.** The `model` field takes `sonnet`/`opus`/`haiku`/`fable`, a
  full ID, or `inherit`. Resolution order since v2.1.251: the per-invocation
  `model` parameter, then the definition's frontmatter, then
  `CLAUDE_CODE_SUBAGENT_MODEL`, then the main model. `…_FORCE=1` (v2.1.257)
  makes the variable override everything. Built-ins: `claude-code-guide` is
  Haiku, `statusline-setup` is Sonnet, Explore and Plan follow the main model,
  and the docs say to define your own `Explore` with `model: haiku` for a
  cheaper one. The docs also say the model can pass `model` on a call, so the
  *parent model* can choose the child's tier. Sub-agents inherit the parent's
  thinking setting; there is no per-sub-agent thinking option.
  (Piebald 2.1.303 extraction, see `agent-subagent-architectures.md` §7c.)
- **GitHub Copilot CLI** (leaked YAML). Per-role pins: `code-review`/`research`
  on Sonnet, `explore`/`task` on Haiku 4.5, and `rubber-duck` deliberately
  unset so it inherits the user's live choice (`agent-subagent-architectures.md`
  §3).
- **Amp** pins `oracle` to a different vendor entirely. **Codex** goes the
  other way: its catalog sets `default_reasoning_level: low` but
  `multi_agent_reasoning_effort: "xhigh"`, spending *more* per child than per
  orchestrator turn, because there the orchestrator routes and the children
  hold the judgment (`codex/model-catalog.md`; `agent-design/medium.md` §3d-i).
- **OpenCode** has a "small model" with a fallback chain for titles and similar
  side jobs (`agent-turn-output.md` §1). **Claude Code** uses Haiku for titling.

What pattern A costs. The strong parent is billed for every turn that
decides to delegate and every turn that reads a report, and its context grows
by each report. If the parent is Opus and the children are Haiku, the Opus
turns are few but each carries the full conversation. The saving is real when
the *bulk* of tokens (reading files, running queries, scrolling output) happens
in children whose transcripts the parent never sees.

What it risks. The parent only sees the child's final report. For data work
that is a summary of rows the parent did not see, which is where a cheap model
drops the one caveat that mattered. The report format has to carry evidence
(§6), not just conclusions.

## 3. Pattern B: two stages

Two independent runs, a typed handoff between them. Nothing in the second run
depends on the first run's context window.

- **Aider architect/editor** is the oldest example: an architect model
  describes the change, a separate editor model produces edits. This
  collection's copy (`aider/architect_prompts.py`) notes the architect never
  checks the editor's output, so there is no verification across the seam.
- **Forge today** already has the seam. `mode: plan` produces a
  decision-complete spec that `mode: implement` receives in a `<plan>`
  envelope; `analyse` has `explore` (read-only, mints `table://` refs) and
  `answer` (writes the report). `medium.md` §3d-i argues for spending on the
  step whose output later steps cannot check.
- **Claude Code `opusplan`** is the interactive version: Opus while planning,
  Sonnet while executing, switched by mode.

Why staging beats a sub-agent for your case: the report writer gets a clean,
small context made of the evidence, which is cheaper per token and gives the
strong model *less to be distracted by*. It also puts the handoff in a place
the harness can inspect, validate and persist. Staging costs you the ability
for the writer to ask the collector a follow-up; the fix is to let the writer
run its own read-only queries (§6).

Prompt caching favours staging too. Switching models mid-conversation
discards the cache, since caches are per model. Cursor's evaluation counts
cache misses from switching as a cost. A stage boundary starts a fresh context
anyway, so no cache is lost; a mid-run switch in pattern D is where the cost
bites.

## 4. Pattern C: the advisor tool (cheap executor, strong consultant)

Anthropic's advisor tool (beta header `advisor-tool-2026-03-01`, launched
April 2026) inverts pattern A. The cheap model runs the loop and may call
`advisor`, which runs a separate Opus inference **server-side within the same
`/v1/messages` request**.

Mechanics from the docs:

- The executor emits an `advisor` tool use with empty input; the server builds
  the advisor's view from the executor's *full transcript* (system prompt,
  tools, prior turns, tool results). The advisor has no tools and its thinking
  is dropped; only advice text reaches the executor. For newer advisor models
  the result is `advisor_redacted_result`, readable by the executor but not by
  your client.
- Billing is per model: `usage.iterations[]` separates `message` (executor)
  from `advisor_message` (advisor rates). Typical advisor output is 400–700
  text tokens, 1,400–1,800 with thinking. `max_uses` caps calls per request
  only; a conversation-wide cap is client-side. Advisor tokens don't draw from
  task budgets.
- The advisor must be at least as capable as the executor (Sonnet 4.6 or
  newer). Not available on Bedrock, Google-managed Vertex or Foundry.
- Anthropic's guidance: good for long agentic work where most turns are
  mechanical and planning matters; poor for single-turn Q&A and for work where
  every turn needs the strong model. Haiku executors under-call the advisor, so
  the docs suggest a turn-2 nudge (+~7 points on their internal tasks; a late
  nudge hurt). These are vendor internal numbers.

Fit for data analysis: the advisor shape helps *planning* ("which tables, which
join, what would make this number wrong") because the advisor sees the whole
transcript. It does **not** write the report unless the executor does. If the
cheap model's prose is the weak point, pattern C leaves it in the cheap
model's hands. It is a vendor-specific beta tied to one API, so a design that
must run on several providers cannot depend on it, only allow for it.

## 5. Pattern D: routers and "auto"

Two different things are called auto; keep them apart.

**Claude Code's "auto mode" is not a model router.** It is the permission
classifier in `agent-permissions-approval.md` §2c: a model call that decides
whether to allow a tool call. A cheap model *does* decide something there, but
what it decides is consent, not which model runs.

**Model routers, as found:**

- **Cursor Router** (the system behind Auto). Two stages per turn. A complexity
  predictor, *Compass*, scores the turn 0–1; below a threshold the turn goes to
  the price-efficient model. At or above it, a task router classifies along
  domains, tasks and modifiers and picks a frontier model. A frontier model is
  eligible for a task label only if it clears a one-sided 75% uplift threshold
  over the cheap one, and an optimizer picks a traffic mix within the mode's
  cost budget (Balance or Intelligence). Compass is trained to predict user
  satisfaction from follow-up behaviour. Cursor reports Auto Intelligence above
  a frontier baseline's satisfaction at 68% lower cost, and Balance beating
  Opus 4.8 at 41% lower cost (vendor figures; the article does not state the
  baseline for the percentages and does not discuss router latency, fallback or
  mid-conversation switching).
- **GitHub Copilot Auto.** Started as availability and rate-limit balancing
  (2025), now scores the task on reasoning, code complexity, bug-diagnosis
  difficulty and tool-orchestration needs, and says it "routes along natural
  cache boundaries". GitHub does not publish the classifier; the changelog does
  not say whether the choice is per turn or per session. Billed at the chosen
  model's rate.
- **Academic baselines.** RouteLLM (Berkeley/LMSYS 2024) reports keeping ~95%
  of GPT-4 quality with large call reductions on benchmarks; FrugalGPT
  (Stanford 2023) is the cascade formulation (try cheap, escalate on low
  confidence). Both are on single-turn tasks and older models; I found no
  head-to-head on agentic workloads.

Observations that matter for design:

1. **Routers are an interactive-product feature.** Their training signal is
   user satisfaction and their unit is the turn. A hands-off run has neither a
   satisfaction signal nor a human to correct a bad route, which is why Forge's
   dispatcher is a deterministic scheduler with no model in it
   (`agent-design/orchestration.md` §4, §8).
2. **A router is only needed when the harness cannot tell the difficulty
   itself.** When the workflow has named stages ("collect", "write the
   report"), the stage *is* the routing signal and costs no tokens. Cursor's
   Compass exists because a free-form chat turn has no such label.
3. **Cache boundaries are the constraint.** Both Cursor and GitHub mention
   cache cost. Route at stage or task boundaries, not mid-context.
4. **The cascade is the one router idea that survives automation.** Run the
   cheap model, check an objective signal (tests, a verifier, a schema), and
   escalate on failure. It needs a cheap, trustworthy failure signal, which
   data analysis lacks (§6).

## 6. What is different about data analysis

`agent-data-analysis.md` establishes that analysis correctness cannot be
checked by running the code, and §12a (DAB) found that ~88–90% of wrong
answers are failures of *planning or implementing the computation*, only
11–13% data selection. That cuts against the obvious split:

- "Cheap model collects" is safe when collecting means **retrieval with a
  known shape**: run this query, profile this table, fetch these files.
- It is unsafe when collecting means **deciding what to compute**, writing
  non-trivial SQL or pandas, or choosing joins. That is the part DAB says
  fails, and a wrong number from the collector reaches the report writer as a
  fact.

So the line to draw is not "tool calls vs prose" but **mechanical vs judgment
steps**. A good split is:

| Step | Needs | Model tier |
|---|---|---|
| Schema and profile reads, running a fixed query, fetching files | Follow instructions, call tools correctly | cheap |
| Deciding the analysis plan, join keys, metrics definitions | Judgment, checked by nothing downstream | strong |
| Writing queries/code that compute the answer | Correctness; verified only by provenance and cross-checks | strong, or cheap with a verifier |
| Summarising big tool output into a handoff | Faithfulness | cheap is fine if the evidence refs are carried alongside |
| Writing the report from verified evidence | Synthesis, prose, calibration of claims | strong |

The handoff matters more than the tiering. Three habits recur across the data
agents in this collection:

- **Pass references, not prose.** `table://` refs and stubs
  (`agent-design/data.md` §2a–2d) mean the writer reads the rows it cites
  rather than trusting a summary of them.
- **Let the writer re-query read-only.** A writer that cannot check a number
  can only repeat it.
- **Gate on provenance, not on whose model said it.** `data.md` §2f's gate
  checks that each claim in the report points at a ref; that works regardless
  of which tier produced the claim.

## 7. How the harnesses compare

| Harness | Per-role model | Who chooses | Router | Notes |
|---|---|---|---|---|
| Claude Code | yes: frontmatter, per call, env var, `opusplan` | user, definition author, or the parent model | none for models (auto mode is permissions) | Explore/Plan follow main model by default |
| Copilot CLI | yes: YAML pins, one inherits | author | Auto (task scoring, unpublished) | Haiku for `explore`/`task` |
| Cursor | no per-role | router | Compass + task router | per-turn, with cost modes |
| Amp | yes: `oracle` on another vendor | author | none found | fixed pins |
| Codex | yes: effort levels per delegate role | catalog | none | more effort on children than orchestrator |
| Aider | yes: architect/editor/weak models | user config | none | no cross-check |
| OpenCode | small model for side tasks | config | none | titles, summaries |
| Anthropic API | advisor tool | developer | none | executor/advisor pair |

Nothing here uses a cheap model to pick a *stage's* model; the only learned
routers (Cursor, Copilot) serve interactive turns, and the pins are static
config.

## 8. Findings

1. For "cheap collects, strong writes", **two stages joined by a typed handoff
   is the better default; a pinned-model sub-agent is the quick version.**
2. The advisor tool is the right idea for the *opposite* case (cheap executor
   that needs occasional strong planning) and is not portable.
3. Per-stage pinning needs no router. A router earns its keep only when the
   harness cannot name the stage, which is not Forge's situation.
4. For data analysis, tier by **mechanical vs judgment**, not by tool use vs
   prose. DAB says the judgment steps are where wrong answers come from.
5. No source measures cheap-collector/strong-writer on analysis tasks; the
   evidence is by analogy from coding. Treat the split as a hypothesis to
   measure (see `agent-design/models.md` §6).
