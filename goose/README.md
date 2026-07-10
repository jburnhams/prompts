# Goose

- **Type**: Coding agent (Block's general-purpose, extensible AI agent — CLI
  + desktop)
- **License**: Apache-2.0
- **Source**: https://github.com/block/goose
- **Retrieved from**: `main` branch,
  `crates/goose/src/prompts/` (2026-07-10)

Goose's prompts are Jinja2-style templates (`{% if %}` / `{{ var }}`)
rendered by its Rust core, covering the main system prompt plus a set of
task-specific prompts used for sub-features (planning, recipes, session
naming, compaction, etc). This is the complete contents of the `prompts/`
directory.

## Files

- `system.md` — the main system prompt (persona, extensions/tools framing,
  operating rules).
- `tiny_model_system.md` — a shorter system prompt variant for small/local
  models.
- `subagent_system.md` — system prompt used when Goose spawns a sub-agent to
  handle a delegated task.
- `plan.md` — prompt for "plan mode" (produce a plan before executing).
- `recipe.md` — prompt for generating/following a Goose "recipe" (a
  reusable, shareable YAML task definition — the feature block.com credits
  with scaling Goose internally).
- `compaction.md` — prompt used to summarize/compact long conversation
  history.
- `session_name.md` — prompt for auto-generating a short session title.
- `apps_create.md` / `apps_iterate.md` — prompts for Goose's app-building
  mode (scaffolding vs. iterating on an existing app).

Not included: `permission_judge.md`, which was empty (0 bytes) at the
retrieved commit.
