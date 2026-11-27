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
- In use: stage 1 (the kernel words; facets `area`, `decider`, `moment`) and stage 2, the
  context area (facets `operation`, `content`, `reach`), from 2026-11-26; stage 3, the
  control area (facets `target`, `response`), from 2026-11-27. The other areas (tool use,
  coordination, output, verification, operations) get their own words in later stages;
  until then use the kernel words and ask for the rest.
- Existing docs were renamed to the heading words on 2026-11-27 (see `changelog.md`). Words
  that stayed on purpose: verb "nudges", "scaffolding" for templates, "reminder" (finds
  `system-reminder`), and product or paper names in title case.
- Words inside stored prompts and sources (`leaked/`, `skills/`, each source folder's
  stored files) and Keel's schema identifiers keep their authors' wording.
- Common slips: **agent** is a model configured to act, not a product; Claude Code,
  Codex and Goose are **harnesses**. "Mode" alone is ambiguous: say **permission mode**
  for the approval sense. A separate model that checks or helps is a **second model**
  (judge, monitor, classifier and grader are its aliases); one that holds an action until
  it answers (Codex's Guardian, the auto-mode classifier) is a **blocking monitor**.
- Changed 2026-11-27 (stage 3): a **steer** redirects the agent, and a **system reminder**
  is the harness channel, which also carries notices that redirect nothing. An
  **escalation** passes one decision up (to a person, a stricter check or a higher risk
  tier); a **handoff** passes the work. A run's **authority** is what it may do; which
  instruction wins is **precedence**. Clearing old tool results to fit the window is part
  of **compaction**; cutting a result when it arrives is **truncation**.

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
