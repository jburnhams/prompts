# Approaches to building a code/PR review bot

Everything in this collection that's specifically a code- or PR-review tool
(as opposed to a general coding agent) makes a different set of choices at
each stage of the pipeline. This doc pulls those choices out and puts them
side by side, stage by stage, with links to the source folder for full
detail. It doesn't cover general-purpose coding agents (Cline, Aider,
etc.) — only things whose job is specifically reviewing code.

## Sources covered

| Source | Scope | Category |
|---|---|---|
| [`pr-agent`](./pr-agent) | GitHub PR | Full open-source agent |
| [`skills/agent37/local-review`](./skills/agent37/local-review) | Local uncommitted diff | Claude Code skill |
| [`skills/anthropic/code-review`](./skills/anthropic/code-review) | GitHub PR | Claude Code skill |
| [`skills/anthropic/pr-review-toolkit`](./skills/anthropic/pr-review-toolkit) | GitHub PR (chat-only, no GH I/O) | Claude Code skill |
| [`skills/anthropic/security-guidance`](./skills/anthropic/security-guidance) | Local edits, via hooks | Claude Code skill |
| [`skills/turingmind`](./skills/turingmind) | Local uncommitted diff | Claude Code skill |
| [`skills/bmad-code-review`](./skills/bmad-code-review) | Local diff, branch, or PR (no GH I/O) | Claude Code skill |
| [`skills/claude-code-cookbook`](./skills/claude-code-cookbook) (`pr-review`+`pr-fix`) | GitHub PR | Claude Code skill |
| [`github-pr-bots/claude-code-action`](./github-pr-bots/claude-code-action) | GitHub PR (`@claude`, or automated) | GitHub Action |
| [`github-pr-bots/gemini-code-review`](./github-pr-bots/gemini-code-review) | GitHub PR, or local branch | Gemini CLI extension |
| [`github-pr-bots/codex-review`](./github-pr-bots/codex-review) | GitHub PR | OpenAI reference implementation |
| [`github-pr-bots/opencode-review`](./github-pr-bots/opencode-review) | GitHub PR (`/oc` mention, or automated) | GitHub Action |
| [`composio-swekit/pr_review`](./composio-swekit) | GitHub PR | Multi-agent framework template (LangGraph) |
| [`github-pr-bots/agent-approval-check`](./github-pr-bots/agent-approval-check) | GitHub PR, merge side (approval gate + stamp sweep) | GitHub Action + Claude Code workflow; added 2026-10-17, see §12 |
| [`deepseek-harness/skills/dsh-code-review`](./deepseek-harness) | GitHub PR, one repo only | Repo-resident skill + a self-maintenance loop |
| [`openclaw/.agents/skills/autoreview`](./openclaw) | Any git target (branch, PR, ref range), one repo | Repo-resident skill + a 6,168-line Python driver calling a second model |

The **last two rows** are different animals from the other thirteen and
are worth saying so up front.

`autoreview` is the only source here that is a *program that calls a
review model*, rather than a prompt handed to an agent already running.
It builds and validates a change bundle, chunks it byte-exactly when
oversized, invokes one of five named engines (Codex, Claude, Amp, Pi,
Kimi) with a pinned model and reasoning effort, validates the returned
JSON against a strict schema, and stops. That shape is what lets it do
three things nothing else here can: **starve the reviewer of context on
purpose** (§4), state **round-cost economics** to the model (§2), and
enforce a **priority threshold** as a prompt preamble rather than a
post-filter (§6). It also ships a consumer-side contract telling the
*calling* agent how to treat the output, which no other source has
(§9).

The `dsh-code-review` row is a different animal again. Every other source here is a **portable** review tool:
it ships criteria that are meant to apply to any repository. `dsh-code-review`
is deliberately the opposite — a skill that reviews *one* codebase, whose
content is the accumulated residue of that repo's own human review
history, and which is **rewritten periodically from mined review
comments** rather than authored once. It therefore contributes almost
nothing to stages 1–4 below (it delegates all of those to its host agent)
and dominates a stage none of the others have, which is why §11 exists.

---

## 1. Trigger & scope

What kicks off a review, and what's actually in scope.

| Trigger style | Sources |
|---|---|
| Slash command, local uncommitted changes | [`agent37/local-review`](./skills/agent37/local-review), [`turingmind`](./skills/turingmind) (`/review` + `/deep-review`), [`gemini-code-review`](./github-pr-bots/gemini-code-review) `/code-review` |
| Slash command, an existing PR | [`anthropic/code-review`](./skills/anthropic/code-review), [`pr-review-toolkit`](./skills/anthropic/pr-review-toolkit), [`claude-code-cookbook`](./skills/claude-code-cookbook) `pr-review`, [`gemini-code-review`](./github-pr-bots/gemini-code-review) `/pr-code-review`, `pr-agent` `/review` + `/improve` |
| `@mention` in a PR/issue comment | [`claude-code-action`](./github-pr-bots/claude-code-action) tag mode, `@codex review`, `@gemini-cli /review`, [`opencode-review`](./github-pr-bots/opencode-review) `/oc` or `/opencode` |
| GitHub Action on PR events (`opened`/`synchronize`) — fully automatic | [`claude-code-action`](./github-pr-bots/claude-code-action) agent mode, [`gemini-code-review`](./github-pr-bots/gemini-code-review) workflow example, [`codex-review`](./github-pr-bots/codex-review), [`opencode-review`](./github-pr-bots/opencode-review) |
| Background hook, no explicit trigger at all | [`security-guidance`](./skills/anthropic/security-guidance) (fires on edit/commit) |
| Flexible cascade (asks what to review if unclear) | [`bmad-code-review`](./skills/bmad-code-review) — 5-tier cascade: explicit arg → recent conversation → sprint-tracking file → current branch → ask |

