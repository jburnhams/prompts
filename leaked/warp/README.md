# Warp

- **Type**: Coding agent (agentic terminal) · **Vendor**: Warp
- **Status**: closed source (leaked)
- **Mirror source**: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Warp.dev (2026-07-10)

## Files
- `Prompt.txt` — system prompt.

## Self-verification and testing

See [`agent-self-verification.md`](../../agent-self-verification.md) for
the cross-source comparison this feeds into. Absent as an autonomous
mechanism, and structurally distinctive in *why*: the whole "# Task
completion" section is built around **not** auto-verifying.

- "Do exactly what was requested by the user, no more and no less! ...
  if a user asks you to fix a bug, once the bug has been fixed, don't
  automatically commit and push the changes without confirmation.
  Similarly, don't automatically assume the user wants to run the build
  right after finishing an initial coding task."
- The one carve-out inverts every other §7 example in this collection:
  verification is offered, not performed — "it is also acceptable to
  ask the user if they'd like to lint or format the code after the
  changes have been made," and confirming a fix "typically ensur[es]
  valid compilation... or by writing and running tests," but only after
  *asking if the user wants* that check. Every other prompted-only
  source in this doc instructs the agent to verify on its own
  initiative; Warp explicitly requires permission first.
- This sits in tension with the prompt's own general default: "bias
  toward action to address the user's query. If the user asks you to do
  something, just do it, and don't ask for confirmation first" —
  verification is carved out as the specific exception to that bias.
- No SWE-bench-lineage echo, no bounded-retry cap, no deterministic
  gate, no judge call, no `/review` command, no hook system — the tool
  set here (`run_command`, `read_files`, `grep`, `file_glob`,
  `edit_files`, `create_file`) has no completion-gating logic anywhere.

## Compaction and turn output

See [`agent-context-compaction.md`](../../agent-context-compaction.md)
and [`agent-turn-output.md`](../../agent-turn-output.md) for the
cross-source comparisons these feed into. Nothing found for either
topic in `Prompt.txt`'s 162 lines — a targeted keyword search (summar-,
compact, context window, token, truncat, title, session name, rename,
thinking, reasoning, scratchpad) turned up only unrelated hits about
**file-reading** truncation ("This can only respond with 5,000 lines of
the file. If the response indicates that the file was truncated, you
can make a new request to read a different line range"). Given Warp's
terminal app visibly supports long-running, named agent sessions, this
reads as a capture gap — this single, short, general-purpose system
prompt almost certainly doesn't carry whatever context-management and
session-naming logic lives in the surrounding app, not evidence either
mechanism is genuinely absent from the product.

## Permissions and approval

See [`agent-permissions-approval.md`](../../agent-permissions-approval.md)
for the cross-source comparison this feeds into. No named modes, no
risk-classification flag, no allow/deny list, no config file — command
safety is left entirely to the model's own prompted judgment, and the
prompt actively discourages seeking confirmation on ordinary work.

- **The whole mechanism is one vague, unenforced instruction**: "Bias
  strongly against unsafe commands, unless the user has explicitly
  asked you to execute a process that necessitates running an unsafe
  command... NEVER suggest malicious or harmful commands, full stop."
  No boolean flag, no LOW/MEDIUM/HIGH tag, nothing in a tool schema —
  "unsafe" is a natural-language judgment call remade every time, not a
  structured classification step.
- **The prompt's general instinct actively cuts against asking for
  approval at all**: "bias toward action to address the user's query.
  If the user asks you to do something, just do it, and don't ask for
  confirmation first." The one carve-out is scope creep, not command
  risk — "don't automatically commit and push the changes without
  confirmation" is about not doing unrequested follow-up work, not
  about vetting a command before running it.
- No sandbox/isolation is mentioned as a complementary safety layer,
  no persistence/session-memory for prior approvals, no escalation
  behavior for a modified command — there's no approval step to
  escalate from. The weakest, most unstructured approval posture found
  across the sources checked for this doc.

## Git and version control

See [`agent-git-vcs.md`](../../agent-git-vcs.md) for the cross-source
comparison this feeds into. The only source in this collection with a
**dedicated, named, VCS-agnostic-by-design "# Version control"
section** — git is the assumed default but explicitly not the only
option.

- **VCS-agnostic framing, distinctive among every source checked**:
  "You can usually assume that the user's is using `git`, unless
  stated in memories or rules above. If you do notice that the user is
  using a different system, like Mercurial or SVN, then work with
  those systems." No other source in this survey hedges its git
  guidance this way.
- **Confirm-before-commit is a named exception to Warp's general
  bias-toward-action stance** (already covered under Self-verification
  above, repeated here as it's equally a git-specific rule): "don't
  automatically commit and push the changes without confirmation" —
  the model may act on the requested task without asking, but
  committing/pushing that work is carved out as needing confirmation
  regardless.
- **A pager-avoidance instruction stated three times across the
  file**, underscoring it as an operationally important, tool-agnostic
  constraint: "When using VCS CLIs, you cannot run commands that
  result in a pager... With `git`, for example, use the `--no-pager`
  flag when possible (not every git subcommand supports it)." Also
  applies to `gh`: "you can also use CLIs for the repository host, if
  available (like `gh` for GitHub)... The same guidance regarding
  avoiding pagers applies to these CLIs as well."
- **No commit-message conventions, no checkpoint/undo system, no
  worktree isolation, no branch-management rules found.** No PR-
  creation tool or description template — Warp only reads PR/issue
  info via `gh`, per "you can use the `gh` CLI to fetch information
  about pull requests and issues"; PR creation itself would be an
  ordinary `gh pr create` shell command subject to the same general
  "bias strongly against unsafe commands" judgment and the confirm-
  before-commit/push rule above.
