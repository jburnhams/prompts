# Hex's agents, and the context they run on

*Read 2026-11-12. Tags as in [`README.md`](./README.md).*

## 1. One agent, several doors

Hex markets several agents. The docs and the talk describe them as one
agent with different entry points and tool bundles. "Magic" is the old
name: Hex AI features were "formerly referred to as Hex Magic in
product". [docs]

| Surface | For | What it adds | Source |
|---|---|---|---|
| **Threads** | non-technical "self-serve" users, Explorer role | Chat that "heavily prioritizes semantic models and endorsed data sources"; shows thinking and tool calls live, then collapses them; returns tables, pivots and charts the user can keep exploring by hand | [docs] |
| **Notebook agent** | Editors in a project | Creates and edits Python, SQL, Markdown, pivot, input and chart cells; every change must be confirmed or undone **per cell**; inspects lineage before deleting a cell | [docs] |
| **Modeling agent** | Managers and Admins | Writes and edits semantic model YAML; "Always review the generated YAML"; agent checkpoints appear in the semantic project's history | [docs] |
| **Chat with App** | viewers of a published app | A Thread "with the app as context" that can change inputs and filters, sort, re-run, and also write new SQL beyond the app | [docs] |
| **Generative apps** | app builders | Prompted apps; a screenshot tool so "the agent can see the apps it builds" (2026-07-21); small chart edits routed to "a smaller, faster model" (2026-09-29) | [changelog] |
| **Slack, MCP, CLI, API** | anywhere | The Threads agent, entered from outside | [docs] |

Context Studio stopped separating "Threads" and "Notebook agent" in
September 2026 and now classes activity by purpose: **Analysis**, **App
building**, **Modeling**. "Where someone opens the agent doesn't tell you
much about what they're working on." [changelog 2026-09-29]

The talk says the same from the inside: the agents "started as separate
implementations and are merging into shared capability bundles (tools,
static context, prompts, behavioral specs) with different UX". [secondary]

### What a Thread is

- "Every Thread is backed by an unlisted project that the agent uses to
  answer questions." Editors can switch between **Agent**, **Notebook**
  and **App** views; "Selecting a cell reference in one of the agent's
  responses will take you directly to that cell in the Notebook."
  [docs]
- Saving does not copy: "it's the same project your Thread has been using
  all along". Others can edit the notebook "but can't continue your
  original Thread". Only the creator can send messages. [docs]
- A recipient must have "Can view results" on **every** data connection
  the Thread used, "including data connections used in the projects the
  agent used as context". [docs]
- "Sensitive threads" hide contents from Context Studio but "Workspace
  admins can still access the full contents if they have a direct link
  … so sensitive mode does not guarantee absolute privacy." [docs]

### Tools the docs name

"Examples of tools include searching for semantic columns, creating
visualizations, generating and executing SQL, and looking at
visualization results", plus a published-app search that "prioritiz[es]
endorsed projects" and "will not look at any unpublished projects", web
search and URL fetch (admin switch), file uploads (CSV joinable with
warehouse data; images). [docs]

**Subagents**: "the Hex Agent uses subagents to break your question into
focused workstreams that run in parallel — including finding the right
data connections, tables, and schemas, as well as handling chart
creation." Model selection "will only be applied to the main agent", not
to subagents "built for purpose specific tasks such as visualizations".
Since 2026-07-30 the main agent "builds straightforward charts directly
instead of handing off", keeping the chart subagent for complex ones.
[docs, changelog]

### Models

- **No routing.** "Hex does not do model routing — Auto defaults to a
  single model Hex chooses to optimize for speed, cost, and quality."
  Context Studio shows what Auto picked ("Auto (Opus 4.7)"). [docs,
  changelog 2026-08-10]
- A picker lists Anthropic, OpenAI, Moonshot and xAI models; effort maps
  "directly to the effort levels exposed by the underlying AI provider".
  A workspace default applies across every surface "including Slack,
  MCP, CLI". Selection "is stored per thread"; "New threads always
  start on Auto". [docs, changelog]
- Some models need the admin switch "Allow data retention for specific
  models"; providers otherwise run under zero data retention. [docs]

### Approvals

Two modes in the prompt bar since 2026-09-15: "*Ask for approval* …
pause for confirmation before destructive actions like deleting a cell
or publishing", or "*Skip approvals*" with undo of the last turn.
"Anything that expands access like granting OAuth, reconnecting an app,
or authorizing an MCP server still stops and waits for your approval."
[changelog] The access-expanding exception is a floor the user cannot
lower, which is the same shape as `../../agent-permissions-approval.md`'s
non-bypassable rules. [inference]

