# Inside the Scaffold: A Source-Code Taxonomy of Coding Agent Architectures

- **Author**: Benjamin Rombaut
- **License**: CC-BY 4.0
- **Source**: https://arxiv.org/abs/2604.03515 (submitted 2026-04-03,
  revised 2026-04-10 as v2)
- **Stored here**: `inside-the-scaffold-v1.pdf` — the **v1** PDF
  specifically (https://arxiv.org/pdf/2604.03515v1), retrieved
  2026-07-10. A v2 exists at
  [arxiv.org/abs/2604.03515v2](https://arxiv.org/abs/2604.03515v2) if you
  want the revised version instead.

Stored here (rather than just linked) since it's directly useful
background for this repo: a systematic **architecture**-level comparison
of 13 open-source coding agents, complementary to this repo's own
**prompt**-level comparisons in
[`../../coding-agent-approaches.md`](../../coding-agent-approaches.md) and
[`../../code-review-approaches.md`](../../code-review-approaches.md).

## What it covers

A taxonomy across three layers — control architecture, tool/environment
interfaces, and resource management — built by reading actual source code
(claims are grounded in specific file paths and commit hashes, not
documentation). Key findings: control strategies sit on a spectrum from
fixed pipelines to Monte Carlo Tree Search rather than falling into
discrete categories; tool counts across the 13 agents range from 0 to 37;
context-compaction strategies vary across seven distinct approaches; and
11 of the 13 agents compose the same five loop primitives (ReAct,
generate-test-repair, plan-execute, multi-attempt retry, tree search) in
different combinations rather than inventing bespoke control flow.

## Agents analyzed

CLI tools: Aider, Cline, Codex CLI, Gemini CLI, OpenCode — all also in
this collection (see their own top-level folders).

SWE-bench-family agents: AutoCodeRover, OpenHands, SWE-agent, Prometheus,
DARS-Agent, Moatless Tools, Agentless — OpenHands and SWE-agent are in
this collection; AutoCodeRover, Prometheus, DARS-Agent, Moatless Tools,
and Agentless are noted as candidates for a future pass in the root
README.

Reference baseline: mini-swe-agent — also in this collection
(`../../mini-swe-agent/`).
