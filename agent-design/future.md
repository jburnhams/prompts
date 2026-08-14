# Future considerations

The long-horizon tier of the roadmap — see `medium.md` for the
concrete next upgrades and the escalation triggers, and `README.md`
for the v1 design itself. Everything here is either gated on
measurement that `medium.md`'s telemetry item has to produce first,
or is a genuine subsystem whose cost only pays off at a scale v1
hasn't reached. Nothing here should influence a v1 implementation; it
exists so these ideas are tracked instead of forgotten or silently
re-litigated later.

- **Adoption-verified criteria maintenance.** The reviewer core
  (`system-prompts.md` §4) is hand-authored and has no revision
  mechanism — it says what it says until someone edits it. The upgrade
  is a periodic job that rewrites it from human review feedback that the
  code actually adopted. Precedent and full mechanism:
  `../code-review-approaches.md` §11 (DeepSeek Harness is the only
  source in the collection that treats criteria provenance as a pipeline
  stage; Qodo, CodeRabbit and Greptile do adjacent things from weaker
  signals — `../agent-memory-learning.md` §8). Five parts carry the
  design, roughly in order of how much each is worth:
  - **Adoption is a question about the tree, not the thread.** A
    resolved thread, a merge, a 👍, and an author's "fixed" reply are
    all context, not proof — a PR can merge with feedback rejected or
    superseded. The evidence is two PR-specific patch snapshots
    (feedback-time baseline→`B`, and target-parent→merge), chosen so a
    change that arrived independently on the target branch appears in
    neither and cannot be miscredited to the comment.
  - **Rewrite the criteria wholesale, never append.** The drafting pass
    returns complete replacement text, so every run re-derives the whole
    document and a rule can be folded or dropped. An append-only store
    can only grow, and checklist bloat is the failure mode this exists
    to prevent — not finding rules.
  - **Two independent judges, never author-as-judge.** Independent
    verdicts are what expose unsupported generalization from a single
    incident before it reaches the criteria.
  - **A human promotes**, and is instructed not to defer to the judges:
    hunt for checklist bloat, extrapolation from one PR, and duplicated
    coverage with what the core already says.
  - **Expect zero.** DeepSeek's published acceptance run turned 426
    human feedback items over 62 merged PRs into zero rule changes. A
    version of this that produces a candidate every run is broken.

  **Gated on** `medium.md` §3e's finding-outcome telemetry, which is the
  input this needs and does not yet exist — build the measurement first.
  **Not** worth copying: DeepSeek keeps the mechanism on a single
  operator's machine outside the repository, and its own risks section
  names the consequence (single-maintainer bus factor). That reasoning
  was specific to one skill and one maintainer; it does not transfer to
  a tool serving criteria across every repo Forge reviews.

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
- **Cross-run repo memory — resolved and moved to `medium.md` §6.**
  This entry previously tracked the open question and its blocker: a
  Forge-writable memory file that future runs read is *exactly* the
  self-instruction-poisoning surface the conventions file is defended
  against (`formats.md` §3a). Dedicated research
  (`agent-memory-learning.md`) resolved it rather than mitigating it —
  the writer is a separate outcome-triggered run with no filesystem
  and one schema-validated write tool, so there is no writable file to
  poison, provenance is stamped harness-side rather than authored, and
  the human-owned conventions file is never a write target. What
  remains genuinely open, and stays here: whether learnings should
  ever influence *suppression* of review findings (`medium.md` §6f
  ships informs-never-vetoes deliberately), which needs the finding
  outcome data of §3e before it can be argued from evidence rather
  than from taste.
- **Semantic / symbol-aware code search.** V1's Grep/List sits at the
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
- **A flat spelling of batch `Read`, if parse failures ever show up in
  the normalisation telemetry.** `Read`'s `files: [{path, start_line,
  end_line}]` is an array of objects, which is the one parameter shape
  that forces the model to emit escaped JSON inside the tool-call
  channel rather than a delimiter-matched primitive
  (`agent-tool-implementations.md` §3g). The flat alternative already
  exists in the tolerance table as an accepted input — an array of path
  strings — and could be promoted to the advertised schema with ranges
  moved into the string (`src/a.ts:120-180`, OMP's selector grammar),
  keeping batching *and* flatness at the cost of a mini-language the
  description has to teach. Deliberately not done pre-emptively: the
  telemetry rule in `tools.md` exists exactly for this, every
  normalisation is already counted, and a malformed-arguments rate is
  the signal that would justify the change. Ordering matters here —
  measure, then reshape.
- **Dialect-aware tool-call scanning.** §3g's other half: a harness that
  handles its wire format's failure modes rather than treating a bad
  call as the model's problem — a call leaked into output text, a
  malformed call header, a turn that emits no call at all. V1 inherits
  whatever the provider SDK does, which is the right call for one model
  family on a managed API, and OMP's eleven dialect converters are the
  shape this takes if Forge ever runs on open-weights models where
  nobody else is fixing it. The build list is
  `agent-tool-call-dialects.md` §7 — a renderer plus a deliberately
  wider scanner, call-ID minting where the dialect has none, streaming
  that holds partial delimiters across chunks, history conversion in
  both directions, and the tool catalogue moving into the system prompt
  at a cost paid every turn.
