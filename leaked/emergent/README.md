# Emergent

- **Type**: Coding/app-building agent · **Vendor**: Emergent
- **Status**: closed source (leaked)
- **Mirror source**: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Emergent (2026-07-10)

## Files
- `Prompt.txt` — system prompt.
- `Tools.json` — tool/function definitions (despite the name, this is
  plain-text tool documentation, not actually parseable JSON).

## Sub-agents

A **fleet of six named, single-purpose specialist agents**, each exposed
as its own tool taking essentially one parameter (`task`, a free-text
description) — the most agent-per-narrow-job design in this collection,
contrasting with the typed-but-general registries (Claude Code's
`general-purpose`/`statusline-setup`/`output-style-setup`) or the
capability-tiered menu (Amp's Task/Oracle/Codebase-Search) seen
elsewhere:

- **`auto_frontend_testing_agent`** — "Expert agent for UI testing using
  playwright and browser automation."
- **`deep_testing_backend_v2`** — "Expert agent for testing backend using
  curl and UI using playwright." `Prompt.txt` elevates this specific
  agent to a mandatory workflow step, not an optional delegate: "YOU MUST
  test BACKEND first using `deep_testing_backend_v2`," coordinated
  through a shared `test_result.md` file that documents its own
  "Testing Protocol and communication protocol with testing sub-agent" —
  a **file-mediated handoff channel**, distinct from every other
  source's in-band tool-call/tool-result protocol.
- **`integration_playbook_expert_v2`** — generates playbooks for
  third-party API integrations; `Prompt.txt` requires its output be
  followed *exactly*: "Always implement third-party integrations EXACTLY
  as specified in the playbook returned by integration_playbook_expert_v2.
  Even the model names and configuration of the code should be as per the
  OUTPUT OF THE integration_playbook_expert_v2 SUBAGENT" — one of the
  strongest "trust the sub-agent's output unconditionally" statements in
  this collection.
- **`vision_expert_agent`**, **`support_agent`**, **`deployment_agent`** —
  image-URL selection, platform Q&A, and native-deployment debugging,
  respectively; each still just a `task` string in, free-text report
  back.
- **A rare explicit reliability warning about the sub-agent's own
  competence**: "Subagent sometimes is dull and lazy so doesn't do full
  work or sometimes is over enthusiastic and does more work. Please
  check the response from sub agent including git-diff carefully." — no
  other source in this collection warns the orchestrator this bluntly
  that a sub-agent's self-reported summary may not match what it
  actually did, or prescribes a concrete verification method (diffing
  the actual changes) rather than just trusting the report.
- **Scope discipline pushed onto the sub-agent, not just the
  orchestrator**: "Agent or subagent should mostly only focus on solving
  the problem... should not get distracted with documentation,
  deployment, extensive tests, security, privacy, code quality too much"
  — an MVP-speed framing applied uniformly to both levels.
