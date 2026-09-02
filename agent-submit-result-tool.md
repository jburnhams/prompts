# The submit/complete-result tool: params in, and where they go

A further drill-down alongside [`agent-self-verification.md`](./agent-self-verification.md)
and [`agent-turn-output.md`](./agent-turn-output.md), but asking a narrower
question than either. `agent-self-verification.md` asks *whether anything
checks the work* before a task is declared done; `agent-turn-output.md`
asks what a single LLM turn produces (narration, plans, reasoning). This
doc asks about the mechanism itself that a model calls to say "I am done":
does one exist at all, what parameters does it expose, and — the part
nobody else in this collection tracks in detail — **what actually consumes
those parameters once the call is made**. A `result` string can be shown
verbatim to a human, folded into a benchmark harness's `model_patch`
field, become a PR title, or simply gate whether the agent loop is allowed
to stop; the same-shaped tool name hides at least four incompatible
answers to "then what?"

**Sources covered**: Augment SWE-bench Agent, SWE-agent, mini-swe-agent,
Live-SWE-agent, Composio SWE-Kit (both its LangGraph and CrewAI variants),
Roo Code, Cline, CodeBuddy (leaked), Jules (leaked), Replit (leaked),
GitHub Copilot CLI (leaked) and Copilot Chat, Grok Build (leaked), Google
Antigravity (leaked), Devin (leaked), Factory/Droid (leaked), OpenHands,
Codex CLI, Gemini CLI, OpenCode, Crush, Lovable (leaked), Claude for
Chrome (leaked), Claude Code (leaked), and Microsoft Agent Framework
(via `codeact-hyperlight/`) — 24 sources, several with confirmed
absences rather than findings, which is itself part of the picture.

---

## 1. A structured tool with one free-text field, consumed as an in-process stop flag

**Augment SWE-bench Agent**'s `complete_tool.py` is the cleanest instance
in the collection — read in full:

```python
class CompleteTool(LLMTool):
    name = "complete"
    description = "Call this tool when you are done with the task, and supply your answer or summary."
    input_schema = {
        "type": "object",
        "properties": {
            "answer": {
                "type": "string",
                "description": "The answer to the question, or final summary of actions taken to accomplish the task.",
            },
        },
        "required": ["answer"],
    }

    @property
    def should_stop(self):
        return self.answer != ""
```

`run_impl` asserts the answer is non-empty, stores it on `self.answer`,
and returns the literal string `"Task completed"` as the tool result
shown back to the model — the actual `answer` text never re-enters the
model's own context. `should_stop` is polled by the outer agent loop
after every tool call; it is the *only* code path that ends the loop.
Notably, nothing in this file extracts a diff — the SWE-bench `model_patch`
that presumably gets scored is captured separately (a `git diff` against
the sandboxed workspace, external to this tool), meaning `answer` is pure
narration with no structural consumer beyond "loop may now stop."

## 2. Sentinel-string completion — no tool at all

Four sources in the SWE-bench lineage skip a dedicated tool entirely and
instead detect completion by pattern-matching ordinary shell output.

- **mini-swe-agent** / **Live-SWE-agent** (`config/mini.yaml`,
  `config/livesweagent.yaml`, byte-for-byte identical mechanism): the
  model is told to run `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` as a
  bash command, "not combine[d] with any other command," after which "you
  cannot continue working on this task." No JSON schema, no `result`
  field — the *literal string* is the whole payload. `mini.yaml`'s normal
  interactive loop otherwise ends when the API-level `finish_reason`/
  `has_tool_calls` says the model produced no more tool calls; the sentinel
  is a second, distinct signal specifically for the benchmark harness to
  detect "submission happened."
