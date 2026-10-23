# Keel: how a run ends

Generated ending tools, and finishers. Part of [Keel](./README.md). Section numbers are shared across Keel's files, so a reference like §7f means the same section everywhere; [the README](./README.md#files) lists which file holds each.

---

## 5. Completion tools: separate tools, or a flag on a tool?

**Neither. The spec declares a contract, and the harness generates the
tool.** Authors don't write `Complete`, and they can't mark an arbitrary
tool as run-ending.

| Contract in the spec | Generated tool | Ends the run? | What the harness does on the call |
|---|---|---|---|
| `completion` | `harness/Complete` (or `tool_name`), unless `complete: false` | yes: `complete` | validates `report` against `report_schema`, runs the completion `checks`, files spinoffs, evaluates sinks and continuations |
| `completion.finishers[]` | one tool per finisher, under its `name` | yes: `complete`, with `outcome.finisher` set | completion checks, then the wrapped tool or harness action; on failure, back to the model (§5a) |
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
specs with no report schema, completion checks, spinoffs or finishers, because
there's nothing to validate.

### 5a. Finishers: choosing the ending from a set of tools

Use case 0b asks for the opposite of a generic `Complete`: pick some
real tools (update Jira, open a PR, ask for help) and make *those* the
ways a run can end. That is a **finisher**: an entry in
`completion.finishers` naming a declared tool (an MCP tool or a
harness action, §7g), the
status it ends with, and whether it takes a report.

This keeps the reasons above intact, because the termination is still
the harness's, not the tool's. The tool doesn't know it's a finisher,
and the same MCP tool can be a finisher in one template and an ordinary
mid-run tool in another. What the author marks is the *ending*, in the
contract, which is the right place for it.

- **The model sees a separate generated tool.** It takes `summary`,
  `report` when `report: true`, and `args`: the wrapped tool's
  arguments with the finisher's and the `ToolRef`'s overrides applied.
  The arguments are nested under `args` so that no server argument can
  collide with `summary`. That costs a nested object in the call, which
  `agent-tool-implementations.md` §3g measures as slightly less reliable
  to emit, and it's the price of not reserving names in every server's
  schema.
- **Completion checks run before the action, not after.** The
  first-`done` checklist, `report_crosscheck` and the rest fire on the
  finisher call.
  A PR is opened, or Jira is moved, only after they pass. For an
  irreversible action that order is the whole point.
- **A failed action doesn't end the run.** The error goes back to the
  model with a `finisher_failed` refusal code, and the run continues:
  it can fix the problem, or pick another ending.
- **A finisher's tool is declared, not granted.** `FinishWithJiraUpdate`
  wraps `mcp:jira/update_issue`, which `coding.java` declares in a group
  it grants to nobody. The model can move the ticket as its ending, and
  can't do it halfway through. Granting it as well would allow both,
  under two different names (R11).
- **Harness actions are tools like any other** (§7g), so a finisher
  wraps them the same way. `coding.java` ends with
  `action/open_pull_request` or `action/request_help`. Both are
  declared in a group granted to nobody, with their branch, labels and
  channel fixed by argument overrides.
- **`complete: false`** removes the generic `Complete`. The run can
  then end only through a finisher, `AskUser`, `HandOff`, or the
  final-turn nudge, which lists exactly the endings that exist.

**Ask for help during the run, or as the ending.** These are
different, and both are useful. `AskUser` mid-run suspends and resumes
the same task with its context, which is right for a question. A
`request_help` finisher ends the run and hands the task to a person,
which is right when no single answer would unblock it. Their
descriptions say so, because the model choosing between them is the
point.
