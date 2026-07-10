# VS Code Agent (leaked extraction)

- **Type**: Coding agent (VS Code's built-in Copilot agent mode)
- **Vendor**: Microsoft · **Status**: leaked extraction, kept separate from
  the official `../../copilot-chat/` folder
- **Mirror source**: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/VSCode%20Agent (2026-07-10)

Microsoft's `vscode-copilot-chat` is officially open source (see
`../../copilot-chat/`), so prefer that folder as the authoritative source.
This folder is kept anyway because it's a differently-dated, independently
extracted snapshot — useful for spot-checking whether the official repo
matches what's actually shipped/observed at runtime, and because it
includes some prompt variants (e.g. `nes-tab-completion.txt` for "next edit
suggestion" tab-completion) not present in the official repo's agent/
folder.

## Files
- `Prompt.txt` — main agent-mode system prompt.
- `claude-sonnet-4.txt`, `gemini-2.5-pro.txt`, `gpt-4.1.txt`, `gpt-4o.txt`,
  `gpt-5.txt`, `gpt-5-mini.txt` — per-model variants.
- `chat-titles.txt` — prompt for auto-generating chat/session titles.
- `nes-tab-completion.txt` — prompt for inline "next edit suggestion"
  tab-completion (not an agent-mode feature, but from the same extraction).
