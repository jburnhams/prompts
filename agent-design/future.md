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
- **A standing PR-steward loop.** **Largely superseded by
  [`orchestration.md`](./orchestration.md)** — the lifecycle policy this
  item deferred ("when to give up, how to hand off to a human") is that
  document's §7 give-up queries and its `abandoned` state, and what
  remains of the steward is not an orchestration layer at all but a
  ledger task whose wake predicate is a PR event. Kept below as the
  original statement of the problem. Today every run is one-shot:
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
- **Task splitting: spinning off a dependent task with its own context.**
  **Superseded by [`orchestration.md`](./orchestration.md) §6**, which
  specifies the spinoff as a `Complete.report.spun_off` array with a
  two-valued `relation` (`blocks_this`/`follows_this`) and answers all
  three prerequisites named below: the dependency relationship
  (`depends_on` on the task record), the approval policy (**asymmetric**:
  `blocks_this` auto-chains because its parent is already stalled,
  `follows_this` is gated on an approving reply because it is new scope
  the run invented), and what the originating run does while it waits —
  **nothing; it ends, and the task waits**.
  The sequencing note at the end of this item still stands and is
  restated there. Kept below as the original statement.
  A coding run is dispatched with a `paths` scope and a set of `kinds`,
  and its context is resolved once against them
  ([`context-files.md`](./context-files.md) §1b). A run whose fix reaches
  outside that scope is therefore working, for those files, without the
  conventions that govern them. v1's answer is to record it and let the
  review entrypoint catch what the coding run could not — deliberately
  minimal, because the alternatives are both worse: re-resolving mid-run
  papers over a mis-scoped task and adds the only mid-run service
  dependency in the design, and blocking the write stalls the ticket with
  nothing to hand the overflow to.

  The real fix is the thing to hand it to: **a run that finds work outside
  its remit spins off a dependent task rather than stretching itself**,
  and that task is dispatched with its own `paths`, its own `kinds` and
  its own resolution. That makes "keep tasks focussed" structural rather
  than aspirational, and it makes each task's context correct by
  construction instead of correct-if-the-scoping-was-right.

  What it needs before it can be specified: a spinoff primitive with a
  dependency relationship (this ticket blocks that one), a policy for who
  approves the split — the same policy-pass question `medium.md` §5's
  product-owner entrypoint raises — and an answer to what the originating
  run does while it waits, which is either `AskUser`'s suspend/resume
  protocol (`formats.md` §5) or a completion that names the follow-up.
  Sequencing note: this is one of three things that want to land together
  — context narrowing ([`context-files.md`](./context-files.md) §1b's
  "Narrowing, later"), what a run does when it reaches outside its scope,
  and task splitting. None is urgent while v1 hands every run the whole
  corpus, and each is awkward without the other two.

  Note the shape is close to the existing dependency-change path below:
  file the ask, suspend, integrate when it ships. The difference is that
  the dependency here is a task in the same repository rather than a
  change in another one, which may mean it is the *easier* case to build
  first rather than a separate subsystem.
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
- **Cross-run repo memory — resolved, moved to `medium.md` §6, and now
  specified in [`memory.md`](./memory.md).**
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
  than from taste. `memory.md` narrows it slightly — informs-never-vetoes
  is now a `binding` value rather than a prose rule, so lifting it would
  mean letting a machine-written section carry `policy`, which is a
  sharper question than the one this entry originally asked.
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
- **Artifacts: a session-scoped store, and a stub in place of the
  payload.** ~~Gated on a real case.~~ **Promoted into scope — specified
  in [`artifacts.md`](./artifacts.md).** The real case arrived from a
  direction this entry did not anticipate: **Jira and PR attachments**,
  which both fetch tools currently drop. The entry below is left as
  written; the two decisions it defers to "that point, not now" are
  answered in `artifacts.md` §5.1 (minting is *ingest*-triggered, with
  spill minting **in scope after all** — see the supersession note in
  `README.md`'s decision log) and §4a (the selector
  termination rule, which replaces the exempt-the-read-tool carve-out;
  a reference to a gone artifact fails loudly with the re-fetch call
  named, §5.5). V1 has no answer for a tool result that is legitimately
  large — the caps in `tools.md` truncate or error, and both are the
  right default for the *file* case, where the model asked for
  something specific and the recovery is a narrower call. They are the
  wrong default for the case where the payload's *shape* is what the
  model needs and its *contents* are not: a 40k-row query, a
  full dependency tree, a screenshot, a heap dump. The pattern the
  field converged on — store the bytes out of context, return a stub
  describing the shape, and give the model operations that *reduce*
  rather than a way to load it all back one turn later — is written up
  in `../agent-tool-result-transport.md` §7, including the six
  decisions it forces and the two traps this collection has already
  documented (the circular `Read`→file→`Read` spill, and the stub
  whose referent outlives, or fails to outlive, compaction).
  Three things make this cheaper here than it would be elsewhere:
  - **The substrate exists on the target stack.** ADK ships an
    `ArtifactService` — named, versioned `Part`/`Blob` objects, session
    scope by default with a `user:` prefix widening to all of a user's
    sessions, `InMemory` and GCS backends — and, critically,
    `LoadArtifactsTool` appends a loaded artifact **to that request
    only**, never to conversation history. That is a strictly better
    contract than a file path, because it makes an expensive load a
    one-turn cost instead of a permanent one. Nothing here needs
    building; it needs wiring and a policy.
  - **The model-facing shape costs zero new tools.** OMP's answer is
    the one to copy: `artifact://<id>` is a URI scheme the existing
    read tool already understands, taking the same selector grammar as
    a file (`:N-M`, `:raw:N-M`). `Read` already has a path parameter, a
    range concept and a paging contract; an `artifact:` scheme reuses
    all three, and the alternative — a `LoadArtifact` tool plus a
    `QueryArtifact` tool plus their descriptions — is the tool-count
    inflation `tools.md`'s granularity rule exists to resist.
  - **The stub format is already specified.** `formats.md` §8a's block
    grammar (tag-framed, attributes carry facts, `!` lines carry notes)
    covers an artifact stub without inventing anything: an
    `<artifact id=… kind=… rows=… bytes=… expires=…>` header with a
    preview inside it is the same shape as `<file>`.

  **Gated on** a real case. V1's tools are `Read`/`Grep`/`List`/`Bash`
  over a working tree, and the honest position is that none of them
  routinely produces something worth storing — `Bash` is the only
  candidate and its cap plus a truncation notice has not yet been shown
  to fail. Build this when a tool that legitimately returns bulk data
  is added (the `medium.md` §2e classpath/dependency index is the first
  plausible one), not before: an artifact store with nothing in it is
  the unused-escape-hatch surface `tools.md` §1 argues against. Two
  decisions to make **at that point, not now**: whether minting is
  automatic on overflow (Claude Code's spill) or explicit (a tool
  chooses), and whether a stub must survive compaction or fail loudly
  when its referent is gone.
