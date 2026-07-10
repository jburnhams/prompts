# Bolt.new

- **Type**: AI app-building agent (full-stack web apps, runs in-browser via
  WebContainer)
- **License**: MIT
- **Source**: https://github.com/stackblitz/bolt.new
- **Retrieved from**: `main` branch,
  `app/lib/.server/llm/prompts.ts` (2026-07-10)

This was previously flagged as a "candidate for next pass" after being
skipped from the `leaked/` bulk-import (its prompt is mirrored there via a
leak aggregator, but since Bolt is genuinely open source, the real source
is better). There's also a popular community fork, `stackblitz-labs/bolt.diy`
(multi-LLM support), with its own prompt worth adding separately if wanted.

## Files

- `prompts.ts` — the full system prompt: persona, WebContainer environment
  constraints (no `pip`, no native binaries, browser-only execution),
  formatting rules, and the `<boltArtifact>`/`<boltAction>` output protocol
  bolt.new parses to apply changes.

## Tool surface

The most tightly constrained shell of any source in this collection —
everything else assumes a real OS underneath; Bolt's runs entirely inside
a browser.

- **Shell**: an explicit **allowlist** of exactly 39 commands (`cat`,
  `chmod`, `cp`, `echo`, `hostname`, `kill`, `ln`, `ls`, `mkdir`, `mv`,
  `ps`, `pwd`, `rm`, `rmdir`, `xxd`, `alias`, `cd`, `clear`, `curl`,
  `env`, `false`, `getconf`, `head`, `sort`, `tail`, `touch`, `true`,
  `uptime`, `which`, `code`, `jq`, `loadenv`, `node`, `python3`, `wasm`,
  `xdg-open`, `command`, `exit`, `export`, `source`) — no
  `grep`/`find`/`sed`/`awk` in the list at all, and the prompt explicitly
  says to prefer Node.js scripts over shell scripts since "the environment
  doesn't fully support shell scripts."
- **Search**: none of the usual text-search tools (`grep`, `find`, `rg`)
  are in the shell allowlist — search has to be done via Node scripting
  or `head`/`tail`/`sort` pipelines instead.
- **Code execution**: `python3` is present but explicitly **standard-library
  only** — "there is NO `pip` support," and "even some standard library
  modules that require additional system dependencies (like `curses`) are
  not available." `node` is fully supported and is the recommended
  scripting language. No C/C++ compiler ("WebContainer CANNOT run native
  binaries or compile C/C++ code").
- **Editing**: no dedicated edit tool — `<boltAction type="file">` carries
  the **complete file contents**, not a diff, matching the whole-file-rewrite
  pattern common to this collection's app-builder archetype.
- **Browser/web**: `curl` is in the allowlist (network access from inside
  the sandbox), but no browser-automation/screenshot tool.
- **Multimodal**: not addressed.
- **Sandbox/isolation**: the sandbox *is* the whole runtime — StackBlitz's
  WebContainer, an in-browser Node.js environment with no real OS,
  documented in the prompt itself rather than left implicit.