## 2. Context: four assets and a routing rule

Hex calls the work "context engineering" and gives it a product, Context
Studio. [docs]

| Asset | Loaded | Who writes it | Where it can live |
|---|---|---|---|
| **Workspace context**, the file `hex.md` | "always included in every conversation" | Admins, Managers | Hex, or a git repo synced in (reserved path `hex.md`) |
| **Guide library** | "retrieved dynamically when relevant", chosen by frontmatter `name` and `description` | Admins, Managers | Hex, or synced; synced guides are read-only in Hex |
| **Endorsements and exclusions** on tables, schemas, models, projects | as metadata on every search | Admins, Managers | Hex only |
| **Warehouse descriptions** | as schema metadata | anyone who can edit metadata | Hex, or the warehouse |
| **Semantic models** | preferred over tables by every agent | Admins, Managers | Hex, git, or synced from Cube, dbt MetricFlow, Snowflake Semantic Views, Databricks metric views, Apache Ossie |
| Reference repositories (code) | downloaded "within the thread" when a repo description matches | admin-configured | GitHub or GitLab cloud |
| User memory and personal preferences | every conversation, per user | Hex (nightly), the user | Hex |

[docs; reference repositories from `hex-skills` `advanced-context.md`,
source]

**The routing rule**, as Hex's own skill states it [source:
`context-consultant/SKILL.md`]:

> - Endorsing tables → endorse in Hex. Banning bad tables → **exclude
>   from AI** (not text bans in `hex.md`).
> - What a column contains → warehouse description. Join logic →
>   semantic model (else descriptions).
> - Applies to every question → `hex.md`. A specific domain/question
>   type → a guide.
> - Metric formulas → a guide or semantic model (not the always-on
>   context).

and from `context-architect.md`: "**Anti-pattern — don't duplicate in
workspace context.** Do not add a domain→table routing table to the
workspace context file. If your descriptions are good, the agent already
knows which endorsed asset to pick." Sizes recommended: `hex.md` "under
~300 lines / 800 words"; a guide "~150 lines / 350 words". [source]

The `hex.md` / guide-library split is AGENTS.md plus skills, with
retrieval by frontmatter description. Hex arrived at the same two tiers
as `../../agent-design/context-files.md` §1a, and adds a third that the
design lacks: **source-level flags (endorse, exclude) that the agent's
search reads, so a ban never depends on the model obeying prose.**
[inference]

### Governed mode

[docs, changelog 2026-10-30] Admins choose the sources the agent works
from: **Endorsed data**, **Semantic models only** ("doesn't query
warehouse tables directly or retrieve other projects as context. It can
still use SQL or Python to calculate and visualize results retrieved
through semantic models"), or **Custom** per asset type (all, endorsed,
specific statuses, none). The changelog adds a **Projects only** shape:
"It can run projects and change inputs, but won't write new warehouse
queries."

- It can be forced on Explorers and defaulted for everyone; Editors and
  above can toggle it per conversation.
- Config changes "apply to future agent responses in existing
  conversations".
- And the disclaimer, in a box of its own: **"Governed mode isn't a
  security control.** Governed mode strongly steers the agent toward the
  sources you choose, but it isn't a hard security boundary and doesn't
  replace data permissions." "Users can still query any data they have
  access to directly."

Hex says "strongly steers" and "guided to work from", so it is
reasonable to read Governed mode as filtering what the agent's search
tools return, not as a credential change. [inference] The honest label
is the lesson.

### Memory, kept apart from curated context

"User memory is a personal profile … updated nightly … inferred from
your Hex usage and conversation signals. Every conversation with the
agent receives this profile as user context, shaping how it
investigates and responds **without replacing checks against schemas,
endorsements, guides, and other workspace context**." Users can view and
turn it off. Personal preferences are separate, explicit and private.
[docs]

The talk gives the reason for the separation: memory is kept apart from
data-team context "because user memories can conflict with authoritative
definitions". [secondary]

## 3. Seeing what the agent did, and improving it

### Resources used, looked at versus used

