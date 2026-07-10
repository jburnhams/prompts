# local-review

Reviews uncommitted local changes (staged + unstaged) before commit.
Orchestrates a Haiku agent to summarize the diff, then 5 parallel Sonnet
agents (CLAUDE.md compliance, bug/logic errors, OWASP security scan,
TypeScript/perf/quality, and a code-simplification specialist), then scores
each finding's confidence 0-100 via a Haiku agent per issue and filters out
anything below 80 before presenting results grouped by severity.

## Scaffolding (beyond the prompt text)

- **Context construction**: a Haiku agent runs `git status`, `git diff`
  (unstaged), and `git diff --staged`, and summarizes what changed — the
  raw diff itself isn't reformatted (unlike PR-Agent's custom hunk format;
  see `../../../pr-agent/README.md`), it's just handed to reviewer agents
  along with the summary.
- **Extra context**: a second Haiku agent separately locates the root
  `CLAUDE.md` plus any `CLAUDE.md` in directories containing modified
  files, so review agents can check compliance.
- **Tools**: `Bash(git diff/status/log/blame/show)` only — read-only.
- **Confidence scoring**: same shape as TuringMind's (see
  `../../turingmind/README.md`) — a Haiku agent scores each finding 0-100
  and anything under 80 is dropped, but the rubric here is coarser (0/25/50/
  75/100 buckets with qualitative descriptions) rather than an additive
  point system.
- **Output format**: fixed Markdown template with Critical (95-100) /
  Warning (80-94) / Simplification sections, each entry as
  `**file.ts:42** - description` plus explanation and suggested fix. No
  "filtered issues" transparency section (unlike TuringMind's).

## Files
- `commands/local-review.md` — the full command prompt (orchestration
  steps, sub-agent instructions, confidence scoring rubric, output format).
- `plugin.json` — plugin metadata.
