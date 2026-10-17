# Codex's own repository review skills (removed 2026-09-30)

- **License**: Apache-2.0
- **Source**: `github.com/openai/codex`, `.codex/skills/code-review*/SKILL.md`
- **Read at**: `ee6814b` (2026-09-12), the commit this folder's README
  records. Missed in that pass, because it read the shipped corpus and not
  the repository's own agent guidance.
- **Removed by**: `18131270fe` (2026-09-30, #49713), "Remove
  repository-local Codex guidance, skills, and environment config". That
  commit deleted the root `AGENTS.md`, every skill under `.codex/skills/`,
  and `.codex/environments/environment.toml` in one change. Its message
  gives no reason. Captured here because these four files were the clearest
  example in the collection of a repository encoding **its own risk
  surface** as review lenses.

The structure: one orchestrator skill fans out a subagent per sibling
`code-review-*` skill at `xhigh` reasoning, and returns "every single issue
from every subagent". It adds a `code-reviewed` label only when the person
running the review owns the PR, and posts no GitHub comments unless asked.
The three lens skills follow, verbatim.

## `code-review-change-size`

```
Unless the change is mechanical the total number of changed lines should not exceed 800 lines.
For complex logic changes the size should be under 500 lines.

If the change is larger, explain whether it can be split into reviewable stages and identify the smallest coherent stage to land first.
Base the staging suggestion on the actual diff, dependencies, and affected call sites.
```

## `code-review-breaking-changes`

```
Search for breaking changes in external integration surfaces:
- app-server APIs
- CLI parameters
- configuration loading
- resuming sessions from existing rollouts

Do not stop after finding one issue; analyze all possible ways breaking changes can happen.
```

## `code-review-context`

```
Codex maintains a context (history of messages) that is sent to the model in inference requests.

1. No history rewrite - the context must be built up incrementally.
2. Avoid frequent changes to context that cause cache misses.
3. No unbounded items - everything injected in the model context must have a bounded size and a hard cap.
4. No items larger than 10K tokens.
5. Highlight new individual items that can cross >1k tokens as P0. These need an additional manual review.
6. All injected fragments must be defined as structs in `core/context` and implement ContextualUserFragment trait
```

## Why these matter for review design

- **Rule 5 of `code-review-context` is an escalation rule, not a finding
  rule.** A new context item that can exceed 1k tokens is P0 and "need[s]
  an additional manual review", whether or not anything is wrong with it.
  This is the post-2026 pattern in miniature: a repo-specific invariant
  whose *touch*, not its violation, raises the amount of human attention.
- **The lenses are the repo's blast-radius map.** "External integration
  surfaces" (APIs, CLI flags, config loading, resume from old rollouts)
  are exactly where a change can't be quietly reverted, because something
  outside the repo already depends on the old shape.
- **Size as a review-feasibility rule**, with a split proposal ("the
  smallest coherent stage to land first") rather than a complaint.
  Graphite's stacking and Bugbot's "too large to review" comment are the
  product versions of this.

See [`../agent-design/risk.md`](../agent-design/risk.md) for how these feed
the design.
