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
                    │  Bash · Grep · Glob      │
                    │  Task · AskUser          │
                    │  FetchJira · AddComment  │
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
| Review-mode delegation | Fixed parallel specialist team + validator pass, always | Single-pass no sub-agents (PR-Agent, Codex-review's approach); user-chosen sequential/parallel (`pr-review-toolkit`'s approach) | Hands-off delivery raises the cost of a false positive (no human filters before posting) enough to justify the fixed second pass unconditionally, per `code-review-approaches.md`'s takeaways |
| Task completion signal | Structured schema **and** a human-readable summary field inside it | Freeform chat-style final message only (Claude Code); a bare machine schema with no prose (Codex-review's JSON-schema output) | Consumers are mixed: CI/Jira automation need the schema, but the summary field exists for whatever the harness renders into a PR or Jira comment for a person to read — Forge doesn't post that itself |
| Comment body format | `AddComment.body` is always plain Markdown, regardless of target platform | Platform-native formats from Forge itself (Jira Cloud's ADF, wiki markup) | The schema stays platform-agnostic; converting Markdown to whatever a specific tracker actually requires is harness-side plumbing, not something Forge's prompts or schemas should encode — same reasoning as keeping git writes out of the agent's tool surface |
| `AskUser` semantics | Suspend the run, post the question via `AddComment`, resume on reply | Synchronous in-process blocking prompt | Hands-off has no human watching the process to answer synchronously; the suspend/resume shape also reuses `AddComment` instead of adding a second communication channel |
| `AddComment` in `implement` runs | Not wired at all — plan-mode coding runs and review runs only | Wired with usage guidance (an earlier revision); wired with no guidance (the original draft) | No `implement` workflow step posts anything — the Complete report is that mode's only outward channel, with `judgment_calls`/`summary` carrying what a ticket note would have said and the harness deciding what reaches the ticket. A wired-but-unused tool on an unsupervised path is the same injection surface that keeps `AskUser` out of review mode, so the structural-gates principle applies. `AskUser`'s suspension posting is unaffected (harness-side, `formats.md` §5). Tracked upgrades: `medium.md`'s PR-comment-responder runs wire it for threaded replies in that one task source; a general implementation-decision-notes channel stays in `future.md` |
| Diff delivery to the review agent | Pre-formatted plain unified diff, baked into the task envelope | Custom hunk format (PR-Agent's `__new hunk__`/`__old hunk__`); leave it to the model to run `git diff`/`gh` itself (most Claude Code skills) | `code-review-approaches.md` §3's takeaway: pre-formatting trades a little build complexity for guaranteed line-number accuracy, which matters when comments post unsupervised. Plain unified diff (Codex-review's choice) rather than PR-Agent's custom hunks, to keep the format lean |
| Git write operations | None in v1 — no commit, push, branch, or PR creation from inside the agent; enforced by a harness-side blocklist on git write subcommands in `Bash`, not prompt text alone | Claude Code's interactive convention (commit/push once explicitly asked in the current turn); the coding agent's originally-designed default of committing/pushing/opening a PR itself under `mode: implement`; prompt-only enforcement (an earlier draft) | The harness checks out the task's target branch *before* the run starts; the agent edits files in that working tree and stops. A finished, uncommitted working tree **is** the deliverable — an external process (whatever invoked the run, which already owns git identity, signing, and PR-creation conventions) picks it up from there. Keeps git write concerns, and everything that comes with them (author identity, signing keys, commit-message conventions, PR templates), entirely outside the agent's tool surface in v1. The blocklist upgrade over prompt-only: Augment SWE-bench Agent's `banned_command_strs` substring check is the only code-level git restriction in the collection (`agent-git-vcs.md` §2) and shows the structural version of this specific rule costs a few lines, not a permission engine — so the design's own structural-gates principle applies here too |
| Live todo/planning tool | None in v1 | A `TodoWrite`-style stateful tool (near-universal in archetype 1, `coding-agent-approaches.md` §6) | No one is watching a live todo list update turn by turn; step tracking is folded into the `Complete` report's step list instead. Not the same question as the row below — this is about a tool for tracking progress *during* a single run, which Forge still doesn't have |
| Plan mode | A second `mode` value (`plan`) on the *same* coding system prompt — read-only investigation ending in `AskUser`, a structured plan (`formats.md` §3c), or a terminal no-action finding (empty `steps`), consumed by a later `implement` run via a `<plan>` envelope tag when a plan was produced | A separate third system prompt/entrypoint; a model-side heuristic deciding when to plan first (Codex CLI's "skip planning for the easiest 25%"); a live in-run planning tool (conflated with the row above, but genuinely different — see `formats.md` §6); a third, separate read-only `investigate` mode for standalone research tasks | Reuses one read-only tool scope instead of standing up new machinery — the closest precedent is Gemini CLI's Plan Mode and OpenCode's `plan.txt`/`build-switch.txt`, both mode-variants of one base agent rather than separate agents. No source in the collection treats "investigate, don't even plan" as its own peer top-level mode: OpenCode's closest analog, `explore`, is a subordinate sub-agent type its `build`/`plan` orchestrator delegates to, not a mode a dispatcher picks directly (`agent-permissions-approval.md` §1); Factory/Droid's leaked prompt collapses diagnosis and planning into one binary Diagnostic/Implementation split with no separate plan-artifact step at all. Folding standalone investigation into `plan`'s own possible outcomes matches that shape more closely than keeping a third mode did. Mode selection (plan-first vs. straight to `implement`) is made by whatever invokes a run, not by Forge itself |
| Plan → implement gating policy | Deliberately unspecified in Forge's own prompt (`formats.md` §6) | A built-in human-approval gate, reusing `AskUser`'s suspend/resume mechanism for "approve this plan?"; unconditional auto-chaining straight into `implement` | Asked directly rather than assumed. Forge's contract is identical either way — post the plan, call `Complete(status: "planned")` — so the choice of whether an `implement` run fires immediately or waits for a reply is a deployment-time policy the harness owns, not a behavior difference in the agent |
| Sub-agent tool-scope narrowing | `reviewer` and `validator` sub-agent types get `Read`/`Grep`/`Glob` only — no `Edit`/`Write`, and no `Bash` at all | Full tool parity for every sub-agent type (Claude Code's `general-purpose: Tools: *`); read-only-git `Bash` for review sub-agents (agent37/TuringMind's allowlist shape) | Matches the narrower-scope pattern `agent-subagent-architectures.md` §6 finds in Claude Code's own `statusline-setup`/`output-style-setup` types and in Amp's `oracle` — a reviewing sub-agent has no legitimate reason to touch files. Read-only-git `Bash` was rejected too, not just writes: v1 has no command-level `Bash` filter, so "read-only git only" would be prompt-enforced where the design's own principle is structural gates for anything that can write; agent37/TuringMind's allowlists lean on Claude Code's permission engine, which Forge doesn't have in v1. The cost — a validator can't `git show` the base version when judging whether an issue is pre-existing — is mitigated by the `-U5` diff context plus the head-SHA working tree, and named in `medium.md` as the escalation trigger for adding a filtered `Bash` |
| Review dedup identity | Author-agnostic — compare candidate findings against every existing comment in `<existing_comments>` regardless of who posted it; no skip gate on "have I reviewed this commit before" at all | A hard skip in step 1 keyed to a specific agent identity (would require a new `{{AGENT_USERNAME}}` env field, and only catches Forge's own prior comments, not a human's or another bot's) | An identity-keyed check is both fragile (the platform-visible username and the internal placeholder name can drift apart) and too narrow (it only prevents Forge repeating itself, not repeating anyone). Dropping the skip gate also means re-reviews are always allowed to run — a new push can have new issues even on a PR already reviewed once — with the pipeline's dedup step doing the actual noise-prevention work instead of a run-level gate |
| Read-only mode enforcement | Structural: the harness doesn't wire `Edit`/`Write` at all in `plan` runs, for the orchestrator or its `general-purpose` delegates; prompt rules remain as a second layer | Prompt-only enforcement (the original draft: tools wired in every mode, "never call them" as instruction) | Same argument as the scratch-directory row: a structural boundary can't be forgotten. Gemini CLI strips agent-kind tools in code; Composio scopes per role at the tool level (`agent-subagent-architectures.md` §6); `agent-permissions-approval.md`'s core finding is that serious sources layer prompts *on top of* structural gates, never instead |
| `review_only`/`investigate` modes | Both folded into `plan` — no separate mode value for either; a standalone research task is a `plan` run that ends with an empty `steps` list instead of a forward-looking plan | Two distinct modes, `review_only` defined as "treat the same as `investigate`" and `investigate` as its own read-only peer of `plan` | `review_only` and `investigate` had identical authorization and differed only in framing; folding one into the other (an earlier step) still left a mode defined almost entirely by "same as `plan`, minus the plan artifact." No source in the collection gives standalone investigation its own peer top-level mode (see the Plan mode row above) — collapsing to two mode values total (`plan`/`implement`) matches the field's actual binary shape and removes a mode that was pulling less weight than its own upkeep cost across `system-prompts.md`/`tools.md`/`formats.md` |
| Large-diff policy | Skip-with-reason above a harness-configurable size threshold (fixed changed-line count, or a char-count-estimated fraction of the model's token budget adjusted for specialist fan-out) | Sharding — split specialists per file group, merge findings afterward | Rejected, not deferred: no source in the collection does automated sharding-with-merge, including Anthropic's own `/code-review` skill (its troubleshooting doc's answer to large PRs is "consider splitting large PRs into smaller ones," a PR-author step taken *before* review, not a harness mechanism). BMAD's chunking is human-mediated across separate runs — a person decides the group boundaries and reconciles follow-ups — which doesn't transfer to an unsupervised pipeline with no one present to arbitrate a cross-file finding split across batches |
| Completion integrity | Two deterministic gates: first `Complete(done)` in `implement` returns a fixed checklist instead of completing (second call goes through), and the harness cross-checks the report against real `git status` after the run | Trusting the self-report (original draft); a separate LLM verification judge (Claude Code's internal adversarial verifier) | False completion claims are the best-measured failure mode in the research (`agent-self-verification.md` §7: a leaked 29-30% false-claim rate drove dedicated internal tooling); mechanical gates "can't be talked out of firing" and cost no extra model call, where an LLM judge is a real subsystem (v2 at earliest) |
| Run bounding | Harness turn budget + context high-water mark; crossing either injects a final-turn nudge that permits only `AskUser` or `Complete`; no compaction in v1 (`formats.md` §7) | Unbounded runs (original draft — silent death on context exhaustion); a full compaction subsystem from day one | "Always end via Complete" is unenforceable without a guaranteed last turn (Copilot Chat's forced last-turn cutoff is the precedent); compaction is a deep subsystem (`agent-context-compaction.md`) that leanness says to defer, but *saying so* beats leaving the ceiling unhandled |
| Comment anchoring | Anchors are new-file line ranges (`line`/`line_end`); harness validates an anchor is commentable and degrades to a `file:line`-prefixed general comment, visibly, when it isn't | Single-line anchors with no side convention and no validation (original draft); PR-Agent-style per-hunk line-number injection from day one | The decision log's own rationale for pre-baking the diff was line-number accuracy — anchor validation is the cheap backstop that makes a mis-derived number degrade visibly instead of silently; hunk-injection remains the documented upgrade if mis-anchoring shows up in practice |
| Reproduction/throwaway files | A dedicated scratch directory outside the git working tree (`{{SCRATCH_DIR}}`, named in `<env>`), never cleaned up because it's never inside git state to begin with | Instructing the agent to delete temp files before calling `Complete`; a `.gitignore` convention for a fixed reproduction-file naming pattern | A cleanup instruction depends on the model remembering a step at the very end of a long run — one missed case and a `reproduce.py` rides along into whatever the external process commits. `.gitignore` is better but still depends on it being correctly configured and not overridden by something like `git add -A -f`. A structural directory boundary can't be forgotten or misconfigured; step 5 of the coding workflow also adds a final `git status` sanity check as a second line of defense regardless |

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

## Reading order

1. `system-prompts.md` — the two orchestrator prompts and the three
   sub-agent prompts.
2. `tools.md` — every tool's description and input schema.
3. `formats.md` — the wire formats that connect a task to Forge and
   Forge's output back out: the context envelope, the completion
   schema, the review-finding schema, the `AskUser` suspend/resume
   protocol, and the run-bounding contract.
4. `medium.md` — the medium-term roadmap: concrete post-v1 upgrades
   with design sketches, plus the named escalation triggers.
5. `future.md` — long-horizon and measurement-gated work, tracked
   separately so it isn't silently re-litigated later.

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
