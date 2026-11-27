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
- If a concept you need has no entry, ask for one (below) rather than inventing a word
  here.
- Stage 1 (the kernel words and the `area`, `decider` and `moment` facets) is in use from
  2026-11-26. Each area (context, control, ...) gets its own words in a later stage.
- Words inside stored prompts and sources (`leaked/`, `skills/`, each source folder's
  stored files) and Keel's schema identifiers keep their authors' wording.
- Common slips: **agent** is a model configured to act, not a product; Claude Code,
  Codex and Goose are **harnesses**. "Mode" alone is ambiguous: say **permission mode**
  for the approval sense. A separate model that checks or helps is a **second model**
  (judge, monitor, classifier and grader are its aliases).

### Looking up and asking for terms

The glossary grows as research goes: settling one concept usually opens up more, and
older terms sometimes need a sharper edge or a breaking change. So:

1. **Look up before you write a new concept word.** No checkout needed:
   ```bash
   T=https://raw.githubusercontent.com/jburnhams/taxonomies/main/tools/term.py
   curl -fsSL $T | python3 - lookup prompts "words for the concept"
   ```
   It gives the term to use (an alias or old label finds its term), or the closest terms
   with their scope and near miss, and any request already made.
2. **When nothing fits, use your own word now and add a request** to
   [`term-requests.md`](./term-requests.md) (template there): Ask `new`, a one-sentence
   definition, what lookup showed and why it does not fit, an example link and a count.
   If a term is unclear for your case, or its label or edge looks wrong, add a `clarify`
   or `change` request instead of working round it.
3. **At the start of a pass**, run `curl -fsSL $T | python3 - changes prompts --since <date>`
   with the date your last changelog entry checked to. Switch the words it marks
   BREAKING in the docs you touch, remove your requests it shows answered, and say in the
   new changelog entry which date you checked to and which requests you made.

Requests are answered in the taxonomies repo
([`domains/prompts/requests.md`](https://github.com/jburnhams/taxonomies/blob/main/domains/prompts/requests.md));
the rules are in [`design/growth.md`](https://github.com/jburnhams/taxonomies/blob/main/design/growth.md)
(proposed).