**Takeaway**: "local diff" tools (agent37, TuringMind, Gemini's `/code-review`)
and "PR" tools are mostly disjoint feature sets, not modes of the same
tool — only BMAD and Gemini's extension span both, and even then via two
separate commands with different context-gathering and output logic, not
one command that branches.

## 2. System prompt / preamble — what's sent before the diff

*(Revised after a direct challenge to the first draft of this section —
"surely running a full coding-agent system prompt just to do a review is
massive context bloat, doesn't OpenCode have a leaner mode?" That's a
fair question, and checking it properly surfaced a more interesting
answer than the original version had. Findings and their sourcing below.)*

Three separate questions, best kept apart: (a) is there a real API-level
system/user split at all; (b) if this tool runs inside a host coding
agent (Claude Code, Gemini CLI, Codex CLI, OpenCode), **can** that host's
own default system prompt be swapped for something leaner; and (c),
regardless of (b) — does the tool actually in front of you *do* that, or
does it just default to the full thing?

### (a) + (b): every host agent here supports running leaner — this isn't hypothetical

| Host | Override mechanism | Source |
|---|---|---|
| Claude Agent SDK | Defaults to an **empty/minimal** system prompt unless you opt in with `systemPrompt: { type: "preset", preset: "claude_code" }`. Without the preset you get a "much more barebones agent" — no coding conventions, no tool-use guidelines beyond the basics. | [Claude Code docs, "Modifying system prompts"](https://code.claude.com/docs/en/agent-sdk/modifying-system-prompts) |
| Claude Code CLI / `claude-code-action` | The full built-in prompt is the *default* when you run the actual `claude` CLI (as opposed to the bare SDK), but it can be fully replaced via `system_prompt:` (override) or extended via `append_system_prompt:` | `claude-code-base-action` docs, referenced from [`claude-code-action/README.md`](./github-pr-bots/claude-code-action) |
| Gemini CLI | `GEMINI_SYSTEM_MD` env var can point at a fully custom `system.md`, replacing the default provider-specific prompt entirely | Referenced in [`gemini-cli/README.md`](./gemini-cli) |
| Codex CLI | `--config experimental_instructions_file=<path>` overrides the built-in instructions (marked experimental) | [`openai/codex` discussion #7296](https://github.com/openai/codex/discussions/7296) |
| OpenCode | Fully custom agents via `"agent": { "review": { "prompt": "{file:...}" } }` in config, plus a built-in read-only "Plan" agent as a lighter-weight option than "build" | [OpenCode docs, Agents](https://opencode.ai/docs/agents/) |

So the capability to avoid shipping a whole general-purpose coding-agent
prompt just to review a diff **exists on every platform** represented in
this collection.

### (c): none of the actual review tools in this collection use it

This is the part worth sitting with. Every source that runs inside a host
agent — all 6 Claude Code skills, `claude-code-action`, `gemini-code-review`,
`codex-review`, and `opencode-review` — relies on that host's **default,
full** system prompt and layers its review instructions on top, rather
than overriding it with something leaner:

- None of the `create-prompt`/formatter code in `claude-code-action`, and
  none of the Claude Code skill files, set `system_prompt`/`--append-system-prompt`
  or the SDK's `preset` option — checked directly in the source, not
  inferred.
- `gemini-code-review`'s command `.toml` files and its GitHub Actions
  wiring (`workflow-example/gemini-review.yml`) contain no reference to
  `GEMINI_SYSTEM_MD` — checked directly, no match.
- `codex-review`'s GitHub Actions example builds `codex-prompt.md` and
  runs plain `codex exec`/`openai/codex-action` — no
  `experimental_instructions_file` anywhere in the workflow.
- **`opencode-review` was checked specifically because of this question**,
  and it's the clearest case: `github.handler.ts` explicitly falls back to
  `default_agent` from config, or `"build"` — OpenCode's full
  general-purpose, edit-capable coding agent — [when no `agent` input is
  set](https://github.com/anomalyco/opencode/blob/dev/packages/opencode/src/cli/cmd/github.handler.ts).
  A leaner "Plan" (read-only) agent exists and a fully custom one can be
  configured, but **neither is the default** — you have to opt in.
  Worse, an [open OpenCode issue](https://github.com/anomalyco/opencode/issues/5005)
  reports that even explicitly disabling the Plan/Build/General agents
  doesn't stop OpenCode's own default persona text from being injected —
  so even opting in doesn't cleanly guarantee you've fully escaped the
  base prompt.

`pr-agent` remains the only source that's a genuinely bare model call by
construction — not because it made a deliberate "run lean" choice that
the others declined, but because it was never built on top of a host
agent CLI in the first place. It calls the API directly with its own
`system=`/`user=` fields (see below) — there's no larger prompt underneath
it to strip away.

### What precedes the diff, source by source

| Source | Real system/user split? | What precedes the diff |
|---|---|---|
| `pr-agent` | **Yes** — literal `system=`/`user=` fields sent as separate API roles | Persona ("You are PR-Reviewer...") → a full **worked example of the diff format itself** (fake file, fake hunks) before any real data appears → rules for what to flag and how to word comments → optional `skills_context`/`extra_instructions` → the Pydantic output schema. All of this is in `system`; the real diff only ever appears in `user`. This is the only source that teaches the model its diff format via example ahead of time rather than just handing over real hunks and hoping the model infers the convention. |
| `codex-review` | No — one flat prompt file, on top of Codex CLI's full default system prompt | Persona/instructions text ("You are acting as a reviewer for a proposed code change...") is written to `codex-prompt.md` first; repo/PR metadata and the unified diff are appended to the *same file* afterward, by a shell script, not a separate message. |
| `security-guidance` | No | A persona line ("You are a security expert reviewing {language}...") and instructions, with the actual diff/file content interpolated in after by the calling Python code. |
| `gemini-code-review` (`/pr-code-review`) | No, but persona is skill-gated, on top of Gemini CLI's full default system prompt | The template's `<CONTEXT>` block (repo, PR number, tool names to call — **not diff text**) appears first, followed by a `<PROTOCOL>` directive that activates the `code-review-commons` skill (persona, objective, instructions, constraints) *before* the model ever calls the tool that returns the actual diff. |
| `gemini-code-review` (`/code-review`, local) | Same shape | `<CONTEXT>` says "call `git diff` to retrieve the changes" — a pointer, not inline diff — then the same commons-skill activation happens before the diff is fetched. |
| `claude-code-action` (tag mode) | No, but a large fixed context envelope precedes Claude's own reasoning, on top of Claude Code's full default system prompt | Strict order: `<context>` → `<pr_body>`/`<issue_body>` → `<comments>` → `<review_comments>` → `<changed_files>` → `<metadata>` → `<trigger_comment>`. Notably **no diff content anywhere** in this envelope — Claude is instructed at the end to run `git diff` itself if it needs one, so "before the diff" here really means "before Claude decides to go get one." |
| `opencode-review` | No, same shape as Claude Action, on top of OpenCode's full "build"-agent default system prompt | `<github_action_context>` (meta-instructions: PR push/creation happens automatically, don't caveat about it) → `<pull_request>` block (title/body/author/branches/state/additions/deletions/commit count/file count) → `<pull_request_comments>` → `<pull_request_changed_files>` (list only, no diff) → `<pull_request_reviews>` (formal reviews). Also no diff content — same "model fetches it itself" pattern as Claude Action. |
| `turingmind`, `agent37/local-review`, `anthropic/code-review`, `pr-review-toolkit`, `claude-code-cookbook`, `bmad-code-review` | No — a single flat Markdown command/skill file, on top of Claude Code's full default system prompt | Frontmatter (`allowed-tools`, `description`) → a one- or two-line description of the command's job → (for `anthropic/code-review` specifically) an explicit "Agent assumptions" constraints block → numbered steps. Fetching the diff is itself an early **step**, not data injected ahead of the instructions — there's no persona statement ("You are X") in most of these at all; the operative persona at that point is just Claude Code's own default. |

**Takeaway**: the "system prompt, then diff" mental model really only
applies cleanly to `pr-agent`. Everything else either (a) fetches the
diff on demand as part of following instructions, so there's no fixed
"before/after" boundary, or (b) is a thin instruction layered on top of a
much larger, separately-authored host system prompt that this repo
documents elsewhere (`gemini-cli/`, `codex/`, `opencode/`,
`leaked/claude-code/`) — and, per the research above, could in principle
be swapped for something leaner on every one of these platforms, but
isn't, in any of the actual published review tools checked here.

### (d) Two instructions nobody else gives the reviewer

`autoreview`'s prompt carries two rules that are not about *what* to
find, but about the economics and the psychology of a single pass, and
neither has an analogue elsewhere in this collection.

**Round-cost economics, stated to the model:**

> Report EVERY distinct actionable defect in this single pass, ordered
> most severe first. **Each review round costs the caller a full
> fix-test-review cycle; withholding a known defect until a later round
> wastes one.**

Most prompts here ask for completeness. This one explains what
incompleteness costs the human, which is the difference between a
preference and a reason. It matters most in a hands-off pipeline, where
a second round is not "the reviewer adds a comment" but an entire
dispatch.

**An explicit second sweep against attention collapse:**

> Before returning, sweep the bundle once more for independent defects
> in other files or failure modes that you may have stopped scanning for
> after an earlier find.

That is a named failure mode — the model finds something good, and its
remaining attention narrows around it — addressed with a cheap
deterministic instruction rather than a second model call. Compare §6's
validation passes, which all check findings that *were* made; this
checks for findings that were not.

Two more, for completeness. Nested review is forbidden **by name**
(*"Forbidden nested review commands include: codex review, autoreview,
claude review, oracle review"*), which is what stops a reviewer with
shell access from recursively spawning reviewers. And oversized bundles
are chunked with a byte-exactness assertion — the code raises
`internal error: review bundle chunking omitted or reordered input` if
concatenation does not reproduce the bundle — with the chunk prompt
telling the model that *"original change bytes appear exactly once
across the chunk sequence"* and that repeated headers in continuation
context *"are not extra change content."*

## 3. Context construction — diff format

The most consequential low-level choice: how does the diff actually reach
the model?

| Approach | Sources |
|---|---|
| Custom decoupled hunk format — separate `__new hunk__`/`__old hunk__` blocks, line numbers injected into the new hunk only | `pr-agent` (both `/review` and `/improve`) |
| Structured API result with LEFT/RIGHT line numbers per hunk (not raw text) | [`gemini-code-review`](./github-pr-bots/gemini-code-review) `/pr-code-review` (`pull_request_read.get_diff`) |
| Plain unified diff, pre-baked directly into the prompt text | [`codex-review`](./github-pr-bots/codex-review) (`git diff --unified=5`), [`gemini-code-review`](./github-pr-bots/gemini-code-review) `/code-review` (`git diff -U5 --merge-base`), [`security-guidance`](./skills/anthropic/security-guidance) |
| Diff-source cascade with format validation + chunking for huge diffs | [`bmad-code-review`](./skills/bmad-code-review) (staged/uncommitted/branch/commit-range/pasted, >3000 lines → offer to chunk) |
| No pre-formatted diff at all — the model runs `git diff`/`gh` itself when it needs one | [`agent37/local-review`](./skills/agent37/local-review), [`turingmind`](./skills/turingmind), [`anthropic/code-review`](./skills/anthropic/code-review), [`pr-review-toolkit`](./skills/anthropic/pr-review-toolkit), [`claude-code-cookbook`](./skills/claude-code-cookbook), [`claude-code-action`](./github-pr-bots/claude-code-action) tag mode, [`opencode-review`](./github-pr-bots/opencode-review) |

**Takeaway**: pre-formatting the diff (PR-Agent, Gemini, Codex) means the
tool controls exactly what the model sees and can guarantee line-number
accuracy for later comment-posting; leaving it to the model (most Claude
Code skills) is simpler to build but pushes correctness of "which line is
this on" onto the model actually running the right `git diff` invocation.

## 4. Extra context beyond the diff

| Context source | Sources |
|---|---|
| `CLAUDE.md`/`AGENTS.md` compliance | [`agent37/local-review`](./skills/agent37/local-review), [`anthropic/code-review`](./skills/anthropic/code-review), [`turingmind`](./skills/turingmind), `codex-review` (implicitly, via normal CLI behavior) |
| **`AGENTS.md` compliance with an attribution contract** — the rule file is not just context, a finding that leans on it must *cite* it | Codex CLI's `ReviewTask` rubric (read 2026-09-12; [`codex/review-rubric.md`](./codex/review-rubric.md)). Precedence is stated (`AGENTS.override.md`, then `AGENTS.md`, then configured fallbacks, more-specific wins) and the format is deliberately loose — "Guidance may use headings, checklists, bullets, tables, or concise prose; do not require formal IDs or schemas." Then the contract: a finding is **rule-supported** "only when applicable guidance materially contributes repository-specific scope, an invariant, remedy, convention, or confirmation behavior **beyond generic correctness advice**", and every rule-supported finding must carry "the applicable project instruction file that supplies the rule and its **smallest supporting line range**", with "Do not fabricate citations." See §11a. |
| Linked issue-tracker ticket (Jira/Linear-shaped: title, requirements, DoD) | `pr-agent` |
| Spec/story file + frontmatter-referenced docs, for acceptance-criteria checking | [`bmad-code-review`](./skills/bmad-code-review) (gates a whole extra "Acceptance Auditor" review layer) |
| Org-wide review standards / injected "skills" text | `pr-agent` (`skills_context`, `repo_context`) |
| Existing PR comments / formal reviews, as context | [`claude-code-action`](./github-pr-bots/claude-code-action) tag mode (see §8), [`claude-code-cookbook`](./skills/claude-code-cookbook) `pr-fix` |
| Prior review state (what changed *since the last review*) | [`security-guidance`](./skills/anthropic/security-guidance) |
| None beyond the diff + PR title/body | [`codex-review`](./github-pr-bots/codex-review), [`gemini-code-review`](./github-pr-bots/gemini-code-review) `/pr-code-review` |

**Accumulated context — what the reviewer learned from previous
reviews** — is a category none of the open-source prompts above have,
and all three major closed-source reviewers do. See
[`agent-memory-learning.md`](./agent-memory-learning.md) §8 for the
detail: Qodo Merge mines *accepted* suggestions monthly into a
`.pr_agent_auto_best_practices` file injected through the same slot as
hand-written best practices (the open-source `pr-agent` ships the config
keys and an empty `relevant_best_practices` prompt variable, but not the
generator); CodeRabbit turns natural-language replies on a PR into
scoped, admin-approvable "learnings" loaded on every comment it writes;
and Greptile learns implicitly from 👍/👎 reactions and from whether a
comment was addressed between first and last commit, suppressing comment
classes the team keeps ignoring — with security findings exempted from
suppression. The signal these three learn from is human reaction to
their own output, which is why their loops run automatically while
coding agents' self-mined memory tends to sit behind an approval queue.

**The opposite move: deliberately withholding the repository.**
Every row above adds context. `autoreview` removes it, and says so to
the model:

> The review sandbox is intentionally empty. The change bundle and
> explicit prompt or datasets are the only reviewed-repository source.
> Read-only tools cannot access unchanged repository files.

The Codex adapter runs the reviewer in an empty workspace so ignored
files and linked-worktree metadata are unreadable. The point is not
economy — the reviewer keeps web search and read-only tools *for
external dependency contracts and upstream docs* — it is that a
reviewer with a working tree will wander into it and report on code the
PR never touched.

That trade has an obvious failure mode, and the prompt closes it with
the corollary rule rather than leaving it implicit:

> Do not report a missing import, symbol, definition, call site, config
> entry, or other unchanged context solely because it is absent from the
> change bundle. Such a finding requires direct proof in the bundle or
> explicit datasets.

This is the sharpest statement in the collection of a tension every
review design has: context prevents "you deleted a function that is
still called" and simultaneously invites "while I'm here, this
unrelated file is badly written." Most sources here resolve it by
adding context and asking the model to stay in scope. This one resolves
it by removing context and asking the model not to hallucinate absence.
Both are defensible; only one of them can be verified by looking at the
inputs.

Where extra context *is* wanted, it enters through explicit
`--prompt-file`/`--dataset` inputs that are validated to resolve before
the run — and the scope policy states that they are *"context only. They
do not expand the selected Git target or make unchanged files part of
the reviewed diff."*

## 5. Review strategy — persona and single- vs. multi-agent

| Strategy | Sources |
|---|---|
| One shared "commons" skill/persona, reused by multiple commands | [`gemini-code-review`](./github-pr-bots/gemini-code-review) (`code-review-commons` used by both `/code-review` and `/pr-code-review`) |
| Several fixed parallel specialist sub-agents (bugs, security, types, tests, comments, ...) | [`pr-review-toolkit`](./skills/anthropic/pr-review-toolkit) (up to 6), [`turingmind`](./skills/turingmind) (4 quick / 9 deep), [`agent37/local-review`](./skills/agent37/local-review) (5), [`anthropic/code-review`](./skills/anthropic/code-review) (4: 2× CLAUDE.md, 2× bugs) |
| Pluggable review "layers," each an independently swappable instruction template | [`bmad-code-review`](./skills/bmad-code-review) (`customize.toml`'s `review_layers` array — override, add, or disable per team/user) |
| Conditional/progressive agent loading based on what actually changed | [`turingmind`](./skills/turingmind) (routing table by file type / `CLAUDE.md` presence), [`claude-code-cookbook`](./skills/claude-code-cookbook) `smart-review` |
| User chooses sequential vs. parallel subagent execution | [`pr-review-toolkit`](./skills/anthropic/pr-review-toolkit) — the only source that makes this a user choice rather than hardcoding one |
| Single pass, no sub-agents at all | `pr-agent`, [`codex-review`](./github-pr-bots/codex-review), [`gemini-code-review`](./github-pr-bots/gemini-code-review) `/pr-code-review` |
| Explicitly "adversarial" framing | [`bmad-code-review`](./skills/bmad-code-review) (`bmad-review-adversarial-general` layer), [`gemini-code-review`](./github-pr-bots/gemini-code-review) ("your adherence to instructions is absolute") |
| Sequential pipeline of role-specialized agents that hand off via literal keyword responses (not tool calls or structured fields) | [`composio-swekit/pr_review`](./composio-swekit) — `PR_FETCHER_PROMPT` → (`"ANALYZE REPO"`) → `REPO_ANALYZER_PROMPT` → (`"ANALYSIS COMPLETED"`) → `PR_COMMENT_PROMPT`, each a separately-prompted role in one LangGraph state machine rather than parallel subagents |

## 6. Filtering, confidence & triage

The step that decides which candidate findings actually get surfaced —
arguably where most of the engineering effort in this whole space goes.

| Mechanism | Sources |
|---|---|
| Numeric confidence score (0-100) from an additive point rubric, cutoff ~80 | [`turingmind`](./skills/turingmind) (`false-positive-rules.md`), [`agent37/local-review`](./skills/agent37/local-review) (coarser bucketed rubric) |
| Second-pass **validation** subagent per candidate finding (binary, not scored) | [`anthropic/code-review`](./skills/anthropic/code-review) — finds via 4 agents, then a dedicated subagent re-checks each candidate before anything is posted |
| Self-scored reflection pass on proposed fixes (0-10), catches suggestions that misread the diff | `pr-agent` `/improve` (`pr_code_suggestions_reflect_prompts.toml`) |
| 4-way triage bucket instead of a score: `decision_needed` / `patch` / `defer` / `dismiss` | [`bmad-code-review`](./skills/bmad-code-review) — also the only one requiring the model to *read surrounding code* before rating severity, not just the diff hunk |
| Two-pass LLM verification: initial scan → broader "final review" pass → separate refutation prompt | [`security-guidance`](./skills/anthropic/security-guidance) |
| Severity classification only, no explicit false-positive filtering step described | [`gemini-code-review`](./github-pr-bots/gemini-code-review), [`codex-review`](./github-pr-bots/codex-review) (has a `confidence_score` field but no filtering logic in the prompt), [`claude-code-cookbook`](./skills/claude-code-cookbook) |
| Explicit "show what got filtered and why" transparency to the user | [`turingmind`](./skills/turingmind) only — a fixed "Filtered Issues" section with counts by reason |
| Suppress anything a green CI gate already proves, as a stated scope rule | [`dsh-code-review`](./deepseek-harness) — "omit issues already enforced by a green gate"; the skill's declared job is the residue automation cannot reach |
| Volume cap stated as a preference, not a threshold: one substantiated blocker beats a list | [`dsh-code-review`](./deepseek-harness) — "a short review with one substantiated blocker is better than a list of nits" |
| **Priority threshold injected as a prompt preamble, plus an anti-inflation clause** | [`autoreview`](./openclaw) — `--max-priority` defaults to **P0**, and the threshold is prepended to the prompt rather than applied as a post-filter: *"Finding threshold: report only P0. Omit all lower-priority observations, polish, speculative risks, and follow-up ideas outside that threshold. **Do not mark the patch incorrect solely for an omitted lower-priority issue.**"* The second sentence is the part worth stealing: a schema with both a per-finding `priority` and a summary `overall_correctness` will otherwise have the model fail the patch on something it was just told not to report. |
| **Scope discipline as its own policy block, with a release-freeze mode** | [`autoreview`](./openclaw) — a separate `review_scope_policy()` block states that the helper *"is a closeout gate. Do not turn a narrow patch into a broad redesign request,"* that *"a broader ideal design is not an actionable finding unless the current patch cannot safely land,"* and that where the right fix needs a new protocol, migration or contract the finding must still *"stay tied to the smallest changed line that proves the current patch is not landable."* On a release branch it switches to freeze discipline — only blockers, backport regressions, install/upgrade breakage, crashes, data loss, concrete security exposure or release-infrastructure failures. This collection has plenty of "stay in scope" instructions; this is the only one that is a *mode*. |

## 7. Output format & schema

| Format | Sources |
|---|---|
| Machine-enforced JSON Schema (OpenAI structured outputs, `additionalProperties: false`) | [`codex-review`](./github-pr-bots/codex-review) — the strictest in the collection |
| Pydantic-modeled YAML (documented schema, not API-enforced) | `pr-agent` |
| Fixed Markdown template with fill-in placeholders | [`turingmind`](./skills/turingmind) (`output-format.md`), [`agent37/local-review`](./skills/agent37/local-review), [`gemini-code-review`](./github-pr-bots/gemini-code-review) `/code-review` |
| Freeform Markdown, examples given but not a strict schema | [`claude-code-cookbook`](./skills/claude-code-cookbook), [`pr-review-toolkit`](./skills/anthropic/pr-review-toolkit) |
| Structured checklist items written into a project file, not chat | [`bmad-code-review`](./skills/bmad-code-review) (`- [ ] [Review][Patch] ...` in the story file) |
| Tag-delimited request-side structure (this is input formatting, included because it's the same idea applied to context instead of output) | [`claude-code-action`](./github-pr-bots/claude-code-action) (`<context>`, `<comments>`, `<review_comments>`, `<changed_files>`, `<trigger_comment>`) |

## 8. Proposed-change format

How (or whether) a fix actually gets proposed, not just described.

| Format | Sources |
|---|---|
| Structured `existing_code`/`improved_code` snippet pair, self-verified before surfacing | `pr-agent` `/improve` |
| GitHub-native committable ` ```suggestion ` block | [`anthropic/code-review`](./skills/anthropic/code-review) (only when it's small/self-contained), [`gemini-code-review`](./github-pr-bots/gemini-code-review) `/pr-code-review` |
| Fenced ` ```diff ` block, **required** on every finding | [`turingmind`](./skills/turingmind) — the only source with no "no fix" escape hatch |
| Freeform code snippet, encouraged but optional | [`agent37/local-review`](./skills/agent37/local-review), [`claude-code-cookbook`](./skills/claude-code-cookbook) |
| Direct file edits once a finding is approved — no suggestion step at all | [`bmad-code-review`](./skills/bmad-code-review) (`patch` bucket) |
| No fix proposed, ever — issue-only by design | `pr-agent` `/review`, [`pr-review-toolkit`](./skills/anthropic/pr-review-toolkit) (freeform "concrete fix suggestion" text, no schema), [`codex-review`](./github-pr-bots/codex-review) (schema literally has no field for it) |

## 9. Delivery mechanism & existing-comment handling

Where the output actually ends up, and whether the tool is aware of
what's already on the PR.

| Delivery | Existing comments read? | Sources |
|---|---|---|
| Real inline GitHub PR comments (MCP tool) | Checks only if *the bot itself* already commented, to avoid re-running | [`anthropic/code-review`](./skills/anthropic/code-review) |
| Real inline GitHub PR review comments via `GITHUB_CREATE_A_REVIEW_COMMENT_FOR_A_PULL_REQUEST`, plus a final quality-rating comment | **Yes — the most explicit dedup instruction found anywhere in this collection**: told twice to call `GITHUB_LIST_REVIEW_COMMENTS_ON_A_PULL_REQUEST` and "check before commenting if that comment has already been made, and avoid making duplicate comments," not just for its own prior runs but generally | [`composio-swekit/pr_review`](./composio-swekit) |
| GitHub's native pending-review flow (create → add comments → submit, locked to event type `COMMENT`) | No | [`gemini-code-review`](./github-pr-bots/gemini-code-review) `/pr-code-review` |
| Raw REST API `curl` calls, no `gh`/MCP | No — will duplicate comments on re-run | [`codex-review`](./github-pr-bots/codex-review) |
| Single structured summary object/comment, not per-line | No | `pr-agent` `/review` |
| Single plain issue/PR comment via a direct REST call | No | [`opencode-review`](./github-pr-bots/opencode-review) (`octoRest.rest.issues.createComment`) |
| One continuously-updated tracking comment; formal reviews/approvals explicitly forbidden | Yes — both regular comments and formal PR reviews are pre-loaded as context (kept in separate prompt sections) | [`claude-code-action`](./github-pr-bots/claude-code-action) tag mode |
| Reading existing comments **is the entire point** — classifies them, then produces reply templates back to reviewers | Yes, exclusively | [`claude-code-cookbook`](./skills/claude-code-cookbook) `pr-fix` |
| Terminal/chat output only, nothing touches GitHub | N/A | [`agent37/local-review`](./skills/agent37/local-review), [`turingmind`](./skills/turingmind), [`pr-review-toolkit`](./skills/anthropic/pr-review-toolkit) (despite being framed as PR review — no GitHub comment tool in its `allowed-tools` at all), [`gemini-code-review`](./github-pr-bots/gemini-code-review) `/code-review` |
| Written into project files instead of GitHub (spec/story file, sprint-status.yaml, deferred-work.md) | No | [`bmad-code-review`](./skills/bmad-code-review) |
| Inline editor reminders injected as you type/commit, not a comment at all | N/A (not comment-based) | [`security-guidance`](./skills/anthropic/security-guidance) |

**A consumer-side contract — how the *calling* agent must treat the
output — which no other source here ships.** `autoreview`'s `SKILL.md`
is largely not a review prompt at all; it is instructions for whoever
invoked the review:

- *"Treat review output as advisory. Never blindly apply it."*
- *"Verify every finding by reading the real code path and adjacent
  files"*, and read dependency docs/source/types when a finding depends
  on external behaviour.
- *"Reject unrealistic edge cases, speculative risks, unrelated
  rewrites, and fixes that over-complicate the codebase."*
- *"Run one bounded review pass… rerun Autoreview only when the user
  explicitly requests another pass"* — and, pointedly, *"Stop as soon as
  the helper exits 0 with no accepted/actionable findings. Do not run an
  extra review just to get a nicer 'clean' line, a second opinion, or
  clearer closeout wording."*
- Patience rules against a caller killing a slow reviewer: heartbeat
  lines are *"healthy progress, not a hang"*, and *"Do not kill a review
  just because it has been quiet for 2-5 minutes."*
- A guard against laundering a partial result into a clean bill:
  *"Treat `scoped-clean` with exit 0 as clean only for the selected Git
  target and requested priority. `filtered` is not a correctness
  certificate; `incomplete` requires resolving the scope mismatch."*

And an anti-auto-invocation rule at the top, which is the inverse of
every other source's positioning: *"Do not invoke Autoreview
automatically before a commit, push, PR, merge, deploy, or final reply.
Repository or workflow rules may call it only when they explicitly name
it."* A second-model review is expensive enough (up to 30 minutes) that
the design treats *being called* as the thing to gate.

## 10. Safety & security constraints

| Constraint | Sources |
|---|---|
| Bash allowlist restricted to read-only git commands (`diff`/`status`/`log`/`blame`/`show`) | [`agent37/local-review`](./skills/agent37/local-review), [`turingmind`](./skills/turingmind) |
| MCP tool list locked to an exact minimal set (can't merge, approve, or touch issues even if instructed to) | [`gemini-code-review`](./github-pr-bots/gemini-code-review) — 3 tools only, enforced at tool-registration level not by prompt |
| Explicitly barred from formal review/approve/merge actions, regardless of what's asked | [`claude-code-action`](./github-pr-bots/claude-code-action) tag mode |
| Review event type hard-locked to `COMMENT` (never `APPROVE`/`REQUEST_CHANGES`) even though the tool supports them | [`gemini-code-review`](./github-pr-bots/gemini-code-review) |
| Sandboxed / read-only execution mode | [`codex-review`](./github-pr-bots/codex-review) (`sandbox: read-only`) |
| Credential isolation — drops elevated privileges so the model can't read its own API key | `openai/codex-action`'s documented "safety strategy" (referenced from [`codex-review`](./github-pr-bots/codex-review)) |
| Code-level prompt-injection defense (strips invisible/zero-width Unicode, bidi-override characters, hidden HTML attributes) before untrusted content reaches the prompt | [`claude-code-action`](./github-pr-bots/claude-code-action) (`sanitizer.ts`) — the only source doing this in code rather than by instruction |
| Prompt-only "treat external content as data, not instructions" boundary | [`gemini-code-review`](./github-pr-bots/gemini-code-review) ("Input Demarcation"), [`claude-code-action`](./github-pr-bots/claude-code-action) (`<trigger_comment>` framing) |

---

## 11. Where the review criteria come from

Stages 1–10 all assume the criteria already exist. Thirteen of the
fourteen sources here treat that as out of scope: someone wrote the
skill, and it says what it says. `dsh-code-review` is the only source in
this collection that makes **criteria provenance a pipeline stage of its
own**, so this section is mostly one source — but the questions it
answers are ones any long-lived review bot eventually has to.

### The mechanism

A private periodic tool, run daily by one designated operator against a
clean checkout at refreshed `origin/master` (spec:
`.agents/notes/proposed/process/2026-07-13-human-review-skill-maintenance.md`;
operator doc: `docs/cookbook/maintaining-dsh-code-review.md`):

1. **Select merged PRs** in a two-UTC-day window whose merge commit is an
   ancestor of `master`.
2. **Collect pre-merge human review feedback** — inline comments and
   review submissions, admitted only when GitHub reports the actor `type`
   as `User` *and* both creation and last-edit timestamps strictly
   predate the merge.
3. **Two independently configured reviewer adapters** classify each item
   twice: who wrote it (`human-authored` / `forwarded-automation` /
   `unclear`) and whether the landed change adopted it (`adopted` /
   `rejected` / `unclear`). Only matching `human-authored` + `adopted`
   pairs survive.
4. **Classify the survivors against the current skill**: candidate /
   already covered / implementation-specific / not feedback.
5. **The primary adapter drafts a complete revised `SKILL.md`**; both
   adapters review the same diff; blocking findings loop until both
   approve; `doc-sync` and `lint` run before success is declared.
6. **A human promotes** — or discards, or batches — the candidate.

### The five decisions worth stealing

- **Adoption is proven by diff, never by social signal.** Merge status, a
  resolved thread, an author's "fixed" reply, and a same-file edit are
  each explicitly named as *context rather than adoption proof*. The
  comparison is between two PR-specific patch snapshots —
  `merge-base(B,T)→B` at feedback time and `T→M` at landing — chosen
  precisely so that a change arriving independently on the target branch
  appears in neither, and cannot be miscredited to the comment. This is
  the single most transferable idea in the source: **"did the author act
  on this?" is a question about the tree, not about the thread.**
- **The learning source is human feedback only, by contract.** Bot
  findings are excluded, and so are humans forwarding bot findings —
  rejected explicitly, on the grounds that the source contract is human
  review. A review bot that learns from review bots converges on
  whatever the bots already emphasise.
- **Two adapters, never one as both author and judge.** The stated reason
  is that "independent verdicts expose unsupported generalization before
  it reaches the skill." The tool refuses to run when the two adapter
  commands resolve to byte-identical executables — while the Agent Note
  admits in its Risks section that byte-distinctness is all it can check,
  and genuine provider independence is a deployment contract it cannot
  verify.
- **Mined feedback is untrusted input.** It is wrapped in an
  `<untrusted-feedback nonce="…">` block with a 128-bit nonce so a comment
  body cannot forge the closing tag; adapters run with a scrubbed
  environment and `cwd` in a private run directory, not the repo root.
  This is the only place in this collection where a review pipeline
  treats *the review comments themselves* as a prompt-injection surface.
- **The human promoting is instructed not to defer.** "Do not defer to
  'the reviewers approved'; the maintainer contract is that the operator
  makes the final decision" — and is told exactly what to hunt for:
  checklist bloat, historical prose, unsupported extrapolation from a
  single incident, duplicated coverage. Committing adapter output
  verbatim is called out as wrong; small edits during promotion are
  "expected and preserve the reviewer judgment the workflow depends on."

### What the measured run says

The Agent Note's acceptance criteria carry the numbers from the
2026-07-15 end-to-end run: **62 merged PRs scanned, 5 skipped, 426 human
feedback items considered, 0 candidates surfaced.** Adoption plus
analysis took ~8 minutes across the two adapters, and one adapter
id-hallucination was absorbed by batch-level fail-closed without aborting
the run.

Zero is the headline result, and the cookbook pre-empts the obvious
misreading: "Days without a skill update are the workflow behaving
correctly, not a stall." A pipeline that turns 426 comments into zero
rule changes is one whose filters are doing the work — the failure mode
it was built against is checklist bloat, and the note names the two ways
in: "treating every comment as a lesson produces checklist bloat;
treating merge, thread resolution, or an author's 'fixed' reply as proof
of adoption promotes feedback that the final code may not implement."
Note also that recurrence is explicitly *not* required — "a singleton may
qualify" — so the zero is not an artifact of demanding repeated evidence.

### The rest of the loop that isn't the loop

Two adjacent process documents in the same repo carry the review lessons
that didn't fit in a skill:

- **Regression guards must be proven to fail.** From
  `docs/cookbook/responding-to-pr-review-on-a-stack.md`: "prove it FAILS
  on the unfixed code (introduce the regression, watch red, revert) — a
  guard that passes both ways guards nothing." Same doc, on delegation:
  "a sub-agent's report describes intent, not necessarily what landed …
  A sub-agent that reframes a problem as already handled is a signal to
  dig in personally."
- **Review-state handoff is modelled as commands, not derived state**
  (`.agents/notes/implemented/process/2026-08-10-event-directed-pr-review-status.md`).
  `review_requested` → `In review`; `review.submitted` with state
  `changes_requested` → back to `In progress`. The note rejects deriving
  it from GitHub's aggregate `reviewDecision` because an old
  `CHANGES_REQUESTED` stays effective after the author has fixed the code
  and re-requested review — and guards the one backward transition on the
  latest status event having been written by the automation actor, so
  automation can never overwrite a human-owned status.

## 11a. Repository rules as a citation obligation, not a context blob

Added 2026-09-12. §11 is about where review criteria *come from* over time;
this is the adjacent question of what a reviewer owes the reader when a
finding rests on a repository's own written rule. Codex's rubric is the only
source here that answers it, and the answer is three constraints that only
make sense together.

**One: a rule has to earn the label.** Rule-supported means the guidance
"materially contributes repository-specific scope, an invariant, remedy,
convention, or confirmation behavior beyond generic correctness advice." A
repo whose `AGENTS.md` says "write clear code" has not supplied a rule; a
repo that says "all DB writes go through `withTx`" has. Without this test,
every finding becomes nominally rule-supported the moment a rule file exists
anywhere in the tree, and the label stops carrying information.

**Two: the citation must be minimal and real.** "Verify the applicable
project instruction file that supplies the rule and its **smallest
supporting line range**, then include one compact Markdown or local-file
reference in the finding body. Do not fabricate citations or add hidden
metadata or output fields." Pointing at a 400-line conventions document is
not a citation — it is a dare. The smallest-range rule is the same discipline
the rubric already applies to `code_location` ("avoid ranges longer than
5–10 lines"), turned on the reviewer's own evidence.

**Three, and this is the one most implementations would miss: the presence
of a rule file must not change the finding set in either direction.** "Do
not omit ordinary findings or invent findings solely because a rule file
exists." Both failure modes are real and they pull opposite ways. A reviewer
handed a style guide drifts into enforcing it and stops hunting bugs; a
reviewer told that rule-supported findings are the valuable ones starts
quietly dropping the correctness findings it cannot attribute. One sentence
closes both.

The rubric pairs this with **P0–P3 priority tags**, mirrored as a numeric
`priority` field in the JSON, and the P0 definition is worth quoting because
it defines severity by the *absence of preconditions* rather than by impact:
"Drop everything to fix. Blocking release, operations, or major usage. **Only
use for universal issues that do not depend on any assumptions about the
inputs.**" Compare `autoreview`'s threshold-as-preamble in §6, which uses P0
as a filter; here P0 is a claim about how the bug triggers, which is
checkable by the author in a way that "how bad is it" is not.

One more line, added in the same pass, belongs with §6's attention-collapse
material: **"Do not stop at the first qualifying finding. Continue until
you've listed every qualifying finding."** `autoreview` spends a paragraph
building an explicit second sweep for the same reason; this is the one-sentence
version, and it sits directly beside the opposite instruction ("If there is
no finding that a person would definitely love to see and fix, prefer
outputting no findings"), which is the pairing that makes either safe.

## 12. How much human attention: the August–October 2026 shift

*Added 2026-10-17 from a pass over vendor changelogs and docs (Aug–Oct
2026) and the open-source review sources re-read at their current heads.
Sources and SHAs are in [`sources.md`](./sources.md), "The review-attention
pass".*

Through mid-2026 every source in this document answered one question:
*what is wrong with this diff?* In the three months to October the
industry added a second output, and it is a separate one: **how much
human attention, and from whom, this change needs before it merges.**
Anthropic states the target most plainly in its [code-review
post][anth-post]: "the least human review time that doesn't increase
reverts or incidents". Reverts and incidents are the guardrail, and
approvals per PR, human comments and wait time are what gets driven down.

### What each source now produces besides findings

| Source | Attention / risk output | Set by | Can it lower human involvement on its own? |
|---|---|---|---|
| **Anthropic internal** ([post][anth-post]) | Low / medium / high tier → 0 / 1 / 2 human approvers. Low = docs, copy, additive-behind-a-flag; medium includes named sensitive areas (caching, auto-updater, system prompts); high = two people | A classifier, from **the change, not the author**; a second classifier **can only escalate**; lighter paths only for trusted authors | Yes for low tier, after green checks. An agent's approval never counts as a human's, the person who prompted an agent change is a required reviewer, and approvals bind to one commit |
| **Claude Code Review** (GA 2026-10-15) | Severity counts as machine-readable JSON in the check run (`{"nit","normal","pre_existing"}`); the check itself is always neutral | Review agents | No. It "never approves or blocks"; gating is left to the customer's CI parsing the counts, and a **missing** count line must be read as "no verdict", not zero |
| [`agent-approval-check`](./github-pr-bots/agent-approval-check) (Anthropic, MIT) | Required status: N human approvals on agent-authored PRs | Deterministic; triggered by **authorship** | No. Fails closed; exempt paths are the only relaxation |
| [`pr-stamp-sweep`](./github-pr-bots/agent-approval-check) (Anthropic, MIT) | `stamp / needs-discussion / skip`, `securitySensitive` by *what is touched*, and an adversarial verifier **only on stamp candidates** | Two agents | It recommends; a maintainer stamps |
| [PR-Agent](./pr-agent) (2026-08-31 →) | `risk_level`, `merge_recommendation` (`no_concerns_found / needs_review / changes_required`), `failure_modes` with `detected_by` / `covered_in_this_pr`, `review_priority_files` | The model, in one pass, all opt-in | No; advisory fields in the review comment |
| **Cursor Bugbot** | `riskScore` in the PR summary; effort `low / default / high / smart`, where `smart` takes a natural-language rule for picking the level per PR | Not documented | Not by Bugbot itself. Repo config is read from the **base branch** and can lower Autofix but never enable it |
| **CodeRabbit Triage** (2026-08-13 →) | Per-PR priority P0–P3 with a stated reason; separate rated facts (risk, security risk, **blast radius**, review effort) that admin rules can match | Deterministic base score (validated finding severity, linked-ticket urgency, PRs blocked behind it) plus a model "verdict"; override order manual > verdict > admin rule > base | Yes, through a rule: "Merge low-risk changes" merges when risk *and* review effort are low and required checks and reviews pass. Branch protection still wins |
| **Copilot code review** | An effort level per review (Lite / Balanced; Balanced default since 2026-09-28); an overview split into Open (with `new`), Resolved since last review, and Previously missed | Admin/user setting | No |
| [OpenClaw ClawSweeper](./clawsweeper) | Eight domain-typed `merge-risk` labels, typed `maintainerDecision` kinds, `mergeRiskOptions` (fix / accept / pause), real-behaviour proof status, S–F proof/patch/overall tiers | The review model; code enforces protected labels and computes readiness (a D/F patch tier, missing proof, a pending decision or an unvalidated head all block) | Not any more: the automerge loop the [skill](./openclaw/clawsweeper-skill.md) describes has been retired, and `security-boundary` is the one risk label wired into a hard gate |
| **Meta DRS + RADAR** ([papers](./agent-risk-assessment.md#6-predicting-change-risk-from-history-metas-drs-and-radar)) | A predicted incident probability per diff, used as a percentile; RADAR's auto-approve when every change falls in a safe category | A model fine-tuned on expert-labelled incident causes; percentile thresholds by author or source (P5 for humans, P50 for proven runbooks) | Yes: RADAR landed 331k+ diffs with about a third the revert rate and about a fiftieth the incident rate of non-RADAR diffs; a human can still veto during a landing delay |
| **Cursor Approval Agents** | Optional risk score with a maximum threshold; per-directory `APPROVAL_POLICY.md` | Model plus Bugbot/Security findings; policies read from base | Yes, below the threshold. Never when a PR loosens its own approval policy; stricter rule on conflict |
| **gitStream** ([repo](https://github.com/linear-b/gitstream), Apache-2.0) | Estimated review minutes; labels; required approvals; auto-approve | Deterministic `.cm` rules; review time from a hosted ML model | Yes, for rule-defined safe changes (formatting, docs, tests, images) |
| [Codex repo skills](./codex/repo-review-skills.md) (removed 2026-09-30) | "P0 … need an additional manual review" for any new context item that can exceed 1k tokens | A repo-specific lens | No |

### Seven patterns, and how widely each one is shared

1. **Attention is a separate output from findings, because a clean review
   isn't a safety claim.** Claude Code Review says outright that a review
   with no findings doesn't mean the code is error-free. Bugbot (week of
   2026-10-05) stopped reporting "clean" when every finding was *filtered
   out*. CodeRabbit's docs say P3 on an unreviewed PR means no signal
   raised it, not that someone looked and found little. PR-Agent is the
   counter-example: its `risk_level` is defined mostly by findings, so a
   quiet change to a sensitive area reads `low`.
2. **The risk floor comes from what the change touches, and only goes
   up.** Anthropic's second classifier only escalates. `pr-stamp-sweep`
   defines `securitySensitive` by surface (auth, sanitisation, parsers of
   untrusted input, actor checks, shell construction). Codex's repo lens
   escalates on *touching* model-visible context. CodeRabbit lets admin
   rules match on blast radius but explicitly **not** on file paths or
   CODEOWNERS, which is the opposite choice and the weaker one for this
   purpose.
3. **Instructions that lower scrutiny need more provenance than ones that
   raise it.** Claude Code Review honours "lower severity / exclude paths /
   cap nits" in `REVIEW.md` only from a protected default branch, while
   additive rules apply more widely. Bugbot reads `bugbot.yaml` from the
   base branch so "a PR can't change how Bugbot reviews itself", and the
   file can lower Autofix but never enable it. `agent-approval-check` runs
   only on base-branch-executed triggers. All three follow the same rule:
   a relaxation must come from somewhere the PR can't write.
4. **Approval binds to a SHA, and an agent never counts.** This shows up
   in Anthropic's policy, `agent-approval-check`'s `/approve <sha>` with
   stale-flagging, ClawSweeper's "passed the exact current head", and
   Bugbot treating a run cancelled by a new push as not satisfying the
   required check (2026-09-21). The sibling-PR guard is a subtle
   consequence: a status attached to a SHA unblocks every PR with that
   head.
5. **Depth is chosen per PR, and increasingly by rule rather than by
   size.** Anthropic sets Quick / Standard / Deep by the cost of a missed
   bug. Bugbot's `smart` mode takes a prose rule. Copilot and Greptile
   (Base / Plus / Apex, reported secondhand) sell effort tiers. Only
   Anthropic ties depth to risk explicitly; the rest tie it to cost.
6. **Re-review is a state machine, and resolution has reasons.** Copilot
   added resolution reasons (*Addressed / Won't fix / Incorrect*,
   2026-08-27) and later auto-resolves its own comments by reason.
   PR-Agent feeds back `active / resolved / dismissed` findings and
   requires word-for-word restatement for identity. Claude Code Review's
   re-review now reports the count of earlier findings still open instead
   of "no issues" (2.1.295). Anthropic's convergence fixes are a
   three-round cap, diff-only re-review after a few passes, and flagging
   bug *classes*. Copilot's "Previously missed" bucket is new: older
   issues found on a later pass go **only in the overview**, never as
   inline comments, so they don't read as blame.
7. **The cheapest effective filter may not be an LLM.** Atlassian's
   [RovoDev Code Reviewer paper][rovo] (one year in production on
   Bitbucket) found its LLM factual-correctness judge "surprisingly
   ineffective". A ModernBERT **actionability classifier**, trained on
   five months of comments labelled by whether they led to a code change,
   gave the large gain (about +15–20 points of location alignment). Their
   production metric is **code resolution rate**, the share of comments
   whose lines changed in a later commit: 38.7% for the bot against
   44.45% for humans.

### What did not change

- **Nobody's reviewer approves.** Every hosted reviewer here still
  explicitly does not approve. Where a merge does happen (CodeRabbit's
  rule, ClawSweeper's automerge, Anthropic's low tier) a separate
  deterministic gate merges, using the review as one input, behind a
  switch an administrator owns.
- **No open-source source computes a risk tier from paths plus content
  with an escalate-only rule.** Anthropic's classifier is internal.
  CodeRabbit's and Bugbot's risk calculations are undocumented. PR-Agent's
  is a self-report. The design side of this repo now specifies one:
  [`agent-design/risk.md`](./agent-design/risk.md).

[anth-post]: https://claude.dev/blog/solving-code-review-at-anthropic/
[rovo]: https://arxiv.org/abs/2601.01129

## 13. Rovo Dev, Devin Review and Greptile (read 2026-10-17)

Three hosted reviewers, read from their documentation. None publishes
prompts. What is recorded here is what each does differently enough to
matter for [`agent-design/`](./agent-design).

### Atlassian Rovo Dev code review

The reviewer on Forge's own platform (Bitbucket Cloud and GitHub). Its
production results are in the RovoDev paper (§12, pattern 7): a trained
actionability classifier beat an LLM judge, and 38.7% of comments led to
a code change.
- **Triggers:** on PR creation (the default), on every commit, or manual
  only. In Bitbucket only the PR author can trigger a manual review.
- **Acceptance-criteria check against the linked Jira work item:**
  - The ticket is found from a key in the **branch name** first, then
    commit messages. **If commits name more than one key, they are
    ignored.**
  - Criteria are read from the description, or from custom fields named
    Acceptance Criteria / AC, Business / Functional Requirements, or
    Definition of Done. If the description is empty the search is skipped
    entirely, even when the custom fields have content.
  - Each criterion gets **one of three results: met, missing from the
    code, or needs manual checking.** On by default in Bitbucket.
- **Custom instructions** live in `.rovodev/.review-agent.md`: Markdown
  bullets grouped by topic. The documented examples include requiring
  risky changes to be behind feature gates and warning about publicly
  exposed authorization policy paths. The docs don't say which branch
  the file is read from.
- **Licensing:** both features need the PR author's own Rovo Dev Standard
  seat on the connected Jira site. The standalone product is being folded
  into Jira subscriptions.
- **Not documented:** severity levels, summary format, any approve or
  merge behaviour.

For Forge, the AC check is the important part. `medium.md` §3a's
ticket-compliance lens is the same idea, and Rovo settles three details
it left open: how to find the ticket, which fields to read, and a
three-valued per-criterion result.

### Cognition Devin Review

A review *interface* for large, often agent-written PRs. Its aim is to
make a human's read faster rather than to post more comments.
- **Groups related hunks** and orders them so the PR reads top to bottom,
  instead of in alphabetical file order, with an explanation per group.
- **Detects moved and copied code** and shows where it came from, instead
  of a full delete plus a full add. Cognition's point is that most diff
  viewers inflate relocated code and bury the small real edits.
- **Three-level flags:** red (probable bug), yellow (warning), gray
  (FYI), each dismissable.
- **Chat with the codebase in context**, and stacked-PR support (splitting
  large changes, fixing comments across a stack).
- Works on public PRs without an account (`devinreview` in place of
  `github` in the URL), and from a CLI (`npx devin-review <pr>`).

No risk or attention output. The two ideas worth taking are reading order
and moved-code detection, and both are things a harness can compute
before any model sees the diff.

### Greptile (v5 and review tiers, September 2026)

- **v5 is a swarm of single-hypothesis agents.** Each agent investigates
  one suspected bug in parallel. Over a month-long A/B test on more than
  a million PRs, median review time fell from about 5:04 to 2:25, and the
  share of comments authors addressed rose from 52% to 66%. This is the
  sampling-variance kind of fan-out (§6a of `agent-design/review.md`),
  split by hypothesis rather than by lens.
- **Review tiers:** Base, Plus and Apex cost 1, 3 and 10 credits. **Auto**
  picks a tier per PR "from its size, risk, and complexity" (criteria not
  published), and you pay for the tier that ran. Plus and Apex show the
  tier next to the confidence score.
- **`greptile.json` loads from the PR's source branch**, with one
  exception: `autoApprove` (approve "low-risk 5/5 reviews") is read from
  the **base** branch "so a PR can't loosen it for itself". That makes
  every other setting (`strictness`, `commentTypes`, `ignorePatterns`,
  scoped `customContext.rules`, `instructions`) editable by the PR under
  review. Claude Code Review, Bugbot and Cursor Approval Agents all read
  from base; Greptile exempts only the setting that grants approval.
- **Learning:** 👍/👎 reactions are the main signal, a 👎 with a short
  reason teaches faster, and **no reaction slowly lowers a comment
  pattern's priority**. Improvement takes "the first few weeks". How
  feedback becomes a rule, the scope of what is learned, and any way to
  inspect or reset learned rules are not documented, and the security
  exemption recorded in `agent-memory-learning.md` §8 isn't mentioned on
  the current page.
- **Other settings:** `statusCheck` posts a pass/fail check per review;
  `includeConfidenceScore` adds a 0–5 confidence score to the summary;
  `context.repos` reads related repositories; rules can be scoped by file
  glob.

## 14. ReviewBench, and the week's smaller review changes (read 2026-10-19)

**ReviewBench** — GitHub, [blog post](https://github.blog/ai-and-ml/github-copilot/reviewbench-an-open-benchmark-for-ai-code-review/)
by Michelle Zhou and Alejandro Carderera de Diego, 2026-10-05; site
`review-bench.ai` (the page returned only its title to this pass, so
everything below is from the post).

- **Corpus.** 219 public PRs from 187 repositories, 19 languages, sampled
  so language and repository size match GitHub overall (calibrated against
  103.9M PRs), with PR size deliberately weighted toward the "reviewable
  middle and tail" rather than one-file changes.
- **Golden set, in three stages.** Candidates from human reviewers,
  **issues inferred from author follow-up commits**, deterministic
  analysis tools and several frontier models from different families;
  semantic deduplication; validation under a published rubric with Claude
  Sonnet 5 as grader. "A finding counts as a true positive only if it is
  true, relevant, and non-trivial." Each finding has a severity
  (Critical/Medium/Low) and category (Correctness, Security, Reliability,
  Maintainability, Testing, …). Senior engineers who did not build the set
  re-labelled true positives and agreed 96.6% of the time.
- **Metrics.** Grounded precision/recall/F1 count only matches against
  gold labels; augmented ones let the judge credit valid findings missing
  from the gold set. **Grounded recall is the headline** because
  augmented recall's denominator depends on each agent's output. Fβ for
  choosing a precision/recall weighting. (The post says "six metrics in
  two families" in one place and lists four in another.)
- **Offline predicted online.** A multi-model ensemble for Copilot's lite
  tier was predicted to improve precision, recall and volume at lower
  cost; the online A/B gave addressed rate +8.0%, recall +13.6%, comment
  volume +61%, cost −8.0%. Predicted critical comments +227%, observed
  +262%. One experiment, on the authors' own product.
- **Submission.** An agent is a container image plus configuration and
  the submitter's model key; GitHub supplies the judge. 25-PR smoke set,
  then the full 219 PRs in three rounds; a maintainer approves results and
  only improvements are published.
- **No leaderboard numbers in the post**, and no license stated.

What it changes here: §5 and the attention work in §12 compared review
tools by mechanism, because there was no shared measurement. ReviewBench
is the first one that is multi-language, built from real PRs, publishes
its judge, and has any offline-to-online evidence. It also independently
uses the follow-up-commit signal `agent-design/risk.md` §8a adopted two
days earlier for risk calibration. Forge's use of it is in
`agent-design/eval.md` Suite 3.

**Smaller changes the same fortnight:**

- **Claude Code Review left research preview** on 2026-10-15 for Team and
  Enterprise ([announcement](https://claude.com/resources/articles/code-review-is-now-generally-available)).
  The behaviour documented in §12 is unchanged as far as the announcement
  says.
- **Copilot code review** can be requested through the REST and GraphQL
  APIs, and its default effort moved from Lite to Balanced on 2026-09-28
  (secondary reporting; not checked against GitHub's changelog this pass).
- **PR-Agent** (`qodo-ai/pr-agent`, read at `fbf7f6d3fc`): CI artifact
  credentials are redacted before the artifact goes into the prompt
  (#3989, 2026-10-09; not mentioned in `pr-agent/README.md`, which covers
  the CI-artifact markers), and chunked reviews now cap merged findings
  at `num_max_findings` (#4138). Failure modes and dismissal handling are
  already in the README. Since the 2026-10-17 refresh at `5a50bf1e` only
  `configuration.toml` changed (GitLab subgroup inheritance, Jira project
  keys, model routing; no prompt text), so the stored prompt files stand.

## Design takeaways

A few things stood out across all fourteen:

- **Diff format and delivery mechanism are the two axes that most
  determine engineering complexity.** Pre-formatting the diff (PR-Agent,
  Gemini, Codex) and posting via a structured API (GitHub's pending-review
  flow, or a JSON-schema response) is more work to build but gives much
  tighter control over line-number correctness than "let the model run
  `git diff`/`gh` itself," which every Claude-Code-skill-style tool here
  defaults to.
- **False-positive filtering is where the real design divergence is.**
  Everything from a simple threshold (TuringMind, agent37) to a two-stage
  validation subagent (Anthropic's `/code-review`) to a 4-bucket triage
  system that re-reads surrounding code before rating severity (BMAD).
  None of the "no filtering step described" tools (Codex, Gemini,
  Cookbook) are necessarily worse — they may just push that judgment into
  the base model's instructions rather than a separate pipeline stage.
- **Most of these don't read existing PR comments**, though the exceptions
  are informative. Of the fourteen, `claude-code-action` reads them as
  context, `claude-code-cookbook`'s `pr-fix` exists entirely to consume
  them, and `composio-swekit/pr_review` goes furthest — an explicit,
  twice-stated instruction to check for and avoid duplicate comments
  before posting. Everything else reviews from scratch every time,
  including tools that will duplicate a comment if you re-run them on the
  same PR (Codex's reference implementation says so explicitly). The
  spread suggests dedup-awareness isn't hard to add — most sources just
  didn't bother.
- **"Proposes a fix" and "flags an issue" are treated as separate concerns**
  more often than not — PR-Agent and Gemini both split them into different
  commands/prompts entirely, rather than one command doing both.
- **Most "review prompts" aren't system prompts.** Only `pr-agent` sends a
  true system-role message; everything else is an instruction layer on
  top of a host agent's own (much larger, mostly closed-source) system
  prompt. Reading a skill file in isolation tells you what's *added*, not
  what the model is actually operating under end to end — pair it with
  the relevant host prompt (`gemini-cli/`, `codex/`, or the leaked
  `leaked/claude-code/`) for the full picture.
- **Nobody but DeepSeek treats "where did this criterion come from?" as a
  question.** Thirteen sources ship hand-authored criteria with no stated
  provenance and no revision mechanism; `dsh-code-review` is rewritten
  from mined, adoption-verified human feedback on a daily cadence (§11).
  The gap matters most for the sources with the *longest* checklists,
  since a checklist that only ever grows is the failure mode the
  DeepSeek workflow is explicitly designed against.
- **A review skill can be scoped to one repo and get sharper, not
  narrower.** The portable sources have to state criteria generally
  ("check for security issues"), which is why their false-positive
  machinery has to be so elaborate (§6). `dsh-code-review` can instead
  say "for every touched `./invariant`, require an owner event-stream or
  mutable-data relationship at the point where that package can observe
  it" — a check that is mechanical to apply and impossible to state
  portably. The trade is real: it needs a per-repo maintenance loop to
  stay true.
- **"What the model sees" is itself reviewable, and only one source
  reviews it.** `dsh-code-review` makes *model perspective* a manual
  check — "inspect the exact prompts, tool schemas, results, and
  diagnostics the model receives across affected modes; flag concepts
  outside the model's task, then verify stable text verbatim and dynamic
  behavior through snapshots." For anyone building agent infrastructure,
  prompt and schema text is production behavior, and this is the only
  review source in the collection that puts it in the diff.
- **The strongest anti-false-positive lever may be subtraction, not
  scoring.** §6 is dominated by machinery that rates findings after
  generating them. DeepSeek's two rules — omit anything a green gate
  already enforces, and prefer one substantiated blocker over a list —
  cut the candidate set before scoring rather than filtering after, which
  costs nothing to implement and is orthogonal to every rubric in §6.
