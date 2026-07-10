# code-review

Reviews a GitHub pull request. Launches 5 independent reviewer agents
(CLAUDE.md compliance, bug detection, git-history/blame context, prior PR
comment history, and code-comment verification/accuracy), scores each
finding's confidence, and posts only high-confidence (default threshold 80)
comments as inline GitHub PR comments with direct links.

This is the plugin `agent37`'s `local-review` (see `../../agent37/`) says
it's explicitly modeled on — worth comparing the two side by side.

## Files
- `commands/code-review.md` — the full command prompt.
- `plugin.json` — plugin metadata.
- `README-orig.md` — the plugin's own README from the source repo (usage,
  config options), kept for reference.
