# Agent design: a hands-off coding + review agent

A concrete design — not an implementation — for a new agent, synthesized
from the patterns catalogued in the rest of this repo rather than
invented from scratch. This folder is the output of that synthesis: two
system prompts, a lean tool surface, and the wire formats that connect
them, written out in full so they could be implemented against directly
on any model/harness.

Placeholder identity name used throughout: **Forge**. Swap it everywhere
it appears (`system-prompts.md`) before shipping — nothing else depends
on the name.

## Starting brief

The design target, as given:

- No code, language-agnostic — a specification, not an implementation.
- A **leaner initial tool set that can be expanded later**, rather than
  a maximal kitchen-sink surface from day one.
- Sub-agent support from the start, but two different shapes:
  **dynamic** (ad hoc, model-decided) delegation for the coding
  entrypoint, and a **multi-agent** (fixed team) pipeline for review.
- Favour Claude Code's methodology where this repo's research shows it
  converged on something good, but take inspiration from every source
  in the collection rather than cloning one product.
- **Hands-off, not conversational** — this agent runs a task to
  completion unsupervised, closer to this repo's archetype 2
  (benchmark-driven issue-to-patch solver) than archetype 1
  (interactive kitchen-sink pair-programmer) — but with an `AskUser`
  escape hatch for genuine blocking ambiguity.
- First-class Jira and PR integration: a tool to fetch a Jira issue, and
  a single tool that can post a new comment or a threaded reply on
  either a Jira issue or a PR.

## Why archetype 2, not archetype 1, and what that changes

`agent-archetypes.md` draws the sharpest line in this collection between
agents driven turn-by-turn by a human in a chat/IDE loop (archetype 1:
Claude Code, Cursor, Cline, OpenCode, ...) and agents that run one task
to completion with no one watching (archetype 2: SWE-agent, OpenHands,
Augment SWE-bench Agent, ...). Archetype 1's defining traits — a
terseness-under-4-lines mandate, mid-task status-update protocols,
"ask before assuming" as a soft default — exist to serve a human
reading along in real time. None of that applies here: the consumer of
this agent's output is a Jira ticket and a PR, not a chat window. So
Forge inherits archetype 2's shape (little persona chatter, a
fixed explore → implement → verify → report loop, a single unambiguous
completion signal) and grafts on exactly one archetype-1-style
interaction primitive — `AskUser` — as the deliberate exception, not the
default.

That has a real consequence for tool design (see `formats.md`'s AskUser
section): a chat-facing `AskUser` blocks in place and waits for the next
human turn. A hands-off agent has no "next human turn" to wait for in the
same process — so `AskUser` here **suspends the run and exits**, posting
its question through the same `AddComment` tool used for everything
else, and the task resumes later (webhook or poll, same pattern this
session itself uses for `subscribe_pr_activity`) when a reply lands.

## Two entrypoints, one core

```
                    ┌─────────────────────────┐
                    │   Shared core tool set   │
                    │  Read · Edit · Write     │
                    │  Bash · Grep · List      │
                    │  Task · AskUser          │
                    │  FetchJira · AddComment  │
                    │  InspectImage            │
                    │  Complete                │
                    └────────────┬─────────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              │                                      │
     ┌────────▼─────────┐                 ┌──────────▼──────────┐
     │   Coding agent    │                 │    Review agent      │
     │  (archetype 2)     │                 │  (archetype 4/5)     │
     │                    │                 │                      │
     │ Jira ticket in →   │                 │  PR diff in →        │
     │ implement, verify, │                 │  fixed team of       │
     │ leave branch ready │                 │  specialist +        │
     │                    │                 │  validator sub-agents│
     │ Task→general-purpose│                │  Task→reviewer,      │
     │ for open-ended      │                │  Task→validator      │
     │ search/investigation│                │                      │
     └────────────────────┘                 └──────────────────────┘
        2 modes: plan · implement
```

Both entrypoints are the *same* model running under a different system
prompt (`system-prompts.md`), sharing the identical tool schemas
(`tools.md`). The difference is orchestration philosophy, matching the
brief's "dynamic for coding, multi-agent for review":

