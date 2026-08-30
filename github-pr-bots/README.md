# GitHub PR bots

A fourth category: the automated bots/GitHub Actions each major vendor
offers that review pull requests directly on GitHub (as opposed to the
`skills/` folder's Claude-Code-specific slash commands, or the top-level
folders' full standalone CLI/IDE agents). The question this folder is
trying to answer for each vendor: **how does it turn a PR into a model
request** — diff format, what context besides the diff gets pulled in,
how existing comments are handled, and how the response gets turned back
into GitHub comments/suggestions.

## Sources

| Folder | Vendor | Status |
|---|---|---|
| [`claude-code-action/`](./claude-code-action) | Anthropic | Genuinely open source (MIT), and what actually runs |
| [`gemini-code-review/`](./gemini-code-review) | Google | Genuinely open source (Apache-2.0), and what actually runs |
| [`codex-review/`](./codex-review) | OpenAI | OpenAI's own **published reference implementation**, explicitly *not* the real hosted service — see that folder's README |
| [`opencode-review/`](./opencode-review) | Anomaly (OpenCode) | Genuinely open source (MIT); defaults to the full general-purpose "build" agent, not a review-specific one — see that folder's README |

## Copilot: nothing found

GitHub's actual hosted "Copilot code review" (the bot that leaves inline
comments as a real PR check) is closed-source, server-side infrastructure
— no diff-formatting or prompt-construction logic is published anywhere.
Two things exist that are *not* that, and weren't added here to avoid
implying otherwise:

- A [`/review-code` prompt file](https://docs.github.com/en/copilot/tutorials/customization-library/prompt-files/review-code)
  from GitHub's own docs — an optional, user-installable prompt for
  Copilot Chat's editor-side review of *selected code*, unrelated to the
  hosted PR-review bot's mechanics (no diff/PR formatting logic at all).
- `microsoft/vscode-copilot-chat`'s `src/extension/prompts/node/github/`
  folder (already excluded from `../copilot-chat/`, which does include the
  rest of that repo's agent-mode prompts) — only contains
  `pullRequestDescriptionPrompt.tsx` (PR *description* generation), not
  review/diff-formatting logic.

Worth re-checking if GitHub ever open-sources the actual review service.

## Which revision do the context files come from?

Added 2026-08-30, from the workflow YAML stored in each folder plus the
loader research in the per-harness READMEs. Every CLI agent in this
collection discovers its context file (`AGENTS.md`, `CLAUDE.md`,
`GEMINI.md`, …) by walking the **filesystem it is pointed at** — never by
asking git for a blob at a revision. So for a bot, the question "which
version of the review rules applied?" is answered entirely by the
checkout step, and the answer is not the same as the answer for the diff.

- **Nothing in this collection pins context files to a revision.** No
  loader takes a ref, reads from an index, or records the SHA the file came
  from. Provenance recorded in the prompt is always a *path*
  (`Contents of /repo/CLAUDE.md`, `--- Context from: /repo/GEMINI.md ---`,
  `Instructions from: /repo/AGENTS.md`), never a path plus a commit. A
  reviewer reading the transcript cannot tell which version of the rules
  the model was given.
- **Codex's reference workflow checks out the merge commit.**
  `actions/checkout@v5` with `ref: refs/pull/${{ ... }}/merge`, while the
  diff is computed separately as `git diff --unified=5 "$BASE_SHA"
  "$HEAD_SHA"`. So `AGENTS.md` comes from **base ∪ head** — a rule added on
  the base branch after the PR was opened applies immediately, and a PR that
  *edits* `AGENTS.md` changes the rules used to review that same PR. The
  diff shows that edit; the loader has already obeyed it.
- **Gemini's reference workflow is a `workflow_call`, so the ref is the
  caller's.** `actions/checkout@v6` is used with no `ref:`, which resolves
  to whatever the triggering event defaults to: `refs/pull/N/merge` under a
  `pull_request` event, but the **repository's default branch** under
  `issue_comment` — and the workflow's own concurrency key
  (`github.event.pull_request.number || github.event.issue.number`) shows
  the comment-triggered path is expected. In that case `GEMINI.md` comes
  from `main` while the PR content comes from the API: the rules and the
  code under review are from different trees.
- **Both vendors' bots disable their own trust gate to get there.** Gemini
  CLI will not load context files from an untrusted folder at all, and in
  a headless run raises `FatalUntrustedWorkspaceError` rather than
  prompting — so the workflow sets `GEMINI_CLI_TRUST_WORKSPACE: 'true'`
  (see [`../gemini-cli/`](../gemini-cli)). Codex has the parallel gate
  (`active_project.is_untrusted()` skips project-doc discovery entirely).
  The trust decision that a human makes once per folder on a laptop is,
  in CI, made statically in YAML for every PR head the workflow will ever
  see, including from forks.
- **Claude's action doesn't load them itself — it tells Claude to.** The
  generated prompt says "IMPORTANT: Always check for and follow the
  repository's CLAUDE.md file(s)" and "Follow the repo's CLAUDE.md file for
  project-specific guidelines"; the actual loading is Claude Code's own
  `getMemoryFiles()` walk over whatever the workflow checked out.
- **A sharp asymmetry in Claude's action, visible in one file.**
  `src/github/utils/sanitizer.ts` runs `sanitizeContent` over PR/issue
  titles, bodies, review bodies and comments (`src/github/data/formatter.ts`
  calls it at every one of those sites): it strips zero-width and control
  characters, **bidi overrides** (`‪-‮`, `⁦-⁩`), soft
  hyphens, Markdown image alt-text and link titles, hidden HTML attributes
  (`alt`, `title`, `aria-label`, `data-*`, `placeholder`), decodes numeric
  entities to printable ASCII only, and redacts GitHub token patterns. None
  of that touches `CLAUDE.md`. The text a drive-by commenter can write is
  scrubbed; the text a contributor can commit — which the same PR can
  modify, and which the prompt then tells the model to *follow* — is not.
- **Codex's hosted service is documented as scoping rules by proximity**:
  per OpenAI's docs it applies the closest `AGENTS.md` "Review guidelines"
  section to each changed file. The published cookbook workflow gets a
  weaker version of this for free, because Codex CLI's ordinary root→cwd
  discovery runs anyway.
- **Cross-repository sources exist and are not revision-pinned either.**
  OpenCode's `config.instructions` accepts `https://` URLs, fetched per
  session with a 5s timeout and no caching or integrity check; OpenHands'
  `load_public_skills` pulls from `github.com/OpenHands/extensions`; Cline
  has a `remote` rules tier pushed by an organization; Claude Code has
  managed-policy `CLAUDE.md` (un-excludable) and a team-memory tier synced
  across an org. In each case the bytes that steer the review can change
  without any commit appearing in the repository being reviewed.
