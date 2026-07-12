# Leaked / reverse-engineered prompts

Unlike the rest of this collection, prompts under `leaked/` come from
**closed-source** products. They were extracted by users (via prompt
injection, network inspection, jailbreaks, etc.), not published by the
vendor. Treat them accordingly:

- **Provenance is unverifiable.** No vendor confirmation that the text is
  accurate, current, or complete.
- **They rot fast.** Vendors change these prompts frequently; a given leak
  is a snapshot, often already stale by the time it's found.
- **License/redistribution is murky.** These are typically republished by
  third parties under an implicit "fair use for research" norm, not an
  explicit open-source license from the vendor.

Each subfolder's README notes exactly where the leak came from so you can
judge reliability yourself.

Most of these were pulled in bulk from
[`x1xhlol/system-prompts-and-models-of-ai-tools`](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools),
a large, actively maintained community aggregator (2026-07-10 snapshot).
Folders that say "not from the x1xhlol aggregator" in their README came from
elsewhere.

Deliberately skipped from that aggregator: non-coding assistants (Cluely,
Comet Assistant, NotionAI, Perplexity, Poke, Dia) and, from its "Open
Source prompts" folder, the entries that are genuinely open source —
Cline, Codex CLI, Gemini CLI, and RooCode — which are sourced directly from
their own repos instead (see the root README). Bolt turned out to also be
genuinely open source and was moved to `../bolt/`.

`lumo/` is the one exception that *looks* like it belongs in that "Open
Source prompts" folder but doesn't: Proton has not actually open-sourced
Lumo (see that folder's README for sourcing on this), so it stays here
rather than being promoted to an official folder.

`jules/` is **not from the x1xhlol aggregator at all** — Google's Jules
isn't covered there (checked directly; the aggregator's `Google/` folder
only has Antigravity and an AI Studio "vibe-coder" prompt). It comes
from a small, independent, low-star repo
([`DiaAviLinden/Jules-system-prompt`](https://github.com/DiaAviLinden/Jules-system-prompt))
with thinner provenance than most sources here — see its README for the
extra caveats that come with that.

`github-copilot-cli/` is also **not from the x1xhlol aggregator** —
both its files were mirrored from a different, independently-maintained
leak aggregator, [`asgeirtj/system_prompts_leaks`](https://github.com/asgeirtj/system_prompts_leaks)
(retrieved 2026-07-12). Distinct from [`copilot-chat/`](../copilot-chat)
already in this collection, which covers the separate, open-source VS
Code Copilot Chat *extension* — GitHub Copilot CLI is a different
product with no prior coverage here. See that folder's README for how
its two captures (a standalone terminal prompt and a shorter "Copilot
CLI runtime in VS Code" variant) relate to each other.

`grok-build/` is likewise from the `asgeirtj/system_prompts_leaks`
aggregator (`xAI/grok-build.md`, retrieved 2026-07-12), not x1xhlol's —
this collection's first xAI coding-agent coverage. Notable for a
tool-description surface that closely, in places verbatim, matches
Claude Code's own leaked tool descriptions already stored in
[`claude-code/`](./claude-code) — see that folder's README for the
side-by-side quotes.

`codex-supplement/` is also from `asgeirtj/system_prompts_leaks`
(`OpenAI/Codex/`, retrieved 2026-07-12), not x1xhlol's — six files
supplementing, not duplicating, this collection's official
[`../codex/`](../codex) folder (which is sourced from the real,
open-source `openai/codex` GitHub repo, not from any leak). Covers a
later model variant (`gpt-5.6`), a swappable personality-template
system, a Plan Mode prompt, and a Chrome-browser-control skill that's
very likely a *different* Codex-branded product surface than the
terminal CLI `../codex/` documents — see that folder's own README for
the full provenance distinction, including a note on one file
(`codex-auto-review.md`) whose name is misleading about its content.
`cursor/` also gained a sixth file from this same aggregator (`Agent
Prompt (asgeirtj capture).md`) alongside its five original
x1xhlol-sourced captures — see that folder's own README for what's new
in it, including this collection's first confirmed Cursor
worktree-isolation and sub-agent-delegation findings.

**Looked for and not found**: CodeRabbit, Greptile, and Qodo (beyond the
already-included open-source `pr-agent`) don't appear to have any leaked
system prompt published anywhere as of 2026-07-10 — not in the aggregator
above, nor in other leak-collection repos/gists checked. Worth re-checking
periodically.

## Sources so far

| Folder | Product | Vendor |
|---|---|---|
| [`windsurf/`](./windsurf) | Windsurf (Cascade) | Windsurf (formerly Codeium) |
| [`amp/`](./amp) | Amp | Sourcegraph |
| [`factory/`](./factory) | Factory (Droid) | Factory |
| [`cursor/`](./cursor) | Cursor | Anysphere |
| [`devin/`](./devin) | Devin AI | Cognition |
| [`replit/`](./replit) | Replit Agent | Replit |
| [`lovable/`](./lovable) | Lovable | Lovable |
| [`v0/`](./v0) | v0 | Vercel |
| [`same-dev/`](./same-dev) | Same.dev | Same |
| [`manus/`](./manus) | Manus | Manus (Monica) |
| [`orchids/`](./orchids) | Orchids.app | Orchids |
| [`leap-new/`](./leap-new) | Leap.new | Encore |
| [`emergent/`](./emergent) | Emergent | Emergent |
| [`augment-code/`](./augment-code) | Augment Code | Augment |
| [`codebuddy/`](./codebuddy) | CodeBuddy | Tencent |
| [`trae/`](./trae) | Trae | ByteDance |
| [`qoder/`](./qoder) | Qoder | Qoder |
| [`kiro/`](./kiro) | Kiro | AWS |
| [`junie/`](./junie) | Junie | JetBrains |
| [`traycer/`](./traycer) | Traycer AI | Traycer |
| [`warp/`](./warp) | Warp | Warp |
| [`xcode/`](./xcode) | Xcode Intelligence | Apple |
| [`zai-code/`](./zai-code) | Z.ai Code | Zhipu AI |
| [`google-gemini/`](./google-gemini) | Gemini (AI Studio vibe-coder) | Google |
| [`google-antigravity/`](./google-antigravity) | Antigravity | Google |
| [`vscode-agent-leaked/`](./vscode-agent-leaked) | VS Code Agent (leaked snapshot) | Microsoft |
| [`claude-code/`](./claude-code) | Claude Code (leaked snapshot) | Anthropic |
| [`claude-for-chrome/`](./claude-for-chrome) | Claude for Chrome | Anthropic |
| [`anthropic/`](./anthropic) | Claude.ai default assistant | Anthropic |
| [`lumo/`](./lumo) | Lumo | Proton |
| [`jules/`](./jules) | Jules (async coding agent) | Google |
| [`github-copilot-cli/`](./github-copilot-cli) | GitHub Copilot CLI | GitHub (Microsoft) |
| [`grok-build/`](./grok-build) | Grok Build | xAI |
| [`codex-supplement/`](./codex-supplement) | Codex (supplementary leaked captures) | OpenAI |
