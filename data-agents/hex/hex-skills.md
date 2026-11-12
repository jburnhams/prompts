# `hex-inc/hex-skills`: Hex's prompts for other people's agents

- **Repo**: `github.com/hex-inc/hex-skills`, MIT, read at `17f928f`
  (2026-11-11), cloned `--depth 20`. Fifteen commits since 2026-03-12.
- **What it is**: Agent Skills for Claude Code (plugin marketplace),
  Codex (`AGENTS.md` routing), Cursor and any `npx skills` host, plus a
  separate bundle for Snowflake Cortex Code. Not Hex's own agent prompts:
  these teach an *outside* coding agent to drive Hex through the CLI.
- **Tag**: everything quoted here is [source].

## 1. What is in it

| Skill | Lines (`SKILL.md`) | Job |
|---|---|---|
| `context-consultant` | 163 | A dispatcher over two subagents (`context-architect`, `eval-engineer`), two workflows (`bootstrap`, `improve-loop`) and references, for building and measuring the context Hex's agents run on |
| `looker-migration` | 219 | Rebuild Looker dashboards in Hex: the coding agent reads LookML and Looker's API, Hex's notebook agent builds a generative app, the coding agent verifies |
| `tableau-migration` | 213 | The same for Tableau `.twb` workbooks |
| `snowflake-coco/hex` | router + 8 sub-skills | The above plus setup, project authoring, notebook authoring, "business analytics", and Cortex `AI_*` functions, for Snowflake's agent |

## 2. The idea that runs through all of it: two agents, two lanes

Every skill splits the work between an outside coding agent that cannot
see the data and Hex's agent that can.

From `context-consultant/SKILL.md`:

> **Two agents, two lanes.** You own the plumbing (repo, config, CLI, PR
> flow) but can't see the warehouse — the **Hex agent** (Threads/Notebook)
> can. When content must reference real tables/columns, have it draft it,
> then bring the draft back. Never invent names you can't verify.

From `looker-migration/SKILL.md`:

> This coding agent (reading this skill) is **blind to the things that
> make the build correct**: it can't see the live **warehouse schema** or
> data, it can't see the customer's **Hex workspace context** … **Division
> of labor:** this coding agent owns **understanding the Looker source** …
> and **verifying the result** (the fidelity gate + visual-QA loop). The
> notebook agent owns **buildin[g]** …

The channel between them is a Thread: `hex thread create`, poll `hex
thread get`, `hex thread continue` for fixes. That is the MCP server's
`create_thread` / `get_thread` / `continue_thread` (`mcp-server.md` §2)
on the CLI. [inference] It is Lens's `HandOff` in reverse: the cheap
outer agent hands *data* work to the specialist and keeps the
orchestration and the checking.

## 3. Context-consultant

Covered in `agents-and-context.md` §2 (routing rule, sizes, the
semantic-first policy) and `evals.md` §5 (rubric rules). Three things
not covered there:

**Tell it once, then detect.**

> The user should tell you their setup **once**. Most of it is
> detectable, and the rest gets remembered, so returning users skip
> straight to their task.

The skill runs `hex connection list`, `hex context semantic-project
list`, `hex suggestion list`, reads `hex_context.config.json` and any
`evals/*.yaml`, then reads a six-line `hex_context.profile.md` if
present, and asks only what is left. "Re-detecting each session is cheap
and keeps it fresh; the profile only holds what detection can't."

**Run the loop yourself, return the verdict.**

> **Run the loop yourself and return the verdict, not the mess.** Eval
> runs and thread transcripts are large; that output belongs in this
> subagent, not the main thread. … hand back the conclusion: the pass
> rate, which cases moved, and the specific gap behind each real
> failure.

**Ask the specialist to audit itself.** For a semantic-first rollout the
skill has the Hex agent review its own context: "*Review my workspace
context and guides against my semantic models. Tell me what to change so
you always answer semantic-model-first and only drop into raw SQL with
my explicit approval. Flag anything in my guides … that's already
covered by a model, so I can remove it and stop tempting you into
hand-written SQL.*" The rationale: "It knows its own routing and your
models; you don't."

## 4. The migration skills' SQL-fidelity gate

`looker-migration/reference/sql-review.md` is the most careful
verification text in the repo. Its premise:

> It catches the **dangerous error class**: SQL that is *syntactically
> fine* — it runs, the run-status oracle returns COMPLETED — but is
> **semantically wrong**. Missed an explore-level filter, wrong week
> anchor, `count` where the measure was `count_distinct`, wrong grain, a
> `one_to_many` join that fanned out the rows … The oracle can't see any
> of these (they all COMPLETE), and **the agent that wrote the SQL is the
> worst judge of it** — it made the mistake precisely because it didn't
> notice.

The fix is "**structured + independent + targeted + measured**":

1. **A translation ledger** per SQL cluster: fields, measure types,
   filters at every scope, grain, date granularity and week start, window
   calcs, joins with their `relationship:`, row-level security, nested
   access, Liquid.
2. **Independent re-derivation.** "On Claude Code (and hosts with
   subagents): spawn a subagent. Give it *only* the LookML … and the
   cluster's ledger row — **not** the SQL you wrote". Without subagents,
   a fresh-context self-review: "Not 'does this look right'; **'here's
   what it should be — does it match?'**"
3. **A mistake-class checklist** and **differential probes** that prove a
   filter or join behaves.
4. **Numeric parity**: Looker's own result rows from its API against
   Hex's from `hex cell run --with-output`, diffed per cluster.

And the render half, `visual-qa-loop.md`: Looker's render API produces
the source PNG; Playwright with a persistent profile, which "the
*customer* logs into … **once**", screenshots the Hex app; the diff
drives "surgical `hex thread continue` fix batch[es]". "Absence of
browser access means visual QA is blocked, not passed" (from the CoCo
`hex-project` skill).

Two things here are worth recording for Lens [inference]:

- **The unit of review is the SQL cluster, not the chart**, "the unit
  that carries the filters, joins, and grain". Several tiles share one
  query; review the query once.
- **"Blocked, not passed"**: a check that could not run is reported as
  not run. That is `generative.md` §2c's fixed "what it did *not* check"
  line, arrived at independently.

## 5. What the repo does not contain

No Hex system prompt, no tool schemas, and no prompt for Hex's own agent
except the "guide-writing guide", a guide meant to be *added to a
workspace* so the Hex agent can "draft data-grounded context". That file
is the closest thing to a Hex-agent prompt in public, and it is context,
not a system prompt.
