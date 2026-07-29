# Kiro

- **Type**: Coding agent (spec-driven IDE) · **Vendor**: AWS
- **Status**: closed source (leaked)
- **Mirror source**: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Kiro (2026-07-10)

## Files
- `Mode_Clasifier_Prompt.txt` — classifies user intent into one of Kiro's
  modes.
- `Spec_Prompt.txt` — "spec mode": turns a request into a formal
  requirements/design/tasks spec before coding.
- `Vibe_Prompt.txt` — "vibe mode": freeform conversational coding, no spec.

## Memory, learnings, and retrospectives

See [`agent-memory-learning.md`](../../agent-memory-learning.md) for the
cross-source comparison this feeds into. Kiro has no machine-written
memory store; its contribution to the topic is **steering files**, the
most explicitly *conditional* human-written instruction mechanism in the
collection.

- **Location and shape** (from `Spec_Prompt.txt`/`Vibe_Prompt.txt`):
  "Steering allows for including additional context and instructions in
  all or some of the user interactions with Kiro... They are located in
  the workspace `.kiro/steering/*.md`" (plus `~/.kiro/steering/` for the
  global tier, with workspace overriding global), and they support file
  references via `#[[file:<relative_file_name>]]` "so that documents
  like an openapi spec or graphql spec can be used to influence
  implementation in a low-friction way."
- **Four inclusion modes rather than always-on** — `always` (default),
  `fileMatch` (glob-conditioned, e.g. `components/**/*.tsx`), `manual`
  (`#steering-file-name`), and `auto` (description-matched) — set in YAML
  frontmatter. Only Claude Code's `paths:`-scoped `.claude/rules/` and
  OpenHands's keyword-triggered microagents match this, and neither
  offers all four.
- **The agent may write them, but only when asked**: "You can add or
  update steering rules when prompted by the users, you will need to
  edit the files in `.kiro/steering` to achieve this goal" — the
  explicit-request-only posture, applied to a shared committed file
  rather than to a private store. Vendor docs add three
  IDE-generated defaults (`product.md`, `tech.md`, `structure.md`) and a
  "Refine" action, plus `AGENTS.md` support noted as loading universally
  because that format has no inclusion-mode field.
- **Specs are not memory**: `.kiro/specs/{feature}/requirements.md`,
  `design.md`, and `tasks.md` are per-feature working artifacts, and
  nothing distils them into durable cross-session knowledge afterwards.
