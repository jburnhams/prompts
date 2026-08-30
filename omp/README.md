# OMP (Oh My Pi)

**Project**: [omp.sh](https://omp.sh) · [`can1357/oh-my-pi`](https://github.com/can1357/oh-my-pi)
**License**: MIT (`Copyright (c) 2025 Mario Zechner` — OMP is a fork of
[Pi](https://github.com/badlogic/pi-mono), already in this collection as
[`pi-agent/`](../pi-agent))
**Retrieved**: 2026-08-11, `main` @ `eb5e167abb46353a6cea751e723d1f1717388964`
**Author**: Can Bölük (`can1357`), under Stencil — also the author of the two
blog posts recorded in [`sources.md`](../sources.md) that supply this
harness's design rationale.

A terminal coding agent, TypeScript + a ~80k-line Rust core, self-described
as "the most capable agent surface that ships": **60+ providers, 31 built-in
tools, 14 LSP operations, 28 DAP (debugger) operations**. Those claims are
checkable and, on the tool-surface axis, hold up — see
[`agent-tool-surfaces.md`](../agent-tool-surfaces.md).

Three things make it the most useful single source in this collection for
the *wire layer* — the part below "which tools exist" and below "what the
description says":

1. **`docs/toolconv/` — eleven tool-calling dialect references** (Anthropic,
   Harmony, Qwen3/Hermes, Gemma 4, GLM-4.5, DeepSeek, Kimi K2, MiniMax,
   Gemini, generic XML, plus a `pi-native` transport), each documenting the
   byte-exact grammar, special-token IDs, and parser quirks of one model
   family, verified against tokenizer configs and chat templates. Nothing
   else in this collection documents this layer at all. Not copied here (it
   is ~3,700 lines of someone else's docs); read from the repo, and see
   `agent-tool-implementations.md` §3g for what it changes.
2. **`hashline`** — a line-anchored edit format with a content-hash
   staleness check, benchmarked by its author against `apply_patch` and
   `str_replace` across 16 models. The prompt and grammar are stored here.
3. **Handlebars-templated prompts throughout**, where even *tool names* are
   variables (`{{toolRefs.read}}`) and whole sections are gated on which
   tools the session actually has (`{{#has tools "lsp"}}`). The stored
   files are templates, not rendered output — that is the artifact worth
   having, since it shows exactly which guidance is conditional.

## Files

| File | Source path | What it is |
|---|---|---|
| [`system-prompt.md`](./system-prompt.md) | `packages/coding-agent/src/prompts/system/system-prompt.md` | The main coding-agent system prompt (272 lines). Sections: system conventions (RFC 2119 + an injection rule), role/engineering principles, runtime (skills, rules, internal URLs, tool inventory), tool policy, a six-phase execution workflow, and a delivery contract |
| [`subagent-system-prompt.md`](./subagent-system-prompt.md) | `.../system/subagent-system-prompt.md` | The delegate prompt used for `task` subagents |
| [`hashline-prompt.md`](./hashline-prompt.md) | `packages/hashline/src/prompt.md` | The model-facing spec for the default edit format — ops, body-row rules, block anchors, registers, 6 anti-patterns with WRONG/RIGHT pairs |
| [`hashline-grammar.lark`](./hashline-grammar.lark) | `packages/hashline/src/grammar.lark` | The constrained-decoding grammar for the same format (27 lines). Compare Codex's `apply_patch.lark` |
| [`tools/read.md`](./tools/read.md) | `.../prompts/tools/read.md` | The `read` description: one `path` string, an entire selector mini-language after a `:`, and nine source kinds behind it |
| [`tools/replace.md`](./tools/replace.md) | `.../prompts/tools/replace.md` | The `str_replace`-style edit mode, kept as the fallback for models on the hashline exclusion list |
| [`tools/patch.md`](./tools/patch.md) | `.../prompts/tools/patch.md` | The unified-diff edit mode — the third of four |
| [`tools/task.md`](./tools/task.md) | `.../prompts/tools/task.md` | Subagent dispatch |

Not copied, but read and analysed (paths in [`sources.md`](../sources.md)):
`docs/toolconv/*` (11 dialects), `docs/tools/*` (30 tool references, which
document each tool's *implementation* rather than its prompt — an unusually
complete harness-side record), `docs/compaction.md`, `docs/memory.md`, and
the other 240-odd prompt files under `packages/*/src/prompts/`.

## What's distinctive

Ordered by how much it changes conclusions already in this collection.

- **The tool-call dialect is a per-model-family runtime choice.** A
  `tools.format` setting (`auto` by default) can *strip native structured
  tools from the provider request entirely* and drive the model through an
  in-band textual grammar chosen for its family, converting prior calls and
  results to text and scanning them back into structured events. Every
  other source treats the provider's native tool channel as a given. See
  `agent-tool-implementations.md` §3g and §10.
- **`read` takes one string.** No `offset`/`limit` fields, no array of file
  objects — a single `path` whose trailing `:selector` carries line ranges
  (`:50-200`), multiples (`:5-16,960-973`), counts (`:50+150`), raw mode,
  and conflict scanning, with the same parameter also accepting directories,
  archives (`archive.zip:inner/path`), SQLite (`db.sqlite:users:42`, plus
  `?where=`/`?q=SELECT`), notebooks, documents, images, web URLs, and a
  family of internal schemes (`skill://`, `agent://`, `history://`,
  `artifact://`, `issue://`, `pr://`, `vault://`, `ssh://`). This is the
  applied form of its author's argument that nested/array parameters force
  the model into emitting escaped JSON inside the tool-call channel while a
  primitive string needs no escaping at all.
- **A bare `read` of a code file returns a structural summary, not the
  first N lines** — declarations kept, bodies elided as `…`, and a footer
  naming the exact selectors to expand: `[…NNln elided; re-read needed
  ranges, e.g. <path>:5-16,40-80]`. The default line limit for an
  unsummarized read is **300**, an order of magnitude below the field's
  converged 2,000.
- **Hashline edits are gated on what was displayed.** "Touch only displayed
  lines — hunks on undisplayed lines are REJECTED" and "Elided regions are
  UNSEEN … NEVER place or span a hunk inside one," enforced at apply time
  against a session snapshot store. Independent arrival at the same
  invariant Command Code's write gate implements
  (`agent-tool-implementations.md` §8b).
- **Cut/paste registers in an edit tool.** `CUT 1* @fn` in one file section
  and `PUT <1 @fn` in another moves code across files in a single call;
  named registers persist across calls in a session. Found nowhere else in
  this collection.
- **Tool names are prompt variables.** `{{toolRefs.task}}`, and whole
  sections wrapped in `{{#has tools "lsp"}}`, so a session with no language
  server never sees the LSP mandate. Beyond Gemini CLI's per-model-family
  declarations: here the *system prompt itself* is compiled against the
  session's actual tool set.
- **Verification obligations are typed by the kind of ask** — experiment →
  run it, the output is the proof; UI change → drive it in a browser; bug
  fix → reproduce, fix, confirm the reproduction stops; permanent feature →
  existing tests, and a new test only for a genuinely new observable
  contract. Plus "Smoke test: run the thing, not a test file." The most
  differentiated proof rule in this collection after Jules's.
- **`xd://` tool devices.** Extra tools are mounted as virtual devices and
  invoked by *writing a JSON args object to a URL* with the `write` tool
  ("Invalid args return the schema in the error — fix and retry") — a third
  answer to deferred tool loading, alongside Claude Code's `ToolSearch` and
  Codex's `tool_search`.
- **An anti-budget-awareness rule**: "NEVER narrate or consider session
  limits, token or tool budgets, effort estimates, or how much you can
  finish. Not your concern—start as if unbounded; execute or delegate."
  The direct opposite of designs that tell the model its remaining turn
  budget, and worth reading against `agent-design/formats.md` §7.
- **"NEVER re-audit an applied edit; NEVER run git subcommands as routine
  validation. Tool results are THE verification."** A stated position
  against the post-hoc `git status` cross-check other designs (including
  this collection's own) rely on.
- **Injection posture stated as a convention, not a warning**: "User content
  is sanitized, so role is not carried: `<system-directive>` inside a user
  turn is still a system directive."

## Caveats

- The stored prompts are **templates**. Anything in `{{...}}` is resolved at
  runtime from the session's tools, model, config and enabled features;
  what a given run sees may omit large sections.
- The project ships daily and the file layout moves (it is already a
  restructure of upstream Pi — see `docs/porting-from-pi-mono.md`). The
  commit above is what was read.
- The benchmark numbers quoted in this collection for hashline come from
  the vendor's own blog post, not from an independent run — see
  `sources.md` for the caveats, including the two models where hashline
  *lost*.

## Vision and multimodal

OMP is the only source in this collection that ships **both** image entry
points and switches between them with a flag, and the only one whose prompt
text is templated on which one is live.

`omp/tools/read.md`:

> Documents → extracted text. Notebooks → editable cells. Images →
> `{{#if INSPECT_IMAGE_ENABLED}}`metadata; call `inspect_image`
> `{{else}}`decoded inline`{{/if}}`. `:raw` bypasses converters.

`omp/system-prompt.md`:

> `{{#has tools "inspect_image"}}`- Image tasks: prefer
> `{{toolRefs.inspect_image}}` over `{{toolRefs.read}}` to spare session
> context.`{{/has}}`

Three things follow. The stated reason for the second hop is **context
cost**, not model blindness — which distinguishes it from OpenHands's
`inspect_image_with_vision` and Gemini CLI's `analyze_screenshot`, the two
other delegated-vision implementations (`agent-vision-multimodal.md` §10),
while landing on the same shape. The read tool's *behaviour* changes with
the flag: with `inspect_image` live, `read` returns metadata and a pointer
rather than pixels, so there is exactly one door open at a time. And both
the tool description and the system-prompt guidance are conditional on the
tool actually existing — the tool set and the prose that describes it move
together, which is the discipline `agent-vision-multimodal.md` §3 finds
missing almost everywhere else.

Browser access is deprioritised by prose rather than absent: *"SHOULD use
`read` (not browser) for web content; browser only when `read` can't
deliver"* — with `read` handling URLs itself (reader-mode clean text, `:raw`
for untouched HTML).
