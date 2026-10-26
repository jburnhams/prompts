# Run recovery: what an agent is told when its runner died

*Added 2026-10-26 in the weekly pass. Sources and SHAs are in
[`sources.md`](./sources.md), "The weekly pass (read 2026-10-26)".*

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