- **`config/benchmarks/swebench.yaml`** hardens this into a three-step
  protocol with the sentinel and the payload emitted together as one
  observation: `git diff -- path/to/file1 ... > patch.txt` (scoped,
  excluding tests/tooling files "unless directly part of the issue"),
  inspect `patch.txt` for correct `--- a/`/`+++ b/` headers, then
  `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt` as the
  **exact** required command. Two procedural rules not phrased this way
  anywhere else in this collection: creating/verifying the patch and
  submitting it "MUST be separate commands (not combined with `&&`)," and
  editing `patch.txt` after verification requires re-verifying. The
  implication (not shown as harness code in this collection, but strongly
  implied by the protocol) is that the harness scans the same tool-result
  text for the sentinel and then treats everything after it as the patch
  to extract — the completion signal and the payload share one channel.
- **SWE-agent**'s `submit` (part of the `review_on_submit_m` bundle,
  `default.yaml`): takes no model-visible arguments at all — it operates
  on the working tree. The actual `bin/submit` script that turns the
  tree into a `model_patch` isn't stored in this collection (a real
  research gap, not confirmed empty); what *is* captured is
  `SUBMIT_REVIEW_MESSAGES`, a canned checklist re-injected as the tool's
  own observation on a first call (already the subject of
  `agent-self-verification.md` §2 — cite, don't repeat the gate
  mechanics here). The parameter surface for this family is thus "none":
  the payload is derived from repo state at call time, not from anything
  the model passes in.
- **Composio SWE-Kit** forks the same lineage twice, into two different
  non-tool mechanisms: its LangGraph variant routes on one of exactly
  three allowed *entire response strings* (`"ANALYZE CODE"` /
  `"EDIT FILE"` / `"PATCH COMPLETED"` — a supervisor-graph routing
  keyword, not a tool call), while its CrewAI variant just says "you can
  submit your changes to the codebase by simply running the submit
  command" inside the sandboxed shell, with no JSON schema captured for
  either.

**The common shape across §2**: none of these four sources give the model
a structured field to narrate *what* it did — the payload is either a
fixed sentinel string or the repo's own working-tree diff, extracted by
the harness rather than composed by the model. This is the opposite
design choice from every source in the rest of this doc, where the model
writes its own summary/title/description as a tool argument.

## 3. `attempt_completion` — one tool name, at least three incompatible schemas

- **Cline**'s schema, captured verbatim (`cline/system.ts`):
  > **result**: *(required)* "The result of the task. Formulate this
  > result in a way that is final and does not require further input from
  > the user. Don't end your result with questions or offers for further
  > assistance."
  > **command**: *(optional)* "A CLI command to execute to show a live
  > demo of the result to the user... DO NOT use commands like `echo` or
  > `cat` that merely print text."

  Downstream: `result` is displayed verbatim as the final chat message;
  `command`, if given, is actually executed by the harness and its
  output/demo shown alongside. The tool's own description states the
  consumption model directly — "The user may respond with feedback if
  they are not satisfied with the result, which you can use to make
  improvements and try again" — i.e. rejection re-enters the *same*
  conversation as an ordinary next turn, not a structured retry channel.
  Gating is prompt-only (a `<thinking>` self-check the model is told to
  perform), not a code-level block — already the negative-comparison
  callout in `agent-self-verification.md` §2.

- **Roo Code** references the same tool name throughout its prompt
  sections and README but — unlike Cline — its actual parameter schema
  isn't shipped as prompt text in this collection; only prose ("use the
  attempt_completion tool to present the result") survives locally, with
  the real schema and blocking logic (`AttemptCompletionTool.ts`) read
  live from GitHub for the README rather than captured here. What *is*
  new for this doc, not covered in the self-verification write-up: for
  sub-agent delegation, a child's `attempt_completion` summary is injected
  back into the **parent's own conversation history** as the deferred
  tool result for the original `new_task` call (`agent-subagent-
  architectures.md` lines 113/297) — the parent literally cannot resume
  until this fires. That is a structurally different consumer than a
  top-level agent's `attempt_completion`, which is just displayed to a
  human.

