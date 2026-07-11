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
mid-task: when compaction triggers (proactive vs. reactive-on-error),
what gets kept vs. discarded, whether it's a dedicated LLM call or a
simple truncation, prompt-cache interaction, and how it composes with
project-memory files and sub-agent context isolation.

### Other candidate drill-downs (not started)

Same four-axis pattern as the docs above — system prompts,
tool surfaces, and sub-agents are covered; code review has its own
top-level doc. Candidates for the same treatment, roughly in priority
order:

- **Permissions & approval architecture** — ask/allow/deny rule
  systems, sandbox levels, auto/"YOLO" modes, human-in-the-loop
  approval gates. Substantial material already surfaced as asides
  while researching sub-agents (Codex's six-mode permission engine
  with an LLM fast/slow classifier, OpenCode's permission rulesets,
  Gemini CLI's TOML policy engine, Roo Code's approval flow) but never
  pulled together as its own axis.
- **Testing/verification & self-review loops** — the "reproduce bug →
  fix → verify → edge cases → submit" workflow template shared across
  nearly every SWE-bench-lineage agent, plus review-before-submit
  patterns (SWE-agent's actual reviewer/chooser LLM calls, Augment's
  ensembler, Codex's own review pass). Distinct from
  `code-review-approaches.md`, which is about reviewing *someone
  else's* PR — this is an agent checking its own work.
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
published by the vendor. 29 sources so far — see
[`leaked/README.md`](./leaked/README.md) for the full list and caveats on
provenance and reliability. Most came in bulk from one community aggregator
repo; a couple (Factory/Droid, Lumo) from standalone gists/mirror-repo
subfolders.

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
