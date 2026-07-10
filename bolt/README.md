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
