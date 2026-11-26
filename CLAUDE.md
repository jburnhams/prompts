# Working in prompts

Research into how AI agent products work, and the designs in `agent-design/` (Keel,
Forge, Lens). Layout and reading order are in [`README.md`](./README.md).

## Vocabulary: use the glossary

The words for this repo's concepts (agent, harness, run, turn, tool surface, MCP server,
skill, sub-agent, context file, approval, steer, eval, ...) are defined once in the
`prompts` glossary in `jburnhams/taxonomies`:
[`domains/prompts/glossary.md`](https://github.com/jburnhams/taxonomies/blob/main/domains/prompts/glossary.md),
with its sorting questions in
[`facets.md`](https://github.com/jburnhams/taxonomies/blob/main/domains/prompts/facets.md).
Read it before writing a research doc or a design doc here.

- Use each entry's heading word. If you reach for one of its aliases, use the heading
  word instead.
- If a concept you need has no entry, add a `candidate` entry there rather than
  inventing a word here.
- Stage 1 (the kernel words and the `area`, `decider` and `moment` facets) is in use from
  2026-11-26. Each area (context, control, ...) gets its own words in a later stage.
- Words inside stored prompts and sources (`leaked/`, `skills/`, each source folder's
  stored files) and Keel's schema identifiers keep their authors' wording.
- Common slips: **agent** is a model configured to act, not a product; Claude Code,
  Codex and Goose are **harnesses**. "Mode" alone is ambiguous: say **permission mode**
  for the approval sense. A separate model that checks or helps is a **second model**
  (judge, monitor, classifier and grader are its aliases).