- **Coding mode is one system prompt covering two `mode` values**, not
  two agents: `plan` (read-only — investigate, then `AskUser`, a
  structured plan for a later run, or a terminal "no code change
  needed" finding when the investigation itself is the whole task) and
  `implement` (the default — edit and verify). There is no separate
  read-only "investigate" mode: a standalone research task is just a
  `plan` run that concludes with an empty step list instead of a
  forward-looking plan — see `formats.md` §3c. `plan` and `implement`
  are two separate *runs*, not two phases of one run — see `formats.md`
  §6 for exactly how a plan produced by one run reaches the next.

- **Coding mode** delegates the way Claude Code's `Task` tool does:
  ad hoc, model-decided, stateless one-shot calls to a single
  `general-purpose` sub-agent type, used only when the orchestrator
  judges a sub-task will burn a lot of exploratory context it doesn't
  need to keep (`agent-subagent-architectures.md` §1's "context-window
  conservation" framing — Claude Code, OpenCode, and Amp all state this
  as the reason, near-verbatim, and it's the framing Forge's coding-mode
  prompt uses too).
- **Review mode** does not leave delegation to model judgment at all —
  it always fans out to a fixed team, mirroring Anthropic's own
  `/code-review` skill (`skills/anthropic/code-review/commands/code-review.md`):
  parallel specialist finders, then a second, independent validator pass
  per candidate finding before anything is posted. `code-review-approaches.md`
  §5-6 catalogues why this matters more here than in an interactive
  tool: with no human pre-filtering before comments go live, the
  validation pass is the only thing standing between a specialist's
  hallucinated finding and a real PR comment.

## Design decisions and why

Resolved through discussion before any prompt text was drafted — see the
chat transcript for the reasoning; this is the settled position each
subsequent doc assumes.

| Decision | Chosen | Rejected alternative(s) | Rationale |
|---|---|---|---|
| PR platform coverage | Bitbucket as the primary PR platform, GitHub as a peer — one `AddComment` tool with a three-value `platform` enum (`jira`/`bitbucket_pr`/`github_pr`), one platform-neutral review envelope with a `Platform:` field | GitHub-only v1 (the original draft); separate per-platform comment tools | The deploying stack is Atlassian (Jira + Bitbucket), so a GitHub-only enum baked the wrong default into the schemas. The structure was already right — the brief's one-tool-for-all-platforms rule meant this shift changed enum values and prose, not architecture. Platform capability gaps (suggestion-block support varies by deployment; threading is native on Bitbucket, review-thread-scoped on GitHub; GitHub's pending-review batching has no Bitbucket equivalent) are handled harness-side with visible degradation in the tool result — the same pattern as anchor validation, so Forge's prompts never branch per platform |
| Edit/diff wire format | `old_string`/`new_string`, must uniquely match | Aider/Cline `SEARCH/REPLACE` fences, `apply_patch`-style patches, whole-file rewrite | `coding-agent-approaches.md` §5: the only format that needs no worked-example teaching block in the prompt itself, and it's the one Claude Code, Gemini CLI, and (per its README) OpenHands converge on independently |
| Coding-mode delegation | Ad hoc `Task` tool, stateless one-shot, single `general-purpose` type at launch | A typed registry from day one; an addressable/resumable child (Codex CLI/OpenCode-style) | Matches "leaner initial tool set" — a typed registry and resumable children are real, well-precedented upgrades (`agent-subagent-architectures.md` §2) but not needed until coding-mode tasks get complex enough to want them |
| Review-mode delegation | Two harness-selected run shapes sharing every wire format, the shared reviewer core, and the validator pass: **multi-stage** (fixed parallel specialist team — the reference and default) and **single-stage** (one broad-lens finder context running the identical dedup → validate → deliver tail; `review.md` §6, `system-prompts.md` §2b). Validation is unconditional in both | Multi-only always (the earlier draft); single-pass with no validation (PR-Agent, Codex-review's approach); user-chosen sequential/parallel (`pr-review-toolkit`'s approach) | Hands-off delivery raises the cost of a false positive (no human filters before posting) enough to justify the second pass unconditionally — but that argument binds to the *validator*, not the fan-out: a single finder plus independent validation keeps the two-opinion guarantee at a fraction of the cost on the small PRs that dominate real queues. The shared core and identical formats make the shape a per-run harness flag, not two products; fan-out still earns its cost on large diffs (lens focus, parallelism, later per-role models) |
| Task completion signal | Structured schema **and** a human-readable summary field inside it | Freeform chat-style final message only (Claude Code); a bare machine schema with no prose (Codex-review's JSON-schema output) | Consumers are mixed: CI/Jira automation need the schema, but the summary field exists for whatever the harness renders into a PR or Jira comment for a person to read — Forge doesn't post that itself |
| Comment body format | `AddComment.body` is always plain Markdown, regardless of target platform | Platform-native formats from Forge itself (Jira Cloud's ADF, wiki markup) | The schema stays platform-agnostic; converting Markdown to whatever a specific tracker actually requires is harness-side plumbing, not something Forge's prompts or schemas should encode — same reasoning as keeping git writes out of the agent's tool surface |
| `AskUser` semantics | Suspend the run, post the question via `AddComment`, resume on reply | Synchronous in-process blocking prompt | Hands-off has no human watching the process to answer synchronously; the suspend/resume shape also reuses `AddComment` instead of adding a second communication channel |
| `AddComment` in `implement` runs | Not wired at all — plan-mode coding runs and review runs only | Wired with usage guidance (an earlier revision); wired with no guidance (the original draft) | No `implement` workflow step posts anything — the Complete report is that mode's only outward channel, with `judgment_calls`/`summary` carrying what a ticket note would have said and the harness deciding what reaches the ticket. A wired-but-unused tool on an unsupervised path is the same injection surface that keeps `AskUser` out of review mode, so the structural-gates principle applies. `AskUser`'s suspension posting is unaffected (harness-side, `formats.md` §5). Tracked upgrades: `medium.md`'s PR-comment-responder runs wire it for threaded replies in that one task source; a general implementation-decision-notes channel stays in `future.md` |
| Diff delivery to the review agent | Pre-formatted plain unified diff, baked into the task envelope | Custom hunk format (PR-Agent's `__new hunk__`/`__old hunk__`); leave it to the model to run `git diff`/`gh` itself (most Claude Code skills) | `code-review-approaches.md` §3's takeaway: pre-formatting trades a little build complexity for guaranteed line-number accuracy, which matters when comments post unsupervised. Plain unified diff (Codex-review's choice) rather than PR-Agent's custom hunks, to keep the format lean |
| Git write operations | None in v1 — no commit, push, branch, or PR creation from inside the agent; enforced by a harness-side blocklist on git write subcommands in `Bash`, not prompt text alone | Claude Code's interactive convention (commit/push once explicitly asked in the current turn); the coding agent's originally-designed default of committing/pushing/opening a PR itself under `mode: implement`; prompt-only enforcement (an earlier draft) | The harness checks out the task's target branch *before* the run starts; the agent edits files in that working tree and stops. A finished, uncommitted working tree **is** the deliverable — an external process (whatever invoked the run, which already owns git identity, signing, and PR-creation conventions) picks it up from there. Keeps git write concerns, and everything that comes with them (author identity, signing keys, commit-message conventions, PR templates), entirely outside the agent's tool surface in v1. The blocklist upgrade over prompt-only: Augment SWE-bench Agent's `banned_command_strs` substring check is the only code-level git restriction in the collection (`agent-git-vcs.md` §2) and shows the structural version of this specific rule costs a few lines, not a permission engine — so the design's own structural-gates principle applies here too |
| Live todo/planning tool | None in v1 | A `TodoWrite`-style stateful tool (near-universal in archetype 1, `coding-agent-approaches.md` §6) | No one is watching a live todo list update turn by turn; step tracking is folded into the `Complete` report's step list instead. Not the same question as the row below — this is about a tool for tracking progress *during* a single run, which Forge still doesn't have |
| Plan mode | A second `mode` value (`plan`) on the *same* coding system prompt — read-only investigation ending in `AskUser`, a structured plan (`formats.md` §3c), or a terminal no-action finding (empty `steps`), consumed by a later `implement` run via a `<plan>` envelope tag when a plan was produced | A separate third system prompt/entrypoint; a model-side heuristic deciding when to plan first (Codex CLI's "skip planning for the easiest 25%"); a live in-run planning tool (conflated with the row above, but genuinely different — see `formats.md` §6); a third, separate read-only `investigate` mode for standalone research tasks | Reuses one read-only tool scope instead of standing up new machinery — the closest precedent is Gemini CLI's Plan Mode and OpenCode's `plan.txt`/`build-switch.txt`, both mode-variants of one base agent rather than separate agents. No source in the collection treats "investigate, don't even plan" as its own peer top-level mode: OpenCode's closest analog, `explore`, is a subordinate sub-agent type its `build`/`plan` orchestrator delegates to, not a mode a dispatcher picks directly (`agent-permissions-approval.md` §1); Factory/Droid's leaked prompt collapses diagnosis and planning into one binary Diagnostic/Implementation split with no separate plan-artifact step at all. Folding standalone investigation into `plan`'s own possible outcomes matches that shape more closely than keeping a third mode did. Mode selection (plan-first vs. straight to `implement`) is made by whatever invokes a run, not by Forge itself |
| Plan → implement gating policy | Deliberately unspecified in Forge's own prompt (`formats.md` §6) | A built-in human-approval gate, reusing `AskUser`'s suspend/resume mechanism for "approve this plan?"; unconditional auto-chaining straight into `implement` | Asked directly rather than assumed. Forge's contract is identical either way — post the plan, call `Complete(status: "planned")` — so the choice of whether an `implement` run fires immediately or waits for a reply is a deployment-time policy the harness owns, not a behavior difference in the agent |
| Sub-agent tool-scope narrowing | `reviewer` and `validator` sub-agent types get `Read`/`Grep`/`List` only — no `Edit`/`Write`, and no `Bash` at all | Full tool parity for every sub-agent type (Claude Code's `general-purpose: Tools: *`); read-only-git `Bash` for review sub-agents (agent37/TuringMind's allowlist shape) | Matches the narrower-scope pattern `agent-subagent-architectures.md` §6 finds in Claude Code's own `statusline-setup`/`output-style-setup` types and in Amp's `oracle` — a reviewing sub-agent has no legitimate reason to touch files. Read-only-git `Bash` was rejected too, not just writes: v1 has no command-level `Bash` filter, so "read-only git only" would be prompt-enforced where the design's own principle is structural gates for anything that can write; agent37/TuringMind's allowlists lean on Claude Code's permission engine, which Forge doesn't have in v1. The cost — a validator can't `git show` the base version when judging whether an issue is pre-existing — is mitigated by the `-U5` diff context plus the head-SHA working tree, and named in `medium.md` as the escalation trigger for adding a filtered `Bash` |
| Review dedup identity | Author-agnostic — compare candidate findings against every existing comment in `<existing_comments>` regardless of who posted it; no skip gate on "have I reviewed this commit before" at all | A hard skip in step 1 keyed to a specific agent identity (would require a new `{{AGENT_USERNAME}}` env field, and only catches Forge's own prior comments, not a human's or another bot's) | An identity-keyed check is both fragile (the platform-visible username and the internal placeholder name can drift apart) and too narrow (it only prevents Forge repeating itself, not repeating anyone). Dropping the skip gate also means re-reviews are always allowed to run — a new push can have new issues even on a PR already reviewed once — with the pipeline's dedup step doing the actual noise-prevention work instead of a run-level gate |
| Read-only mode enforcement | Structural: the harness doesn't wire `Edit`/`Write` at all in `plan` runs, for the orchestrator or its `general-purpose` delegates; prompt rules remain as a second layer | Prompt-only enforcement (the original draft: tools wired in every mode, "never call them" as instruction) | Same argument as the scratch-directory row: a structural boundary can't be forgotten. Gemini CLI strips agent-kind tools in code; Composio scopes per role at the tool level (`agent-subagent-architectures.md` §6); `agent-permissions-approval.md`'s core finding is that serious sources layer prompts *on top of* structural gates, never instead |
| `review_only`/`investigate` modes | Both folded into `plan` — no separate mode value for either; a standalone research task is a `plan` run that ends with an empty `steps` list instead of a forward-looking plan | Two distinct modes, `review_only` defined as "treat the same as `investigate`" and `investigate` as its own read-only peer of `plan` | `review_only` and `investigate` had identical authorization and differed only in framing; folding one into the other (an earlier step) still left a mode defined almost entirely by "same as `plan`, minus the plan artifact." No source in the collection gives standalone investigation its own peer top-level mode (see the Plan mode row above) — collapsing to two mode values total (`plan`/`implement`) matches the field's actual binary shape and removes a mode that was pulling less weight than its own upkeep cost across `system-prompts.md`/`tools.md`/`formats.md` |
| Large-diff policy | Skip-with-reason above a harness-configurable size threshold (fixed changed-line count, or a char-count-estimated fraction of the model's token budget adjusted for specialist fan-out) | Sharding — split specialists per file group, merge findings afterward | Rejected, not deferred: no source in the collection does automated sharding-with-merge, including Anthropic's own `/code-review` skill (its troubleshooting doc's answer to large PRs is "consider splitting large PRs into smaller ones," a PR-author step taken *before* review, not a harness mechanism). BMAD's chunking is human-mediated across separate runs — a person decides the group boundaries and reconciles follow-ups — which doesn't transfer to an unsupervised pipeline with no one present to arbitrate a cross-file finding split across batches |
| Completion integrity | Two deterministic gates: first `Complete(done)` in `implement` returns a fixed checklist instead of completing (second call goes through), and the harness cross-checks the report against real `git status` after the run | Trusting the self-report (original draft); a separate LLM verification judge (Claude Code's internal adversarial verifier) | False completion claims are the best-measured failure mode in the research (`agent-self-verification.md` §7: a leaked 29-30% false-claim rate drove dedicated internal tooling); mechanical gates "can't be talked out of firing" and cost no extra model call, where an LLM judge is a real subsystem (v2 at earliest) |
| Run bounding | Harness turn budget + context high-water mark; crossing either injects a final-turn nudge that permits only `AskUser` or `Complete`; no compaction in v1 (`formats.md` §7) | Unbounded runs (original draft — silent death on context exhaustion); a full compaction subsystem from day one | "Always end via Complete" is unenforceable without a guaranteed last turn (Copilot Chat's forced last-turn cutoff is the precedent); compaction is a deep subsystem (`agent-context-compaction.md`) that leanness says to defer, but *saying so* beats leaving the ceiling unhandled |
| Comment anchoring | Anchors are new-file line ranges (`line`/`line_end`); harness validates an anchor is commentable and degrades to a `file:line`-prefixed general comment, visibly, when it isn't | Single-line anchors with no side convention and no validation (original draft); PR-Agent-style per-hunk line-number injection from day one | The decision log's own rationale for pre-baking the diff was line-number accuracy — anchor validation is the cheap backstop that makes a mis-derived number degrade visibly instead of silently; hunk-injection remains the documented upgrade if mis-anchoring shows up in practice |
| Review diff base & construction | Merge-base three-dot diff (`base_sha` = merge-base), `-U5 -M`, harness-built, with visible elision markers for generated/binary/oversized files (`review.md` §2) | Two-dot diff against the base branch tip; letting the model run `git diff` itself; silent omission of oversized files | A two-dot diff charges the PR with unrelated base-branch drift — every source that states its base is on the merge-base side (Gemini's `--merge-base`, Devin, the leaked Claude Code review skill's explicit three-dot). Rename detection stops a moved file reading as hundreds of new lines. Elisions are visible in both `<diff>` and `<changed_files>` so absence is never misread as "unchanged" — same degrade-visibly contract as anchor validation |
| Specialist/validator brief context | Briefs assembled by verbatim transclusion of envelope blocks — including `<existing_comments>` as intent context, under explicit discussion rules (threads are never verdicts nor a skip list; dedup stays orchestrator-side; contradicting an explicit human decision demands a concrete defect and must engage the thread); specialists never see each other's output; the validator never sees the specialist's transcript (`review.md` §4–5) | Paraphrased/summarized diffs per specialist; comment-blind specialists and validators (an earlier draft, on an injection-surface argument); comment-aware finders that self-dedup | A paraphrased diff re-introduces the line-number laundering the pre-baked diff exists to prevent. Comment-blindness causes a concrete collaborative failure: a finder that can't see "please change X to Y" flags Y and proposes the revert, arguing with a human decision under the very thread that made it — and no other stage catches it, because dedup drops duplicates, not contradictions. The injection exposure is bounded (code-level sanitizer, data-not-instruction rule, code-verified findings, authenticated colleagues on the primary internal deployment). Self-dedup stays rejected so candidates are raised then visibly dropped, never silently unraised; validator independence (re-derive from code, not the finder's argument) is what makes confirmation worth anything |
| Repeat reviews | V1 stateless (full review + dedup against open threads); phase 2 adds stateful sessions — `<review_state>`, an interdiff with `<scope>`-restricted finders, thread reconciliation with reply+resolve, and a hard one-round cap on standing-firm replies (`review.md` §7, `medium.md` §3f) — all as additive tags/fields on unchanged v1 shapes. Threads anchored to an earlier head carry their staleness structurally: `at_sha` in v1, then/now diff blocks plus a conditional format note in phase 2 (`review.md` §3a–3b) | Stateful from day one; always-stateless forever; unbounded back-and-forth on disputed threads; a third `outdated` status value conflating "code moved" with "conversation over" (an earlier draft — wrong exactly when an author pushes a fix and awaits the reviewer) | The v1 floor is already correct (never spams), so state is an upgrade not a fix; additive-only evolution keeps the wire format stable from launch, which is the property hardest to retrofit; the one-round cap exists because a bot that argues in rounds burns the trust the validator pass protects |
| Reproduction/throwaway files | A dedicated scratch directory outside the git working tree (`{{SCRATCH_DIR}}`, named in `<env>`), never cleaned up because it's never inside git state to begin with | Instructing the agent to delete temp files before calling `Complete`; a `.gitignore` convention for a fixed reproduction-file naming pattern | A cleanup instruction depends on the model remembering a step at the very end of a long run — one missed case and a `reproduce.py` rides along into whatever the external process commits. `.gitignore` is better but still depends on it being correctly configured and not overridden by something like `git add -A -f`. A structural directory boundary can't be forgotten or misconfigured; step 5 of the coding workflow also adds a final `git status` sanity check as a second line of defense regardless |

| Tool result format | Prose payloads (file contents, diffs, matches, command output) as raw text; fact payloads (exit codes, counts, truncation state, ids) as named fields; XML-style tags only to delimit untrusted or heterogeneous content | All-JSON results (MCP's `structuredContent` shape applied to everything); all-XML framing (Windsurf/OpenCode's tag style applied to every result); leaving it unspecified per tool (the original draft) | `agent-tool-implementations.md` §5: every source read as code returns file bodies as raw text even when a typed object exists one layer up, because JSON-escaping code inflates tokens and breaks the byte-exact match `Edit` depends on — while the two harnesses that *did* add structured results added them for shells specifically (Codex's `exec_command` output schema, Goose's split stdout/stderr), the one place the model demonstrably confuses "the command printed to stderr" with "the harness failed". Anthropic's own guidance declines to pick a global winner ("no one-size-fits-all"), which is an argument for deciding per payload shape rather than per product |
| Tool granularity rule | Split a primitive when the split changes a *harness* answer — permission class, destructiveness, concurrency safety, result shape; otherwise keep one tool with a discriminator | Per-verb tools (Manus's 29, Crush's eight `lsp_*`); maximal consolidation (Goose's five tools with no read/grep at all, Codex's shell-plus-`apply_patch`) | The rule is descriptive before it's normative: it predicts most of the field, including the cases where a single product goes both ways (Claude Code splits `Read`/`Edit`/`Write` but keeps twelve ripgrep flags inside one `Grep`; OpenCode keeps nine LSP operations in one tool but `read` and `write` apart). It also explains the shell as the deliberate exception — `Bash` is unclassifiable by construction, which is exactly why it carries six figures of classifier code in Claude Code's tree. Anthropic's "consolidate around workflows" guidance is not in tension: it addresses domain/API tools, not the primitives an agent composes for itself |
| Read/Edit line-number contract | `cat -n` (number + tab + exact bytes) on Read, with both tools' descriptions stating that `old_string` matches the bytes *after* the tab | No line numbers (simplest, and removes the failure mode entirely); numbers only on ranged reads | Unanimous across every source read as code, and the failure mode it creates is cheaper than what it buys: line numbers are how the model cites locations, pages through a file, and anchors review findings. Claude Code and Zed both carry explicit code comments tying the read format to the edit tool's matching rule — treating them as one contract, which is why this design states it in both descriptions rather than one |
| Caps vs errors on oversized reads | Cap by default with a self-describing footer; error when the call *explicitly* asks for more than a cap allows | Always truncate (never error); always error (never cap) | Measured, not argued: Claude Code tested truncating instead of throwing for explicit over-limit reads (`FileReadTool/limits.ts`, experiment #21841) and reverted — tool-error rate fell but mean tokens rose, because the error result costs ~100 bytes and the truncated one costs a full page the model didn't ask for. The footer requirement is the other half: three independent implementations (Gemini CLI's `Action:` block, OpenCode's `Use offset=N to continue`, Claude Code's pagination note) converge on stating the exact next call, and a cap without one is what turns into a retry loop |
| Input validation strictness | Strict advertised schema, tolerant parser (coerce stringified numbers, accept obvious path-field aliases, clamp out-of-range line numbers, normalise a bare string where an object was expected) | Strict both ways (the original draft — `additionalProperties: false` and reject anything that doesn't match) | A rejected call costs a full turn and teaches the model nothing; a normalised one costs nothing. Cline's SDK is the strongest precedent — a 13-branch union behind a single advertised `read_files` shape, with the code comment "the advertised JSON Schema is unaffected" — and Zed clamps `start_line: 0` to 1 with a comment noting models do it "despite instructions". OpenCode's reverse migration (removing coercion once the tool was LLM-only) is the reminder that this is an empirical, per-model call rather than a law |
| Read-before-edit | Harness-side state: `Edit`/`Write` fail on a path this run hasn't `Read`, with the cache recording *what was seen* (bytes, `(mtime, size)`, partial-view flag) rather than a boolean — so `Edit` accepts a partial view (its byte-exact match anchors the change) while `Write` requires a full one | Prompt-only instruction (the original draft); a boolean "was this path read" gate for both tools (the earlier version of this row) | Same structural-gates argument as the git-write blocklist, and it's enforced in code in the one product that documents it. The boolean version had a real hole: a model could read 50 lines of a 2,000-line file and then `Write` it wholesale, destroying 1,950 lines it never saw. Byte equality against disk — not the partial flag — is what the gate tests, which also keeps a clamped-but-complete read from being refused (`agent-tool-implementations.md` §8b, a deadlock reported from production in a harness with this design's exact clamp/gate/dedup combination). Unchanged-file read dedup — a stub instead of re-sent content — is built on the same cache and is the largest token saving available for its build cost, but it turns on invalidation this design can't yet get right (v1 can't see what `Bash` did to the tree, and a stale "still current" claim is a correctness bug, not a performance one), so it's deferred to `medium.md` §2g rather than shipped |
| `List` replacing `Glob` | One read-only path tool: glob matching, directory listing and a line-counted tree, selected by an `output` mode; no separate `Glob`/`LS` | A `Glob` plus a separate `LS` (the older leaked Claude Code surface); `Glob` plus `Bash ls` (Claude Code's current shape); folding directory listing into `Read` (OpenCode's shape, and this pass's first suggestion) | All three operations are read-only, concurrency-safe, non-destructive and return the same thing — a set of paths — so by this design's own splitting rule they differ only in rendering, which is a parameter. `Bash ls` was the weakest option here specifically: review sub-agents have no `Bash` at all, so listing would have been unavailable exactly where orientation matters. Folding listing into `Read` works but wastes the chance to have a real orientation view; the line-counted tree is what Goose keeps when it cuts its entire developer surface to five tools, and the counts feed the whole-file-vs-range decision `Read` asks the model to make. `Glob` survives as a harness-side alias, since models trained around other harnesses reach for it by name |
| Batch `Read` with per-file ranges | `files: [{path, start_line?, end_line?}]` — several files per call, each with its own optional inclusive line range | Single-path `Read` with `offset`/`limit` (the original draft, Claude Code's shape), relying on parallel tool calls for batching; a glob-driven bulk reader (Gemini CLI's `read_many_files`) | Turn count *is* this design's run budget (`formats.md` §7), so collapsing five reads into one call buys headroom under the same ceiling — a stronger argument here than in an interactive agent, where parallel tool calls already cover most of it. `start_line`/`end_line` over `offset`/`limit` because every line number the model has came from a `cat -n` read, a Grep hit, a diff hunk or a review finding, and ranges need no arithmetic to build from those; `offset`/`limit` is accepted and normalised. Cline's SDK is the precedent, including the failure mode its schema text warns about — models put the range in a separate array element instead of on the path's object — which is why that warning is carried verbatim into the description. The cost is a result format with per-file blocks and per-file errors, and an overall size budget across entries; a bad entry reports inline instead of failing the call. **A later pass surfaced a real counter-argument** (`agent-tool-implementations.md` §3g): an array of objects is the one parameter shape that forces the model to emit escaped JSON inside the tool-call channel, where a scalar parameter is delimiter-matched and cannot fail to parse — so this shape trades parse reliability for turn count, and the field's one published experiment on it puts nested-argument designs at the bottom. OMP takes the opposite route, a single `path` string carrying a selector grammar (`src/a.ts:50-200`, `:5-16,960-973`), which is flat but single-file. The decision stands for v1 on the grounds that turns are this design's actual budget (`formats.md` §7) and the tolerant parser already accepts the flat spellings, but it is now a *measured* trade rather than a free win, and `future.md` records what would change it |
| Build substrate (Java ADK, tools over MCP) | Keep the design substrate-neutral; record fit, compromises and workarounds separately in `adk.md` | Folding substrate constraints into the tool spec itself (an earlier revision put an MCP/ADK section inside `tools.md`) | The design should describe the agent we want, not the agent a particular framework version makes easy — otherwise a framework fix leaves a permanently weakened spec behind, and the compromises stop being visible as compromises. Keeping them in one document also makes them re-checkable on an ADK upgrade, which matters more than usual here: Java and Python ADK already differ in how they convert MCP results, so the constraints are version- and language-specific rather than protocol-level |
| Tool limits: configurable or fixed | Every numeric limit is a config value with an opinionated default, resolved built-in → model-family → deployment → per-run, and rendered into the tool descriptions it appears in; formats, contracts and invariants are not configurable at all | Hardcoded constants (what the design had, with numbers restated in prose that could drift); a fully configurable tool layer including result shapes | Numbers are facts the model is told at the moment they matter, so they can vary per deployment and per run; formats are contracts it relies on across a whole run, so a deployment able to flip them would produce combinations nobody tested — the `cat -n` prefix is the sharpest case, since `Edit`'s matching rule is written against it. Rendering descriptions from the same constants the code enforces is Crush's shape (`view.md.tpl` interpolates its own limits) and Claude Code's (`renderPromptTemplate` over resolved limits), and it removes the drift the earlier draft's restated numbers invited. Defaults are stated rather than left to the deployment because "make it configurable" isn't a decision: where the field converged the convergent number wins (2000 lines, 2000-char lines, 250 grep results), and where it didn't the choice is argued in the table. The per-run layer deliberately doesn't reach the envelope — the model learns limits from its descriptions and from cap footers, never from a config block it could reason about |
| Tolerant parsing, structurally | Strict advertised schema; tolerance in three declared layers (generic normalisations applied to every tool, a short per-tool table of accepted alternate forms, range clamping), with every normalisation counted as telemetry | Ad-hoc rescue code inside each tool; JSON Schema as the sole enforcement (the position this design started from) | Enumerable beats scattered: the per-tool alternates are data, so they can be tested, listed in the design, and deleted when telemetry shows they never fire. Two guardrails keep it from becoming a pile of hidden formats — normalise only when the transform is information-preserving and unambiguous (an unrecognised key that might carry real intent is an error naming the key, not a silent drop), and treat every fired alternate as evidence the description or schema is wrong for this model. Both directions are observed in the field: Cline's SDK accepts thirteen shapes behind one advertised schema; OpenCode deleted its coercion once the tool became LLM-only. Normalisation applies to observer/permission copies only, never to the API-bound input, which is Claude Code's `backfillObservableInput` rule and preserves prompt caching |
| Cross-run memory: who writes it | A separate **learnings run** (`medium.md` §6) — a fourth entrypoint, triggered by PR outcome, that reads a terminal PR the same way a review run reads an open one and records what the next run should know | An inline memory tool on working runs (Windsurf's `create_memory`, Cursor's `update_memory`, Augment's `remember`); mining transcripts at run completion; no cross-run memory at all (v1's position) | Windsurf's eager in-flight writing is the worst fit available here: its stated safety net is "memories are presented to the USER, who can reject them," and a hands-off agent has no user watching. Deferring to PR outcome buys the signal that makes memory worth having — `agent-memory-learning.md` §8's finding that review bots learn from a better signal (human reaction to a posted comment) than coding agents do (self-assessment). It also collapses what looked like two mechanisms into one: a coding run's output becomes a PR and gets reviewed, so both entrypoints reach the same terminal state carrying the same artifacts. Four independent teams (Codex CLI, Gemini CLI, Copilot CLI, Antigravity) built background consolidators over *finished* work; none writes durable memory from inside a live run |
| Learnings-run substrate | No workspace, no filesystem, no file writes — code access via ref-pinned `SearchSource`/`ReadSource` (`medium.md` §2e), memory writes via one schema-validated `CreateMemory` tool, provenance stamped harness-side | Writing memory as markdown files under a harness-confined write root (Gemini CLI's patch-into-`.inbox` model, the earlier draft here); storing memory in a git repo the agent manipulates (Codex CLI's model) | A writer with file tools needs a whole validation layer — path resolution under an allowed root, patch validation, silent discard of escapes — that exists *only because* it has file tools. Removing the filesystem removes the layer: confinement stops being enforced and becomes structurally true. It also makes provenance and evidence enforceable by schema rather than by prompt, which matters because the run's own correctness discipline depends on them. Codex's git store was rejected specifically: git there is a diff engine feeding a batch consolidator over many rollouts, solving churn we don't have, and it would smuggle git write concerns back into an agent surface the design deliberately keeps them out of. No vector store either — `agent-memory-learning.md` §4 finds no first-party implementation retrieves memory by embedding similarity, and grep over a model-written index keeps the store auditable |
| Learnings-run read path | A capped, flat `<learnings>` envelope tag on coding and review runs; no detail tier, no read tool, and nothing injected at all when the store is empty | Index-plus-detail with topic files materialized into the run's workspace (the earlier draft — broken by workspaces being optional); a dedicated memory read/search tool | Progressive disclosure solves a size problem that doesn't exist yet — Codex ranks to a bounded top-N, Gemini CLI targets 0–5 new entries per run, one repo's memory fits a capped block for a long time. Both alternatives commit to machinery now; not building the middle step leaves the better end state available, since detail can later be served through the same ref-pinned read family rather than a new tool. The cap is harness-enforced with an error rather than a nudge (Claude Code's model: "everything past the limit is dropped on the next load"), and the empty-store case injects nothing so a cold repo never pays tokens for a capability with no content behind it (Codex's read-path builder returns nothing at all on an empty summary) |
| Run narrative | A `Narrate` tool (`medium.md` §2f) the orchestrator calls a handful of times per run — `phase`/`summary`/`kind`, where `kind: "detour"` marks an approach change — persisted by the harness as a durable artifact serving both a watching human and §6's learnings runs | Mining the raw transcript for the same information after the fact (§6's original position); per-tool-call narration (Windsurf's `toolSummary`); no narrative at all, relying on the `Complete` report alone | The report says what happened; nothing said *why the approach changed*, and that is precisely what a retrospective needs and what a post-hoc reader can least reliably reconstruct — `agent-memory-learning.md` §7 shows Codex spending most of a 569-line prompt inferring exactly this from raw rollouts. Capturing it first-hand at the moment of the pivot is nearly free by comparison. Two independent precedents converge on the same trigger (`agent-turn-output.md` §3a): Gemini CLI's `update_topic` fires on "an unexpected event... that requires a strategic detour," and Codex's `update_plan` requires "an `explanation` of the rationale" whenever the plan changes mid-task. Rate is the failure mode, not volume — both throttle explicitly, and Antigravity supplies the drafting rule ("synthesize a narrative, don't copy checklist items verbatim"). It also fills a real gap on the unsupervised path: an `implement` run currently has no outward channel at all until it completes |
| What a learning may do to a finding | Inform only — learnings reach the orchestrator and the finders as context, never the validator, and never suppress a finding | Greptile-style suppression of comment classes the team keeps ignoring; feeding learnings to the validator as additional evidence | Validator independence is the load-bearing property of the whole review pipeline (`review.md` §5: re-derive from code, not from the finder's argument), and a learning is exactly the kind of prior argument it must stay independent of — so a learning can change what gets *raised*, and only code decides what gets *confirmed*. On suppression: it is the most valuable thing in the review-bot research and the most dangerous thing to adopt early, and Greptile itself hardcodes an exemption so security findings are never suppressed. Revisit once §3e outcome data exists — tracked in `future.md` as the one genuinely open question left from this pass |
| Where cross-run learnings live | A **learned tier of the context service**, which is the code/git/artifact proxy — learnings keyed by ref alongside the code they are about, `binding: "default"` always, arriving in the ordinary resolution (`memory.md` §2) | A dedicated memory store with its own read path and a `<learnings>` envelope tag (`medium.md` §6d, superseded); the harness merging a learned block into a resolution it did not produce | The service already reduces every tier to `(source repo, ref)` and resolves refs across every repository *and* Artifactory, so it is the only component that can answer "what is this fact about, and is that thing present in this run" — which is what makes dependency-scoped learnings possible at all, an axis `../agent-memory-learning.md` §1 finds in no source in the field. Reusing the section contract also collapses four things `medium.md` §6 had to specify separately: the cap is the existing budget, provenance is the existing path+revision rule, "which learning applied" is answered by the existing run record, and **informs-never-vetoes becomes a `binding` value the precedence machinery enforces** rather than a rule the orchestrator must honour. The cost is named rather than dodged (`memory.md` §2c): a resolution stops being a pure function of `(repo, ref, team)`, so the learned tier needs its own version, run-record entry and cache-key component. Harness-side merging was rejected for putting assembly in two places and giving the learned tier none of those properties |
| When a learning is captured | **Capture in session** (`Retrospect`, before `Complete`), **promote on outcome** (the learnings run) — candidates carry `confidence`, the promoter decides (`memory.md` §3) | Extraction from artifacts in the learnings run alone (`medium.md` §6, superseded); a field on `Complete`; a lighter model over the transcript as the primary path | The run that did the work is the best **witness** and the worst **judge**: it knows why the approach changed and cannot know whether the change was right, and at end-of-run the PR outcome does not exist yet. Both mature implementations split the same way for the same reason (Codex Phase 1 records evidence, Phase 2 decides whether repeated signals amount to a preference); Codex also labels an outcome `uncertain` when "only the assistant claims success without validation". Folding it into `Complete` was checked against the collection and has **no precedent** — Trae's `finish` takes one `summary`, Jules's `submit` takes branch/commit/title/description, and Jules is the one product with both capabilities, in two separate tools. The transcript pass survives as the fallback for runs that captured nothing (human-authored PRs), which is also where the cost is |
| Findings the agent cannot act on | A separate `ReportProblem` channel with a `note`/`impairment`/`blocker` priority, addressed to a human maintainer, never retrieved by a future run; `blocker` is terminal and suspends the task on a wake predicate (`memory.md` §6) | Storing them as memories; leaving them in `Complete`'s report; using `AskUser` | A store whose entries no future run can act on is where memory systems go to die, and "the `edit` tool mangles CRLF" is exactly that shape. Sorting by **addressee** separates them: a learning is what a future run should do differently, a request is what somebody else should fix. Devin's `report_environment_issue` is the only first-class precedent and supplies the shape that survives an unsupervised run — report *and continue*, "do not try to fix environment issues on your own". DeepSeek supplies the other half from the opposite direction, with feedback that by contract "never reaches the model". It also closes a hole `context-files.md` §10a left: a run that concludes a *convention* is wrong previously had only `AskUser` and its report. `blocker` reuses `medium.md` §4c's generalized wake predicates rather than adding machinery, and requires that no workaround exists — which is why `workaround` is a required field at the other two levels |
| Proof obligation on `implement` | Typed by what was asked: a bug fix proves itself with the step-2 reproduction no longer triggering; a behaviour change with the existing tests covering the changed contract; an investigation by running it; anything runnable also gets a smoke test — start it, exercise the changed path, observe. A new test is written only for an observable contract the suite doesn't already cover | A uniform "run the tests, add tests for your change" step (the original draft) | The uniform version has two defects the research surfaced (`omp/`'s verification section is the sharpest statement of both). It produces test churn on investigations and on changes already covered — cost the reviewer pays, since a hands-off agent's output is a diff someone else reads. And it has no *run the program* mode at all: a passing suite is weak evidence for a bug fix, because that suite already failed to catch the bug. The counterpart rule — never re-audit an `Edit` that already returned success — is the same principle spending turns instead of tokens |
| Whole-file `Read` of a large source file | Returns an **outline**: declarations shown, bodies elided in place with each elision's exact line range, plus a footer naming the re-read. Status `outlined`, distinct from `truncated`; explicit ranges are never outlined | Returning the first `read.default_lines` lines (the original draft, and every source but one); no summarization at all | The first-N-lines answer optimizes for a human scrolling; this agent's alternative is a turn spent discovering the file was the wrong one. An outline plus a targeted range read is usually two calls where a blind whole-file read is one call and a re-read — and the batch `Read` collapses several ranges into that second call. It composes safely here for a reason specific to this design: `Edit` matches bytes exactly, so the model *cannot* edit an elided body without reading it first, and the outline is recorded as a partial view so `Write` refuses too. OMP is the only precedent (`agent-tool-implementations.md`); the cost is a parser dependency and a guess that wants measuring, which is why it is the third open question in `eval.md` |
| Binary and oversized payloads | An **artifact store**: bytes stay out of context, the model gets a `<artifact>` stub carrying shape (`kind`, `mime`, `bytes`, `dims`, `name`, `origin`, `trust`, `expires`) and tools that operate on the reference. `artifact://<id>` is a path scheme `Read` already understands; images get one new tool. **Superseded the same day by the row below** — the store turned out to be half of a single address space rather than a thing of its own. See [`artifacts.md`](./artifacts.md) | Inlining base64 (never — 2.5–3.6× the bytes as text, and the field's best measurement is a 146 KB PNG costing 106,356 tokens against 39,199 handled natively); a `LoadArtifact` + `QueryArtifact` tool pair; keeping the caps-and-truncate answer that v1 already had | `future.md` gated this on "a real case" and predicted the dependency index would be first. Jira/PR **attachments** arrived earlier and are a harder case that settles the design: a 40k-row result has a useful prefix so truncate-and-narrow is a real recovery, but **there is no first 10% of a PNG**. So the store is the primary representation for a class of payload, not an overflow backstop. `../agent-tool-result-transport.md` §7b's six decisions are answered in `artifacts.md` §5 |
| When artifacts are minted | **Ingest, unconditionally and completely** — `FetchJira` and the PR fetch return *every* attachment as a stub, minted from metadata the issue API already returns, with bytes fetched lazily on first look | Minting on overflow only (Claude Code's spill — what every harness in the field does); returning a filtered or size-capped subset of attachments | The model cannot choose what to look at before it knows what exists, and a fetch that silently omits three of five attachments produces an agent confidently reasoning about a ticket it hasn't seen. Completeness is affordable precisely because minting is eager and fetching is lazy: ~40 tokens per stub, zero downloads unless the model looks. No harness in the collection mints on ingest, because none of them ingests a tracker issue — `../agent-vision-multimodal.md` §16 records the clean negative that no PR-review bot handles images at all. Spill minting stays out of v1 |
| Whether a load is permanent | **No — a look is one turn by default**; `pin: true` is the explicit exception, budgeted at 2 | Writing every loaded image into conversation history (what every harness in the field does); a bespoke eviction/supersession pass | ADK's `LoadArtifactsTool` appends to *that request only*, which is free on the target stack and strictly better than a file path. It also dissolves a problem `../agent-vision-multimodal.md` §8 found nobody solving: screenshots accumulate everywhere, and the one harness that evicts (Gemini CLI) needs a bespoke supersession pass *only because* its snapshots were written into history first. Not writing them in means no eviction machinery at all — and retention can then follow the image's role, which a single global rule cannot |
| Vision: one tool, three ops | `InspectImage` with `extract_text` \| `ask` \| `view`, plus `region` and `pin` ([`vision.md`](./vision.md)) | Folding images into `Read` (invisible cost, ungateable, unrefusable); a separate tool per operation; no vision at all | `Read`'s reducing grammar is a line range and an image has no lines — which is the bar `tools.md`'s granularity rule sets for admitting a tool. `extract_text` leads because the most common diagnosis image in a tracker is a screenshot of an error message, which OCR answers exactly, with no model call and no image in context; every harness surveyed reaches for the general capability and misses the cheap specific one |
| Delegated vision | A **single-turn, tool-less sighted sub-model** called inside `InspectImage`, budget-charged, self-suppressing when unconfigured — not a `Task` sub-agent | A `Task`-family sub-agent with tools and a loop; putting every image directly in the orchestrator's context | The strongest convergent finding in `../agent-vision-multimodal.md` §10: Gemini CLI and OpenHands independently built a *defanged* delegate (`excludedPredefinedFunctions` / `tools=[]`). `Task` would give it a tool set, a loop and a turn budget it needs none of and is more dangerous with. The second justification is containment, not cost — see the row below |
| Untrusted images | Role-routed: `trust="external"` images go through `extract_text`/`ask` unless the run states a reason to `view`; image-derived text is confined to the untrusted envelope | Treating images like any other tool result; refusing to look at external attachments at all | **You cannot nonce-wrap an image** — the mechanism `context-files.md` and `review.md` both rely on works by being unforgeable *in the text stream*, and pixels are not in it. Instructions rendered into an image are invisible to every text heuristic shipped anywhere (`../agent-vision-multimodal.md` §12). The tool-less sub-model is the one real containment boundary available: nothing for an injected instruction to act with, and its output reaches Forge already marked as data. Refusing outright would be theatre — a customer's screenshot of a broken checkout is exactly the thing worth looking at |
| One address space for everything readable | A **ref grammar** — `<scheme>://<locator>[:<selector>]`, with a bare path as working-tree shorthand — spoken by every read tool. Six schemes: working tree, `file://`, `git://`, `dep://`, `artifact://`, `run://`. Supersedes the "artifact store" row above, which scoped this to attachments only | Per-source tools (`ReadSource`/`SearchSource` as `medium.md` §2e proposed); three parallel vocabularies (that entry's `scope` strings, `context-files.md`'s `(repo, ref)` pairs, and `artifact://`) left unreconciled | This **removes two tools and adds none**. `tools.md`'s granularity rule says split a primitive when the split changes a harness answer — permission class, destructiveness, concurrency, result shape; `ReadSource` against `Read` changes none of the four, differing only in where the bytes come from, which is exactly what a scheme encodes. The design was already growing the vocabulary in three places without noticing. Cost accepted and named: a local read is microseconds and a remote one is a network call, hidden behind one tool name — mitigated by the ref being self-describing and by keeping §2e's local-first ordering guidance in the description |
| No `http(s)://` scheme | Absent by design; a tracker attachment is reachable only as `artifact://<id>`, an id minted from a URL the *harness* recorded from the tracker's API | Allowing arbitrary URLs now that refs are universal; a `jira://` scheme resolving live | **The absence is the security property.** A universal ref namespace sounds like it hands the model a fetcher; it does not, because every scheme resolves through a configured resolver that never takes a hostname from the model. That keeps the SSRF discipline structural rather than a validation rule — which matters because these fetches carry credentials, and a credentialed fetch of a third-party-influenced URL is the textbook escalation |
| Text extraction | A property of `Read`, uniform across PDF, spreadsheets, `.docx`, HTML, archives, notebooks **and images** (OCR); every conversion announces itself, `:raw` bypasses | An `extract_text` op on the image tool (an earlier draft the same day); per-format tools | Extracting text is what reading a non-text format *means* — scoping it to images was the same category error the field makes when it reaches for a vision model to read a screenshot of a stack trace. Putting it in `Read` makes one rule cover every format and leaves `InspectImage` with only what genuinely needs pixels or a model. The announce-the-conversion rule exists because OCR'd text and a real PDF text layer are not equally trustworthy and the model must be able to tell |
| Oversized non-write results | **Spill to a ref**: an `<artifact>` stub plus a preview, with the recovery note naming a ranged call against the snapshot. Supersedes the truncate-with-footer half of the *Caps vs errors* row above; the explicit-over-limit-request error is unchanged | Truncate with a footer (the prior decision, and what the measured experiment compared against); hard error always; deferring spill minting entirely (an earlier draft the same day) | The prior decision rested on Claude Code's experiment #21841, which compared exactly two options — truncate, or error. **Spill-to-ref is a third that was not on the table and dominates both**: the preview is a size you choose, and the recovery call reads an *immutable snapshot* instead of a mutable file, which kills a race nobody in the collection handles (page two of a paged read coming from a file that changed after page one). Termination is structural rather than an exemption: a read carrying a selector never spills, and every recovery note names a ranged call, so the circular-spill trap closes in one step |
| MCP `resource_link` for refs | Not used — a ref travels as text inside the `<artifact>` stub | Returning `resource_link`, the content type MCP designed for exactly this | The binding cannot carry it: `adk.md` §2's table shows ADK-Java turning **any** non-`TextContent` block into an error, `resource` named alongside `image` and `audio`. Independently, `../agent-tool-result-transport.md` §3f found `resource_link` the least uniformly handled block type in the field, silently dropped by two of seven client projections. So MCP is central to this design as a *namespace*, not as a block type — and a URI in text that the model can read and pass back is strictly better than a link the client drops |
| Image-injection posture | `trust` carried and framed on every image, image-derived text confined to the untrusted envelope, and the tool-less sub-model as the containment path — but **no `external`-routing prompt rule in v1**, because Jira attachment is restricted to authenticated org members in the target deployment. The rule is written down in `vision.md` §5 and switches on with the first deployment that accepts outside attachments | Shipping the routing rule anyway (an earlier draft the same day); dropping `trust` entirely as unnecessary; refusing to view external images | Asked rather than assumed, and the answer changed the design. A prompt rule that can never fire is dead weight the model pays for every turn, so it is reserved rather than shipped. `trust` itself stays because two *other* paths are genuinely external — third-party source under `dep://`, and outside contributors' PR comments — and because it also carries provenance and staleness. The structural fact that survives any policy change is recorded regardless: **an image cannot be nonce-wrapped**, so the mechanism the rest of this design leans on is unavailable here, and the residual risk of an insider-authored mockup is accepted and named rather than mitigated |
| Artifact durability | Durable object storage (ADK `ArtifactService`'s GCS-class backend), so `expires="persist"` genuinely outlives the run | In-memory/run-local only, which would make `persist` mean "until the container goes away" | Confirmed as a deployment fact rather than chosen. Three things follow: evidence referenced by a `Complete` report is retrievable after the run ends, `run://` is implementable rather than aspirational, and **cross-run artifacts become gated on a use case rather than on missing substrate** — still out of v1, but for a different and weaker reason than before |
| Sighted model for `ask` | A separate, cheaper vision-capable model alongside the main one | One model serving both roles (delegation still buys containment but the cost argument evaporates); no sighted model at all (`InspectImage` doesn't ship, `Read`'s OCR still works) | Confirmed as a deployment fact. It means the cost argument for `ask` over `view` holds as written rather than resting on containment alone. The tool stays self-suppressing when unconfigured either way, so the spec is unchanged by the answer — but the guidance in the tool description ("ask first, view when the image *is* the specification") is only honest if the delegate is genuinely cheaper |
| Reviewer sight | A fourth specialist lens, `visual`, is the **only** review role with `InspectImage` wired — and the only lens fanned out **conditionally**, when the PR carries an image artifact or touches UI-classified paths. Validator stays text-only | Text-only across the whole pipeline (an earlier draft the same day); granting the orchestrator instead; granting every lens | Asked rather than assumed. Codex is the only source in the collection that treats reviewer sight as its own decision (`Disabled`/`TextOnly`/`Multimodal`); this resolves it one notch further open. The validator's text-only-ness is the load-bearing part: granting it sight would **dissolve** §5's independence rule rather than serve it, since it would be checking the same pixels with the same eyes. So a `visual` finding must anchor to the line of code producing what the image shows and is re-derived from code like any other — which also enforces something worth enforcing, because a lens that cannot tie what it sees to a line of code produces "this looks a bit off," which nobody can act on. Conditional fan-out is **not** new here — `conventions` is already skipped when no conventions file is scoped to the changed paths, on identical reasoning (a specialist with nothing in scope still costs a full run to return an empty list), so `visual` inherits an established pattern rather than introducing one. **Amends the tool-scoping key**: `visual` is a fourth `role` on the existing `reviewer` type rather than a fourth type, so tool availability keys on the `(subagent_type, role)` pair — both are model-supplied enums the harness maps to a tool set, so the pair gates exactly as structurally as the type did, and one reviewer core stays parameterised by lens instead of fracturing into two prompts |
| `git://` backing service | A Sourcegraph-class **code-search** service, so `Grep` over `git://` is a real indexed query | A platform API with weak code search (`Grep` would degrade visibly or wait for phase 2); shallow clone into the workspace (both work, first read pays a clone) | Confirmed as a deployment fact, and it is what makes the two-tool collapse in `artifacts.md` §1 whole rather than one-and-a-half — the `ReadSource` half of the merge works against any backing, the `SearchSource` half needs a real index |
| `Read`'s conversion set | PDF, spreadsheets, `.docx` and archives are all v1, alongside images-as-OCR | A narrower first cut (PDF only, or images only) with the rest deferred until a ticket demanded it | Asked; the answer was all four. They share one mechanism — a MIME-keyed converter behind the same tool, the same selector grammar and the same announce-what-you-did rule — so the marginal cost of the fourth is small once the first exists, and each maps to a real attachment type on this deployment's tickets |

## What's deliberately not in v1

Leanness cuts, not verdicts — every one is a documented,
well-precedented pattern in this collection, tracked rather than
dropped. The roadmap is split by horizon: `medium.md` carries the
concrete next upgrades (new tools, CI integration, the loop-closing
run sources, and the escalation triggers v1 ships simple versions of),
sketched in enough detail to implement against; `future.md` carries
the long-horizon and measurement-gated ideas, kept deliberately lean.
Both are separate from this README so they don't distract from
implementing v1 itself.

## Maintaining these documents

Two rules, adopted from the Agent Note discipline in
[`../deepseek-harness/`](../deepseek-harness) (see
[`../agent-memory-learning.md`](../agent-memory-learning.md) §9 for the
full scheme, most of which is deliberately not adopted — this folder
does not need lifecycle folders or a format gate):

- **A decision is never edited into a different decision.** Supersede it
  and cross-link, keeping both legible. Editing a decision row to track
  where its subject now *lives* — a renamed tool, a moved section, a
  changed default — is required, not forbidden; changing what it decided
  is what needs a new row saying what it replaced and why. The decision
  log below accumulates re-litigated items precisely because that line
  has not been drawn, and "we already considered that" is only useful
  when the record says what was considered.
- **Alternatives are recorded, never invented.** Where the alternatives a
  decision beat are genuinely not reconstructible, say so in that row
  rather than writing plausible-sounding ones after the fact. DeepSeek's
  gate accepts an explicit marker for exactly this case, which is a
  better answer than a well-written guess — a fabricated alternative
  reads identically to a real one and quietly makes the record
  worthless.

## Reading order

1. `system-prompts.md` — the two orchestrator prompts and the three
   sub-agent prompts.
2. `tools.md` — every tool's description and input schema.
3. `formats.md` — the wire formats that connect a task to Forge and
   Forge's output back out: the context envelope, the completion
   schema, the review-finding schema, the `AskUser` suspend/resume
   protocol, the run-bounding contract, and (§8) the byte-level shape
   of every tool result — including how a multi-file, multi-range
   `Read` delimits its blocks without escaping anything.
4. `context-files.md` — where the agent's standing instructions come
   from and how they become prompt bytes. Three tiers — org and team
   resolved by a context service at dispatch, repo discovered by a
   filesystem walk — with a two-axis precedence rule (`policy` from above
   beats the repo, `default` from above loses to it) and the response
   contract the context service has to meet. Then discovery and collision
   rules for the repo tier, the byte budget
   and how truncation is announced, path+revision provenance, the
   nonce-bearing envelope, what the file is *scoped* to instruct, and
   the review-mode rule that conventions are read at the **base** SHA
   (the same merge-base `review.md` §2 already computes for the diff) and
   a diff touching them is a finding rather than an instruction. §12
   covers the programmatic channels v1 does without — MCP server
   `instructions`, skills, hooks, plugins — and the four rules if any of
   them is added later. Supersedes one decision in `review.md` §1 and
   promotes one `medium.md` deferral (structural write protection for the
   conventions file) into v1.
5. `review.md` — the review entrypoint's payloads in full depth: the
   diff-construction algorithm, the comment-thread model (including
   stale threads' then/now rendering), the exact finder/validator
   brief formats, the two run shapes (single-stage and multi-stage),
   re-review sessions (state, interdiff, thread reconciliation),
   mid-run race policy, and the seam with comment-driven fix runs.
6. `examples/` — worked, end-to-end instances of every review
   payload, all on one fictional PR followed from first review
   through re-review to a responder run.
7. `memory.md` — what survives a run: the learned tier of the context
   service (which is the code/git/artifact proxy, so knowledge is keyed
   by ref alongside the code it is about — including **dependency
   coordinates**, an axis no source in the research has), the
   capture-in-session / promote-on-outcome split, the record schema and
   its per-category promotion gates, mechanically-computed staleness, and
   `ReportProblem` — the improvement-request channel, with a `blocker`
   priority that suspends the task. Supersedes `medium.md` §6 on where
   the store lives, how a learning is captured, and what a learning is
   addressed to; §6's run shape and safety rules stand.
8. `medium.md` — the medium-term roadmap: concrete post-v1 upgrades
   with design sketches, plus the named escalation triggers.
9. `future.md` — long-horizon and measurement-gated work, tracked
   separately so it isn't silently re-litigated later.
10. `adk.md` — implementation-substrate notes, not design: how this
   surface fits Java ADK with every tool exposed over MCP, what needs
   overriding (the MCP result envelope, the retry policy on mutating
   tools), what to accept, and what to verify against a running stack.
   Deliberately separate so the design itself stays substrate-neutral.
11. `eval.md` — the measurement harness: the hostile-workspace fixtures,
   the accuracy-*and*-cost metrics, the rules of engagement (reps, noise
   floor, two models, caveats recorded next to verdicts), and the
   ship/no-ship log. This is what turns `tools.md`'s configuration
   section from seventeen opinions into seventeen decisions, and it
   carries the list of open questions it exists to close.
Per-source notes — what one harness does and whether it transfers —
live in that harness's own folder, not here. `../deepseek-harness/`
is the worked example: its README carries the travels/doesn't-travel
split, and what this design took from it is stated in the design files
themselves at the point of the decision.

This design has been through three full review passes against the rest
of this repo's research — one after the first draft, one after the docs
settled, and a third that reset platform primacy and split the roadmap. Every finding from both passes has been folded directly into
the documents above (and into this decision log) rather than kept as a
separate write-up. The second pass's findings were mostly seam-level:
internal contradictions between documents (the review sub-agents' Bash
scope was stated three different ways), schema/description mismatches
(background Bash promised a polling shape the schema couldn't express),
and wire-format fields the pipeline depended on but the envelope never
carried (comment ids for `in_reply_to`, resolved/outdated markers for
the dedup step) — the kind of thing that surfaces when reading the
documents as an implementation spec rather than as a design argument.
It also produced two substantive changes, both from research docs the
first pass leaned on less: the no-git-writes rule gained a harness-side
blocklist (Augment SWE-bench Agent's precedent showed the structural
version of that one rule is a few lines, not a permission engine —
`agent-git-vcs.md` §2), and the project-conventions file gained
explicit self-instruction-poisoning defenses (Roo Code's
`RooProtectedController` precedent — `agent-permissions-approval.md`
§3).

The third pass made one structural change and several seam fixes. The
structural change: Bitbucket became the primary PR platform (the
deployment target is an Atlassian stack), which turned out to cost only
enum values and prose because the one-tool-for-all-platforms shape was
already right — see the "PR platform coverage" decision row. The seam
fixes: the unbounded validator fan-out gained a harness-side
concurrency cap (Codex CLI's and OpenHands's code-enforced caps are the
precedent — `agent-subagent-architectures.md` §5), and suggestion
blocks gained the same visible-degradation contract anchors already had
for deployments that can't apply them. The same pass replaced the flat
deferred-work list with the two-horizon split (`medium.md`/`future.md`)
and pulled the highest-leverage deferred items — CI integration, the
review → fix handoff, PR-comment-responder runs, Jira search and
ticket-compliance review context — forward into concrete,
implementable sketches.

A follow-up to the third pass added a cross-repo and long-horizon
tier to `medium.md`: ref-pinned source search/read beyond the working
tree (`SearchSource`/`ReadSource`, with a dependency-coordinate
resolver in phase 2), dependency-change escalation
(`ProposeDependencyChange` — filing a requirement into the owning
team's Jira project, gated by default), and waiting primitives at two
scales (an in-run `Await` for things already in flight, and the
AskUser suspend/resume protocol generalized to build/Jira/PR/timer
wake conditions). The unifying observation: v1's AskUser protocol was
already a task-suspension mechanism with one hardcoded wake predicate
— the higher-level capabilities are new predicates on existing
machinery, not new machinery.

A fourth pass went deep on the review entrypoint specifically —
tightly defining what actually reaches the model at every stage. It
produced `review.md` (the diff-construction algorithm, a threaded
comment model replacing the flat comment list, exact
verbatim-transclusion brief formats for specialists and validators,
stateful re-review sessions with thread reconciliation, and a mid-run
race policy) plus the `examples/` folder of worked payloads, and
threaded the results back through `formats.md`, `system-prompts.md`,
and `medium.md` (§3f). Its design stance is recorded in the three
review-specific decision rows above; the phasing rule it enforces —
every post-v1 addition is an additive tag or field, so the v1 wire
shapes never change meaning — is stated in `review.md` §10.

A fifth pass, driven by design review of the fourth, made three
changes. It reversed the comment-blind finder decision (finders and
validators now receive the comment threads as intent context under
explicit discussion rules — see the brief-context decision row — after
the blind design was shown to produce validator-confirmed comments
arguing with explicit human requests). It made thread staleness
structural: threads anchored to an earlier head carry `at_sha`,
per-comment `@ sha` markers, and (phase 2) `<code_then>`/
`<changed_since>` blocks with a conditional `<format_notes>`
explainer, replacing the `outdated` status value that had conflated
"code moved" with "conversation over" (`review.md` §3a–3b). And it
split review runs into two shapes — multi-stage and single-stage —
sharing one reviewer core, one set of wire formats, and one
unconditional validator stage (`review.md` §6, `system-prompts.md`
§2b), with dedup's two jobs placed deliberately: external dedup in
both shapes before validation, internal dedup only where two finders
exist.

The same follow-up added the design's first third entrypoint to the
roadmap (`medium.md` §5): a product-owner mode whose deliverable is
tracker artifacts — epics broken into stories and tasks, requirements
and acceptance criteria, code-evidence-grounded estimates, backlog
grooming — rather than code or review comments. It reuses the
existing discipline on a new substrate: the tracker is that mode's
working tree (`WriteJira` wired in PO mode only, gated by default,
with a post-run report-vs-tracker cross-check mirroring the coding
mode's `git status` check), AskUser delivery generalizes to
chat/email/UI channels harness-side with Jira kept as the audit
record, and Confluence-style documentation reading (`SearchDocs`/
`FetchDoc`) arrives as shared tooling all three entrypoints use.

A sixth pass took the collection's memory-and-retrospectives research
(`agent-memory-learning.md`, written for it) and resolved what
`future.md` had been tracking as an open question with a named
blocker. The result is `medium.md` §6: cross-run learning as a fourth
entrypoint — a **learnings run**, triggered by PR outcome rather than
by run completion, that consumes a terminal PR through the review
side's own envelope blocks (plus a follow-up diff, the unfiltered
thread set, and optionally the originating run's report and
transcript) and emits memory records through a single `CreateMemory`
tool. Its four settled decisions are the last rows of the log above.
The shape it converged on is that a learnings run *is* a review run
with a different subject and a different delivery channel — which is
why it reuses the diff builder, the thread model, the completion
contract, and, in phase 2 for dedup and merge, the review pipeline
itself, rather than standing up parallel machinery. It also collapsed
what had looked like two mechanisms into one: since a coding run's
output becomes a PR and gets reviewed, both entrypoints reach the same
terminal state carrying the same artifacts, and one envelope covers
both. Two consequences landed elsewhere: `medium.md` §2e gained a
`run:<run-id>` transcript scope (a scope value on an existing tool,
not a new tool), and §3e's finding-outcome telemetry was promoted from
a measurement nicety to a prerequisite, since it is the substrate the
review half learns from. Ordering against §5 is free — neither
entrypoint blocks the other.

A seventh pass went down one level from "which tools exist" to how the
basic tools are *implemented*, reading the actual source of nine harnesses
rather than their prompt text (the new
[`agent-tool-implementations.md`](../agent-tool-implementations.md), with
fetch paths and commits recorded in [`sources.md`](../sources.md)). Its
main output was an implementation contract in `tools.md` — three channels
per tool, output-format policy, self-describing caps, spill-to-scratch,
errors-as-instructions, tolerant parsing, the shared `cat -n`/`Edit`
contract, read-before-edit as harness state, and per-tool read-only/
concurrency/destructive metadata — with `Read`, `Edit`, `Write`, `Grep`
and `Bash` rewritten against it.

Discussion of that pass then changed the tool surface itself in two
places, both settled in the log above. `Glob` became **`List`**: one
read-only path tool covering glob matching, directory listing and a
line-counted tree behind an `output` mode, which also removes review
sub-agents' dependence on a `Bash ls` they don't have. And **`Read`
became a batch tool** — `files: [{path, start_line?, end_line?}]` — on
the argument that turn count is this design's actual run budget. Four
findings were deliberately *not* adopted and are tracked in `medium.md`
instead: unchanged-file read dedup (§2g, blocked on invalidation this
design can't yet get right), a model-family fork of the edit format,
deferred tool loading behind a search tool, and a single-tool `Lsp` in
OpenCode's operation-enum shape (all §7).

The same pass added `medium.md` §2f, `Narrate`, from an observation
that the learnings design had left implicit: the transcript is a poor
retrospective input — dirty, large, and an injection surface — and the
thing a retrospective most needs from it, *why the approach changed*,
is the thing a post-hoc reader can least reliably reconstruct. A
handful of first-hand narrative entries per run, with detours marked
as such, supply it directly and serve a watching human at the same
time, which an unsupervised `implement` run otherwise has no channel
for. Researching it produced a new section in
[`agent-turn-output.md`](../agent-turn-output.md) (§3a: narration
sorted by *what it contains* and *how long it survives*, rather than by
delivery mechanism) and resolved a question that doc had carried as
unresolved — Gemini CLI's `update_topic` is not a session-title
mechanism but a progress-narration channel, which is why it is the
closest precedent for `Narrate`.

An eighth pass went a layer below the seventh — from how tools are
implemented to what actually crosses the wire and what the evidence for
any of it is worth. Sources: a vendor teardown of one read tool, two
harness write-ups and the open-source harness behind them (OMP), a
second harness's read-tool A/B eval (Hermes), and the academic
benchmarks plus an audit of them
([`agent-tool-call-dialects.md`](../agent-tool-call-dialects.md) is the
new research doc; `agent-tool-implementations.md` §3f–§3h, §4a, §4a2,
§5d, §6b–§6e and §8b are the rest).

It corrected two latent bugs. `Write` was gated on *whether* a path had
been read, so a 50-line read of a 2,000-line file licensed a wholesale
rewrite that destroyed 1,950 unseen lines; the read-state cache now
records what was seen, and `Write` requires a full view. And the three
read ceilings were two: a file of merely-wide lines cleared every
per-entry cap and fell through to the batch rule, which truncates whole
entries and would have returned nothing for a one-file call.

It inverted one architecture. The tolerance layers ran *before*
validation — the design that Command Code shipped, broke, and reverted
after a `write` whose content was legitimately JSON-shaped got rewritten
on the way to disk. Repairs now run only on a failing input, at the paths
the validator itself disagreed at, in a declared order (parse a
JSON-string array before wrapping a bare string, or `'["a","b"]'` becomes
`['["a","b"]']`: schema-valid, meaning lost).

Two additions came from the same pass rather than from a bug. `Read` now
outlines a large source file instead of returning its first 2,000 lines,
which composes safely here because byte-exact `Edit` structurally
prevents editing what was never shown. And the `implement` prompt's
verify step became typed by what was asked, with a smoke-test mode it
never had and a much narrower default on writing new tests.

The pass also produced `eval.md`, and the reason is the most useful thing
it found: the public evidence base cannot settle these questions. Of
150+ code benchmarks, two evaluate instructed editing with human
instructions and tests; both are over 90% Python with no TypeScript or
Java, contain no documentation or maintenance edits, and carry oracles
that in most cases cannot detect changes *outside* the edit region —
which is exactly the failure mode an unsupervised agent has. Every
credible harness team in the survey built their own eval instead. This
design now has the specification for one, and `adk.md`'s two
long-standing "this is the eval that decides it" questions finally have
somewhere to be answered.
