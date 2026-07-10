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

## Candidates for next pass

Other open-source coding/review agents worth adding later: Continue.dev,
gpt-engineer, Plandex, AutoCodeRover, bolt.diy (community multi-LLM fork of
Bolt).