- **An audience channel on tool results.** Related but separable, and
  smaller: `formats.md`'s result blocks assume one reader, the model.
  Three of the field's mechanisms assume a result routinely contains
  something for the model, something for the user, and something for
  neither — MCP's `annotations.audience`, the `_meta` convention, and
  MCP Apps' `ui://` views (`../agent-tool-result-transport.md` §8).
  The generalisation is worth writing down even while v1 has no user
  surface to route to: **audience is a property of a content block,
  not of a tool call**, and a format that can only mark the whole
  result will push everything into the model's context by default.
  Forge's user-facing channel today is `AddComment` and the `Complete`
  report, both of which are separate tools rather than annotations on a
  result — which is a coherent answer, and worth revisiting only if a
  run ever needs to hand back an artifact (a chart, a profile, a
  screenshot) that isn't prose.
- **Emit standing context as a diff, not as a per-turn re-render.** The
  envelope (`formats.md` §1) is assembled fresh for every run, and within
  a run the conventions corpus sits in the prompt unchanged from first
  turn to last. That is correct and cheap at v1's scale, where a run is
  one task and the corpus does not change under it. It stops being
  obviously correct the moment a run gets long enough for the corpus to
  change mid-flight — the just-in-time section reveal (`formats.md` §8b)
  is already the thin end of that wedge, and `medium.md` §4's long-horizon
  waiting is the thick end.
  Codex's answer is worth tracking as the most developed one in the
  collection: sixteen named world-state sections, each rendering only its
  own diff against a hashed snapshot of its prior value, so a stable
  section contributes zero bytes after the first turn and the whole
  standing prompt becomes an append-only change stream
  (`../codex/model-catalog.md`; `../agent-context-file-loading.md` §11).
  Two obligations come with it and are the reason this is *not* a v1
  change, because both are real work rather than plumbing:
  - **A changed section has to revoke its predecessor by name.** The old
    text is still in the transcript. Codex's git-attribution section is
    the honest illustration: flipping the policy renders "Ignore any
    earlier instructions requiring Codex attribution", because
    replacement is not available when nothing is being replaced. Every
    section whose *absence* does not obviously mean the new state needs
    that sentence written for it, and getting one wrong leaves two
    contradictory instructions in context with the stale one earlier and
    therefore cheaper to attend to.
  - **The rendered form needs a recogniser, so a resumed or re-dispatched
    run can find and supersede fragments written by an older format.**
    Codex carries a `with_legacy_matcher` per section for exactly this.
    This design versions its formats in prose today; diff emission turns
    that into a runtime requirement.
  Worth noting what it would buy here specifically, which is *not*
  tokens: this design's conventions blocks are nonce-wrapped and
  byte-identical to disk (`context-files.md` §4), so they are already
  cache-stable within a run. The gain is in the second-order case —
  a resumed run (`formats.md` §5) inherits the suspended run's transcript
  *and* re-renders the envelope, so the corpus currently appears twice.
  That is the concrete defect a diffing assembler would fix, and it is
  also fixable far more cheaply by having resume omit the blocks the
  inherited transcript already carries. Do the cheap fix first; treat the
  general mechanism as gated on a run shape that does not exist yet.
