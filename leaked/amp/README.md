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
  work" — stateless, one-shot, single final report. No sub-agent system
  prompt text is captured for any of the three (only the orchestrator-
  facing tool descriptions).
