# Augment Code

- **Type**: Coding agent (IDE extension + CLI) · **Vendor**: Augment
- **Status**: closed source (leaked)
- **Mirror source**: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Augment%20Code (2026-07-10)

## Files
- `claude-4-sonnet-agent-prompts.txt` / `claude-4-sonnet-tools.json` —
  prompt + tools for the Claude 4 Sonnet backend.
- `gpt-5-agent-prompts.txt` / `gpt-5-tools.json` — prompt + tools for the
  GPT-5 backend.

## Memory, learnings, and retrospectives

See [`agent-memory-learning.md`](../../agent-memory-learning.md) for the
cross-source comparison this feeds into. Augment's captures show the
*injection* side of a memory system with unusual clarity, because the
memory block is a literal, named section of the assembled prompt.

- **Memories are a first-class prompt section**, sitting alongside its
  siblings in both captures: `# Additional user rules`, `# Memories`,
  `# Preferences`, `# Current Task List`. The Claude-4 capture spells
  out the provenance: "Here are the memories from previous interactions
  between the AI assistant (you) and the user:" followed by a fenced
  block (empty in the capture, i.e. this user had none). Four separately
  named persistence tiers in one prompt — rules, memories, preferences,
  task state — is a cleaner separation than most sources manage.
- **The write tool is deliberately narrow**: "Call this tool when user
  asks you: to remember something / to create memory/memories. **Use
  this tool only with information that can be useful in the long-term.
  Do not use this tool for temporary information.**" The GPT-5 variant
  compresses it to "Store long-term memory that can be useful in future
  interactions" with a single-sentence `memory` argument ("One concise
  sentence to remember"). The one-sentence cap is the tightest
  per-entry size constraint in the collection.
- **Governance, per vendor sources rather than the captures**: Augment
  later shipped "Memory Review" — an approval queue surfaced in the chat
  panel as an "X Pending Memory" button, letting the user review, edit,
  or discard memories as they are created, motivated explicitly by the
  observation that agents "automatically generated memories, but users
  had no visibility into what was being stored." The recommended usage
  pattern is a **batched end-of-session pass** over the queue "when
  context is freshest" — an approval ritual rather than an approval
  interrupt, and the closest thing to a scheduled retrospective in a
  memory product that has no distillation agent.