- **A hand-off tier: work the agent must not do even with approval.**
  Every gate in this design is passable — `AskUser` suspends and a human
  answer resumes the run, and the git-write ban (`system-prompts.md`)
  is the one true prohibition, enforced by the absence of the capability
  rather than by a policy tier. Codex's computer-use policy enumerates a
  fourth confirmation mode this collection has no other instance of:
  *hand-off required*, where "the agent must not perform the final action.
  It must ask the user to take over and the user must perform the action"
  — credential entry, bypassing a security interstitial, consequential
  financial actions, and eligibility decisions about other people
  (`../agent-permissions-approval.md` §1b).
  The distinction is worth having and is not the same as "always ask": a
  user who says yes to an always-ask prompt gets the action performed,
  and the point of the category is that they should not. v1 does not need
  it, because v1's tool surface cannot reach any of the enumerated
  classes — no browser, no payments, no credential entry, and `AddComment`
  is the only outbound write. It becomes live the moment the surface
  widens in a direction `medium.md` §2 contemplates, and the cheapest
  place to put it is where the git-write ban already lives: a named class
  the prompt states and the harness makes unreachable, rather than a
  policy the model is trusted to apply.
- **Per-segment evaluation of `Bash` command strings.** `tools.md` treats a
  `Bash` call as one unit for its read-only-git and no-git-write rules.
  Codex splits the command string at shell control operators — pipes,
  `&&`, `||`, `;`, `(...)`, `$(...)` — evaluates each segment
  independently, and then declines to rule-match at all on commands
  containing redirection, substitution, environment assignment or globs,
  "to limit the scope of what an approved rule allows"
  (`../agent-permissions-approval.md` §5). v1's ban is prompt-level and
  its enforcement story is the harness refusing git writes, so the gap is
  narrow today — but it is exactly the gap that widens if the harness ever
  implements the ban as a pattern match, since `git status && git commit`
  and `$(echo git) commit` both defeat a naive one. Record the rule now,
  adopt it with any enforcement layer that matches on command text: match
  per segment, and treat the shell-feature forms as unmatchable rather
  than as matching nothing.
- **Code Mode, as the escape hatch focused tools cannot reach.**
  `tools.md`'s not-configurable list rules out a general `execute(code)`
  on the data surface, for reasons that are about what the harness can
  see before execution rather than about expressiveness
  ([`local.md`](./local.md) §2f). The cases it genuinely cannot express
  are reshaping beyond SQL, joining a query result to a non-tabular
  tool's output, and multi-step orchestration where each step depends on
  the last. **The trigger is the first task where a data run needs two
  tool results combined in a way no selector expresses** — not a
  judgement that programs are nicer than tools. If it lands, two things
  are already decided. The sandbox is the tier-2 shape
  (`../agent-local-compute.md` §4): an opaque-origin iframe with
  `default-src 'none'` in an injected CSP, providers passed as function
  parameters rather than globals so a program cannot enumerate
  `globalThis` for capabilities it was not handed, and a Worker inside
  the frame so a synchronous loop is terminable — Cloudflare's own
  executor documents the gap this last part closes, a timeout that
  "cannot preempt tight synchronous loops". And approval inside a
  program is a solved problem rather than an open one: a durable
  tool-call log plus abort-and-replay, with an explicit `step()`
  side-effect boundary (`../code-mode/cloudflare.md`). That is
  substantial machinery this design does not have, which is the argument
  for the trigger rather than for building it speculatively.
