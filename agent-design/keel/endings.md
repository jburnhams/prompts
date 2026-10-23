# Keel: how a run ends

Generated ending tools, and tools marked as endings. Part of [Keel](./README.md). Section numbers are shared across Keel's files, so a reference like §7f means the same section everywhere; [the README](./README.md#files) lists which file holds each.

---

## 5. Completion tools: separate tools, or a flag on a tool?

**Neither. The spec declares a contract, and the harness generates the
tool.** Authors don't write `Complete`, and they can't mark an arbitrary
tool as run-ending.

| Contract in the spec | Generated tool | Ends the run? | What the harness does on the call |
|---|---|---|---|
| `completion` | `harness/Complete` (or `tool_name`), unless `complete: false` | yes: `complete` | validates `report` against `report_schema`, runs the completion `checks`, files spinoffs, evaluates sinks and continuations |
| a tool marked `use: finish` | one ending tool per such tool (§5a) | yes: `complete`, with `outcome.finished_with` set | completion checks, then the tool's call; on failure, back to the model |
| `human.ask_user` | `harness/AskUser` | yes: `suspend` | opens a gate, posts to `channels`, records who may answer |
| `hatches.handoff` | `harness/HandOff`, its `reason` enum = the declared reason ids | yes: `handoff` | starts the continuation wired to that reason |
| `hatches.expand` | `harness/Expand` | no | reveals granted groups and sources |
| `agents.*.spawns` | `harness/Task` | no | spawns a sub-agent under its own grant |
| `human.narrate` | `harness/Narrate` | no | appends to the run narrative |

Why not a `terminal: true` flag that authors could set on any tool:

1. **Ending a run is harness behaviour, not tool behaviour.** It means
   exclusivity in the turn (`terminal_not_exclusive`), the final-turn
   nudge naming exactly the allowed terminals, the first-`done`
   checklist, the post-run cross-check, and the outcome on the run
   record. A flag would put the trigger for all of that on a tool whose
   implementation is somewhere else, possibly an MCP server.
2. **A remote server must not be able to end your run, or decide its
   status.** With a flag, a server's tool would be one annotation away
   from doing that.
3. **The report is validated by the harness, against a schema the
   template owns.** If the terminal were a server tool, the server would
   validate it.
4. **The calling convention is stated once.** `../models.md` §4c
   principle 7: `Complete`, `AskUser` and `HandOff` share one rule
   ("calling it is the last thing you do"), which is only stated once if
   one component owns all three.

Authors do control everything that differs between agents: the tool
name, the allowed `statuses`, the `report_schema`, the `summary` cap,
which completion `checks` run, whether spinoffs are allowed, and which handoff
reasons exist and what situation each describes. That is the whole of
what Forge's three entrypoints vary.

**`form: "text"`** covers the quick analysis run (`../models.md` §3): the
run ends on an assistant message with no tool calls, with status
`done`, and that message becomes `outcome.summary`. R5 limits it to
specs with no report schema, completion checks, spinoffs or ending tools, because
there's nothing to validate.

### 5a. Tools marked as endings

Use case 0b asks for the opposite of a generic `Complete`: pick some
real tools (update Jira, open a PR, ask for help) and make *those* the
ways a run can end. A run's tools are one list, and **each entry says
how the agent may use it**: `use: ["call"]` (the default) during the
run, `["finish"]` only as an ending, or `["call", "finish"]` both. The
marking is part of the run's configuration, on the tool's entry in the
template or the saved tool group, and its `finish` block says which
status the ending gives and whether it takes a report.

This keeps the reasons above intact, because the termination is still
the harness's, not the tool's. The tool's server doesn't know it's an
ending, and the same MCP tool can be an ending in one template and an
ordinary tool in another. What the author marks is how *this run* may
use it.

- **The model sees a separate generated tool for each ending.** It takes
  the tool's own arguments, with overrides applied, plus `summary`, and
  `report` when `report: true`. Arguments are flat, so `summary` and
  `report` are reserved: publish refuses a tool with an argument of
  either name (R14). Its name is `finish.name`; otherwise the tool's name
  when it's only an ending, or `Finish` + its name when it's callable
  too.
- **Grant means available; `use` means how.** An ending tool is granted
  like any other. Marking it only `finish` is how `coding.java` lets the
  model move the Jira ticket as its ending but never halfway through.
  Only the orchestrator may be granted ending tools; a sub-agent never
  ends a run.
- **Some built-ins allow only some uses.** Keel's built-in catalogue
  (`tools-and-agents.md` §4a) says which: `Read` can only be called,
  `RequestHelp` can only end a run. MCP tools allow both.
- **Completion checks run before the call, not after.** The first-`done`
  checklist, `report_crosscheck` and the rest fire when the model calls
  the ending. A PR is opened, or Jira is moved, only after they pass. For
  an irreversible ending that order is the whole point.
- **A failed call doesn't end the run.** The error goes back to the
  model with a `finish_failed` refusal code, and the run continues: it
  can fix the problem, or pick another ending.
- **`complete: false`** removes the generic `Complete`. The run can then
  end only through an ending tool, `AskUser`, `HandOff`, or the
  final-turn nudge, which lists exactly the endings that exist.

**Ask for help during the run, or as the ending.** These are different,
and both are useful. `AskUser` mid-run suspends and resumes the same task
with its context, which is right for a question. `RequestHelp`, a
built-in that is only an ending, hands the task to a person through a
channel and ends the run `blocked`, which is right when no single answer
would unblock it. Their descriptions say so, because the model choosing
between them is the point.