- **CodeBuddy** (leaked) forks the tool name but drops the `result` field
  entirely:
  > "Parameters: - options: (optional) A JSON list containing the
  > integration name... i. supabase: Recommended for a Node.js project or
  > user ask supabase." Usage requires wrapping the *entire* free-text
  > response in `<attempt_completion>...</attempt_completion>` tags —
  > there is no named "final result" argument at all; the tag pair *is*
  > the result, and the one actual parameter (`options`) is repurposed as
  > a product-integration upsell channel (flagging `"supabase"`
  > presumably surfaces an integration prompt downstream), not a
  > completion payload. No other source in this survey uses its
  > completion tool for anything but signaling completion — this is the
  > one exception.

## 4. Split per-step vs. whole-task signals, with an explicit PR-shaped payload

**Jules** (leaked) has the richest git→PR handoff traced in this survey,
and it's split across two tools with genuinely different scopes:

- `plan_step_complete(message: str)` — marks one plan step done. Gated by
  its own description: "Before calling this tool, you must have already
  verified that your changes were applied correctly." Downstream: purely
  a plan-tracker state transition, not a task-completion signal.
- `submit(branch_name, commit_message, title, description)` — the
  whole-task signal, full schema:
  > "Commits the current code with a title and description (which should
  > both be git-agnostic) and requests user approval to push to their
  > branch. Call this only when you are confident the code changes are
  > complete by running all relevant tests and ensuring they pass OR when
  > the user asks you to commit, push, submit, or otherwise finalize the
  > code."

  Four required fields, each with a different downstream destination:
  `branch_name` targets the push, `commit_message` becomes the actual git
  commit message, and `title`/`description` are explicitly required to be
  **"git-agnostic"** — they map to a separate PR/task object on Jules's
  side, not to the commit. `submit` doesn't push directly; it "requests
  user approval to push," a human-in-the-loop gate between the call and
  the branch actually updating. A mandatory, deliberately hidden
  pre-step (`pre_commit_instructions` — described to the user-facing plan
  only as "testing, verification, review, and reflection") must run
  first. After submission, `read_pr_comments`/`reply_to_pr_comments` close
  the loop with a human reviewer on the resulting PR, so the same `submit`
  call is the pivot between the agent's internal work and an external,
  human-reviewed GitHub artifact — no other source in this collection
  separates "what the PR says" from "what the commit says" as cleanly, or
  requires human approval on the push *after* the model has already
  declared the work complete.

A related, easy-to-miss field in the same tool list: `message_user`
carries a `continue_working: bool` parameter — "Set to `True` if you
intend to perform more actions immediately after this message. Set to
`False` if you are finished with your turn." This is a second,
independent completion-adjacent signal in the same source, answering "is
the *turn* over" rather than "is the *task* over" (the `submit` tool's
job) — the two questions are cleanly separated into two different tools'
parameters rather than conflated into one.

## 5. Human-confirmation-gated completion

**Replit** (leaked) makes completion something the model cannot assert on
its own authority: `report_progress(summary: string)` — "Call this
function once the user explicitly confirms that a major feature or task
is complete. Do not call it without the user's confirmation... This tool
will ask user for the next thing to do. Don't do anything after this
tool." The `summary` field's schema description imposes narration rules
directly in the schema rather than in surrounding prose (max 5 items,
≤30 words each, "✓"/"→" markers, no jargon — "users are non-technical").
Downstream: calling the tool both reports and hands control back to the
user in the same motion — an explicit stop instruction is embedded in the
tool's own description. This sits alongside the "feedback tools" family
already covered in `agent-self-verification.md` §9 (automated
evidence-gathering paired with a mandatory human-confirmation gate);
`report_progress` is the one in that family whose parameter shape (a
tightly-schemed progress digest) is worth recording here on its own.

## 6. `task_complete` as a confirmed cross-vendor "unattended mode" convention

The single cleanest piece of "shared convention, confirmed from two
independently-captured sources" in this survey: **the same tool name,
gated behind the same concept, in two separately-leaked products from the
same vendor family.**

