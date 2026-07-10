# Archetypes: the few main approaches across this collection

`coding-agent-approaches.md` and `code-review-approaches.md` compare
*stages* (identity, diff format, tool policy, ...) across every source.
This doc is one level up: stepping back from stage-by-stage detail, most
of the ~35 agents/tools/skills/bots in this collection fall into a small
number of recognizable archetypes. Six, plus one thing that isn't an
archetype at all but keeps getting confused for one.

Two axes explain most of the spread before you even get to the
archetypes:

- **Deployment context**: is this driven by a human in a chat/IDE loop
  (turn by turn, needs to communicate progress, gets interrupted), or
  does it run a single task to completion unsupervised (a benchmark
  problem, a CI job, a scheduled bot)? Interactive agents carry
  verbosity rules, status-update protocols, and "ask before assuming"
  language that autonomous agents don't need and mostly don't have.
- **Scaffold richness**: minimal (a couple of tools, one persona
  sentence, everything else delegated to the model's judgment or to
  user-installed extensions) vs. maximal (dedicated tools for
  everything, taught edit formats, memory-file conventions, planning
  tools, sub-agent delegation, per-model prompt variants).

Archetypes 1 and 2 below are mostly explained by axis 1. Archetype 3 is
really axis 2 cutting across both — a design philosophy, not a
deployment context.

## 1. General-purpose interactive pair-programmer ("kitchen sink")

The largest group by far. Runs inside a chat UI or terminal session with
a human actively steering it, turn by turn.

**Defining traits**: an explicit persona/identity statement (often with
self-referential "if asked what you are" handling); a stated terseness
policy, frequently down to a specific line count; a todo/planning tool
used "VERY frequently"; a project-memory-file convention it reads on
startup (`CLAUDE.md`/`AGENTS.md`/`GEMINI.md`/etc.); a taught or
tool-delegated code-editing format; a preference for a delegated
search/sub-agent tool "to reduce context usage"; often per-model prompt
variants since the same chat surface serves several backends.

