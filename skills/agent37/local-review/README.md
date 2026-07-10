# local-review

Reviews uncommitted local changes (staged + unstaged) before commit.
Orchestrates a Haiku agent to summarize the diff, then 5 parallel Sonnet
agents (CLAUDE.md compliance, bug/logic errors, OWASP security scan,
TypeScript/perf/quality, and a code-simplification specialist), then scores
each finding's confidence 0-100 via a Haiku agent per issue and filters out
anything below 80 before presenting results grouped by severity.

## Files
- `commands/local-review.md` — the full command prompt (orchestration
  steps, sub-agent instructions, confidence scoring rubric, output format).
- `plugin.json` — plugin metadata.
