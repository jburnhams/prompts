# Manus

- **Type**: General autonomous agent (used for coding among other tasks)
- **Vendor**: Manus (Monica) · **Status**: closed source (leaked)
- **Mirror source**: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Manus%20Agent%20Tools%20%26%20Prompt (2026-07-10)

## Files
- `Prompt.txt` — main system prompt.
- `Agent loop.txt` — describes Manus's agent-loop execution model.
- `Modules.txt` — describes its module/planning system.
- `tools.json` — tool/function definitions.

## Memory, learnings, and retrospectives

See [`agent-memory-learning.md`](../../agent-memory-learning.md) for the
cross-source comparison this feeds into. Manus describes memory as a
**system-side module feeding the event stream**, not as anything the
agent writes or queries.

- **`<knowledge_module>`, in full**: "System is equipped with knowledge
  and memory module for best practice references / Task-relevant
  knowledge will be provided as events in the event stream / Each
  knowledge item has its scope and should only be adopted when
  conditions are met." Three lines covering retrieval (push, via the
  event stream), purpose ("best practice references"), and conditional
  applicability ("scope... conditions are met") — with no write tool, no
  storage description, and no retrieval tool anywhere in the captures.
- **Consistent with Manus's overall architecture**, where the planner
  module, datasource module, and knowledge module are all described as
  system-provided event producers rather than agent-callable tools; the
  agent's job is to notice and obey what arrives. The nearest analogue
  elsewhere is Copilot CLI's sidekick `inbox` push, and Windsurf's
  "relevant memories will be automatically retrieved... and presented to
  you."
- **The per-item scope condition** is the interesting fragment: it
  implies knowledge items carry applicability metadata evaluated before
  injection — the same idea as Devin's trigger descriptions and Codex's
  `applies_to:` lines, but with the evaluation done entirely
  system-side.
