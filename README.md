# prompts

A collection of system prompts from real-world AI products/agents, for
analysis and comparison.

## Structure

Prompts are organized in folders by source (the tool/project they come from).
Each folder has its own `README.md` noting the license, where the files were
retrieved from (branch/tag + date), and what each file is.

This is a first pass focused on **open-source coding and code-review
agents**, where the system prompt ships directly in the project's public
source code (as opposed to being reverse-engineered/leaked from a closed
product).

**[→ `agent-archetypes.md`](./agent-archetypes.md)** — start here for the
30,000-foot view: the ~35 agents/tools/skills/bots in this collection
sorted into six recognizable architectural archetypes (general-purpose
interactive assistant, benchmark-driven issue solver, minimalist
scaffold, multi-role pipeline, PR-review specialist, app/UI generator),
plus the two axes that explain most of the variance between them.

**[→ `code-review-approaches.md`](./code-review-approaches.md)** —
a synthesized comparison of every code/PR-review-specific source in this
collection, stage by stage (system prompt, diff format, context,
filtering, output format, delivery, safety), with links back to each
source for detail.

**[→ `coding-agent-approaches.md`](./coding-agent-approaches.md)** — the
companion doc, one level down: a comparison of the *full* coding-agent
system prompts themselves (identity, per-model variants, environment
injection, tool-use policy, code-editing format, planning, project-memory
files, safety, communication style), with particular focus on OpenHands,
OpenCode, Codex, Claude Code, and Cursor.

**[→ `agent-tool-surfaces.md`](./agent-tool-surfaces.md)** — a further
drill-down focused specifically on *what tools each scaffold actually
gives the model*: shell type/persistence, search tooling, code execution,
browser/web access, multimodal handling, async/background execution,
persistent memory & deployment, sandbox/isolation, and extensibility
(MCP/skills/dynamic tool sets), across all 21 sources with a documented
tool surface.

**[→ `agent-subagent-architectures.md`](./agent-subagent-architectures.md)**
— a companion drill-down on one specific tool-surface capability: when
and how a scaffold spawns another agent. Covers delegation triggers,
calling protocol (stateless tool-call vs. persistent addressable child
vs. shared-conversation handoff vs. async background process vs.
multi-party orchestration topologies), whether the sub-agent gets its
own system prompt, turn/output bounding, concurrency and write-safety,
and recursion limits, across the 19 sources with a documented sub-agent
mechanism — including Microsoft Agent Framework's five named
orchestration patterns (Sequential/Concurrent/Handoff/GroupChat/
Magentic), a structurally different N-party design found nowhere else
in the collection.

