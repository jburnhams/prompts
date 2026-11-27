# Run recovery: what an agent is told when its runner died

*Added 2026-10-26 in the weekly pass; §3–§4 added 2026-11-02; §5 added
2026-11-09; §6 added 2026-11-11 from the agentic-SDK deep dive; §7
added 2026-11-16. Sources and SHAs are in [`sources.md`](./sources.md),
"The weekly pass (read 2026-10-26)", "(read 2026-11-02)", "(read
2026-11-09)", "Agentic SDKs (read 2026-11-11)" and "The weekly pass
(read 2026-11-16)".*

A hosted agent runs in a container that can disappear mid-turn: the node
is drained, the sandbox runs out of memory, a network partition drops the
harness's connection. The rest of this collection covers what happens
when a run *ends* (`agent-turn-output.md`, the completion docs) and how
long-lived state survives (`agent-context-compaction.md`,
`agent-memory-learning.md`). It does not cover the case in between: a run
that stopped without ending, and the next attempt that has to pick it up.

That case got first-party prompt text this fortnight. Four sources
changed how they handle it, and they split cleanly on one question:
**does the next attempt get the transcript, and is it told what was in
flight when the runner died?**

## 1. The four positions

| Source | What the next attempt gets | Told about the in-flight call? | Told the workspace may be gone? |
|---|---|---|---|
| **Claude Code** 2.1.309 (session restart, session moved to a new runner) | The transcript, plus a reminder | **Yes**, by name, and that it may have caused the failure | **Yes** |
| **Goose** #13015 (resume a failed or cancelled delegate) | The delegate's saved transcript, plus "Continue the task from where you left off." or the caller's instruction | No | No |
| **OpenHands** #5832 (resume a goal loop after a failed audit) | The loop's stored state; the failed round re-runs | Not applicable (the failure is a judge call, not a tool) | No |
| **Keel** as specified (`agent-design/keel/pipelines.md` §7f) | A **fresh** attempt; `prior_attempt` carries the previous attempt's report | No. An `infra_failure` attempt has no report, so the retry starts blind | No |

### Claude Code: two reminders and a requeue tool

[`system-reminder-tool-calls-lost-to-session-restart.md`](./leaked/claude-code/piebald-2.1.310/system-reminder-tool-calls-lost-to-session-restart.md)
lists, by label, every call the previous turn issued that has no result,
and says they "may not have run, or not completely. Check before issuing
them again, and decide whether they are still needed." Two variants: the
calls were lost to a restart, or they are no longer shown in the
transcript at all.

[`system-reminder-session-moved-to-new-runner-resume-prompt.md`](./leaked/claude-code/piebald-2.1.310/system-reminder-session-moved-to-new-runner-resume-prompt.md)
goes further, and is the line worth taking:

> The call may have had nothing to do with that, or it may have caused
> it, for example by using too much memory. Before you run it again,
> check what it did and whether it could have brought the runner down;
> if it could, do the work another way.