**Sources**: Claude Code (leaked), Cursor (leaked), OpenCode, Cline, Roo
Code, GitHub Copilot Chat, Gemini CLI, Codex CLI, Goose, Crush, Windsurf
(leaked), Aider (closer to the edge of this group — no todo tool, no
memory-file convention, but the same "interactive back-and-forth with a
human" DNA).

## 2. Benchmark-driven issue-to-patch solver

Runs one task (a GitHub issue / SWE-bench problem statement) to
completion with no human in the loop, then stops. Optimized for a scoring
harness, not a conversation.

**Defining traits**: little or no persona/identity text; no verbosity
policy (nothing to be terse *to*); a near-fixed 5-6 step loop — explore →
reproduce the bug with a script → fix → rerun the script → consider edge
cases → submit — that turns out to be **shared, sometimes near-verbatim,
lineage across projects** (traced back to the same Anthropic SWE-bench
blog post in this collection's own research: SWE-agent, Augment
SWE-bench Agent, and mini-swe-agent all carry recognizably the same
instruction text); a single unambiguous completion signal instead of a
turn-taking protocol.

**Sources**: SWE-agent, mini-swe-agent, OpenHands, Augment SWE-bench
Agent, Composio SWE-Kit's `swe/` templates, Live-SWE-agent.

## 3. Minimalist / self-sufficient scaffold

Not a deployment context — a philosophy that cuts across archetypes 1 and
2: strip the tool surface down as far as it'll go and either trust the
model's judgment to fill the gap, or explicitly let it extend its own
capabilities.

**Defining traits**: 2-4 tools total, often just `bash` (or `bash` + a
minimal read/write/edit trio); no taught edit-wire-format in the base
prompt; guidelines that are short, conditional, and deduplicated rather
than an exhaustive rulebook; in the most extreme case, an explicit
instruction to *write new tools mid-task* rather than ship a fixed
toolset at all.

**Sources**: mini-swe-agent and Live-SWE-agent (archetype 2's minimalist
wing — bash + `sed`, and "write your own Python tools" respectively), Pi
(archetype 1's minimalist wing — real `read`/`write`/`edit` tools, but a
base prompt that's one persona sentence and two unconditional
guidelines).

## 4. Multi-role orchestrated pipeline

Instead of one agent doing everything serially, the task is decomposed
into role-scoped sub-agents or sub-prompts, each with its own (usually
narrower) tool access, that either run in parallel and get merged or hand
off to each other sequentially.

**Defining traits**: named roles with distinct prompts (not just "the
agent, but told to focus on X"); permission/tool scoping *per role*
(a read-only analyzer literally cannot edit files, at the tool-access
level, not just by instruction); a handoff mechanism — sometimes a tool
call, sometimes literal keyword responses like `"ANALYZE CODE"` /
`"EDIT FILE"` / `"PATCH COMPLETED"` parsed out of plain text.

**Sources**: Composio SWE-Kit (both its 3-role SWE handoff and its 3-role
PR-review pipeline), BMAD's pluggable review layers, most of the
Claude-Code-skill review tools that fan out to parallel specialist
sub-agents (`pr-review-toolkit`, TuringMind, agent37's `local-review`,
Anthropic's own `/code-review`).

## 5. PR-review specialist

Narrow, single-purpose: diff (and sometimes existing PR comments) in,
review findings/comments out. Never a general coding agent, even when
built by the same team as one.

**Defining traits**: this is the entire subject of `code-review-approaches.md`
— diff-format choice, existing-comment handling, confidence/triage
filtering, output schema, delivery mechanism (chat vs. inline PR comment
vs. GitHub's native pending-review flow vs. written into project files).
The variance *within* this archetype is bigger than the variance between
most of the other archetypes — worth reading that doc rather than
summarizing it further here.

**Sources**: PR-Agent, every `skills/*` review tool, every
`github-pr-bots/*` entry, Composio SWE-Kit's `pr_review` templates.

## 6. App/UI generator

A narrower cousin of archetype 1/2: generate a working app or UI from a
prompt, usually into a disposable/sandboxed environment, rather than
navigate and modify an existing large codebase.

**Defining traits**: whole-file rewrite (or a bespoke artifact/action DSL
carrying full file contents) rather than a diff/patch format, since
there's often no large pre-existing file to preserve; environment
constraints described as a *sandbox's* limits (a browser WebContainer, an
ephemeral cloud container) rather than "the user's machine"; less
emphasis on "match existing conventions" since there's frequently nothing
pre-existing to match.

**Sources**: Bolt.new (official); Lovable, v0, Replit, Same.dev, Manus,
Orchids.app (all leaked).

## Not an archetype: orchestration patterns/backends

CodeAct + Hyperlight isn't a competing approach to the six above — it's a
*tool-use strategy* (collapse several tool calls into one generated
program, run it in an isolated micro-VM) that any archetype-1 or
archetype-2 agent could adopt on top of whatever else it already does.
Worth knowing about, not worth placing on the same map.

## Where each source sits

| Source | Primary archetype | Notes |
|---|---|---|
| Claude Code (leaked) | 1 | |
| Cursor (leaked) | 1 | most elaborate mid-task narration protocol of any source |
| Windsurf (leaked) | 1 | |
| OpenCode | 1 | also runs archetype-2-style via its GitHub Action default ("build" agent) |
| Cline | 1 | |
| Roo Code | 1 | |
| GitHub Copilot Chat | 1 | most granular per-model variant split in the collection |
| Gemini CLI | 1 | most parameterized runtime-conditional prompt assembly |
| Codex CLI | 1 / 2 | ships both an interactive persona and a `codex exec` headless path |
| Goose | 1 | |
| Crush | 1 | |
| Aider | 1 (edge case) | no todo tool or memory-file convention |
| Bolt.new | 6 | |
| SWE-agent | 2 | |
| mini-swe-agent | 2 / 3 | |
| OpenHands | 2 | |
| Augment SWE-bench Agent | 2 | |
| Live-SWE-agent | 2 / 3 | most radical minimalism — writes its own tools |
| Pi | 1 / 3 | interactive, but archetype-3 minimal |
| Composio SWE-Kit | 2 / 4 / 5 | spans three archetypes across its templates |
| PR-Agent | 5 | |
| `skills/*` (7 review tools) | 5 | some also 4 (parallel/sequential sub-agents) |
| `github-pr-bots/*` (4 bots) | 5 | |
| Leaked app-builders (Lovable, v0, Replit, Same.dev, Manus, Orchids) | 6 | |
| CodeAct + Hyperlight | *(pattern, not an archetype)* | |

## See also

- [`coding-agent-approaches.md`](./coding-agent-approaches.md) — stage-by-stage
  detail behind archetypes 1-3 and 6.
- [`code-review-approaches.md`](./code-review-approaches.md) — stage-by-stage
  detail behind archetype 5.
- [`papers/inside-the-scaffold/`](./papers/inside-the-scaffold) — an
  independent architecture-level taxonomy (control flow / tool interfaces
  / resource management) that arrives at a related but differently-cut
  picture: composable loop primitives (ReAct, generate-test-repair,
  plan-execute, retry, tree search) rather than named archetypes. Worth
  reading both — this doc optimizes for "which bucket is this agent
  basically like," theirs for "what control-flow primitives is this agent
  built out of."
