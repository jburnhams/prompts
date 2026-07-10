# Windsurf (Cascade)

- **Type**: Coding agent (Windsurf IDE's "Cascade" assistant)
- **Status**: Closed source. This is a **leaked** prompt, not an official
  release.
- **Vendor**: Windsurf (formerly Codeium)
- **Mirror source**: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Windsurf
  — a large, actively maintained community aggregator of leaked/extracted
  system prompts from many closed-source AI products. Retrieved from that
  repo's `main` branch (2026-07-10).
- **Labeled version**: "Wave 11" (the aggregator's internal versioning for
  which Windsurf release this was pulled from — Windsurf doesn't publish
  version numbers for prompt changes).

## Files

- `prompt-wave-11.txt` — the Cascade system prompt: persona, tool-calling
  rules, and behavioral guidelines. Note it explicitly instructs the model
  to claim `GPT 4.1` as its underlying model if asked, regardless of the
  actual model serving the request.
- `tools-wave-11.txt` — accompanying tool/function definitions (JSON-ish
  schemas) available to Cascade.