**[→ `agent-context-compaction.md`](./agent-context-compaction.md)** —
a further drill-down on how a scaffold survives running out of context
mid-task, across 18 sources: trigger model (proactive token-threshold
checks vs. reactive-on-API-error vs. manual commands vs. Cline's
model-proposes/user-approves third shape), prompt shape (free text vs.
structured templates vs. XML), single-mechanism vs. layered-pipeline
vs. pluggable-strategy vs. Cline's multiple-uncoordinated-mechanisms
architecture, incremental/anchored vs. from-scratch summarization,
recovery philosophy (is the discarded detail actually gone, down to
Cline's plain-deletion-no-summary floor and Windsurf's "externalize
before compaction happens" strategy via a persistent memory tool),
prompt-cache interaction, sub-agent isolation, and — compared in
detail — actual numeric token budgets (reserved buffers, summary
output caps, retention thresholds) across the sources that expose them.

**[→ `agent-turn-output.md`](./agent-turn-output.md)** — a further
drill-down on what a single LLM turn actually produces, across 18
sources: session/task title generation (a dedicated cheap-model side
call vs. no generation at all vs. folded into the main model's own tool
calls — ten sources now confirmed or likely "don't bother," though only
Cline and Roo Code are schema-confirmed rather than just
capture-gapped), reasoning/thinking display defaults
(shown-collapsed-by-default vs. hidden-until-opted-in), Codex's
unusually layered raw/summary/effort reasoning-visibility controls,
Devin's `<think>` tool (a mandatory, categorically-hidden reasoning
mechanism that fits neither "native API block" nor "prompted
narration"), Windsurf's schema-embedded per-tool-call narration
requirement, and the recurring but easy-to-conflate distinction between
native model-API reasoning blocks and ordinary prompted narration text.

**[→ `agent-self-verification.md`](./agent-self-verification.md)** — a
further drill-down on how (and whether) a scaffold checks its own work
before calling a task done, distinct from `code-review-approaches.md`
(which is about reviewing *someone else's* PR). Covers: the shared
"reproduce bug → fix → verify → edge cases → submit" workflow template
running through nearly every SWE-bench-lineage agent (SWE-agent,
mini-swe-agent, Live-SWE-agent, Augment SWE-bench Agent), deterministic
non-LLM completion gates (Roo Code's `AttemptCompletionTool`, SWE-agent's
templated `review_on_submit_m`), separate-LLM-call judge/reviewer
patterns and what happens on a failed verdict (SWE-agent's
`ScoreRetryLoop`/`ChooserRetryLoop`, Augment's o1 ensembler, Microsoft
Agent Framework's `with_judge()` nudge-not-restart pattern), the
"review-as-a-general-tool" conflation trap (Codex's `ReviewTask` and
OpenCode's `/review` command are general diff-review utilities, not
self-checks), hook-based user-configured gates (Claude Code's `Stop`
hooks — the one such mechanism actually shipped externally, alongside a
leaked internal-only adversarial verification subagent), and Jules's
per-action mandatory verification, hidden pre-commit tool, and
Playwright-screenshot-as-proof frontend verification — the most
granular self-review discipline found anywhere in this collection. A
second research pass roughly doubled the source count (20 sources
covered in depth) and surfaced two more patterns not in the original
typology: verification authority handed to the *human user* instead of
the model (Replit's automated-evidence-plus-confirmation tools, Warp's
inverted "ask before verifying" default) and "prompt-simulated"
gates that borrow deterministic-gate rhetoric — numbered steps, "no
exceptions" language — without any confirmed code-level enforcement
(Copilot Chat's `vscModelPrompts.tsx` "iron law" block, Factory/Droid's
PR-draft-state gate).

**[→ `agent-permissions-approval.md`](./agent-permissions-approval.md)**
— a further drill-down on how a scaffold decides whether an action
needs a human first, across 17 sources. This turned out to be the
richest single doc in the whole collection: Codex CLI's permission
architecture is not one mechanism but five cooperating subsystems
(a static command-safety classifier, a Starlark rule-engine DSL, an
LLM-based "Guardian" auto-reviewer running a separate cheaper/faster
model with its own risk taxonomy, a real OS-level sandbox on three
platforms, and a network-egress proxy), and Gemini CLI's "TOML policy
engine" turned out to include an opt-in second LLM ("Conseca") that
generates a least-privilege policy for the user's request and then
re-judges every subsequent tool call against it — an entire separate
model acting as judge over the first model's actions, layered on top
of (not replacing) a 5-tier admin/user/workspace/extension/default
priority engine. Claude Code's own leaked permission system has a
third, independently-converged instance of the same idea —
`yoloClassifier.ts`, a two-pass fast/slow LLM gate for its internal-only
`auto` mode — confirmed real via Anthropic's own public hooks docs but
also confirmed **ant-gated** (excluded from the externally-available
mode set), the same internal-only pattern this collection's
self-verification doc found for Claude Code's adversarial verification
subagent, now showing up a second time in an unrelated subsystem. Also
covers: static-vs-LLM risk classification
(OpenHands's genuinely pluggable choice between trusting the model's
own self-tag or a separate Dockerized static analyzer), scope/
persistence of a granted approval (five distinct tiers in Codex vs.
Roo Code's two, with no session-only cache at all), escalation
mechanisms (OpenCode's `doom_loop` circuit breaker on repeated
identical calls, Codex's mid-execution syscall-level interception),
sandbox/isolation as a complementary-not-substitute layer, and the
cross-cutting finding that most of this machinery is invisible to the
model's own system prompt — the harness gates the model, but rarely
tells it the rules.

### Other candidate drill-downs (not started)

Same four-axis pattern as the docs above — system prompts,
tool surfaces, and sub-agents are covered; code review has its own
top-level doc. One candidate remains:

- **Git/VCS interaction mechanics** — commit message conventions,
  checkpoint/undo systems, worktree isolation, branch-management
  rules.

## Sources so far

| Folder | Project | Type | License |
|---|---|---|---|
| [`cline/`](./cline) | [Cline](https://github.com/cline/cline) | Coding agent (IDE extension) | Apache-2.0 |
| [`aider/`](./aider) | [Aider](https://github.com/Aider-AI/aider) | Coding agent (terminal) | Apache-2.0 |
| [`pr-agent/`](./pr-agent) | [PR-Agent / Qodo Merge](https://github.com/qodo-ai/pr-agent) | Code review agent | Apache-2.0 |
| [`swe-agent/`](./swe-agent) | [SWE-agent](https://github.com/SWE-agent/SWE-agent) | Coding agent (issue resolver) | MIT |
| [`openhands/`](./openhands) | [OpenHands](https://github.com/All-Hands-AI/OpenHands) | Coding agent (autonomous SWE) | MIT |
| [`opencode/`](./opencode) | [OpenCode](https://github.com/anomalyco/opencode) | Coding agent (terminal, multi-provider) | MIT |
| [`roocode/`](./roocode) | [Roo Code](https://github.com/RooCodeInc/Roo-Code) | Coding agent (VS Code extension, Cline fork) | Apache-2.0 |
| [`copilot-chat/`](./copilot-chat) | [GitHub Copilot Chat](https://github.com/microsoft/vscode-copilot-chat) | Coding agent (VS Code agent mode + CLI) | MIT |
| [`codex/`](./codex) | [Codex CLI](https://github.com/openai/codex) | Coding agent (OpenAI's terminal agent) | Apache-2.0 |
| [`goose/`](./goose) | [Goose](https://github.com/block/goose) | Coding agent (Block, CLI + desktop) | Apache-2.0 |
| [`crush/`](./crush) | [Crush](https://github.com/charmbracelet/crush) | Coding agent (Charm, terminal) | FSL-1.1-MIT |
| [`bolt/`](./bolt) | [Bolt.new](https://github.com/stackblitz/bolt.new) | AI app-building agent (browser) | MIT |
| [`gemini-cli/`](./gemini-cli) | [Gemini CLI](https://github.com/google-gemini/gemini-cli) | Coding agent (Google, terminal) | Apache-2.0 |
| [`augment-swebench-agent/`](./augment-swebench-agent) | [Augment SWE-bench Agent](https://github.com/augmentcode/augment-swebench-agent) | Coding agent (SWE-bench Verified baseline) | MIT |
| [`mini-swe-agent/`](./mini-swe-agent) | [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) | Coding agent ("the 100 line" SWE-bench baseline) | MIT |
| [`live-swe-agent/`](./live-swe-agent) | [Live-SWE-agent](https://github.com/OpenAutoCoder/live-swe-agent) | Coding agent (writes its own tools mid-task) | MIT |
| [`composio-swekit/`](./composio-swekit) | [Composio SWE-Kit](https://github.com/ComposioHQ/composio) | Coding agent + PR review, multi-role framework | Apache-2.0 |
| [`codeact-hyperlight/`](./codeact-hyperlight) | [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) | Tool-use pattern (CodeAct) + sandboxed execution, not a standalone agent | MIT |
| [`pi-agent/`](./pi-agent) | [Pi](https://github.com/badlogic/pi-mono) | Coding agent (minimal terminal harness) | MIT |

Note: Roo Code and Copilot Chat's source repos were both archived
(read-only) shortly before this collection was put together — files are
still retrievable, just no longer actively developed at those locations.

## Leaked / closed-source prompts

A second category, kept separate from the open-source folders above: prompts
from closed-source products, extracted by third parties rather than
published by the vendor. 30 sources so far — see
[`leaked/README.md`](./leaked/README.md) for the full list and caveats on
provenance and reliability. Most came in bulk from one community aggregator
repo; a few (Factory/Droid, Lumo, **Jules**) from standalone gists/
mirror-repo subfolders. Jules (Google's async coding agent) is worth
flagging specifically: its leaked prompt has the most granular self-review
discipline found anywhere in this collection — mandatory verification
after *every* file-modifying action (not just before submission), plus a
dedicated pre-commit tool, an explicit code-review-request tool, and
Playwright-generated screenshots as proof of frontend verification. See
[`leaked/jules/README.md`](./leaked/jules/README.md).

**Checked and no leak found (as of 2026-07-10)**: CodeRabbit, Greptile, and
Qodo's closed-source products (its open-source `pr-agent` is already
covered above). Worth re-checking later.

**Note on Lumo**: despite Proton's marketing and despite being filed under
a "Open Source prompts" folder in the aggregator repo it was sourced from,
Lumo is not actually open source — it stays in `leaked/` rather than
alongside Bolt and Gemini CLI above.

## Skills / plugins

A third category: Claude Code "skills"/plugins — small, self-contained
prompts that define a single slash command or subagent (e.g. "review my
uncommitted changes") rather than a whole standalone agent. Officially
published, but licensing varies (MIT to Anthropic's source-available
commercial terms) — see [`skills/README.md`](./skills/README.md).

| Folder | Publisher | Contents |
|---|---|---|
| [`skills/agent37/`](./skills/agent37) | agent37-platform | `local-review` (pre-commit review) |
| [`skills/anthropic/`](./skills/anthropic) | Anthropic | `code-review`, `pr-review-toolkit`, `security-guidance` |
| [`skills/turingmind/`](./skills/turingmind) | TuringMind AI | Pre-commit review, quick + deep modes |
| [`skills/bmad-code-review/`](./skills/bmad-code-review) | BMad Code, LLC | Code review as a 4-step state machine w/ pluggable review layers |
| [`skills/claude-code-cookbook/`](./skills/claude-code-cookbook) | wasabeef | PR review, auto-role-suggesting review, PR-fix |

Each of these documents its **scaffolding**, not just the prompt text —
how it constructs the diff/context, what else it pulls in, and how output
gets delivered — since that varies a lot between sources and matters as
much as the prompt wording itself. See
[`skills/README.md`](./skills/README.md) for details on where these came
from.

## GitHub PR bots

A fourth category: the automated bots/GitHub Actions vendors offer that
review PRs directly on GitHub (as opposed to `skills/`'s Claude-Code-only
commands, or the top-level folders' standalone CLI/IDE agents). See
[`github-pr-bots/README.md`](./github-pr-bots/README.md).

| Folder | Vendor | License |
|---|---|---|
| [`github-pr-bots/claude-code-action/`](./github-pr-bots/claude-code-action) | Anthropic | MIT |
| [`github-pr-bots/gemini-code-review/`](./github-pr-bots/gemini-code-review) | Google | Apache-2.0 |
| [`github-pr-bots/codex-review/`](./github-pr-bots/codex-review) | OpenAI | MIT (published reference impl., not the real hosted service — see README) |
| [`github-pr-bots/opencode-review/`](./github-pr-bots/opencode-review) | Anomaly (OpenCode) | MIT (defaults to the full "build" agent, not a review-specific one — see README) |

**Copilot: nothing found.** GitHub's actual hosted Copilot code-review bot
has no published prompt/diff-formatting logic anywhere — closed-source,
server-side. See `github-pr-bots/README.md` for what was checked.

## Papers

[`papers/inside-the-scaffold/`](./papers/inside-the-scaffold) — the PDF
itself (CC-BY 4.0), stored rather than just linked: *"Inside the Scaffold:
A Source-Code Taxonomy of Coding Agent Architectures"*
([arXiv:2604.03515](https://arxiv.org/abs/2604.03515)). Does complementary
analysis to this repo: instead of comparing prompt text, it compares the
*scaffold/architecture code* around 13 open-source coding agents (control
flow, tool interfaces, context management), grounded in specific file
paths and commit hashes. A good companion read to
[`coding-agent-approaches.md`](./coding-agent-approaches.md), and its
source list is where several "candidates for next pass" below came from.

## Candidates for next pass

Other open-source coding/review agents worth adding later: Continue.dev,
gpt-engineer, Plandex, bolt.diy (community multi-LLM fork of Bolt).
From the scaffold-taxonomy paper above: AutoCodeRover, Agentless,
Moatless Tools, DARS-Agent, Prometheus (all SWE-bench-family agents, same
category as `swe-agent/`/`mini-swe-agent/`/`live-swe-agent/`/
`augment-swebench-agent/` above).
