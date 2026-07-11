# SWE-agent

- **Type**: Coding agent (autonomous GitHub issue resolver, Princeton NLP)
- **License**: MIT
- **Source**: https://github.com/SWE-agent/SWE-agent
- **Retrieved from**: `main` branch, `config/default.yaml` (2026-07-10)

SWE-agent defines its prompts inline in a YAML config rather than in Python
source. `default.yaml` includes the system template, instance (task) template,
and the full custom tool/command definitions the agent can call (bash-like
filesystem and search commands, file editor, submit, etc).

## Files

- `default.yaml` — full agent config: system prompt, instance prompt,
  next-step templates, and tool/command definitions.

## Tool surface

**Correction**: this section originally speculated about the `bundles`
referenced by `default.yaml` (`tools/registry`, `tools/edit_anthropic`,
`tools/review_on_submit_m`) without fetching them. They've since been
read directly from the live `SWE-agent/SWE-agent` repo (MIT-licensed,
not a leak) — the bullets below are corrected/expanded accordingly, and
the speculation about `edit_anthropic`'s lineage was only half right.

- **Shell**: "the bash tool," referenced generically in the instance
  template. Confirmed **not** a `tools/` bundle at all — built into the
  core framework (`sweagent/tools/commands.py`), deliberately terse
  ("runs the given command directly in bash," no ACI-style elaboration).
  Concrete constraints confirmed in code: `execution_timeout: 30`s per
  command, `total_execution_timeout: 1800`s for the whole episode, and
  the agent is force-exited after `max_consecutive_execution_timeouts: 3`.
  Interactive-output env vars are explicitly disabled for headless
  operation: `PAGER`/`MANPAGER`/`GIT_PAGER` set to `cat`,
  `PIP_PROGRESS_BAR`/`TQDM_DISABLE` turned off.