- **GitHub Copilot CLI**'s Autopilot mode: "Only call `task_complete` when
  you have fulfilled all aspects of the user request," paired with an
  explicit negative checklist — "When NOT to call `task_complete`:
  ...Tests, build, or lint are failing in code you just changed and you
  haven't fixed them... You wrote code but never ran or otherwise
  validated it." Autopilot mode is explicitly the "user may not even be
  present" mode, so `task_complete` is a loop-termination signal for an
  unattended run rather than a chat message read live. A separately
  defined "Coding Agent Identity" (the cloud/PR-based product) has its
  own time-pressure variant instead: `commitNow: "You are almost out of
  time... Call report_progress detailing your current progress."` — a
  distinct tool name for a distinct trigger (running out of time, not
  finishing the work) in the same captured prompt.
- **Copilot Chat**'s `agentPrompt.tsx` confirms this is a base-agent-level
  mechanism, not per-model prompt text: `task_complete` is injected only
  when `promptContext.request?.permissionLevel === 'autopilot'`, with the
  identical requirement — "Before calling task_complete, you MUST provide
  a brief text summary of what was accomplished in your message. The task
  is not complete until both the summary and the task_complete call are
  present." Same tool name, same gating condition, same "summary must
  precede the call" rule, independently confirmed in the CLI and the VS
  Code agent-mode captures of the same underlying Copilot product family.

**Grok Build** (leaked) has a structurally different, fully-schemed
variant, `update_goal`, with no enum and no linkage to a specific todo:

```json
{
  "title": "UpdateGoalInput",
  "type": "object",
  "required": [],
  "properties": {
    "message": {"type": ["string", "null"], "default": null,
      "description": "Optional short message logged as progress."},
    "completed": {"type": ["boolean", "null"], "default": null,
      "description": "Set to true ONLY when the goal is fully achieved."},
    "blocked_reason": {"type": ["string", "null"], "default": null,
      "description": "Set only when truly stuck after 3+ consecutive failed attempts."}
  }
}
```