It also says "files you created earlier may no longer exist, so verify
the working directory state before relying on prior edits", and marks
the interrupted call's result with a fixed prefix (`[Tool call
interrupted`) so the model can find it.

Operator-side, the self-hosted runner "doctor" has had a requeue tool
since 2.1.224 that appends the failing runner to the session's
`excluded_runner_ids` "so the queue pop doesn't immediately hand it
back". Together: the platform avoids the same runner, and the model is
told to avoid the same action.

### Goose: resume a delegate by id

`summon.rs` gains a `resume` parameter taking the sub-agent id of a
**failed or cancelled** delegate. Only `instructions` may accompany it;
every other field (`source`, `model`, `extensions`, `max_turns`, …) is
rejected, so a resume cannot change what the delegate is. Completed
delegates and delegates from another session are refused. The tool text
tells the model: "If the user says to continue after a stop, resume the
ones from the latest stop unless they name others." There is no warning
about what was in flight.

### OpenHands: the failed round is not counted

The goal controller counts a round only once its audit completes; an
interrupted audit leaves the count where it was, and the resume re-runs
that round. A resume always keeps one round in hand, so a stored count
already at the cap cannot push the loop past `max_iterations`. This is
budget accounting, not prompt text, but it answers a question Keel's
retry has to answer too: whether a died attempt spends budget.

### Codex: the surrounding plumbing

No prompt change, but three commits this fortnight on the same seam:
`thread/sample` now accepts a thread whose last turn failed or was
interrupted (#56020); dropping a local MCP tool-call future now sends the
server a cancellation, with write ordering kept so the cancel cannot
arrive before the request (#56132); and background compaction no longer
panics when it fails before a checkpoint (#55581).

## 2. What follows

- **A death during a tool call is evidence about that call.** Out of
  memory, a fork bomb, a build that fills the disk: the commonest
  self-inflicted runner deaths all happen inside a tool call, and a blind
  retry repeats them. Only Claude Code says so to the model.
- **A blind retry of a deterministic crash spends the attempt budget
  for nothing.** None of the sources counts consecutive deaths on the
  same call; Claude Code's runner exclusion handles a bad *runner*, not a
  bad *action*.
- **The workspace claim must be explicit.** Whether earlier edits
  survived depends on the platform (a retained checkout, a fresh clone,
  a new container). Claude Code tells the model to check rather than
  assume; the others leave it implicit.
- **Re-running a call with external effects is the dangerous case.** All
  four rely on the model checking first. Where the call was a write to an
  external system, that check is what `agent-design/adk.md` §4's
  idempotency keys exist for, and a reminder does not replace them.

Forge's amendment is in
[`agent-design/keel/pipelines.md`](./agent-design/keel/pipelines.md) §7f,
"Interrupted attempts".

## 3. Stopped, not dead: a resource limit inside a live run

*Added 2026-11-02 in the weekly pass, from
[`leaked/claude-code/piebald-2.1.316/`](./leaked/claude-code/piebald-2.1.316).*

§1 covers a runner that died. Claude Code 2.1.314 adds the case just
short of that: the sandbox enforces a limit itself, kills the work, and
the run carries on.
[`system-reminder-cloud-sandbox-sustained-cpu-limit-stop.md`](./leaked/claude-code/piebald-2.1.316/system-reminder-cloud-sandbox-sustained-cpu-limit-stop.md)
fires when a cloud sandbox has used 90% or more of all its CPUs for a
sustained period. At the limit Claude Code stops every shell command of
the session and the processes they started, "also those that used little
CPU". The reminder then tells the model four things, each of which a
generic "command killed" error would leave it to guess:

- **What did not happen.** "The commands themselves did not fail. The
  files are kept."
- **What may restart.** Low-CPU commands such as a dev server can start
  again.
- **What may not.** "Work that fills the CPUs again will be stopped
  again, so do not start it again in the same form."
- **Who decides the new form.** "If the heavy work is still necessary,
  first agree with the user on a form that uses less CPU, for example a
  smaller job or fewer parallel workers."

The limit is enforced, and the prompt's job is only to stop the model
re-running the same job into it. It is the in-run version of §1's
"do the work another way", with the same reasoning: the action is the
evidence. No other source in this collection names a resource stop to
the model; Crush 0.99 caps the output a shell command keeps in memory
(`f88e147`, #4183, commit subject only) but says nothing to the model
about it.

A second 2.1.314 piece covers the other way work goes missing while the
run is alive:
[`system-reminder-background-mcp-call-stopping-session-warning.md`](./leaked/claude-code/piebald-2.1.316/system-reminder-background-mcp-call-stopping-session-warning.md).
In a session that stops after it replies, a background MCP call still
running is "likely cut off … and its result lost, though the server may
still finish the work. So do not say you will report back." Running it
again from a foreground agent "runs it twice; do that only if that is
harmless". That is §2's last point (a re-run call with external effects
is the dangerous case) stated to the model at the moment it matters.

## 4. Loops inside a run: when is a retry "the same" retry?

*Added 2026-11-02, from OpenHands SDK #6278 (`c3985a4`,
`openhands-sdk/openhands/sdk/conversation/stuck_detector.py` and the PR's
`.pr/validation-loops.md` evidence file).*

Every harness here that detects in-run loops counts repeats of "the same
call", and the definition of "same" decides what it catches. OpenHands'
stuck detector compared invalid calls by their arguments, which missed a
model that reworded its `thought` each time (it ran to the 12-iteration
cap with no steer) and stopped a model that was repairing a call field by
field (six failing fields, then five, then four) after three attempts. The
fix changes what is compared:

- **A validation failure is identified by its failing fields**, the
  Pydantic error type and location with list indices zeroed, not by the
  argument values. Two invalid calls with the same set of failing fields
  are the same attempt however the rest of the arguments changed; a call
  that fails on fewer fields is progress and does not extend the streak.
- **Generic validators fall back to argument comparison**, because a
  custom `value_error` or `assertion_error` can report different problems
  at one location. The comparison strips the SDK's own `summary` and
  `security_risk` fields first, so rewording those does not count as a
  different call.
- **Parallel calls in one response are one attempt**: "the model sees
  their errors together", so a steer cannot fire before the model has seen
  any of them.
- **The nudge names the failing fields**: "Your calls to `X` have failed
  validation N times without resolving the failing fields. Latest error:
  … Correct the invalid or missing fields or try a different approach
  before calling this tool again." The detector nudges after three
  responses and stops the run after four, as before.

The PR's own limits section is candid: the detector "remains a
bounded-history heuristic, not a proof of progress", and the evidence is
synthetic model responses against a local HTTP server, not a live-model
evaluation. The counting rule is the transferable part.

## 5. Lost track, not failed: work still running somewhere else (read 2026-11-09)

§1–§3 are about the agent's own runner. The remaining case is work the
agent started that runs somewhere else and reports back later: an MCP
call that returned a task handle (the `io.modelcontextprotocol/tasks`
extension, `agent-tool-result-transport.md` §2b) or a script dispatched
to a REPL. When the harness loses track of that work, the agent does not
know the outcome, and it should not act as though it does.

Claude Code 2.1.319 adds two notices for MCP tasks
([`leaked/claude-code/piebald-2.1.319/`](./leaked/claude-code/piebald-2.1.319)).
When following a task fails but checking continues:

> It did not cancel the task, which may still be running there or may
> have ended. Its outcome is not known, so do not report it as done or
> failed. … Unless the user asks, do not call the tool again (that may
> repeat the work), stop the task, or wait for it.

When checking has stopped, the notice says "No result will arrive
unless this session is resumed later" and repeats "a second call may
repeat the work". The REPL's dispatch description makes the same point
for scripts: "A receipt means the script is queued or running, so
sending it again would run it twice."

Three rules, shared by both:

1. **Unknown is its own outcome.** Losing track is reported as neither
   success nor failure. It is the outcome a harness is most tempted to
   map to `failed`, and the one where `failed` invites a retry that may
   run the work twice.
2. **The handle, not the call, is what gets retried.** Reissuing the
   call starts a second piece of work. Following the handle again, after
   a resume, is the only safe repeat.
3. **Waiting is not the agent's job.** Claude Code says "do not … wait
   for it": the harness keeps checking, and a result that lands later
   arrives as a notification.

No other source in this collection has text for this case. OpenHands'
per-conversation budget and Goose's delegate resume (§1) both assume the
work ran on the agent's own machine. Keel's version is
[`agent-design/keel/tools-and-agents.md`](./agent-design/keel/tools-and-agents.md)
§4e, which records task handles in the `interrupted_attempt` block so a
retry follows them instead of calling again.

Forge's amendments from §3 and §4 are in
[`agent-design/tools.md`](./agent-design/tools.md) (`Bash`, and
"Repeated invalid calls" in the implementation contract) and
[`agent-design/keel/run-spec.md`](./agent-design/keel/run-spec.md)
(`monitors[]` counting).

## 6. Replay: when a framework runs your step again (read 2026-11-11)

§1–§5 are about what the *agent* is told. The agentic SDKs read for
[`agentic-sdks/`](./agentic-sdks) add the layer underneath: the
framework itself re-executes work, by design, in three places a harness
author may not expect.

1. **LangGraph resumes a node from its start.** `interrupt()` pauses
   inside a node; resuming with `Command(resume=…)` "resumes from the
   start of the node, **re-executing** all logic" (`langgraph/types.py`).
   Anything the node did before the interrupt happens again. Resume
   values are matched to `interrupt()` calls by order, so interrupts
   must not fire concurrently. Writes from sibling tasks that finished
   are kept.
2. **An MCP elicitation under `2026-07-28` is a retried call.** A server
   that needs input returns `InputRequiredResult`, and the client sends
   the `tools/call` **again** with the answers (LangChain's
   `langchain/mcp/elicitation.py`, which drives the loop so each round is
   one interrupt). Whatever the server did before it asked is repeated
   unless the server made it idempotent. So an elicitation answered
   inside LangGraph is replayed twice over: once by the protocol, once by
   the node.
3. **A durable engine replays the journal.** Pydantic AI on Temporal,
   DBOS, Prefect, Restate and five others journals model requests and
   the tool calls it wraps; after a crash, completed ones replay from
   the journal and "the one in flight" is retried
   (`pydantic-ai/docs/durable_execution/overview.md`). The in-flight call
   is the one that may have half-happened. A capability's own external
   writes are not journaled unless wrapped: Pydantic's trajectory judge
   warns that its `on_verdict` callback "is not part of the durable
   operation, so a replay calls it again".

The library answer to all three is the same, and Pydantic AI Harness
ships it: **a tool-effect ledger outside the conversation.**
`StepPersistence` records each call's `started`, `completed` and
`failed` against `(run_id, tool_call_id)`, and "after a crash, a tool
with a `started` record and no terminal update should be treated as
`unknown_after_crash`: the side effect may or may not have happened". It
also marks a snapshot `interrupted` when it holds a tool call with no
result, and `continue_run` will not resume from one unless asked. That
is §5's "unknown is its own outcome" with a storage format.

The deep-dive document's rules for side effects (put confirmation
before irreversible work, use stable operation ids, record completed
side effects outside conversation state) are the generic form.

**For Keel.** Keel does not replay: a retry is a fresh attempt
(`agent-design/keel/pipelines.md` §7f), and a dead attempt's writes are
treated as writes that may have happened. Item 2 does reach it, though,
because Keel speaks `2026-07-28`: a deployment elicitation responder
(`agent-design/keel/tools-and-agents.md` §4e) would answer by reissuing
the call. Proposal 4 in
[`agent-design/proposals-agentic-sdks-2026-11.md`](./agent-design/proposals-agentic-sdks-2026-11.md).

## 7. The model's own response failed (read 2026-11-16)

§1–§6 are about tools and runners. This section is about the other half
of every turn: the model's response itself arriving broken. Five
harnesses changed how they handle it in one week, and between them they
cover the four ways a response fails without an API error to say so.

**1. Cut off inside a tool call.** Claude Code 2.1.323 adds a reminder
for a reply that hit the output-token limit mid-call
([`system-reminder-output-token-limit-tool-call-cutoff.md`](./leaked/claude-code/piebald-2.1.325/system-reminder-output-token-limit-tool-call-cutoff.md)):

> The cut fell inside a tool call, so that call did not run and nothing
> of it was kept. Make the call again in a shorter response: split long
> content across several smaller tool calls. For a long file, write the
> first part and then append the rest in later calls.

Three facts are stated: the call did not run, nothing was kept, and the
remedy is a different shape, not the same call again. The SDK side
(2.1.321, [`data-sdk-api-error-params-field.md`](./leaked/claude-code/piebald-2.1.325/data-sdk-api-error-params-field.md))
adds `cut` to tell the two causes apart, which `max_output_tokens` alone
does not: `output_limit` (the request's `max_tokens`) or
`context_window` (`model_context_window_exceeded`). The first is fixed
by a shorter response, the second by a smaller context; telling the
model "split your call" for the second would not help.

**2. A stream that ended early.** Goose #13226 (`0f8a0b9`,
`crates/goose-provider-types/src/formats/anthropic.rs`, read as a diff)
now **holds every tool request until `message_stop` arrives**. A stream
that ends without `message_stop` is a `NetworkError` ("Anthropic stream
ended without message_stop"), and the held requests are never yielded,
so no tool from a truncated response runs. The same change stops
skipping stream events that fail to parse (they are now errors) and maps
an in-stream `error` event to a typed provider error
(`authentication_error`, `rate_limit_error`, `billing_error`,
`request_too_large` as context length, `overloaded_error` as a server
error). Goose #13266 does the same for Bedrock with streaming off.

OpenCode #60674 (`eccfb82`, `packages/core/src/session/runner/to-llm-message.ts`,
read as a diff) takes the other position, because it starts local tools
while the stream is still arriving. A failed stream "is retried from
what had already happened: the local calls that ran and everything
before them". Calls the stream cut off before they ran are dropped;
calls that failed on their input stay, so the model can reissue them;
the last block's provider state (signatures, reasoning) is not
replayed, since the stream may have ended mid-block. That is the price
of early execution: the transcript must record which calls ran, because
their side effects did.

**3. A response whose tool call could not be parsed.** Claude Code's
`retracted_message_uuids`
([`data-sdk-user-message-retracted-message-uuids-field.md`](./leaked/claude-code/piebald-2.1.325/data-sdk-user-message-retracted-message-uuids-field.md),
2.1.323) is on "the synthetic message that asks the model again after a
response whose tool call could not be parsed": the CLI has **dropped
that response from the conversation**, and hosts are told to remove it
too. If the retries run out, the turn ends with
`malformed_tool_use_exhausted`, "terminal for the turn, so a consumer
replaying history must not re-send the prompt by itself"
([`data-sdk-api-error-kind-field.md`](./leaked/claude-code/piebald-2.1.325/data-sdk-api-error-kind-field.md)).

**4. A content-free completion.** OpenHands SDK #6178 (`a233ffd`,
`openhands-sdk/openhands/sdk/llm/llm.py`) raises `LLMNoResponseError`
inside the retry boundary when the only choice has no text, no tool
call and no reasoning. The commit gives the reason: returning it "would
persist an empty agent message whose corrective steer does not break the
stuck detector's agent streak". One exception: an empty answer with
`finish_reason == "length"` is not retried, since a deterministic cut
would only repeat. Claude Code's `empty_completion` (reworded in
2.1.324) ends the turn as an error after "its one retry and a repeat of
that retry", "so that a host shows a failure and not a blank reply".

**Which errors may be sent again.** Three sources this week say an error
class alone does not decide a retry:

- Claude Code's `api_error_type` (2.1.324,
  [`data-sdk-api-error-type-field.md`](./leaked/claude-code/piebald-2.1.325/data-sdk-api-error-type-field.md)):
  "A first-party 503 with `x-should-retry: false` says
  `overloaded_error` though the server said not to retry, so the value
  alone does not say that a retry can help." The field is dropped on
  `dlp_request_denied`, because "if its body said `overloaded_error`, a
  host could send again a request that must not be sent again". The
  kinds list marks `dlp_request_denied`, `safety_monitor_blocked` and
  `malformed_tool_use_exhausted` as never to be re-sent, and
  `tool_history_mismatch` as one where "re-sending the same history
  fails the same way, and rewinding the conversation is the remedy".
- Goose #13325 (`ef8933e`, `retry.rs`): a 400 rejecting the thinking
  setting for the model is a permanent failure, not retried, while a 400
  about an unsupported tool type still is.
- Codex #61587 (`3b8bd2e`, commit message only): `PreModelRequest` and
  `PostModelRequest` hooks get a `request_id` that "stays stable across
  retries" and an `attempt_number` that increments "for each call to open
  a response stream", so retries and fallbacks of one generation can be
  joined.

Crush (`f64fe8e`, `internal/agent/refusal_retry.go`) retries a
`content_filter` finish once per turn ("A misfire usually clears on the
first retry; more mostly waits"), and re-requests the step rather than
continuing it. That is the opposite of Keel's rule for message threads
(a refused turn is never continued, `agent-design/models.md` §6), but
the two do not conflict: Crush starts a fresh request and discards what
the refused attempt streamed.

**The common rule.** A response that did not complete is not a turn.
Nothing from it runs unless the harness already ran it (OpenCode), and
then the record must say exactly which calls ran. A response that
completed but is unusable (unparseable call, no content) is dropped from
the transcript before the model is asked again, so it cannot feed a
loop detector or a later replay. The model is told only what it can act
on: "the call did not run, make it smaller" is useful; "the stream
dropped" is not, because the harness retries that itself.

**Two smaller pieces from the same releases.** Claude Code 2.1.321's
"Finishing work" section
([`system-prompt-work-completion-and-direct-editing.md`](./leaked/claude-code/piebald-2.1.325/system-prompt-work-completion-and-direct-editing.md))
separates ordinary obstacles ("errors, timeouts, locked files, empty
results or failing tools", to be diagnosed and worked through) from
deliberate ones ("a file marked not to be touched, access that was
intentionally withheld, or a safety guardrail", to be left alone and
reported). Forge's persistence rule (`agent-design/system-prompts.md`
§1) already makes the same split for `blocked`. And a new `Yield` tool
([`tool-description-yield.md`](./leaked/claude-code/piebald-2.1.325/tool-description-yield.md))
pauses until an asynchronous tool reports, and "also resumes shortly
before the prompt cache would expire". That is §5's followed handle with
the cache window as a timer.

**For Keel.** Keel specified context overflow (`agent-design/formats.md`
§7 item 3) and runner death (§1), but not a model response that
arrives broken. Amendment: [`agent-design/formats.md`](./agent-design/formats.md)
§7 item 4, with a row in `agent-design/keel/decisions.md` §14a.
