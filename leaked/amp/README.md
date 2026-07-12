# Amp

- **Type**: Coding agent · **Vendor**: Sourcegraph · **Status**: closed source (leaked)
- **Mirror source**: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Amp (2026-07-10)

## Files
- `claude-4-sonnet.yaml` — system prompt used when running on Claude 4 Sonnet.
- `gpt-5.yaml` — system prompt used when running on GPT-5.
- `EXTRACTION-NOTES.md` — the mirror repo's own notes on how these were
  extracted (via Amp's "view Thread YAML" debug feature), kept for
  reproducibility. Also notes that Amp "has other LLMs registered into it
  as tools ('the oracle')" — relevant background for the sub-agent
  section below.
- `amp-code.md` — a much richer, later capture (2026-05-09, binary
  version `0.0.1778328768-gb9a37d`), pulled directly from strings inside
  the `~/.amp/bin/amp` Rust binary's embedded Bun runtime rather than via
  the in-product debug YAML view, mirrored from a different,
  independently-maintained leak aggregator (`asgeirtj/system_prompts_leaks`,
  retrieved 2026-07-12) than the two YAML files above. It doesn't just
  restate the two YAML captures in more detail — it shows the **mode
  architecture the orchestrator prompt is assembled from**, something
  neither YAML file had any way to reveal since each is one rendered
  thread's single prompt. See "Prompt assembly: eleven named modes, not
  one prompt" below — this is a genuine, verified structural finding, not
  a restatement.

## Prompt assembly: eleven named modes, not one prompt

`amp-code.md` documents Amp's system prompt as identity-string-plus-
shared-sections, concatenated at runtime depending on which of (at
least) eleven named agent modes is selected — confirmed by direct
cross-reference, not just asserted by the extraction notes: several
mode sections explicitly say they "share the same" subsections as
another named mode (e.g. §3 Pair Programming Mode's
`<investigate_before_acting>`/`<pragmatism_and_scope>`/`<verification>`/
`<tool_use>`/`<using_subagents>` blocks are stated to be reused verbatim
by §4 Frontier/Lead Orchestrator Mode), and the two YAML captures'
"You are Amp, a powerful AI coding agent" identity line plus their
`todo_write`/oracle/`Task` tool content reappears near-verbatim inside
`amp-code.md`'s §5/§6 (Standard/Full Agent Mode) — real convergent
confirmation that the YAML captures and this binary capture describe the
same underlying product, just different modes of it.

This is a different axis from the "Sub-agents" section below (which is
unchanged and still accurate — the `Task`/`oracle`/`codebase_search_agent`
menu is a *within-conversation delegation* mechanism). What's new here is
that the **top-level identity the orchestrator itself runs under** is
mode-selected, not fixed:

- **d_R "You are Amp."** — the plain default identity, closest to the
  general tone of the two YAML captures.
- **g_R "an autonomous coding agent"** and **O_R "pair programming with
  a user"** — two distinct persistence/collaboration postures: g_R
  explicitly prefers "making progress over stopping for clarification,"
  O_R explicitly frames the model as "a collaborator, not just an
  executor" that should flag the user's own misconceptions.
- **o_R "an autonomous coding agent and lead orchestrator"** — a fourth
  identity, layered on top of O_R's shared sections, whose distinguishing
  addition is delegation ("plan the work, delegate targeted subtasks
  when useful, integrate the results").
- **x_R/P_R/p_R "a powerful AI coding agent"** — three tiers of the same
  base identity: Standard (x_R, closest to the YAML captures' content
  and worked examples), Full (P_R, adds an explicit TODO tool, a named
  three-way subagent menu with a prescribed "Oracle (plan) → Codebase
  Search (validate scope) → Task Tool (execute)" pipeline, and a
  granular parallel/serialize policy), and Lite (p_R, P_R's guardrails
  and parallel-execution policy with the example transcripts and
  quality-bar prose stripped out).
- **j_R/I_R — "optimized for speed and efficiency" / "Rush Mode"** — two
  extreme-terseness identities not hinted at by either YAML capture:
  "SPEED FIRST... minimize thinking time, minimize tokens, maximize
  action," "ULTRA CONCISE. Answer in 1-3 words when possible," with a
  worked example table (`"what's the time complexity?"` → `O(n)`).
- **H_R — the generic subagent prompt.** This is the single most
  valuable addition relative to the existing "Sub-agents" section below,
  which previously stated flatly: "No sub-agent system prompt text is
  captured for any of the three [`Task`/`oracle`/`codebase_search_agent`]
  (only the orchestrator-facing tool descriptions)." `amp-code.md`
  supplies exactly that missing text: "You are [specialAgentName or
  'Amp'], a powerful AI coding agent," with its own compact ruleset
  (absolute paths only, read a file once, treat AGENTS.md as ground
  truth, prefer `finder` for codebase discovery). Confirms the delegate
  runs a real, minimal system prompt of its own rather than an empty
  context window with just the task description.
- **l_R "Agg Man, Amp's platform control-plane assistant"** — not a
  coding agent at all: a separate persona for workspace/thread
  management (finding threads, replying, merge/ship/code-review
  workflow triggers, Slack). Notable for an explicit anti-hallucination
  rule absent elsewhere in this collection's Amp material ("Never invent
  thread content, metadata, or outcomes") and a hard rule against
  self-initiated action on shared/team-visible operations ("Never merge
  a thread proactively or as an assumed next step... Only trigger the
  merge workflow when the user explicitly asks").

**Two smaller, dated findings worth flagging on their own:**

- **Diagrams: Mermaid is gone.** `claude-4-sonnet.yaml`/`gpt-5.yaml`
  both specify a dedicated `mermaid` tool with explicit dark-fill-color
  styling rules ("Use DARK fill colors (close to #000) with light stroke
  and text colors"). `amp-code.md` (the later capture) instead
  explicitly forbids Mermaid: "There is no Mermaid tool or renderer: do
  not write Mermaid syntax such as `graph TD` or `sequenceDiagram`, and
  do not use `mermaid` code fences" — diagrams are now plain
  box-drawing-character ASCII inside a generic `diagram` fenced block.
  A real, dated product change between the two captures, not a
  discrepancy between two descriptions of the same thing.
- **A two-channel turn-output model, absent from the YAML captures**:
  `commentary` (short 1-2 sentence progress updates sent mid-task —
  "a meaningful discovery, a decision with tradeoffs, a blocker") vs.
  `final` (the concluding response, favoring 1-2 short paragraphs over
  bullets for simple tasks). See `agent-turn-output.md` for the
  cross-source note this feeds — the channel *names* directly echo
  OpenAI's Harmony/`gpt-oss` `analysis`/`commentary`/`final` channel
  taxonomy, notable since Amp's underlying model here is Claude, not an
  OpenAI model — evidence of cross-vendor terminology borrowing at the
  scaffold level, not a model-native mechanism.

## Sub-agents

**Three distinct, named sub-agent tools**, each with its own model,
tool scope, and stated use case — identical across both the Claude
4 Sonnet and GPT-5 variants (same three tools, same guidance text). No
other source in this collection offers the model a *menu of different
kinds* of delegation rather than one general-purpose delegate:

- **`Task`** — "Fire-and-forget executor for heavy, multi-file
  implementations. Think of it as a productive junior engineer who can't
  ask follow-ups once started." Tool-scoped to `list_directory, Grep,
  glob, Read, Bash, edit_file, create_file, format_file, read_web_page,
  get_diagnostics, web_search, codebase_search_agent` — full read/write/
  execute access, i.e. it can itself call the codebase-search sub-agent.
  For "feature scaffolding, cross-layer refactors, mass migrations,
  boilerplate generation," explicitly not for "exploratory work,
  architectural decisions, debugging analysis."
- **`oracle`** — "an AI advisor powered by OpenAI's o3 reasoning model
  that can plan, review, and provide expert guidance." **The only
  sub-agent in this entire collection explicitly specified to run on a
  different underlying model than the orchestrator** — every other
  source's delegate runs as the same model driving the main loop (or
  doesn't specify). Read-only tool scope (`list_directory, Read, Grep,
  glob, web_search, read_web_page`) — no edit/bash access, consistent
  with an advisory-only role. For "code reviews, architecture decisions,
  performance analysis, complex debugging, planning Task Tool runs" —
  notably, planning *for* the Task tool is one of Oracle's own stated
  jobs, making it a sub-agent whose output feeds another sub-agent's
  input.
- **`codebase_search_agent`** — "Smart code explorer that locates logic
  based on conceptual descriptions across languages/layers," scoped to
  `list_directory, Grep, glob, Read`. For "mapping features, tracking
  capabilities, finding side-effects by concept," not for "code changes,
  design advice, simple exact text searches" — the same semantic-vs-grep
  distinction other sources draw (Cursor's `codebase_search`, Windsurf's
  `codebase_search`), but exposed here as a callable sub-agent rather
  than a plain tool.
- **A prescribed workflow chaining all three**: "Oracle (plan) →
  Codebase Search (validate scope) → Task Tool (execute)" — stated
  directly as a best practice, making the three-sub-agent menu a
  pipeline rather than three independent options.
- **Fine-grained parallel/serial rules spanning both ordinary tools and
  sub-agents in one policy**: "Codebase Search agents: different
  concepts/paths in parallel," "Oracle: distinct concerns... in
  parallel," "Task executors: multiple tasks in parallel **iff** their
  write targets are disjoint," with a worked good/bad example pair
  (`Task(refactor)` and `Task(handler-fix)` both touching
  `api/types.ts` "must serialize"). More granular than any other
  source's parallel-sub-agent guidance in this collection — Gemini CLI's
  "never mutate the same files" rule is the closest comparison, but
  without Amp's per-sub-agent-type breakdown.
- **Protocol**: matches the Claude-Code-lineage pattern almost verbatim
  for the `Task` tool specifically — "you will not see the individual
  steps of the sub-agent's execution, and you can't communicate with it
  until it finishes, at which point you will receive a summary of its
  work" — stateless, one-shot, single final report. The two YAML
  captures show no sub-agent system prompt text for any of the three
  (only the orchestrator-facing tool descriptions) — **update**: the
  later `amp-code.md` binary capture fills this gap with `H_R`, the
  actual generic subagent system prompt ("You are [specialAgentName or
  'Amp'], a powerful AI coding agent..."), confirming the delegate runs
  a real, minimal prompt rather than a bare task description. See
  "Prompt assembly" above.
