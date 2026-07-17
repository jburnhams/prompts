# Future considerations

The long-horizon tier of the roadmap — see `medium.md` for the
concrete next upgrades and the escalation triggers, and `README.md`
for the v1 design itself. Everything here is either gated on
measurement that `medium.md`'s telemetry item has to produce first,
or is a genuine subsystem whose cost only pays off at a scale v1
hasn't reached. Nothing here should influence a v1 implementation; it
exists so these ideas are tracked instead of forgotten or silently
re-litigated later.

- **Typed sub-agent registry beyond three types.** Coding mode has one
  delegate type; review mode has two (`reviewer`, `validator`). Claude
  Code, Gemini CLI, and Amp all show the next step (named, narrower
  types for specific jobs) once there's a concrete need.
- **Addressable/resumable sub-agents.** Codex CLI's `spawn_agent`/
  `send_input`/`wait_agent`/`close_agent`, OpenCode's
  queue-onto-a-running-job model, and Grok Build's `resume_from`
  (`agent-subagent-architectures.md` §2 — five independent arrivals at
  "addressable, not stateless") are the natural upgrade once a coding
  task needs to steer a sub-agent mid-flight rather than
  fire-and-forget it. Recursive delegation (`general-purpose` calling
  `Task` itself, currently disallowed — `tools.md`) is the same
  underlying question one level deeper.
- **Numeric confidence scoring for review findings.** The validator
  pass is binary (confirmed / not confirmed), matching Anthropic's own
  skill. TuringMind's 0-100 rubric or BMAD's 4-bucket triage
  (`code-review-approaches.md` §6) are richer but add real tuning
  surface — gated on the false-positive rate `medium.md`'s
  finding-outcome telemetry actually measures.
- **Best-of-N ensembling for hard tickets.** Run several full,
  independent `implement` attempts and have a separate judge pick the
  winner — SWE-agent's `RetryAgentConfig` (score-and-retry, or
  chooser-over-a-batch) and Augment SWE-bench Agent's
  majority-vote ensembler are the same shape arrived at independently
  (`agent-subagent-architectures.md` §2, `agent-self-verification.md`
  §3). Expensive by construction (N full runs plus judge calls), so
  it's a per-task dispatch choice for tickets that failed a first
  attempt or are flagged hard — not a default. Forge's
  working-tree-is-the-deliverable design actually suits this well:
  N worktrees, one judged winner, no branch juggling inside the agent.
- **An LLM judge over completed work.** Claude Code's internal
  adversarial verification subagent is the ceiling
  (`agent-self-verification.md` §3); v1's completion-integrity story
  is deterministic only (checklist gate + harness `git status`
  cross-check), which can't be prompt-injected or talked out of
  firing. The judge is the layer above, not a replacement.
- **Context compaction.** A run that outgrows its budgets ends via the
  final-turn nudge with an honest partial report (`formats.md` §7)
  rather than summarizing and continuing — compaction is a genuine
  subsystem (`agent-context-compaction.md`) and the natural lever if
  budget-exhausted runs turn out to be common on legitimately-sized
  tasks.
- **A tiered permission/approval subsystem.** Codex CLI's five
  cooperating subsystems and Gemini CLI's policy engine
  (`agent-permissions-approval.md`) are the eventual ceiling; v1 gets
  structural mode wiring, the git-write blocklist, and one hard prompt
  rule, with `medium.md`'s command-level Bash filtering as the first
  slice. The field's most interesting converged pattern, if this is
  ever built: three vendors independently arrived at "a second,
  cheaper LLM judges the first model's proposed actions" (Gemini CLI's
  Conseca, Codex's Guardian, Claude Code's internal `yoloClassifier`),
  always layered *on top of* a static rule engine that keeps working
  without it, failing closed on error
  (`agent-permissions-approval.md` §2).