"Hex shows you the resources the agent used, and even distinguishes
whether it just *looked at* a resource or actually *used it* in the
analysis", in the Thread Inspector, across Context Studio, and in CLI
output. [changelog 2026-07-30] The eval bootstrap prompt relies on it:
`hex thread get --json` has "its `resources` array (the exact tables
and semantic models it touched)". [docs]

### Warnings: three kinds, raised by the agent

| Warning | What it means [docs] |
|---|---|
| **Missing context** | "The agent needed information that is not documented in your workspace, such as a metric definition, a table relationship, or a business rule" |
| **User doubt** | "The user expressed skepticism or pushed back on the agent's answer" |
| **Data limitation** | "The agent flagged a caveat about the data it used, such as incomplete coverage, a known gap, or an assumption it had to make" |

The CLI filter adds `OTHER`. [source] "Each warning includes suggested
context updates." The Thread Inspector also shows an **Overview** with
"the user's intent, the agent's assumptions", the model and credits.
[docs]

### Suggestions: clustered, thresholded, reviewed

[docs] "When multiple warnings from recent conversations point to the
same underlying knowledge gap, Hex groups them into a single suggestion
and proposes concrete changes". Proposed change types: create or update
a guide, update workspace rules, update table or column descriptions,
endorse a resource. Each is accepted or rejected individually; for
git-synced guides the admin makes the change in git and marks it done.

- "Not every warning becomes a suggestion. Hex filters for durable,
  reusable knowledge gaps … One-off mistakes and product limitations are
  filtered out."
- **Thresholds**, admin-tunable: minimum users **2**, minimum
  conversations **2**, minimum sources **3**.
- **Custom instructions** for "the review agent", e.g. "prefer updating
  guides over adding column descriptions".
- Evidence (the conversations) is visible to Admins only; Managers see
  the suggestion without the evidence.

This is the closest public analogue to the consolidation step in
`../../agent-design/memory.md` §3c, with two things that design does not
have: a **distinct-user threshold** (one user's repeated confusion is
not a workspace gap), and **evidence access split by role**. [inference]

### Topics and export

Topics are generated per conversation, "may not appear for every
conversation", may be assigned "after a conversation becomes inactive".
Every thread, every message and its metadata can be exported by API or
CLI, and joined to user and group. [docs, changelog 2026-07-14]

## 4. Harness internals (secondary only)

From a ZenML LLMOps Database write-up of a talk by Izzy Miller, an AI
engineer at Hex (2026, no exact date). [secondary] Recorded because
nothing first-party covers it; no proposal rests on it alone.

- **Orchestration**: moved to "a Temporal-based architecture" for
  long-running runs, built in-house, run side by side with the old
  system during migration. Runs of "20+ minutes" on complex analysis.
- **Context**: static (tool definitions, system prompts, guides as
  "Hex's version of skills") and dynamic (retrieval over notebooks,
  threads, semantic models, warehouse metadata); guides by progressive
  disclosure; tool search to keep tools out of the window.
- **Tool weight**: the notebook agent had "nearly 100,000 tokens worth of
  tools, which Izzy acknowledges is too many"; merging chart
  create/update/delete into one tool cut tokens "without hurting
  performance". Specific tools are preferred over generic code execution
  because they can encode when and how to use a capability.
- **An ID registry** to stop models confusing cell IDs in notebooks past
  "50–60 cells", now unnecessary with newer models and "technical debt".
- **Ephemeral SQL**: investigative queries that "do not appear in the
  final notebook", which keeps notebooks clean "but hides the evidence";
  users sometimes got an answer from an ephemeral query "with no visible
  proof".
- **Failure modes named**: over-investigation ("50 ephemeral SQL queries
  just to be certain"), a model that given contradictory context "might
  spend 30 minutes pondering and enter a collapse mode of second-guessing
  itself", and **anomaly blindness**: a fan-out bug that puts every sales
  rep at "900%+ of quota" is reported as fact unless the model is
  prompted that something looks wrong.
- **Evals**: core sets of "30-50 carefully crafted examples" with
  repetitions; public benchmarks criticised for bad ground truth; "Metric
  City", a simulated 90-day company warehouse, on which one model scored
  "approximately 4% on day zero and 24% on day ninety".
- **Compaction** threshold raised from 200,000 to 300,000 tokens with a
  million-token window.

The ephemeral-SQL point is the one that matters for Lens: Hex found that
evidence kept off the record is evidence the user cannot check, which is
the case for `lens.quick.v1.md`'s "Never state a number that did not
come from a query in this run" *and* for keeping every query's ref.
[inference]
