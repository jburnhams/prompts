# Permissions and approval: deciding whether an action needs a human first

A further drill-down alongside [`agent-context-compaction.md`](./agent-context-compaction.md),
[`agent-turn-output.md`](./agent-turn-output.md), and
[`agent-self-verification.md`](./agent-self-verification.md): before a
coding agent runs a shell command, edits a file, or makes a network
call, what decides whether it needs to stop and ask a human first? The
answers span a genuinely wide range — from nothing at all (a prompt
that just says "don't do anything harmful"), through static allow/deny
rule engines of wildly varying sophistication, to systems where a
*second, separate model call* judges the *first* model's proposed
action before it's allowed to run.

**Methodology note**: seventeen sources are covered. Eleven required
fresh research — five via live-source investigation (Codex CLI, Roo
Code, OpenCode, Gemini CLI, and a corroborating fetch of Claude Code's
public hooks documentation) and six read from local files already in
this collection (Claude Code's leaked architecture notes, OpenHands,
Cline, Copilot Chat, Goose, Crush, Pi). Six more leaked sources (Cursor,
Devin, Warp, Windsurf, Replit, Factory/Droid) were read from local
files. This doc's own recurring finding, consistent with every other
synthesis doc in this collection: sources that were only ever
characterized by a passing aside ("Codex has a permission engine," "Roo
Code has an approval flow") turned out, once actually investigated at
the code level, to be dramatically more sophisticated than the aside
suggested — Codex CLI's permission architecture in particular is not
one mechanism but five cooperating subsystems, and Gemini CLI's runs an
entire second, independent LLM as a judge over the first model's tool
calls.

## Sources covered

**With confirmed, code-level-verified mechanisms**: Codex CLI, Roo
Code, OpenCode, Gemini CLI, Claude Code (leaked, corroborated by public
docs), OpenHands, Cline.

**With confirmed, prompt-text-level mechanisms** (no live-source
investigation performed; findings are what the captured prompt itself
says, not confirmed against a codebase): Copilot Chat, Crush, Cursor
(leaked), Devin (leaked), Windsurf (leaked), Replit (leaked), Factory/
Droid (leaked).

**Confirmed absent or near-absent**: Goose (a named
`permission_judge.md` file exists upstream but was captured as 0
bytes — a real, evidenced capture gap, not a confirmed absence), Pi
(the one source in this survey whose entire prompt-construction logic
is readable, non-truncated executable code with no permission branch
anywhere in it — an unusually strong negative result), Warp (leaked —
the only source with no structured mechanism of any kind, just a vague
prompted "bias against unsafe commands").

---

## 1. Approval mode taxonomies

Three structurally different answers to "how many discrete states does
the approval posture have."

| Shape | Sources |
|---|---|
| **A small number of named, mutually-exclusive modes, explicitly ordered by permissiveness in code** | Gemini CLI — `plan → default → autoEdit → yolo`, a literal `MODES_BY_PERMISSIVENESS` array. Claude Code (leaked) — six modes (`default`, `plan`, `acceptEdits`, `bypassPermissions`, `dontAsk`, and an internal-only `auto`), independently corroborated by Anthropic's public hooks docs exposing the identical six-value enum. Codex CLI — four modes (`UnlessTrusted`/`OnRequest`/`Granular`/`Never`), with a `Granular` variant carrying five independent sub-toggles (sandbox-escalation, execpolicy prompts, skill execution, `request_permissions`, MCP elicitations) that can each be silently auto-rejected without surfacing to the user. |
| **Named agent/task modes that each carry a baked-in ruleset, rather than one global switch** | OpenCode — `build`/`plan`/`explore`/hidden system agents each ship a distinct permission ruleset, with an orthogonal `auto`/`yolo` flag layered on top (including two undocumented CLI aliases, `--yolo` and `--dangerously-skip-permissions`). Factory/Droid (leaked) — a Diagnostic-vs-Implementation task-scope mode that gates blast radius rather than individual commands. |
| **A continuous per-category policy vector, not discrete states at all** | Roo Code — seven independent booleans (`alwaysAllowReadOnly`/`Write`/`Mcp`/`ModeSwitch`/`Subtasks`/`Execute`/`FollowupQuestions`), each gating a different tool category behind a master switch — no single "mode" exists the way Codex or Gemini CLI have one. |
| **A single self-tag per action, not a mode at all** | Windsurf (leaked) — `SafeToAutoRun` boolean on every `run_command` call. Replit (leaked) — `is_dangerous` boolean on shell-command proposals (Assistant product only; the more autonomous Agent's `bash` tool has no such field). Cline — `requires_approval` boolean on `execute_command`, consulted only "in case the user has auto-approve mode enabled." |
| **No structured mode or tag at all — a vague, prompted judgment call** | Warp (leaked) — "bias strongly against unsafe commands... NEVER suggest malicious or harmful commands." Devin (leaked) — no approval infrastructure whatsoever; see §7. |
| **Not found / capture gap** | Goose, Pi, Aider (not investigated this pass — see `agent-tool-surfaces.md`/other docs for what was checked). |

**The Codex/Gemini CLI "granular sub-toggle" pattern is worth naming
explicitly**: both sources let one nominally-coarse mode selection
silently suppress entire *categories* of approval request rather than
just changing a blanket threshold — Codex's `Granular` config can turn
off MCP elicitation prompts specifically while leaving shell-escalation
prompts on; Gemini CLI's global `deny` rules remove a tool from the
model's function-declaration list entirely rather than merely refusing
it at call time. Both are a stronger, more structural kind of gating
than a simple ask/don't-ask toggle.

## 2. Risk classification: static rules vs. LLM-based judgment

The central axis this doc set out to investigate, and the one with the
widest spread of sophistication found anywhere in this collection.

| Design | Sources |
|---|---|
| **Static only — no LLM classification anywhere in the approval path, confirmed by source-level search, not just absence of prompt text** | OpenCode (real tree-sitter WASM parsing of bash/PowerShell into an AST, sub-command-by-sub-command checking, plus a static offline-generated "arity" lookup table for suggesting allowlist patterns — but zero runtime risk-classification calls). Roo Code (deterministic longest-prefix-match over flat allow/deny string arrays, plus a hardcoded regex bank, `containsDangerousSubstitution()`, that unconditionally forces a manual ask regardless of the lists — pure pattern-matching, never a model call). |
| **A single boolean, self-assigned by the acting model itself, every call** | Windsurf's `SafeToAutoRun`, Replit's `is_dangerous`, Cline's `requires_approval` — three sources with the same shape (the model tags its own action) but no external check on whether the tag is honest; enforcement is entirely in what the *client* does with the flag, not in the flag's accuracy. |
| **Static rules PLUS an opt-in, fully separate LLM reviewer layered on top — not a fallback, not a replacement, a second independent gate** | Gemini CLI's "Conseca" (off by default, `enableConseca`): a fast model (`DEFAULT_GEMINI_FLASH_MODEL`) first synthesizes a least-privilege, per-tool JSON policy tailored to the specific user request, then a second call re-checks each actual tool call against that generated policy and returns `allow`/`deny`/`ask_user` — wired into the *same* priority-tiered rule engine as the static TOML rules (`conseca.toml`, priority 100), not a separate code path. Codex CLI's "Guardian" (off by default, `approvals_reviewer = auto_review`): a dedicated, cheaper/faster model (`codex-auto-review`, low reasoning effort) reviews the exact planned action against a written risk-taxonomy document and returns a structured `{risk_level: Low/Medium/High/Critical, user_authorization, outcome, rationale}` verdict — fail-closed on timeout (90s hard limit), running in a locked-down cached sub-session with no inherited exec-policy rules of its own. Claude Code's `auto` mode (leaked): `yoloClassifier.ts` runs a genuine **two-pass fast/slow LLM design** — a cheap first pass decides allow/no-allow, escalating to a slower "thinking" pass only if the fast pass leans toward blocking — built from recent conversation context plus the user's *own* configured allow/deny rules and `CLAUDE.md`, so the classifier's judgment is itself conditioned on the static rule layer rather than independent of it. A companion `bashClassifier.ts` exists for more granular bash-specific classification but is a confirmed stub in the public repo (see the caveat below). |
| **A genuinely pluggable, operator-selectable choice between the static and LLM philosophies** | OpenHands — three interchangeable `SecurityAnalyzer` implementations: `LLMRiskAnalyzer` (trusts the model's own `security_risk` self-tag verbatim), `InvariantAnalyzer` (a separate, Dockerized static policy-analysis server evaluating the action trace independent of what the model claims), and a third, unexamined `GraySwanAnalyzer`. Unlike Gemini CLI/Codex (where the LLM layer is a fixed add-on), OpenHands makes the entire philosophy a config-time choice — the same "infrastructure over instruction" pattern this collection's compaction and sub-agent docs found distinguishing OpenHands elsewhere. |
| **Confirmed absent — no flag, no tier, nothing** | Cursor (no risk field found in any of five dated prompt versions or the tools JSON — a real gap given `run_terminal_cmd`'s otherwise-detailed approval-flow text), Devin, Factory/Droid, Warp. |

**The caveat that matters most for Claude Code's entry above**: the
`auto` mode itself is confirmed **internal-only** — excluded from the
externally-available mode set by an `isExternalPermissionMode()` type
guard, gated behind a feature flag, the same pattern this collection's
self-verification doc found for Claude Code's adversarial verification
subagent. `bashClassifier.ts`'s own code comment is explicit:
"classifier permissions feature is ANT-ONLY." So of this doc's three
separate-LLM-reviewer implementations, two (Gemini CLI's Conseca, Codex's
Guardian) are real, off-by-default-but-user-reachable features; the
third (Claude Code's `yoloClassifier.ts`) is confirmed to exist and
work as described, but not confirmed to be something an ordinary
external user can actually turn on. Corroborating evidence this isn't
just a leak artifact: Anthropic's own public hooks documentation names
`PermissionRequest` and `PermissionDenied` hook events, the latter
described as firing "when a tool call is denied by the auto mode
classifier" — independent confirmation the classifier is real, without
confirming external availability either way.

**A finer point worth carrying forward**: OpenHands' risk tiers aren't
even fixed — the LOW/MEDIUM/HIGH *definitions themselves* change via a
Jinja conditional depending on whether the agent is running in CLI mode
(host filesystem) or sandboxed/container mode, with a closing rule that
overrides both: "Always escalate to HIGH if sensitive data leaves the
environment." No other source couples its risk categories this tightly
to the actual isolation boundary in play.

**And a fail-safe/fail-open contrast worth naming**: OpenHands defaults
to treating an unclassified action as maximum-suspicion ("When no
security analyzer is configured, treat all actions as UNKNOWN
risk... ensures confirmation is required") and Codex's Guardian
resolves any failure mode — timeout, parse error, session error — to
rejection, never silent allow. OpenCode's headless-mode default runs
the other direction on a different axis (auto-*reject* rather than
block forever when no human is present to answer at all) — see §7.

## 3. Rule/policy definition mechanisms

| Mechanism | Sources |
|---|---|
| **A real embedded scripting language, not a data format** | Codex CLI — `.rules` files are Starlark (Python-like) programs with `prefix_rule()` declarations carrying `pattern`/`decision`/`justification` plus unit-test-style `match`/`not_match` assertions, and a real CLI subcommand (`codex execpolicy check`) for testing rules offline before deploying them. |
| **A structured config format with an explicit source-priority hierarchy** | Gemini CLI — TOML policy files across a 5-tier system (`Admin(5) > User(4) > Workspace(3) > Extension(2) > Default(1)`, computed as `tier_base + toml_priority/1000` so tier ordering can never be overridden by a clever in-tier number), with admin-tier files additionally requiring root/UID-0 ownership and locked-down permissions before being trusted — a real privilege-escalation guard, not just convention. Claude Code (leaked) — settings-file JSON (`{"permissions": {"allow": [...], "deny": [...], "ask": [...]}}`) loaded at policy(managed/enterprise) > project > user > local scope, with a managed-settings flag that can restrict evaluation to policy rules only. |
| **A flat rule array, JSON-configured, with real syntax-aware command parsing underneath** | OpenCode — `{permission, pattern, action}` triples, last-match-wins evaluation, but with actual tree-sitter WASM grammars parsing bash/PowerShell into an AST so compound commands are split and each sub-command checked independently — not a shape any other source in this survey matches. |
| **Flat string arrays in application settings, no DSL at all** | Roo Code — `allowedCommands`/`deniedCommands` plain string-prefix arrays configured through a VS Code settings UI, evaluated by longest-prefix-match. |
| **A prompted, example-based policy — English text, not machine-checked rules** | Copilot Chat's Anthropic-family `operationalSafety` tag ("Take local, reversible actions freely... For actions that are hard to reverse, affect shared systems, or could be destructive, ask the user first," with a named example list) — the only source in this collection classifying risk by a stated *principle* (reversibility) rather than a command list or numeric tier, and doing so in plain prose rather than structured config. Crush's `<critical_rules>` block hardcodes specific named-action gates ("NEVER COMMIT... NEVER PUSH TO REMOTE... unless user explicitly says") the same way, alongside a separate consequence-based heuristic ("Only stop/ask if... could cause data loss"). |
| **A hardcoded, non-configurable protection list, distinct from the general policy** | Roo Code's `RooProtectedController` — `.rooignore`/`.roomodes`/`.roorules*`/`AGENTS.md` and similar are write-protected "regardless of autoapproval settings," a real prompt-injection defense (nothing can talk the agent into rewriting its own instruction files) that sits outside and above the normal allow/deny system entirely. |
| **No rule/policy mechanism found** | Devin, Warp, Pi. |

## 4. Scope and persistence of an approval

How long does "yes" last once granted?

| Tier structure | Sources |
|---|---|
| **Five distinct outcomes spanning one-off to per-host-forever** | Codex CLI — `Approved` (one-off) / `ApprovedExecpolicyAmendment` (written directly to `codex_home/rules/default.rules`, survives process restart) / `ApprovedForSession` (in-memory, this session only) / `NetworkPolicyAmendment` (the same permanent-write pattern, scoped per-host) / plus `TimedOut` and `Abort` as distinct non-approval outcomes. Which of these are even offered to the user is itself dynamic — an amendment option only appears when a concrete rule was actually derivable from the request. |
| **A rich, multi-scope save mechanism plus mode-aware trust propagation** | Gemini CLI — `ProceedOnce`/`ProceedAlways` (session only) vs. `ProceedAlwaysAndSave` (atomically written to a user- or workspace-scoped TOML file, with automatic backup-and-recovery from a corrupted policy file) vs. `ProceedAlwaysServer`/`ProceedAlwaysTool` (scoped to an entire MCP server or tool name, not one command shape). Distinctively, trust propagates only *toward* more permissive modes: approving in `plan` mode (the most restrictive) grants trust across all four modes; approving in `yolo` applies to `yolo` only. |
| **Nominally session-scoped, with a separate persistent layer of unconfirmed reach** | OpenCode — an "always" reply is explicitly session-only (the TUI's own copy: "This will allow ... until OpenCode is restarted"), but a separate SQLite-backed `PermissionSaved` table exists in the schema/DB layer with no confirmed call sites writing to it outside its own definition — flagged as an unresolved, possibly-unwired feature rather than a working persistence tier. |
| **Two tiers only, no session cache at all** | Roo Code — a decision is either asked every single time, or explicitly promoted into the persisted `allowedCommands`/`deniedCommands` settings via an in-chat UI (permanent, survives restarts). There is no analog of Codex's `ApprovedForSession` — everything not already on the persisted lists gets re-asked for the life of the extension. |
| **A rule-source model with both a session tier and four persisted scopes, resolved together rather than layered as fallback tiers** | Claude Code (leaked) — a `PermissionRule` carries a `source` field valued at user/project/local/flag/policy-settings, CLI arg, command, **or session** — i.e. session-scoped rules are one first-class rule source among several, not a separate cache Codex-style. Rules from every source are aggregated into three maps (always-allow/always-deny/always-ask) that a single decision function consults in order (allow wins outright, deny blocks outright), rather than checking session first and falling through to disk. The four persisted scopes (policy/managed-enterprise > project > user > local) load in that precedence order, with a managed-settings flag able to restrict evaluation to policy rules only — an enterprise lockdown Codex/Gemini CLI have no direct equivalent of, closer in spirit to Gemini CLI's admin-tier ownership/permission requirements (§3) than to any of its own persistence peers. |
| **Client-side, out-of-band, and explicitly unreachable by the model itself** | Windsurf — the only sanctioned override for `SafeToAutoRun` is a user-configured settings allowlist the model is told exists but is given no tool to read or write, and is explicitly told to keep opaque in conversation ("do not refer to any specific arguments of the run_command tool in your response"). |
| **Not addressed / no persistence concept found** | Cline (no session-cache language beyond the client-side auto-approve toggle itself), Cursor, Devin, Replit, Factory/Droid, Warp. |

## 5. Escalation behavior

What makes an already-trusted-seeming action re-trigger a fresh
approval?

- **Repeated-identical-call circuit breaker, unlike every other
  escalation mechanism surveyed** — OpenCode's `doom_loop`: if the
  exact same tool call (same tool, same JSON-stringified input) fires
  three times in a row, a fresh ask fires regardless of any prior
  "allow" rule. Every other escalation trigger in this survey re-asks
  because something *changed*; this one re-asks because something
  *repeated*.
- **Content-based downgrade of an otherwise-allowed command** — Gemini
  CLI: a command matching an ALLOW rule still gets force-downgraded to
  `ASK_USER` if it contains shell redirection (`>`, `>>`, `<`, etc.),
  unless the specific rule explicitly permits it or the mode is
  `autoEdit`/`yolo` — checked per-sub-command in a chain, the same
  "split the compound command" idea OpenCode implements via
  tree-sitter, here via a `shell-quote`-based parser.
- **Escalation at the syscall level, inside an already-running sandbox,
  not just a pre-flight gate on the typed command** — Codex CLI: a
  patched shell forwards every individual `exec()` call to a server
  over a Unix socket mid-execution, which can independently run,
  escalate out of the sandbox, re-sandbox, or deny that one syscall —
  a compound command already executing inside the sandbox can have one
  of its internal `exec()` calls separately intercepted and judged,
  something no other source in this survey does.
- **A cumulative rate-limit trigger, unrelated to any single command's
  risk** — Roo Code's `allowedMaxRequests`/`allowedMaxCost`: forces a
  fresh manual approval once N auto-approved calls or $-cost have
  accumulated since the last reset, even when every individual action
  was independently allowlisted. Codex CLI has no equivalent of this,
  though its Guardian has an analogous but differently-shaped circuit
  breaker (3 consecutive denials, or 10 in a trailing 50-entry window,
  force-interrupts the turn back to the human).
- **User-edit-in-place re-approval, an approval-workflow rule rather
  than a risk re-check** — Cursor: "The user may reject it if it is
  not to their liking, or may modify the command before approving it.
  If they do change it, take those changes into account" — confirms a
  propose-then-user-may-edit loop exists, but the model is simply told
  to honor the edited command, not that the edit triggers a fresh risk
  classification. Copilot Chat's Family H/MiniMax prompts carry
  identical text, confirming the same UI pattern exists there too but
  gated per model-family.
- **No escalation mechanism found** — Devin, Warp, Cline (beyond the
  count-based auto-approval-limit message, which is closer to §4's
  persistence axis than a true re-classification trigger), Factory/
  Droid, Replit.

## 6. Sandbox and isolation as a complementary layer

- **Explicitly coupled to the approval decision itself, not a
  substitute for it** — Codex CLI: even under the most permissive
  approval mode short of the full bypass flag, an unsandboxed
  dangerous command stays forbidden unless the sandbox is *also*
  explicitly disabled — confirmed by a source comment explaining that
  even a patch provably confined to writable paths still runs
  sandboxed, "to prevent hard link exploitation." Three real
  platform-specific backends (Landlock/Seatbelt/Windows native).
- **A second, independent policy surface just for the sandbox, keyed
  by the same mode enum** — Gemini CLI: `sandbox-default.toml` defines
  its own per-mode `network`/`readonly`/`approvedTools` settings (a
  short shell-command allowlist), running as a genuinely separate gate
  underneath the tool-call policy engine, not a rewording of it. One
  concrete hardcoded rule lives here specifically: any tool call whose
  arguments match `gha-creds-.*\.json` (GitHub Actions credential
  files) is denied outright, independent of the general rule engine.
- **A different kind of "sandbox" entirely — output isolation, not
  action isolation** — Goose: CSP-based sandboxing applies to
  *generated app content* ("strict CSP, so all JavaScript must be
  inline"), not to the agent's own shell/file actions. Worth
  distinguishing explicitly so this doesn't get miscounted as a
  command-execution safety layer.
- **Confirmed absent, with the entire safety burden resting on the
  approval layer alone** — Roo Code (no sandbox references anywhere in
  `src/core/` beyond an unrelated CI/test context), Cline, Cursor,
  Devin, Warp, Replit, Crush, Copilot Chat.
- **Present as infrastructure but never invoked as a safety
  rationale** — Devin ("a real computer operating system," presumably
  an isolated cloud VM per task by product design) and Factory/Droid
  (a scoping statement about `fileSystem` repository locations) both
  describe an execution environment without ever pointing to its
  isolation as a reason approval can be skipped — the isolation and
  the approval-philosophy discussion simply never touch in the
  captured text.

## 7. Where the enforcement actually lives: harness vs. prompt

A cross-cutting structural finding, not tied to any one axis above: for
most sources with a real mechanism, **the model's own system prompt
says nothing about it**.

- **Claude Code (leaked)**: a targeted search of `Prompt.txt` (the
  plain extracted system prompt) found zero language about permission
  modes, risk classification, or approval mechanics — the entire
  six-mode/rule-resolution/classifier architecture documented above
  lives in harness code the model never sees. The model isn't told the
  rules; it's just gated by them.
- **OpenHands is the partial exception**: `security_risk_assessment.j2`
  *is* injected directly into the model's own system prompt, making it
  an active participant in tagging its own risk — but the harness still
  treats that self-tag as advisory-only, overridable by a pluggable
  analyzer, and fails safe to "ask for everything" if no analyzer is
  configured. The model participates, but isn't trusted.
- **Windsurf, Replit, Cline sit in between**: the risk-tag *field* is
  prompted (the model must supply `SafeToAutoRun`/`is_dangerous`/
  `requires_approval` on every relevant call), but what the client does
  with that tag — whether it's honored, ignored, or checked against an
  allowlist — is entirely outside the prompt.
- **Devin and Warp represent the opposite design philosophy
  entirely — not "hide the mechanism" but "there is no mechanism to
  hide."** Devin substitutes a mandatory `<think>` reflection
  checkpoint and absolute hard-coded prohibitions ("Never force push,"
  "Never use `git add .`") for any form of conditional risk judgment —
  safety is enforced by what the model is *forbidden from doing at
  all*, not by asking permission for what it's allowed to attempt. A
  `<report_environment_issue>` tool implements a notify-and-continue
  pattern for problems, rather than a blocking pause. Warp's prompt
  actively discourages seeking approval at all ("bias toward action...
  don't ask for confirmation first"), carving out only scope-creep
  ("don't push without confirmation") as an exception, not command
  risk.
- **OpenCode's headless-mode default is a clean, code-confirmed
  answer to "what happens when nobody's there to ask"**: without an
  explicit auto-approve flag, non-interactive runs auto-*reject* every
  permission request with a visible warning, rather than blocking
  forever or silently allowing — a fail-closed default worth
  contrasting with Codex's Guardian (which also fails closed, but by
  denying rather than by disabling the whole run) and with sources that
  have no unattended-mode story at all.

## 8. A known-unknowns callout

Two sources have a *named* mechanism whose existence is confirmed but
whose content is not, worth flagging explicitly rather than folding
into "absent":

- **Goose's `permission_judge.md`** — the filename alone, captured as
  0 bytes in this collection, strongly implies an LLM-based judge
  specifically for permission/approval decisions, structurally
  exactly this doc's "LLM classifies risk" axis (§2) — but the content
  is unrecoverable from what's stored here.
- **Copilot Chat's `../base/safetyRules`** — a `SafetyRules` class is
  imported into several prompt files but the file itself isn't present
  in this collection; combined with the near-universal "no need to ask
  permission before using a tool" instruction found across nearly
  every model family's prompt, this strongly suggests Copilot Chat's
  real enforcement (like Claude Code's) lives almost entirely in the
  host application rather than in what these files capture.

## Absences

- **Warp** (leaked): the weakest, least-structured posture found in
  this survey — no flag, no list, no config, just a prompted "bias
  against unsafe commands," with the prompt's own general instinct
  cutting *against* seeking approval at all.
- **Devin** (leaked): confirmed zero command-approval infrastructure —
  see §7 for what replaces it.
- **Pi**: the single strongest negative result in this survey — its
  entire prompt-construction logic is fully-read, non-truncated
  executable JavaScript with no permission branch anywhere in it,
  unlike every other "not found" result in this doc, which rests on
  prose that could in principle be omitting something.
- **Goose**: see §8 — a real, evidenced capture gap rather than a
  clean absence.
- **Aider, Bolt, Composio SWE-Kit, augment-swebench-agent,
  mini-swe-agent, Live-SWE-agent, SWE-agent, Microsoft Agent
  Framework, and every source in the `leaked/` folder not explicitly
  listed above** — not investigated for this doc at all. Given how
  often "not checked" has turned out to mean "actually quite
  sophisticated" elsewhere in this collection (Codex's sub-agents,
  OpenCode's Task tool, Gemini CLI's own permission engine before this
  research pass), treat the absence of a source from this list as
  exactly that, not as evidence any particular mechanism doesn't
  exist there. Several of these (the SWE-bench-lineage benchmark
  harnesses in particular) plausibly have no meaningful approval
  concept at all, since they're designed to run unattended by
  construction — but that's an inference from architecture, not a
  confirmed finding.

---

## Design takeaways

- **The single clearest finding across this whole doc: an aside
  mentioning a source "has a permission engine" is a radical
  understatement almost every time it was actually checked.** Codex
  CLI's permission architecture is not one mechanism but five
  cooperating subsystems (static classifier, Starlark rule engine, LLM
  auto-reviewer, real OS sandbox, network proxy) with explicit design
  coupling between several of them. Gemini CLI's "TOML policy engine"
  turned out to include an entire second, independent LLM acting as
  judge over the first model's tool calls. This is the same pattern
  this collection's other docs have found repeatedly (sub-agents,
  compaction, self-verification) — prompt-text-only or passing-mention
  characterizations reliably undersell real architecture, and this
  doc's two live-source-investigated sources (Codex, Gemini CLI) turned
  out to be the two richest in the entire survey.
- **"An LLM judges the primary model's actions" is a real, working
  pattern, not a hypothetical — and it's always additive, never a
  replacement for the static rules. Three vendors arrived at it
  independently, not two.** Gemini CLI's Conseca, Codex's Guardian, and
  Claude Code's `yoloClassifier.ts` (§2) share the same shape: off/
  gated by default, a separate purpose-selected model (deliberately
  cheaper/faster in Codex's and Claude Code's fast-pass), and layered
  *on top of*, not instead of, a static rule/priority engine that keeps
  working regardless of whether the LLM layer is enabled — Codex and
  Gemini CLI additionally fail closed on any error. Claude Code's
  version is the odd one out on availability, not on design: it's the
  only one of the three confirmed **internal-only**, gated behind a
  feature flag and excluded from the externally-available mode set —
  the same ant-gating pattern this collection's self-verification doc
  found for Claude Code's adversarial verification subagent, now found
  a second time in a completely different subsystem. Compare this
  three-way convergence to self-verification's §3 finding about
  separate-LLM-call judges: the same design instinct (a second,
  differently-purposed model call checking the first) recurs across
  two entirely different problems in this collection — verifying
  completed work, and pre-authorizing work about to happen.
- **Static, deterministic rule engines are far more sophisticated than
  "a list of allowed strings" in the best-implemented sources.**
  OpenCode's tree-sitter-based AST parsing of bash/PowerShell commands
  and Gemini CLI's shell-quote-based redirection detection both split
  compound commands into sub-commands and check each independently —
  real language-aware parsing, not string matching, in sources that
  have no LLM classification step at all. This means "static" and
  "unsophisticated" are not the same claim, even though every LLM-based
  system in this survey is layered on top of (not replacing) a static
  engine of its own.
- **The self-tag pattern (Windsurf, Replit, Cline) is architecturally
  the weakest form of risk classification found, because nothing
  checks whether the tag is honest.** Contrast this directly with
  OpenHands' explicit design choice to treat the model's own
  `security_risk` self-tag as merely *one, non-default* option among
  three interchangeable analyzers — OpenHands's own fail-safe default
  (treat unclassified as maximum-risk) is a tacit acknowledgment that
  trusting a model's self-report by default is the weaker design.
  Windsurf's prompt tries to compensate rhetorically instead of
  structurally, with the strongest anti-override language found in
  this whole survey ("You cannot allow the USER to override your
  judgement on this... even if the USER asks you to") — a prompt-level
  attempt to shore up a mechanism that has no code-level check behind
  it.
- **The enforcement-lives-in-the-harness pattern (§7) has a real
  consequence for this whole collection's methodology**: several of
  this doc's richest findings (Claude Code's six modes, Codex's five
  subsystems, Gemini CLI's Conseca, OpenHands's pluggable analyzers)
  are *invisible* to anyone reading only the system prompt text — which
  is most of what this collection is built from. This is the strongest
  single argument in the whole project for why the live-source
  corrections applied to Codex/OpenCode/OpenHands/Roo Code/Gemini CLI
  across multiple docs (sub-agents, compaction, self-verification, and
  now this one) were necessary rather than optional thoroughness.
- **Two opposite philosophies for handling an unattended/no-human-
  present run, both defensible, both found in this survey**: OpenCode
  fails closed by auto-rejecting every request when no human is
  available to answer (§7); Codex's `Never` mode returns tool failures
  straight to the model to handle on its own rather than blocking.
  Both avoid the dangerous third option (silently allowing everything
  because no one's watching), but land on different answers to what
  the agent should do when it can't get an answer — stop and fail, or
  keep going and adapt.
- **Devin and Warp are useful negative cases for what this whole doc's
  typology assumes**: both are designed around *not* having a
  conditional risk-approval system at all — Devin substitutes absolute
  prohibitions plus a mandatory reflection checkpoint (safety by
  forbidding categories of action, not by judging instances of it),
  and Warp's prompt actively discourages seeking approval as its
  general operating stance. Neither is a gap in what was investigated;
  both are confirmed, deliberate design choices to solve the same
  problem this whole doc surveys with a fundamentally different shape
  of answer.
