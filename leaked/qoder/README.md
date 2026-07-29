# Qoder

- **Type**: Coding agent (IDE) · **Vendor**: Qoder (Alibaba-backed)
- **Status**: closed source (leaked)
- **Mirror source**: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Qoder (2026-07-10)

## Files
- `prompt.txt` — main system prompt.
- `Quest Design.txt` — prompt for planning a "Quest" (Qoder's multi-step
  task unit).
- `Quest Action.txt` — prompt for executing a step within a Quest.

## Memory, learnings, and retrospectives

See [`agent-memory-learning.md`](../../agent-memory-learning.md) for the
cross-source comparison this feeds into. Qoder's contribution is a
**taxonomy-first** memory prompt: rather than describing when to write,
it names the categories a memory can belong to, and one of them is
explicitly about lessons learned.

- **"Memory Management Guidelines: Store important knowledge and lessons
  learned for future reference"**, with four named categories —
  `user_prefer` ("Personal info, dialogue preferences, project-related
  preferences"), `project_info` ("Technology stack, project
  configuration, environment setup"), `project_specification`
  ("Development standards, architecture specs, design standards"), and
  **`experience_lessons`** ("Pain points to avoid, best practices, tool
  usage optimization") — and two scopes, `workspace` and `global`.
- **The write triggers are phrased as discoveries, not as requests**:
  "User explicitly asks to remember something / Common pain points
  discovered / Project-specific configurations learned / Workflow
  optimizations discovered / Tool usage patterns that work well." Only
  the first is user-initiated; the rest are the model noticing something
  worth keeping — the retrospective impulse, stated at capture time
  rather than in a post-session pass.
- **Two tools**: `update_memory` ("Store/update/delete knowledge and
  lessons learned") and `search_memory` ("Search and retrieve codebase
  memory and knowledge content using advanced semantic search").
- **Retrieval is pushed as a proactiveness rule**, repeated across all
  three captures: "If the task requires analyzing the codebase to obtain
  project knowledge, you SHOULD use the `search_memory` tool to find
  relevant project knowledge." The Quest prompts add a budget rule ("you
  SHOULD find all the required knowledge in one query, rather than
  searching multiple times") and a closed-world constraint ("You can
  only search for knowledge from the project knowledge list, do not
  retrieve knowledge outside the knowledge list"), with an injected
  `<project_knowledge_list>` tree acting as the index over a separate
  `<project_wiki>` — an index-plus-detail layout arrived at from the
  wiki direction rather than the memory-file direction.
- **When *not* to search** is spelled out too: "The known context
  information is already very clear and sufficient... The task is too
  simple, no need to acquire codebase knowledge" — the same
  skip-retrieval discipline Codex's read path states, and one most
  sources omit.