- **Active CI/CD control.** `medium.md`'s `FetchBuild` is read-only by
  construction; the next step — triggering pipeline runs, re-running
  failed steps, managing deployments — is a genuinely different
  permission surface (an agent that can trigger a deploy pipeline can
  ship code, which v1's no-git-writes stance exists to prevent).
  Windsurf's `deploy_web_app`/`check_deploy_status` trio is the only
  deployment-as-a-tool precedent in the collection
  (`agent-tool-surfaces.md` §7). If ever built, it belongs behind the
  tiered permission subsystem above, not before it.
- **A standing PR-steward loop.** Today every run is one-shot:
  dispatched, terminates, done. The steward shape — a task that stays
  subscribed to a PR's events (CI results, new comments, new pushes)
  and dispatches the right run type per event until the PR merges or
  closes — is the composition of `medium.md`'s three loop-closing
  sources and its generalized task-suspension primitives (§4c) under
  one harness-side state machine. All the pieces are medium-tier; the
  steward is the orchestration layer over them, plus the lifecycle
  policy questions (when to give up, how to hand off to a human) that
  deserve their own design pass. The same shape has a backlog analog
  once the product-owner entrypoint (`medium.md` §5) exists: a
  standing grooming loop that keeps a board healthy on a schedule
  rather than per-dispatch — same primitives, same
  policy-pass-required caveat.
- **Coordinated multi-repo changes.** `medium.md`'s dependency-change
  path is asynchronous by design: file the ask, suspend, integrate
  when it ships — each repo's change lands on its own timeline. The
  harder version is lockstep: an API change and its consumers, a
  cross-cutting rename, a coordinated version bump — several repos
  that must change *together*, with ordering, atomicity-of-intent,
  and release sequencing owned by something. No source in the
  collection touches this, and it's a real orchestration subsystem
  (change-set modeling, cross-repo rollback story, who merges what
  when) — the multi-repo analog of what `agent-context-compaction.md`
  is to context. Tracked so the asynchronous path doesn't get bent
  out of shape trying to fake it.
- **Cross-run repo memory.** V1 runs start cold except for the
  conventions file and the plan/findings envelope tags. The field
  offers three shapes for "remember this repo across sessions":
  Windsurf's bespoke tagged-database tool, GitHub Copilot CLI's raw
  SQL over a session store, and Grok Build's tool-mediated read/search
  over a plain memory file (`agent-tool-surfaces.md` §7). The tension
  to resolve before adopting any of them: a Forge-writable memory file
  that future runs read is *exactly* the self-instruction-poisoning
  surface the conventions file is defended against (`formats.md` §3a)
  — so memory needs the same structural write-gating and provenance
  story from day one, not retrofitted.
- **Semantic / symbol-aware code search.** V1's Grep/Glob sits at the
  middle of the field's clearest capability ladder — plain text match
  → semantic/embedding search (Cursor, Windsurf, Roo Code) →
  LSP-backed symbol resolution (Copilot Chat)
  (`agent-tool-surfaces.md` §2). The upgrade needs an index built and
  maintained per repo, which is real infrastructure; worth it only if
  exploration cost (turns spent finding things) measurably dominates
  run budgets on large repos. Orthogonal to `medium.md`'s
  `SearchSource` (§2e): that widens search *scope* (other repos,
  dependencies) while keeping ripgrep semantics; this deepens search
  *resolution* on whatever scope exists. They compose — a symbol
  index over the cross-repo corpus is the ladder's top rung — but
  neither depends on the other.
- **Browser/UI verification and multimodal input.** For front-end
  tickets, "verify" currently means tests pass — no way to look at
  the rendered result. Cline's single-tool and Windsurf's
  seven-tool browser automation are the only two real precedents, and
  multimodal input is the least-addressed capability in the whole
  survey (`agent-tool-surfaces.md` §4-5). A screenshot-and-view
  capability is the minimal useful slice; full interactive automation
  is a large dependency for one ticket class.
- **Turn caps for sub-agents.** Copilot Chat's `isLastTurn` nudge (the
  mechanism `formats.md` §7 uses run-level) applied to individual
  `Task` calls. The run-level budget is enough for now; a runaway
  sub-agent still terminates when the parent run's budget is hit.
