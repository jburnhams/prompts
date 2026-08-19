# Changelog

All notable changes to this repository, grouped by day, newest first. Generated from git history.

## 2026-08-18

Merged PR #20 (`claude/deepseek-harness-investigation`), integrating the DeepSeek Harness work from 2026-08-14 into `main`.

- No new file changes beyond the 2026-08-14 entry below (merge commit only).

## 2026-08-14

Added a DeepSeek-specific harness (prompts, review skills, prose standard) and folded its lessons back into the core agent design, then removed the now-redundant standalone notes doc.

- `deepseek-harness/` — new folder in full: `README.md`, `AGENTS.md`, `system-prompt-code-mode.md`, `system-prompt-native.md`, `skills/dsh-code-review.md`, `skills/dsh-find-simplifications.md`, `skills/dsh-pre-push-checks.md`, `skills/dsh-prose-standard.md`, `skills/dsh-trim-cot-leakage.md`, `skills/dsh-trim-cot-leakage-examples.md`
- `agent-design/` — README.md, eval.md, formats.md, future.md, medium.md, review.md, system-prompts.md, examples/{responder-envelope,review-envelope-initial,review-envelope-rereview,specialist-brief-bugs,validator-brief}.md; `deepseek-lessons.md` added then removed (merged into the design and dropped)
- Root docs: `README.md`, `sources.md`, `agent-archetypes.md`, `agent-memory-learning.md`, `agent-permissions-approval.md`, `agent-self-verification.md`, `agent-subagent-architectures.md`, `agent-tool-call-dialects.md`, `agent-tool-implementations.md`, `agent-tool-surfaces.md`, `code-review-approaches.md`

## 2026-08-11

Added OMP as a new source, closed out the read-tool/tool-call-dialects research (vendor teardown, latent bugs, benchmark), and applied the findings to the agent design (eval harness, typed proofs, tool limits).

- `omp/` — new folder in full: `README.md`, `hashline-grammar.lark`, `hashline-prompt.md`, `subagent-system-prompt.md`, `system-prompt.md`, `tools/{patch,read,replace,task}.md`
- `agent-design/` — README.md, adk.md, eval.md, formats.md, future.md, medium.md, system-prompts.md, tools.md
- Root docs: `README.md`, `sources.md`, `agent-context-compaction.md`, `agent-memory-learning.md`, `agent-tool-call-dialects.md` (new), `agent-tool-implementations.md`, `agent-tool-surfaces.md`

## 2026-08-01

Refocused the dependency/docs-retrieval design section (`medium.md` §2e-bis) around classpath resolution and in-container analysis rather than external doc retrieval.

- `agent-design/medium.md`
- `agent-tool-surfaces.md`

## 2026-07-31

Reworked the tool surface (List replaces Glob, Read becomes a batch tool), defined precise tool result formats, moved MCP/Google ADK substrate concerns into a new `adk.md`, and applied tool-implementation research to the design.

- `agent-design/` — new `adk.md`, plus README.md, formats.md, future.md, medium.md, review.md, system-prompts.md, tools.md, examples/specialist-brief-bugs.md
- Root docs: `README.md`, `sources.md`, `agent-tool-implementations.md`

## 2026-07-29

Added a cross-cutting memory/retrospectives doc and rolled memory + turn-output (run narrative) sections into most per-source READMEs; added cross-run learning as a fourth design entrypoint.

- `agent-memory-learning.md` — new
- `agent-design/` — README.md, future.md, medium.md
- `agent-turn-output.md`, `code-review-approaches.md`, `README.md`
- Per-source `README.md` updates across: `aider/`, `cline/`, `codex/`, `coding-agent-approaches.md`, `crush/`, `gemini-cli/`, `goose/`, `opencode/`, `openhands/`, `pr-agent/`, `roocode/`, and `leaked/{amp,augment-code,claude-code,cursor,devin,github-copilot-cli,google-antigravity,jules,kiro,manus,qoder,warp,windsurf}/`

## 2026-07-22

Deep-dived the code-review entrypoint: exact LLM payloads, re-review sessions, stale-thread rendering, and worked examples; reversed the comment-blind-specialist decision so discussion is treated as intent context.

- `agent-design/` — README.md, formats.md, medium.md, review.md, system-prompts.md, tools.md, examples/{README,responder-envelope,review-envelope-initial,review-envelope-rereview,specialist-brief-bugs,validator-brief}.md

## 2026-07-17

Third agent-design review pass: switched the primary issue tracker to Bitbucket and split the roadmap into `medium.md` (near-term) and `future.md` (deferred), adding product-owner and cross-repo/long-horizon entrypoints.

