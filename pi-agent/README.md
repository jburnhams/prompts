# Pi (Agent Harness)

- **Type**: Coding agent (minimal terminal harness — "adapt pi to your
  workflows, not the other way around")
- **License**: MIT
- **Source**: https://github.com/badlogic/pi-mono (`packages/coding-agent`)
- **Retrieved from**: the published npm package
  [`@earendil-works/pi-coding-agent`](https://www.npmjs.com/package/@earendil-works/pi-coding-agent)
  v0.80.6 (compiled `dist/`, since the GitHub source directory listing
  wasn't reachable at time of writing — content matches the published
  package, not hand-transcribed) (2026-07-10)

Not to be confused with `badlogic/pi` (same author, unrelated — a GPU pod
manager for deploying local LLMs). This is "Pi Agent Harness" / pi.dev.

By default Pi gives the model exactly four tools: `read`, `write`, `edit`,
`bash` — extended via user-installed skills, extensions, and prompt
templates rather than a large built-in surface. This shows up directly in
the system prompt: it's built as a small function rather than a long
static document.

## What makes the base prompt minimal

`buildSystemPrompt()` in `system-prompt.js` assembles the whole thing from
a handful of moving parts rather than a large fixed block of rules:

- **One persona sentence**: "You are an expert coding assistant operating
  inside pi, a coding agent harness." No elaborated role/backstory beyond
  that.
- **Tool list built from whatever tools are actually registered** — each
  tool contributes its own one-line snippet (`toolSnippets[name]`, defined
  per-tool elsewhere, not in this file) rather than the system prompt
  hardcoding tool descriptions.
- **Guidelines are conditionally added, with deduplication** — e.g. "Use
  bash for file operations like ls, rg, find" is only added if `bash` is
  available *and* `grep`/`find`/`ls` are not, avoiding redundant
  instructions when more specific tools exist. Only two guidelines are
  unconditional: "Be concise in your responses" and "Show file paths
  clearly when working with files" — contrast with Claude Code/OpenCode's
  much longer, example-laden terseness sections (see
  `coding-agent-approaches.md` §11).
- **No code-editing format taught in the base prompt at all** — unlike
  every source surveyed in `coding-agent-approaches.md` §5, Pi's system
  prompt doesn't describe *how* to edit (no SEARCH/REPLACE teaching, no
  old_string/new_string rules) — that's left entirely to the `edit` tool's
  own schema/description, not the persona-level prompt.
- **Self-documentation via bundled files, not a live doc fetch**: instead
  of Claude Code/OpenCode's "use WebFetch to check the docs website"
  pattern, Pi points the model at *local* file paths shipped with the CLI
  itself (`readmePath`, `docsPath`, `examplesPath`) and instructs it to
  read them "when the user asks about pi itself" — the practical
  implementation of the README's claim that you can "ask the agent to
  explain itself." No other source in this collection self-documents via
  bundled local files rather than a network fetch.
- **A full custom-prompt escape hatch**: if a user sets their own system
  prompt (`.pi/SYSTEM.md` project-level or `~/.pi/agent/SYSTEM.md`
  global), `buildSystemPrompt()` takes an entirely different code path
  that skips all of the above — the tool list, guidelines, and
  self-documentation section are Pi's *defaults*, not something layered
  underneath a custom prompt the way, say, Claude Agent SDK's
  `append_system_prompt` works.
- Project context files (`AGENTS.md`-equivalent) and skills are still
  appended in both the default and custom-prompt paths, in an
  `<project_context>`/`<available_skills>` XML-ish envelope similar to
  other sources in this collection.

## Files

- `system-prompt.js` — the full `buildSystemPrompt()` function described
  above.
- `compaction/prompts.js` — the context-compaction/summarization prompts
  (extracted from `core/compaction/utils.js` and
  `core/compaction/compaction.js`, prompt constants only, not the
  surrounding cut-point-selection logic): a short system prompt plus a
  strict structured-summary template (`## Goal` / `## Constraints &
  Preferences` / `## Progress` / `## Key Decisions` / `## Next Steps` /
  `## Critical Context`), with a separate variant for incrementally
  *updating* an existing summary rather than writing one from scratch.
  Worth comparing against `../goose/compaction.md`, the collection's other
  dedicated compaction prompt.

## Tool surface

The defining trait is that the tool surface **is the prompt** —
`toolsList` is built by mapping over whichever tool names are actually
selected (`selectedTools || ["read", "bash", "edit", "write"]`) and
pulling each one's own one-line description out of `toolSnippets`, a
table defined outside this file per-tool. Nothing about a specific
tool's behavior is hardcoded into the system-prompt text itself.
- **Default four tools**: `read`, `write`, `edit`, `bash` — no
  search/grep/glob tool ships by default. `bash` is the fallback for
  everything else, per the conditionally-added guideline "Use bash for
  file operations like ls, rg, find" (added only when `bash` is available
  *and* dedicated `grep`/`find`/`ls` tools are not, avoiding redundant
  instructions when a project *does* wire up more specific tools) — an
  explicit named preference for `rg` over other search commands when
  falling back to bash, same preference Codex states for its own search
  guidance (see `coding-agent-approaches.md` §4).
- **No taught edit format**: unlike every other source surveyed in
  `coding-agent-approaches.md` §5, the base system prompt says nothing
  about *how* to edit (no SEARCH/REPLACE, no old_string/new_string
  rules) — that's entirely delegated to the `edit` tool's own
  schema/description, which lives outside `system-prompt.js`.
  Consistent with the "small function, not a long document" design: the
  persona/guideline layer stays generic, tool-specific mechanics stay
  with the tool.
  - **Extensibility — skills, extensions, custom tools**: the four
  built-ins are explicitly a starting point, extended via user-installed
  skills (`formatSkillsForPrompt`, appended only if `read` is available),
  extensions, and prompt templates. Any additional registered tool
  automatically gets a line in the tools list the same way the four
  built-ins do, since the list is generated from whatever's registered,
  not a fixed enumeration.
- **Self-documentation via bundled local files, not a fetch tool**:
  `readmePath`/`docsPath`/`examplesPath` point at files shipped with the
  CLI itself; the model is told to read them directly rather than
  fetching a docs website (contrast Claude Code's/OpenCode's
  WebFetch-the-docs-site pattern) — the only source in this collection
  that self-documents this way.
- **Browser/web/multimodal**: none in the base prompt/tool set described
  here.
- **Sandbox/isolation**: not specified — runs as a local CLI process.
- **Full override escape hatch**: a user-supplied `.pi/SYSTEM.md` or
  `~/.pi/agent/SYSTEM.md` replaces the entire tool-list/guidelines/
  self-documentation assembly described above, rather than layering on
  top of it.