- **A cap on suspend/resume cycles.** No built-in limit in v1
  (`formats.md` §5). A real deployment would likely want one
  ("escalate instead of asking a third time") — left unspecified
  rather than picking a number with no concrete reason behind it.
  Once `medium.md`'s generalized suspension (§4c) exists, this entry
  widens from AskUser cycles to suspensions of any kind, and gains a
  second dimension: a maximum total park duration, so a task waiting
  on a dependency that never ships eventually fails honestly back to
  a human instead of sleeping forever.
- **Re-wiring `AddComment` in implement mode as a general
  decision-notes channel.** `medium.md`'s responder source wires it
  for threaded replies where replying is the deliverable; the broader
  idea — posting durable implementation-decision notes to the
  originating ticket mid-run ("chose X over Y because Z") — stays
  future. The information isn't lost meanwhile: judgment calls and
  caveats go in the Complete report, and the harness decides what
  reaches the ticket. Worth doing only if the report → harness →
  ticket path proves insufficient in practice, and then with the same
  scoped-to-one-job prompt guidance plan mode's posting step has.
- **Repo-file content sanitization.** The envelope/FetchJira sanitizer
  (`formats.md` §1) deliberately doesn't touch file contents returned
  by Read/Grep — mangling source bytes would break Edit's exact-match
  contract. A malicious file in a reviewed PR could carry
  invisible-Unicode payloads to a `reviewer` that Reads it; Bash
  output has the same residual exposure (a `git log` on a hostile
  branch returns attacker-authored commit messages). A
  display-layer-only strip (sanitize what the model sees, keep on-disk
  bytes canonical) is the plausible fix; no source in the collection
  does it today.
- **MCP-style third-party extensibility.** V1's tool surface is
  closed by design. If it ever opens, the field's lessons: render the
  prompt's tool list from what's actually wired (Pi, Gemini CLI —
  `agent-tool-surfaces.md` §10) so the prompt can't describe a tool
  that doesn't exist, and treat schema discovery as mandatory before
  first use (Grok Build's `search_tool`-before-`use_tool` rule).
  Every added tool is also added injection surface on an unsupervised
  path — which is the real reason this is future-tier, not the
  plumbing.
- **A conversational product-owner surface.** `medium.md`'s PO
  entrypoint (§5) stays hands-off on purpose: questions travel over
  the suspend/resume protocol, whatever channel delivers them. The
  next step a real PO will ask for is a live session — grooming a
  board *with* the agent in a chat thread, back-and-forth at
  conversation speed. That is an archetype change, not a feature:
  interactive agents carry terseness rules, status-update protocols,
  and turn-taking conventions that hands-off agents deliberately
  lack (`agent-archetypes.md` axis 1, `coding-agent-approaches.md`
  §11), so this is a fourth prompt with its own communication
  contract sharing PO mode's tool surface — not a flag on the
  existing one. The suspension-based mode remains the substrate:
  a live session that ends with unresolved questions parks them the
  same way.
- **Estimation calibration from historical outcomes.** The PO
  entrypoint's estimates are grounded in code evidence but
  uncalibrated. The extension of `medium.md`'s finding-outcome
  telemetry (§3e) to this track: record estimate vs. actual
  (cycle time, PR size, review rounds) per story, and feed the
  distribution back into the estimation rubric. Same
  measurement-before-mechanism ordering as confidence scoring —
  the rubric upgrade is pointless before the data exists.
- **`NotebookEdit` and other niche editors.** Still not load-bearing
  for "implement a ticket / review a diff"; add per-format tools only
  when the repo mix demands them.