- **A pure-TS engine as the `table://` resolver.** An implementation
  note rather than a design change — the ref contract is already
  substrate-neutral, which is the whole point of `data.md` §2a — but it
  is the concrete thing to build against, and worth recording so the
  interface is not re-derived. `../data-agents/hyperparam/`'s
  `AsyncDataSource`/`ScanOptions`/`ScanResults` is about forty lines of
  type and carries the part most resolver interfaces get wrong: **two
  honest push-down booleans**, `appliedWhere` and `appliedLimitOffset`,
  so a parquet source that pushed projection, a CSV source that pushed
  nothing and a Postgres source that pushed everything all report what
  they actually did through one interface. The engine is pure JS with no
  dependencies and no `eval`/`new Function` (verified, not claimed —
  `../agent-local-compute.md` §3), so model-written SQL never becomes
  JavaScript, and the same code runs server-side behind MCP or in a tab.
- **Running Forge's loop in a browser at all.** Deferred rather than
  rejected. `artifacts.md` §6a already specifies the cache tier, so the
  artifact contract is ready for it; nothing else in this design assumes
  a server — except `Bash`, which assumes a machine, and that is the
  whole of the remaining gap.
- **Non-destructive compaction — summaries as read-time overlays.** This
  design has no compaction, and the note is about what to build if it
  ever does. Cloudflare stores a compaction as a row
  (`from_message_id`, `to_message_id`, `summary`) and applies it when
  *reading* the path, so the original messages survive
  (`../cloudflare-agents/implementation.md` §5). Every compaction
  implementation in `../agent-context-compaction.md` is a destructive
  rewrite of the message list. Overlays buy three things that shape
  cannot: a compaction is reversible, two read policies can disagree
  about the same stored history, and the originals stay available to an
  audit after the model has stopped seeing them — and reversibility is
  nearly free at write time and impossible to retrofit. **Two further
  rules come with it, and they are the non-obvious half.** Compaction
  needs *two* triggers, because a between-turns check cannot save a
  long tool-heavy turn that overflows mid-flight; the in-flight one
  should key on the provider's reported token usage rather than on its
  error strings, falling back to total tokens when input tokens are
  missing — over-approximating, so it compacts slightly early rather
  than missing the threshold. And the two triggers need **separate
  budgets**: a compaction that frees nothing does not fail the turn, so
  a retry budget scoped to failed turns will not bound it, and it
  repeats on every step. The trigger for all of this is acquiring
  compaction at all.
- **An idempotency ledger for consequential tools.** Cloudflare's
  `action()` wraps a tool with the four things a *consequential* call
  needs beyond a schema: idempotency by stable key, approval that is
  inline **or** durable ("even from a dashboard with no live socket"),
  per-turn authorization grants, and delivery metadata recorded
  "without changing what the model sees". The first is the one this
  design will need first. `AddComment` is its only outbound write, and
  `adk.md` §4 already records that a transport-level retry re-executes
  the tool — `tools.md`'s tool-call-id-derived spill filename is the
  half-measure that exists today, and it makes the two mechanisms agree
  without making the write idempotent. Note the ledger is a different
  mechanism from Code Mode's abort-and-replay for the same hazard: at
  the tool level rather than the program level. **Trigger:** a second
  outbound write, or the first duplicate comment observed in production.
- **A stated tool-precedence order.** Cloudflare documents seven tool
  sources and the rule that later overrides earlier, with extension
  tools namespaced and client tools winning — and it is the only source
  in this collection that documents one at all, though Claude Code
  merges built-ins, MCP servers and skills, and OpenClaw merges 159
  plugins. v1 has one source, so there is nothing to order and this
  would be ceremony. **Trigger:** the second source — MCP tools, a
  skill surface, or per-deployment additions. Record now that the
  answer is an explicit order *plus* namespacing for the least trusted
  source, because the alternative is discovering the order from a
  collision in production, and because Cloudflare's own ordering has
  the lesson in it: the one source it namespaces is the one whose
  authors it controls least, and the source that wins outright is the
  one that sends its schemas in the request body.