All three fields optional and nullable — there is no `goal_id` tying this
to a particular todo item (`todo_write` tracks per-item state separately);
`update_goal` speaks only to one singular overarching objective. Notable
for this doc specifically: the bounded-retry threshold ("3+ consecutive
failed attempts") is written into the **schema's own field description**,
not into surrounding prompt prose — policy travels with the parameter
definition rather than beside it, a design choice found nowhere else in
this survey.

## 7. No dedicated tool at all — three different ways to have nothing

**No tool, plain end-of-turn prose, nothing for a harness to parse**:
confirmed for **Claude Code** (leaked — zero hits for any
completion-tool name anywhere in `Prompt.txt`; the harness treats a
content-only message with no tool call as end-of-turn, the same rule
`agent-turn-output.md` documents for narration), **Codex CLI** (its
`update_plan` tracks per-step `pending`/`in_progress`/`completed` status
but is a plan tracker, not a task-done signal — the turn just ends via
ordinary prose once all steps are marked `completed`), **Gemini CLI**
(a task-tracker tool marks individual tracked tasks complete, paired with
an instruction to close out with a prose "final summary," and a
notably self-aware rule — "If the user says 'I think we finished that,'
but the tool says it is 'pending', trust the tool" — trusting the
*tracker's* state over a conversational claim, distinct from every §3/§9
judge/human-gate mechanism in `agent-self-verification.md` since nothing
separate is being consulted), **OpenCode** (confirmed absent by keyword
search of an otherwise thorough tool-surface README), and **Crush**
(a `<task_completion>` block and "Before finishing" checklist are pure
prose, closing with "Only say 'Done' when truly done" — the literal word
in a chat message is the entire mechanism, unenforced by any code-level
gate found in these files; already the subject of `agent-self-
verification.md` §7).

**No completion-signaling tool of any kind, in either direction** —
**Lovable** (leaked) and **Claude for Chrome** (leaked): the only "task
complete"-shaped string found in Lovable's tool list turned out to be
inside an *example code snippet the agent had generated for a user's
to-do app*, unrelated to the agent's own completion mechanism. Both
products simply end a task with a final natural-language message — the
cleanest confirmed absence in the survey, consistent with both being
live, synchronous, human-supervised products where the chat message
itself is a sufficient final output.

**Completion externalized to git/PR state, not any chat-level tool call**:

- **Factory/Droid** (leaked): the "submission" *is* a PR's draft/non-draft
  flag. "Create a non-draft PR ONLY when: Dependencies successfully
  installed... All code quality checks green with evidence; Clean
  worktree except intended changes. If any item is missing, do NOT create
  a non-draft PR." The required PR body is structured prose, not a tool
  schema — "Mark it Droid-assisted. Include summaries/logs showing
  installs and all quality checks passed" — making the PR's own content
  the completion payload.
- **Devin** (leaked, background/web product): has no submission tool at
  all. The mandatory `<think>` checkpoint before "reporting completion"
  (already `agent-self-verification.md` §10) is a verification gate, not
  a result-carrying tool — its parameter is free-text scratchpad. The
  actual handoff to GitHub happens earlier and separately, through
  ordinary `git`/PR tool calls made incrementally *during* the session
  ("When a user follows up and you already created a PR, push changes to
  the same PR unless explicitly told otherwise"). "Reporting completion"
  is then just the final chat message in Devin's dashboard transcript —
  no schema, no tool call. (The separately-captured CLI variant of Devin
  has neither the checkpoint nor any submission tool — ordinary prose.)

**An artifact plus a generic channel-exit call, with no result field at
all** — **Google Antigravity** (leaked), the one genuinely new pattern in
this survey not resembling any of the above: its full tool list has no
`finish`/`submit`/`complete_task` entry, and its `Mode` enum
(`PLANNING`/`EXECUTION`/`VERIFICATION`) has no terminal "COMPLETE" state.
Completion is the *conjunction* of two ordinary-looking actions: writing
`walkthrough.md` during VERIFICATION mode ("Create walkthrough.md after
completing verification to show proof of work, documenting what you
accomplished, what was tested, and validation results" — a plain file
write, distinguished only by an `ArtifactType: "walkthrough"` metadata
tag), and calling `notify_user` to leave task-view mode ("Task view mode
continues until you call notify_user or user cancels/sends a message").
`notify_user`'s own schema carries no task-outcome field whatsoever — it
is reused identically for completion, for blocking questions, and for
requesting artifact review, distinguished only by which optional
parameters are set (`PathsToReview`, `BlockedOnUser`). No other source
surveyed here separates "the record of what was done" (a persisted file)
from "the signal that the interaction is over" (a content-free channel
exit) this cleanly — Jules's screenshot-as-proof (§6 of
`agent-self-verification.md`) is the closest analogue, but is
completion-time-only where Antigravity's Walkthrough is a durable,
cross-session document explicitly *updated* rather than recreated on
follow-up work.

## 8. A confirmed gap: OpenHands's `finish`

**OpenHands** ships a `finish` action reachable with **zero arguments**
in the one example captured (`<function=finish>\n</function>`), and it is
present even in the most restricted built-in agent (`readonly_agent`'s
five-tool set: `grep`/`glob`/`view`/`think`/`finish`) — confirming it is a
first-class action in every configuration, not an optional extra. But its
actual parameter schema — publicly documented elsewhere as an
`AgentFinishAction` with `task_completed` (`true`/`false`/`partial`),
`outputs`, and `thought` fields — is **not present anywhere in this
collection's captured `.j2` prompt files**, because OpenHands defines
tools in Python code rather than embedding JSON Schema as prompt text.
What is documented locally is the *consumer* side for delegation:
`AgentDelegateObservation(outputs: dict)` is what a parent controller
receives once a delegated sub-agent finishes — strongly suggesting
`finish`'s uncaptured params populate that `outputs` dict as the child's
return value, but this specific link isn't directly confirmed from files
in this collection. Flagging as an honest gap rather than papering over
it with the publicly-known shape: everything here about OpenHands's
schema needs a fresh live-source read, not something this collection can
already substantiate.

## Absences and gaps worth stating plainly

- **Microsoft Agent Framework** (`codeact-hyperlight/`): no completion
  tool of any kind, model-invoked or otherwise — this is a ledger/plan-
  execute loop where continuation is decided by the harness reading
  ledger state (`todos_remaining()`, `background_tasks_running()`, or the
  optional judge's `JudgeVerdict`), never by the model calling a "done"
  tool. Already the subject of `agent-self-verification.md` §3.
- **SWE-agent's actual `bin/submit` script** — the mechanism that
  presumably turns a working tree into the `model_patch` SWE-bench
  harnesses score — is not present in this collection's local files, only
  described secondhand in the README. A real research gap: asserting
  exactly how it maps to `model_patch` needs a fresh live-source read of
  `tools/review_on_submit_m/bin/submit`.
- **Claude Code's `TaskCompleted` hook event**: confirmed to exist only
  as one name inside a 26-member `HookEvent` union
  (`leaked/claude-code/architecture-notes.md`); no payload schema for it
  is documented anywhere in this collection, and it isn't mentioned again
  in either of the other two leaked Claude Code captures checked. The
  event clearly exists; what data it carries is simply not something this
  collection has captured.

## Design takeaways

- **The same tool name does not imply the same contract.** `attempt_completion`
  alone has at least three incompatible schemas across Cline, Roo Code,
  and CodeBuddy; `task_complete` means "unattended-mode loop-termination
  signal" in the Copilot family specifically, and doesn't appear at all
  in the rest of the survey. Naming conventions in this space are not
  evidence of shared lineage or shared behavior — each has to be read
  from its own source.
- **What "downstream" means splits into at least five genuinely different
  destinations**, and most sources pick exactly one: (1) an in-process
  boolean that stops the agent loop and nothing else (Augment's
  `complete`); (2) the literal text shown to a human as the final chat
  message (Cline, Crush, Codex CLI, Gemini CLI, and every "just ends with
  prose" source); (3) a benchmark harness's scored field, extracted from
  repo state rather than composed by the model (SWE-agent, mini-swe-agent,
  Composio); (4) a structured object that becomes a separate, external,
  human-reviewed artifact — a PR title/body/branch distinct from the
  commit message (Jules, and externalized further still in Factory's
  PR-draft-state and Devin's incremental git pushes); (5) a gate that
  hands the actual accept/reject decision to a human before the loop is
  even allowed to end (Replit's `report_progress`). A tool's parameter
  names alone don't tell you which of these five it feeds — the same
  `result: string` shape could plausibly be any of the first four.
- **The richer the payload's structure, the more separated its fields
  end up being routed.** Contrast the single free-text `answer` in
  Augment's tool (one destination: gone once the loop stops) with Jules's
  four-field `submit` (`branch_name`→push target, `commit_message`→git
  history, `title`/`description`→a separate git-agnostic PR object) or
  Replit's schema-enforced `summary` (a rendering spec baked into the
  parameter description itself, not left to prompt prose). Structure in
  the schema tends to track genuinely different consumers on the other
  end, not just stylistic preference.
- **Google Antigravity's design is the one genuine departure from "a tool
  call with a result field" as the category itself** — completion there
  is a persisted artifact plus a content-free channel-exit call, which
  doesn't fit "structured tool," "sentinel string," or "plain prose" as
  this doc's other buckets define them. Worth treating as a fourth
  category rather than squeezing it into one of the other three.
- **A gate on the tool (does it require passing a checklist first) and a
  contract for the tool (what shape is the payload, who reads it after)
  are independent design axes** — `agent-self-verification.md` already
  maps the former in detail; this doc's finding is that the latter varies
  at least as much, and the two axes don't correlate. SWE-agent gates
  hard (a checklist re-injection scheme) but its `submit` payload is the
  thinnest possible (none — it's derived from repo state); Jules's
  `submit` has the richest payload in the survey and is gated by a
  hidden mandatory pre-step *and* a human approval after the call;
  Cline's `attempt_completion` has a real payload (`result`/`command`)
  but only a prompted, non-code-level gate in front of it.
