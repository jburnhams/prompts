# Changelog

All notable changes to this repository, grouped by day, newest first. Generated from git history.

## 2026-08-30

Opened a new research topic — how agents load repository instruction files into the prompt — read from eleven production loaders' source rather than their docs, then specced the design's own loader against it.

- `agent-context-file-loading.md` — new: the nine questions every loader answers differently (filenames and collision, walk boundaries, ordering, dedup, transformation, imports, envelope, escaping, injection point), plus a tenth the file loaders cannot answer — whether context can change mid-session. Findings that recur: everyone concatenates root-first, so every "sub-directory rules win" claim in the field rests on nothing but position in the text; five dedup keys in use and only Gemini CLI's `dev:ino` is correct on a case-insensitive filesystem; **nobody templates the file** (clean negative across all eleven) and **nobody escapes it either**, so a file containing `</INSTRUCTIONS>`, `</file>` or `# Rules from …` forges its own envelope, with Zed's six-backtick fence the only containment attempt anywhere. Three incompatible postures on authority quoted side by side (Claude Code's "OVERRIDE any default behavior", Gemini CLI's safety ceiling, OpenHands alone shipping an `<UNTRUSTED_CONTENT>` banner *and* a capability scope). §12a covers the programmatic channels — MCP server `instructions` (Claude Code's delta attachments, replacing a prefix rebuild its source names `DANGEROUS_uncachedSystemPromptSection`), skills, hooks, plugins — and finds Codex giving plugin text and hook stdout a `developer` role with an **empty marker pair**, undelimited and outranking `AGENTS.md`. §15 answers the CI question: no loader anywhere is revision-aware, Codex's reference review workflow checks out `refs/pull/N/merge` so **a PR that edits `AGENTS.md` changes the rules used to review it**, and both vendors' workflows statically disable the folder-trust gate
- Per-source `README.md` — new `## Context-file loading` sections in `codex/`, `gemini-cli/`, `leaked/claude-code/`, `opencode/`, `roocode/`, `cline/`, `zed/`, `goose/`, `crush/`, `openhands/`, and `aider/` (the deliberate null case: no loader at all); `github-pr-bots/README.md` gains `## Which revision do the context files come from?`
- Root docs: `README.md` (index entry), `sources.md` (eleven targeted repo reads with paths and commits)

Second pass: turned the research into a loader spec for the design, then reworked it repeatedly as the architecture moved from a filesystem walk to an external context service. Recorded with an explicit v1-versus-direction split rather than as settled spec throughout.

- `agent-design/context-files.md` — new. **Three tiers** (org, team, repo) resolved by a context service at dispatch, with a two-axis precedence rule (`policy` from above beats the repo, `default` from above loses to it) in place of a single ladder. The service is a normalising cache, not a lookup: sections rather than documents are the atomic unit, every tier reduces to `(source repo, ref)` so cache entries invalidate themselves, and the response is a **projection** of a cached whole-repository resolution — the structural decision that keeps later narrowing from being a rewrite. Normalisation is framed as *relocating* an interpretation the agent would otherwise make at runtime, unauditably, rather than adding one, so the pipeline resolves duplicates and contradictions and reports what it resolved instead of gating on human review. Also: path+revision provenance, a nonce-bearing envelope, a scope statement in place of a precedence ladder, budget with heading-boundary truncation announced in-band, JIT as a *reveal* rather than a read, and a harness-side run record covering what the model cannot know. **v1 is blunt** — merged corpus, appended whole; `paths`/`kinds` are reserved and ignored, and the intended future selector for coding runs is the plan rather than a dispatcher field
- `agent-design/` — `review.md` (**supersedes** §1's "repo-controlled, so lower injection risk": conventions are read at `base_sha` and nonce-wrapped, and a PR editing them is a finding), `formats.md` (§1 envelope, §8b JIT rule), `system-prompts.md` (step 1 becomes a fallback), `medium.md` (structural write protection promoted into v1), `future.md` (task splitting with its own context; the sequencing note that narrowing, wander-handling and splitting want to land together), `README.md` (reading order)

Third pass: re-read five memory systems as **source** rather than prompt text, which changed several standing conclusions, then specified cross-run learning against the context service.

- `agent-memory-learning.md` — the leaked Claude Code source's `memdir` read for the first time: a four-type taxonomy whose `<scope>` routes per type, a rule to record validated *successes* as well as corrections, staleness computed from `mtime` and rendered in words, retrieval by a cheap model acting as selector, memory scoped per sub-agent type, and paragraphs carrying eval results in code comments. Its **team-shared** machine-written store contradicts what the doc had recorded as the field's cleanest rule. Plus: Gemini CLI's model-free session digest, Codex consolidating on git dirtiness rather than a DB watermark, three Goose corrections from source (incl. same-tagged entries silently collapsing at read time), Cline's `new_rule` retreat, and the DeepSeek finding that its review-criteria mining loop has produced zero rules while every actual rule change arrived in the PR that established the convention. New sections: library- and harness-scoped memory as named absences, and improvement requests as a channel distinct from memory
- `agent-tool-implementations.md` — new §12: memory tools as a confined second file family (nobody built the database the name implies), the path predicate before any I/O, the create-only write, content guards in `validateInput`, and a shipped bug class this family invites; five new checklist rules
- `agent-tool-surfaces.md` — §7 rewritten: memory-as-a-tool has peaked and is receding, three products having removed one and none added
- `agent-design/memory.md` — new: learnings as a `tier: "learned"` of the context service (which is the code/git/artifact proxy, so knowledge is keyed by ref — including **dependency coordinates**), capture-in-session / promote-on-outcome, the record schema and per-category promotion gates, mechanically-computed staleness from the evidence SHA, and `ReportProblem` with a `blocker` priority that suspends the task. Supersedes `medium.md` §6 on three points
- `agent-design/` — README.md (reading order + three decision rows), context-files.md, medium.md, future.md
- Root docs: `README.md`, `sources.md` (six repo reads), `deepseek-harness/README.md` (the re-read and what it found)

Fourth pass: opened a second new research topic the same day — how agents get pixels in front of a model — read from twelve harnesses' source rather than their prompts, which overturned a large part of the previous multimodal survey.

- `agent-vision-multimodal.md` — new: the four questions a harness answers independently (entry, transport, admission, lifetime) and the pixel-first/text-first split. The **image-in-a-tool-result bug** documented from Cline's own middleware header — Chat Completions cannot carry an image in a `role:"tool"` message, the converter `JSON.stringify`s it, and "the model treats it as ~50KB of opaque text and **hallucinates the image's actual contents**," a failure that never errors — alongside SWE-agent's opposite answer (base64 markdown through stdout, promoted to image blocks by an `image_parsing` history processor, with a with/without ablation config pair). Five capability-gated degradation paths compared **by what their placeholder string lets the model do next**, and the rule that emerges: strip at request-build time, keep the real image in stored history, so a model switch restores sight. Resize budgets tabulated (Codex prices in *patches* as well as pixels; OpenHands drops the ceiling from 8000px to 2000px past twenty images in one request — the only count-aware policy found), and coordinate drift with three shipped fixes: state the scale factor in-band (Claude Code), fix the viewport (Cline), or draw a red crosshair into the screenshot (SWE-agent). §8 is the thin part of the field: only Codex prices images and keeps them atomic through compaction (`retained_image_count` is the only retention metric anywhere), and only Gemini CLI **evicts a stale visual observation** — a type-aware "lifetime of one" supersession that generalises to screenshots and that nobody has generalised. §10 names the strongest convergent finding: three harnesses independently **delegate the look to a second model** and return only text, Gemini CLI defanging its computer-use delegate via `excludedPredefinedFunctions` and OpenHands's tool declining to register when no sighted profile exists. §11 covers screenshots as verification evidence (Jules gates completion on a `screenshot_path` parameter; Codex decides separately, via `Disabled`/`TextOnly`/`Multimodal`, whether the *reviewer* can see), §12 the injection surface every shipped text heuristic misses, §15 the named absences (nobody escapes an image sentinel, bounds-checks a click, or keeps a visual-regression baseline), and §17 a 30-rule checklist
- **Corrections to `agent-tool-surfaces.md`** §4–§5, which had judged this from prompt text: Goose (`read_image`, with a `crop` rectangle for zooming), Crush (`view` returns images), Zed (`read_file` returns images), OpenHands (`inspect_image_with_vision` + a full `browser_use` toolset) and Gemini CLI (**an entire browser sub-agent**, invisible in captured prompts because it builds its own) all handle images; SWE-agent's `image_tools` bundle confirmed. §5's "not addressed at all" row and takeaway rewritten, the browser row corrected, both cross-linked
- Per-source `README.md` — new `## Vision and multimodal` sections in `codex/`, `cline/`, `gemini-cli/`, `openhands/` (which also records that the agent moved to `All-Hands-AI/agent-sdk`), `goose/`, `crush/`, `zed/`, `opencode/` (negative result: `mcp/browser.ts` only opens a URL for OAuth), `roocode/`, `swe-agent/`, `omp/`, `aider/` (the deliberate null), `leaked/claude-code/` (three concentric browser surfaces, and `Claude_Preview` as the only browser scoped to the app under development), `leaked/jules/`, `leaked/google-antigravity/`, `leaked/devin/`, `leaked/windsurf/`
- Root docs: `README.md` (index entry), `sources.md` (twelve targeted repo reads with paths and commits)

## 2026-08-21

Added a new layer to the tool docs — MCP as a **result transport** rather than an extensibility checkbox — grounded in a targeted source read of three clients' MCP projections, and carried the findings into the agent design.

- `agent-tool-result-transport.md` — new: the three layers escaping can appear at and what each costs (measured), MCP's result model at revision `2026-07-28`, six client projections compared from source, the `structuredContent` duplication trap, binary handling, artifacts/handles and the six decisions they force, and the audience channel
- Root docs: `README.md` (index entry), `sources.md` (three targeted repo reads + eleven web references), `agent-tool-implementations.md` (§5a/§5b/§6a cross-links and the measured escaping-vs-framing cost)
- `agent-design/` — `adk.md` (§2b dated against Gemini 3 multimodal function responses; §2c priced), `future.md` (artifact store and audience-channel entries)
- Source folders: `opencode/README.md`, `roocode/README.md` — MCP projection notes

Second pass the same day: applied the transport findings to the design as concrete rules, and established from source which MCP revision the intended stack can actually speak.

- `agent-design/adk.md` — new §0 (the protocol version ceiling: `adk-java` pins MCP Java SDK 1.1.2, the SDK tops out at `2025-11-25`, Java is Tier 2 with a six-month commitment — so `2026-07-28` is not available, and why that costs nothing); §4 adds `Bash` to the retry-hazard list and the errors-as-`isError` wire rule; §5 notes the spec has moved in the design's favour; §6 records the statelessness validation; §8/§9 updated
- `agent-design/tools.md` — the one-text-block wire-shape rule promoted into the implementation contract; errors travel as tool-execution errors, never protocol errors; spill filenames keyed by tool-call id
- `agent-design/formats.md` — §8e's `<bash>` elision note becomes a shape-stating stub with the exact next call
- `agent-design/eval.md` — `envelope_inflation` as a measured metric with a budget
- `agent-tool-result-transport.md` §10, `sources.md` — the SDK/pin ceiling and the two repo reads behind it

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