- **Editing (`edit_anthropic`)**: confirmed by reading
  `tools/edit_anthropic/bin/str_replace_editor` directly — its own
  docstring states verbatim it's "an adaptation of the Anthropic Text
  Editor tool from
  [`anthropic-quickstarts/computer-use-demo`](https://github.com/anthropics/anthropic-quickstarts/blob/main/computer-use-demo/computer_use_demo/tools/edit.py)…
  made it python 3.6 compatible and stateless." So the original
  speculation was directionally right but attributed the wrong lineage:
  this and [`../augment-swebench-agent/`](../augment-swebench-agent)'s
  `str_replace_tool.py` share a common **Anthropic reference-implementation**
  ancestor, not a direct fork of each other. SWE-agent's version adds
  real machinery the bare reference tool doesn't have: a `WindowExpander`
  that snaps view/edit windows to function/class boundaries, a
  tree-sitter-based `Filemap` that elides long function bodies for
  large-file overviews, and integrated flake8 linting that diffs
  pre/post-edit errors to surface only newly-introduced ones. State
  (e.g. `undo_edit` history) persists via the `registry` bundle rather
  than in-process memory, since every tool invocation is a fresh
  subprocess.
- **`registry` bundle — corrected**: defines zero tools of its own
  (`tools: {}`). It's a shared key-value **state-persistence**
  mechanism (`EnvRegistry`, backed by a JSON file), not a
  tool-registration/discovery system as the name might suggest —
  necessary because each tool call is a separate subprocess that can't
  share Python-process memory.
- **Self-review (`review_on_submit_m`) — corrected, and this is the
  important one**: **not** an LLM review pass. `bin/submit` is purely
  deterministic string templating: it counts a stored stage against a
  list of canned message strings (`SUBMIT_REVIEW_MESSAGES`, one entry
  in `default.yaml` — a checklist to rerun the reproduction script,
  delete it, and `git checkout` any modified test files) and re-injects
  the next one as ordinary tool output into the **same single agent
  loop** — no separate model call, no distinct persona, and nothing
  automatically blocks submission if the agent ignores the checklist
  and just calls `submit` again. The genuinely separate-model-call
  reviewer mechanism SWE-agent actually has lives elsewhere entirely —
  see "Sub-agents" below.
- **The classic windowed ACI (Agent-Computer Interface) editor is
  still present**, just not used by this particular `default.yaml`:
  `tools/windowed` (`goto`/`open`/`create`/`scroll_up`/`scroll_down`)
  paired with one of three alternative editing bundles
  (`windowed_edit_replace`, `windowed_edit_rewrite`,
  `windowed_edit_linting`) — mutually exclusive alternatives to
  `str_replace_editor`. Also present but not wired into `default.yaml`:
  `search` (`find_file`/`search_dir`/`search_file`), `forfeit`
  (`exit_forfeit` — give up), `filemap` (standalone version of the
  eliding logic `edit_anthropic` uses internally), `diff_state`, and a
  real **`web_browser` bundle** (`open_site`/`click_mouse`/`type_text`/
  `screenshot_site`/`execute_script_on_page`) — contradicting the
  original "browser/web: not addressed" finding, though this bundle
  isn't part of the `default.yaml` configuration documented here.
- **Code execution**: `python <filename.py>` via the bash tool, same as
  everyone else in the benchmark-solver archetype — no dedicated
  execution tool.
- **Multimodal**: `tools/image_tools` exists as a named bundle (not
  read in depth) — flagged rather than asserted absent, given how wrong
  the original "not addressed" calls turned out for browser/web above.
- **Sandbox/isolation**: not specified in this config (handled by
  SWE-agent's Docker-based runtime outside the prompt).

## Sub-agents

See also [`agent-self-verification.md`](../agent-self-verification.md)
— the `review_on_submit_m` gate and the `ScoreRetryLoop`/`ChooserRetryLoop`
reviewer/chooser mechanism documented in this section are both cited
there as reference cases in the cross-source self-verification survey.

Not previously covered for this source. `default.yaml`'s
`review_on_submit_m` bundle (above) is **not** a sub-agent — it's
deterministic re-prompting within one loop. The real sub-agent-relevant
mechanism lives outside the `tools/` bundle system entirely, in
`sweagent/agent/reviewer.py` and `sweagent/agent/agents.py`, and isn't
wired into `default.yaml` at all — it activates only when an agent
config sets `type: "retry"` instead of the plain `type: "default"`
single-loop config this folder documents.

- **`RetryAgentConfig`** holds a list of `DefaultAgentConfig`s plus a
  `RetryLoopConfig`, running **multiple full independent agent
  attempts** rather than delegating a sub-task mid-loop — a different
  shape from every other sub-agent mechanism surveyed in this
  collection's `agent-subagent-architectures.md` (which are all about
  one agent asking another to do *part* of the work; this is several
  full attempts at the *whole* task, judged after the fact).
- **`ScoreRetryLoop`**: after each complete attempt, a `Reviewer` makes
  its own separate LLM call (a distinct model instance, its own
  `system_template`/`instance_template`, not sharing cost accounting
  with the main agent) fed the full formatted trajectory, and returns a
  numeric acceptance score — optionally sampled multiple times for
  self-consistency, averaged and variance-penalized. Based on the score
  plus `max_accepts`/`cost_limit`, it decides whether to run another
  attempt (each in its own output directory) and finally picks the
  best-scoring one.
- **`ChooserRetryLoop`**: runs several full attempts to exhaustion, then
  a separate `Chooser` LLM call — shown every submission/trajectory —
  picks the single best index, optionally narrowed first by a
  `Preselector` LLM call. Up to three distinct model calls in the
  pipeline (agent, preselector, chooser), each with its own prompt.
- **This is a genuine reviewer/judge sub-agent pattern** — a real,
  separately-prompted model call evaluating another model's completed
  work — but it's *ensemble selection over whole independent runs*, not
  in-conversation delegation of a sub-task. Worth comparing to Augment
  SWE-bench Agent's `ensembler_prompt.py`/`majority_vote_ensembler.py`
  (already documented in this collection) — same underlying idea
  (multiple candidate solutions, a separate LLM picks/scores the best),
  different selection mechanism (majority vote there vs. a
  score/chooser LLM call here).