- `agent-design/` — README.md, formats.md, future.md, medium.md, tools.md

## 2026-07-12

Main agent-design review cycle: added the initial "lean, hands-off coding + review agent" design (Forge), Plan mode, folded `review.md` into the core docs, resolved several open questions (comment format, large-diff handling, AddComment scope), and hardened the design against failure modes from the research docs. Also expanded leaked-source coverage (GitHub Copilot CLI, Grok Build, Codex supplement, Amp, Claude Code Desktop, Devin CLI, Cursor).

- `agent-design/` — README.md, formats.md, future.md, review.md (removed), system-prompts.md, tools.md
- Root docs: `README.md`, `agent-context-compaction.md`, `agent-git-vcs.md`, `agent-permissions-approval.md`, `agent-self-verification.md`, `agent-subagent-architectures.md`, `agent-tool-surfaces.md`, `agent-turn-output.md`
- `leaked/` — README.md, `amp/{README,amp-code}.md`, `claude-code/{README,architecture-notes,claude-desktop-code}.md`, new `codex-supplement/` (README + 6 docs), `cursor/{README, Agent Prompt (asgeirtj capture)}.md`, `devin/{README,CLI Prompt}.md`, new `github-copilot-cli/` (README + 2 docs), new `grok-build/` (README + prompt)
- `codex/README.md`

## 2026-07-11

Heaviest single day: added Zed, Google Antigravity, and Jules as new sources; wrote `agent-git-vcs.md` and `agent-permissions-approval.md` from scratch; expanded self-verification, turn-output, and context-compaction research across ~18 sources each; integrated a much richer Claude Code leak capture.

- New docs: `agent-git-vcs.md`, `agent-permissions-approval.md`
- New folders in full: `zed/` (README + 6 `.hbs` prompt files), `leaked/jules/` (README + 2 details docs)
- `leaked/google-antigravity/` — README.md plus new `CLI Prompt.md`
- `leaked/claude-code/` — README.md, architecture-notes.md, new `bundled-skills/` (17 files) and `new-capture/` (27 files, later integrated)
- Root docs: `README.md`, `agent-context-compaction.md`, `agent-self-verification.md`, `agent-subagent-architectures.md`, `agent-tool-surfaces.md`, `agent-turn-output.md`
- `README.md` updates across most per-source folders: `aider/`, `augment-swebench-agent/`, `cline/`, `codeact-hyperlight/`, `codex/`, `copilot-chat/`, `crush/`, `gemini-cli/`, `goose/`, `opencode/`, `openhands/`, `pi-agent/`, `roocode/`, `swe-agent/`, and `leaked/{README,cursor,devin,factory,replit,warp,windsurf}/`

## 2026-07-10

Repository created and bulk-populated: initial commit plus 24 more commits adding the full set of source folders (system prompts, tool definitions, and READMEs) and the first cross-cutting synthesis docs.

- Root docs added: `README.md`, `agent-archetypes.md`, `agent-subagent-architectures.md`, `agent-tool-surfaces.md`, `code-review-approaches.md`, `coding-agent-approaches.md`
- New folders added in full (system prompts / tools / README for each): `aider/`, `augment-swebench-agent/`, `bolt/`, `cline/`, `codeact-hyperlight/`, `codex/`, `composio-swekit/`, `copilot-chat/`, `crush/`, `gemini-cli/`, `github-pr-bots/` (incl. `claude-code-action/`, `codex-review/`, `gemini-code-review/`, `opencode-review/`), `goose/`, `live-swe-agent/`, `mini-swe-agent/`, `opencode/`, `openhands/`, `papers/inside-the-scaffold/`, `pi-agent/`, `pr-agent/` (incl. `code_suggestions/`), `roocode/`, `skills/` (incl. `agent37/`, `anthropic/{code-review,pr-review-toolkit,security-guidance}/`, `bmad-code-review/`, `claude-code-cookbook/`, `turingmind/`), `swe-agent/`
- `leaked/` added in full (README + per-source captures): `amp/`, `anthropic/`, `augment-code/`, `claude-code/`, `claude-for-chrome/`, `codebuddy/`, `cursor/`, `devin/`, `emergent/`, `factory/`, `google-antigravity/`, `google-gemini/`, `junie/`, `kiro/`, `leap-new/`, `lovable/`, `lumo/`, `manus/`, `orchids/`, `qoder/`, `replit/`, `same-dev/`, `trae/`, `traycer/`, `v0/`, `vscode-agent-leaked/`, `warp/`, `windsurf/`, `xcode/`, `zai-code/`
