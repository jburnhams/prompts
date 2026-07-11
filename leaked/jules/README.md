# Jules

- **Type**: Coding agent (Google's asynchronous/cloud coding agent —
  [jules.google](https://jules.google/), runs tasks in a background VM
  against a GitHub repo rather than an interactive terminal/IDE session)
- **Vendor**: Google · **Status**: closed source (leaked)
- **Mirror source**: https://github.com/DiaAviLinden/Jules-system-prompt,
  branch `add-details-md` (2026-07-11) — a small, independent repo (9
  stars at retrieval time), not part of the larger `x1xhlol` aggregator
  most other `leaked/` folders in this collection come from. The repo's
  own title calls this the "*alleged*" system prompt — no confirmation
  from Google, no stated extraction methodology, sparse provenance.
  Treat this folder with the same "data point, not a spec" caveat as
  every other `leaked/` source, with an extra discount for the thinner
  provenance trail.

## Files

Two genuinely different versions of the prompt exist in the source
repo, both kept here because they show real evolution, not just minor
rewording:

- `DETAILS-VERBATIM-1.md` — the earlier/simpler version (identical to
  the source repo's `DETAILS-0.md`, which is not duplicated here). A
  14-tool set, prose tool descriptions, `[TOOL_CODE_START]`/
  `[TOOL_CODE_END]`-delimited calls (the repo's own note says these
  markers were substituted from Jules's real delimiters "to avoid
  parsing issues," so the actual delimiter tokens are unknown).
- `DETAILS2.md` — a later, substantially richer version: the tool list
  is shown as an actual JSON function-calling schema (not prose), and
  five new tools appear that don't exist in the earlier version —
  `pre_commit_instructions`, `request_code_review`, `read_pr_comments`/
  `reply_to_pr_comments`, `frontend_verification_instructions`/
  `frontend_verification_complete`, and `initiate_memory_recording`.
  See "Self-review & verification" below — this version is the reason
  this source is worth including at all.

No dated commit history was retrievable for either file, so the exact
order/timing of this evolution is inferred from content alone (the JSON
schema and additional tools in `DETAILS2.md` read as later/more mature
than `DETAILS-VERBATIM-1.md`'s simpler prose-tool version), not confirmed
externally.

## Tool surface

- **Shell**: `run_in_bash_session` — a special (non-Python-syntax) DSL
  tool, persistent across calls within one session. `DETAILS2.md` adds
  a constraint the earlier version doesn't state: "all invocations of
  this tool run from the repository root directory" regardless of any
  `cd` in a prior call — every command must be formulated with that in
  mind, a real behavioral gotcha not present in the earlier version's
  description.
- **Editing — a three-tool family, git-merge-diff-marker convention**:
  `create_file_with_block` (new files), `overwrite_file_with_block`
  (full-file replace), `replace_with_git_merge_diff` (targeted partial
  edit using literal `<<<<<<< SEARCH` / `=======` / `>>>>>>> REPLACE`
  markers that "must be exact and on their own lines" — the same
  marker vocabulary as a real git merge conflict, not a bespoke
  invented format).
- **Search**: `grep` only — no semantic/AST search, no dedicated glob
  tool (`ls` covers directory listing).
- **Rollback — a distinctive pair not seen phrased this way elsewhere
  in this collection**: `reset_all()` ("Resets the entire codebase to
  its original state... undo all your changes and start over") and
  `restore_file()` (same, scoped to one file) — explicit, named,
  whole-codebase and single-file undo tools, rather than relying on the
  model shelling out to `git checkout`.
- **Browser/web**: `view_text_website` (fetch a URL as plain text) +
  `google_search` (search, returns titled snippets, told to feed
  results back into `view_text_website` for full content) — a
  fetch+search pair, no browser automation/screenshot capability.
- **Multimodal**: `view_image(url)` in both versions (URL-only).
  `DETAILS2.md` adds `read_image_file(filepath)` for **local** image
  files ("if you need to see image files on the machine, like
  screenshots") — a real capability expansion tied directly to the new
  `frontend_verification_complete` tool's screenshot output (below).
- **Planning — a three-tool sequence with an explicit approval-recording
  step**: `set_plan` (numbered Markdown steps) → `record_user_approval_for_plan()`
  (explicitly logs that the user approved, separate from the plan
  content itself) → `plan_step_complete()` per step. Closer to Codex
  CLI's Plan tool in spirit, but Jules is the only source in this
  collection with a dedicated tool for **recording approval** as its
  own event rather than folding it into the plan or a generic
  human-in-the-loop gate.
- **Sandbox/isolation**: "You are fully responsible for the sandbox
  environment. This includes installing dependencies, compiling code,
  and running tests" — a real cloud VM per task, matching the public
  "async coding agent" framing (tasks run unattended in the background,
  not in a live terminal the user is watching).
- **Sub-agents**: none found in either version — no delegate/spawn tool,
  no named sub-agent registry. Consistent with a single-VM,
  single-agent-per-task design.
- **Compaction/context management**: not addressed in either captured
  version — no summarization tool, no stated token-budget handling. An
  absence worth flagging rather than assuming (see
  [`agent-context-compaction.md`](../../agent-context-compaction.md)),
  though it's plausible this simply wasn't captured by whatever leak
  process produced this repo rather than being genuinely absent from
  the product.

## Self-review & verification

The most distinctive part of this source, and the reason it's worth
adding to this collection even on thin provenance: Jules pushes
verification much further than a single "review before submit" step —
both versions.

- **"Always Verify Your Work" is a per-action rule, not a pre-submit
  one**: "After every action that modifies the state of the codebase
  (e.g., creating, deleting, or editing a file), you **must** use a
  read-only tool (like `read_file`, `ls`, or `grep`) to confirm that
  the action was executed successfully and had the intended effect."
  `plan_step_complete()`'s own tool description reinforces this as a
  hard precondition: "Before calling this tool, you must have already
  verified that your changes were applied correctly." Most other
  sources in this collection's self-review material (SWE-agent's
  `review_on_submit_m`, the general "reproduce → fix → verify → submit"
  workflow template) gate verification at the *end* of a task; Jules
  gates it after *every individual write*.
- **A dedicated pre-commit tool, deliberately hidden from the
  user-facing plan text** (`DETAILS2.md` only): `pre_commit_instructions()`
  — "Get instructions on a list of pre commit steps you need to do
  before submit. Always call this function when you are in pre commit
  step or before submit." The prompt gives an unusual, specific
  instruction about how to *talk about* this tool: the written plan
  must include a pre-commit step, but "in your written plan, do not
  mention the `pre_commit_instructions` tool or 'following
  instructions', instead, you must describe the steps purpose, which
  is to 'ensure proper testing, verification, review, and reflection
  are done.'" A deliberate internal-mechanism/user-facing-explanation
  split not seen phrased this explicitly anywhere else in this
  collection.
- **An explicit code-review request tool**: `request_code_review()` —
  no parameters, no description of what happens after calling it in
  what's captured here, but its existence as a distinct callable tool
  (separate from `pre_commit_instructions`) implies a genuinely
  separate review pass in the product, even though the leaked prompt
  doesn't reveal whether that's another model call, a static analysis
  pass, or something else.
- **Visual verification with generated evidence, for frontend work
  specifically**: `frontend_verification_instructions()` ("Returns
  instructions on how to write a Playwright script to verify frontend
  web applications and generate screenshots of your changes") paired
  with `frontend_verification_complete(screenshot_path)` — the model
  is walked through writing its own verification script, running it,
  and then explicitly submitting a screenshot path as proof of
  completion. No other source in this collection ties self-review to a
  concrete generated artifact (a screenshot) rather than a text
  assertion that verification happened.
- **Post-submission reviewer-feedback loop**: `read_pr_comments()` /
  `reply_to_pr_comments()` — Jules can receive real human PR review
  comments as a first-class input and reply to them individually (JSON
  array of `{comment_id, reply}` objects), closing the loop between
  its own self-review and an actual human reviewer's feedback after
  the code is already up for review.
- **Cross-task memory, mentioned but undetailed**:
  `initiate_memory_recording()` — "start recording information that
  will be useful for future tasks." No retrieval-side tool or mechanism
  is described in what's captured, so this is flagged as a real but
  incompletely-documented capability, not analyzed further here.
