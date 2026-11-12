# Hex

- **Type**: commercial AI analytics platform (notebooks, apps, a
  conversational agent called Threads), with a remote MCP server and an
  MCP Apps connector in Claude. **Closed source.** No system prompt,
  tool schema or harness code is public.
- **Vendor**: Hex Technologies · **Licence**: proprietary (the product
  and the `hex` CLI); the public `hex-inc/hex-skills` and
  `hex-inc/action-context-toolkit` repos are MIT.
- **Prompted by**: Jonathan, 2026-11-12, as one of the per-vendor threads
  out of the MCP Apps deep dive ("please have a separate thread on
  each"). The MCP Apps pass had Hex as one row and one paragraph
  (`../../mcp-apps/data-analysis.md` §3); this folder is the full read.
- **Read**: 2026-11-12. Hex's documentation fetched as Markdown
  (`Accept: text/markdown`, which the site supports for every page), the
  changelog RSS and 16 dated changelog pages (2026-03-03 to 2026-11-10),
  four blog posts, the Claude directory listing, an unauthenticated
  probe of `https://app.hex.tech/mcp`, the public `hex-skills` repo at
  `17f928f` and `action-context-toolkit` at `6246f48`, and one
  secondary write-up of a Hex engineer's talk. Details in
  [`../../sources.md`](../../sources.md), "Hex (read 2026-11-12)".

## How to read this folder: evidence versus inference

Hex cannot be read as code, so every claim here carries one of these
tags, and the tag is the claim's strength:

| Tag | Means | Strength |
|---|---|---|
| **[docs]** | learn.hex.tech, read on 2026-11-12 | What Hex says the product does. Docs-only: not exercised. |
| **[changelog]** | a dated learn.hex.tech changelog entry | Same as docs, plus a ship date. |
| **[blog]** | hex.tech or claude.com blog post | Marketing register; weakest first-party source. |
| **[source]** | code or prompt text in a public Hex repo | Verbatim; strongest evidence, but it is Hex's *skills for other agents*, not Hex's own agent. |
| **[probe]** | an HTTP request made from this session | Observed behaviour, unauthenticated only. |
| **[secondary]** | a third party's summary of a Hex talk | Paraphrase of a paraphrase. Used only for harness internals nothing else covers, and never as the sole basis for a proposal. |
| **[inference]** | this collection's reading of the above | An argument, not a fact. |

**Nothing was run against a Hex workspace.** No account was used, so the
MCP tools, the widgets and the agent were not exercised. Where the docs
and the Claude directory disagree (they do, see `mcp-server.md` §5) both
are reported.

## The files

| File | What |
|---|---|
| [`mcp-server.md`](./mcp-server.md) | The remote MCP server: 18 documented tools in two tiers, an agent behind three of them, polling, sensitive-connection rules, the Claude MCP Apps connector (thinking steps, chart carousel, 24-hour expiry), Hex 4.0's undocumented project tools, and what the docs leave unsaid about what the host model sees |
| [`agents-and-context.md`](./agents-and-context.md) | The agent family (Threads, Notebook agent, Modeling agent, Chat with App, the subagents), the context assets (`hex.md`, a retrieved guide library, endorsements, exclusions, Governed mode, user memory), observability with a three-type warning taxonomy, Suggestions with evidence thresholds, approvals, and the harness internals from the talk |
| [`semantic-layer.md`](./semantic-layer.md) | The semantic model YAML (models, measures, relations, semi-additive measures, views), the Hex 4.0 semantic query file, and **how a query is bound to what the user sees**: model → query file → named table → chart → app element, walked back by Inspect |
| [`evals.md`](./evals.md) | The eval suite format (three rubric types, SQL ground truth computed at grade time, attempts, `warnOnly`, measures), context previews as a fork-test-publish loop, and **the bootstrap prompt Hex publishes for coding agents**, verbatim |
| [`hex-skills.md`](./hex-skills.md) | Hex's public Agent Skills repo: the `context-consultant` dispatcher and its eval-engineer and context-architect subagents, the migration skills' SQL-fidelity gate, with the prompt text that matters quoted |

Proposals for Lens and Forge, **none adopted**, are in
[`../../agent-design/proposals-hex-2026-11.md`](../../agent-design/proposals-hex-2026-11.md).

## Ten findings

1. **The MCP server puts an agent behind a tool, asynchronously.**
   `create_thread` starts a Hex agent run and returns an ID;
   `get_thread` is "designed to be called multiple times until the
   Thread reaches idle status"; `continue_thread` refuses while a run is
   in progress. Threads "typically take several minutes". [docs] It is a
   hand-rolled task protocol on plain tools, not MCP's own task
   mechanism. [inference]
2. **In Claude the poll loop drives the view.** "The Hex Connector will
   continually make `get_thread` calls without user prompting"; the
   widget shows the inner agent's thinking steps, then a carousel of the
   charts and tables it made; Claude then summarises and links to the
   thread. Widgets expire after 24 hours. [docs] What reaches Claude's
   context, and whether rows do, is not documented. [inference: see
   `mcp-server.md` §4]
3. **The view is bound to server-side handles, not to data the model
   carried.** `get_thread` "reports the cell ID of each chart in a
   Thread", and `get_cell_image` renders any chart cell by ID for hosts
   without widgets. [docs] So the chart in Claude is a reference into a
   Hex project, which is shape C in `../../mcp-apps/data-analysis.md`
   §1, reached by a different route: the binding is a cell, not a
   semantic query. [inference]
4. **Every Thread is a project.** "Every Thread is backed by an unlisted
   project that the agent uses to answer questions", and saving it does
   not copy anything: "it's the same project your Thread has been using
   all along". [docs] The conversation is a view over a reproducible
   artifact, which is the property `../../agent-design/data.md` §2f's
   provenance gate tries to impose after the fact. [inference]
5. **Context is four assets with a routing rule, and bans are metadata,
   not prose.** An always-on `hex.md`, a guide library retrieved by
   frontmatter `name`/`description`, endorsements and "exclude from AI"
   on tables, and semantic models. Hex's own skill says "Banning bad
   tables → **exclude from AI** (not text bans in `hex.md`)" and "text
   bans are unreliable". [docs, source]
6. **Governed mode is steering and says so.** It limits the agent to
   chosen sources (endorsed, semantic models only, or a custom mix), and
   the docs warn: "Governed mode isn't a security control … it isn't a
   hard security boundary and doesn't replace data permissions". [docs]
7. **The semantic layer is the agent's preferred substrate, and in 4.0
   its queries are files.** A `.query.yml` names a semantic project, a
   base model or view, and ordered `aggregate`/`select` transforms; "each
   file produces a table named after the file". Modeled measures cannot
   be re-aggregated ("`sum(total_revenue)` [is] invalid"). [docs]
8. **Agent quality is managed as a loop with evidence thresholds.** The
   agent tags conversations with warnings (*missing context*, *user
   doubt*, *data limitation*); a review agent clusters them into
   Suggestions only when at least 2 users, 2 conversations and 3 signals
   agree (defaults); an admin accepts each proposed change. [docs]
9. **Evals are YAML in the repo, graded against SQL that runs at grade
   time, and gate context changes in a fork.** `numeric_value` with a
   `{sql, dataConnectionId}` target, `judge_thread` over the whole
   transcript, `judge_final_answer` over the answer only, 1–5 attempts
   tolerating one failure, and `hex eval run --preview-id` against a
   context preview before `hex context publish`. [docs]
10. **Hex's published prompts are about measurement, not answering.**
    The eval bootstrap prompt and the `eval-engineer` subagent tell a
    coding agent to source cases from real threads, never copy thread
    content into the suite, write rubrics as *failure conditions*, and
    prefer "analytical-reasoning traps" (causal overreach, selection
    bias, Simpson's paradox) over definition gaps, because those "find
    the model's ceiling". [source]

## Corrections to earlier entries in this collection

- `../../mcp-apps/catalogue.md` and `data-analysis.md` §3 described the
  Hex view as "charts and tables with citations". The **citations** come
  from Claude's 2026-01-26 announcement [blog]; Hex's own docs and blog
  never use the word. They say thinking steps show "which tables or
  semantic models the agent is referencing" and let you "spot-check the
  underlying SQL". The carousel is in Hex's docs. Both pages now carry a
  dated note.
- The same pages said "Claude, the host model, sees a text summary". The
  docs say Claude "will summarize its key findings", which is consistent
  with that but does not say what `get_thread` returns to the model.
  Marked as inference.

## What is not known

- **The Hex agent's system prompt, tool schemas and model defaults.**
  Not published. The docs name tool *kinds* ("searching for semantic
  columns, creating visualizations, generating and executing SQL, and
  looking at visualization results"); the talk write-up says the
  notebook agent had "nearly 100,000 tokens worth of tools". [docs,
  secondary]
- **The MCP tools' JSON schemas and annotations.** Behind OAuth. The
  probe confirms an RFC 9728 protected-resource document pointing at a
  separate authorisation server, `auth.app.hex.tech`. [probe]
- **The MCP Apps view's `ui://` resource, its CSP, which app-only tools
  it calls, and the `content`/`structuredContent` split.** Not
  documented; only an authenticated session would show them.
- **Hex 4.0's MCP "4.0 project tools".** Named in the 4.0 docs ("you will
  need to explicitly prompt your external agent to use '4.0 project
  tools'") and absent from the MCP tool list. [docs]
