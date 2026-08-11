# Tool implementations: the layer below "which tools exist"

[`agent-tool-surfaces.md`](./agent-tool-surfaces.md) catalogues *what
capabilities* each scaffold hands the model — which shell, whether there's a
browser, how search is tiered. This doc is the layer underneath: for the
boring, universal primitives — **read, list, search, edit, write, run** —
*how are they actually built*, and what does the field's collective
implementation say about the four questions that decide a tool surface:

1. **Granularity** — many narrow tools, or few broad ones?
2. **Parameters** — typed fields, CLI-style args, or freeform text?
3. **Mimicry** — should a tool look like `cat`/`rg`/`sed`/`patch`, or like
   an API?
4. **Formats** — what does the model actually receive back: JSON, XML,
   plain text?

Unlike the rest of this collection, this doc is grounded primarily in
**source code**, not prompt text — read at specific commits, all recorded in
[`sources.md`](./sources.md). Where a claim comes from a leaked source with
the usual authenticity caveats (Claude Code), it's marked. Where it comes
from this session's own live tool schemas, it's marked too.

Sources read as code: Claude Code (leaked full source), Codex CLI, Gemini
CLI, OpenCode, Crush, Zed, Goose, Cline (SDK), OpenHands (agent SDK), plus
already-stored tool-JSON captures for Manus, Windsurf, Cursor and Grok
Build, plus Anthropic's own published tool-design guidance and the MCP tool
specification.

A later pass added **OMP** (Oh My Pi) to the code-read list — see
[`omp/`](./omp) — which is the only source here that documents the *wire
layer* underneath everything above: eleven per-model-family tool-call
dialect references, a benchmarked alternative to `cat -n` + exact-match
editing, and a harness that can remove native structured tool calls
altogether. It is used in §3g, §4a and §10, alongside its author's two
write-ups (recorded in [`sources.md`](./sources.md)), which supply the
reasoning and the benchmark behind those choices.

The same pass added a fourth class of source, marked wherever it is used: a
**vendor engineering write-up** about a closed harness — Command Code's
["The Read Tool"](https://commandcode.ai/docs/harness-engineering/read-tool)
(Ahmad Awais, 9 Aug 2026), a capability-by-capability teardown of one tool
across ten harnesses. It is the only account here written by a team that
rebuilt a read tool and then said what broke, which makes it the richest
single source on `read` in this collection and also the least neutral: it is
marketing for the product it benchmarks, and its own competitor column is
partly wrong where this collection has read the code (§6b, §8b). The
findings below separate the two — the failure modes it describes are
reproducible reasoning about a tool anyone can build; the scorecard is
treated as a claim, not a finding.

---

## 1. A tool has three consumers, and the good implementations give each its own channel

The single most consistent finding of this pass, and the one that reframes
every other question: in every mature implementation, a "tool" is not one
interface. It is three, bundled:

- **The model channel** — a name, a description, an input schema, and a
  *text* result.
- **The harness channel** — machine-readable facts about the call that the
  model never sees: is it read-only, is it safe to run in parallel, does it
  need permission, what path does it touch, how big may its result get.
- **The human channel** — a rendering: a spinner label, a diff, a collapsed
  result row, a rejection message.

Claude Code's `ToolDef` contract (leaked `src/Tool.ts`) is the most explicit
version. Sorting its ~40 members by audience:

| Channel | Members |
|---|---|
| Model | `name`, `aliases`, `description()`, `prompt()`, `inputSchema`, `inputJSONSchema`, `outputSchema`, `strict`, `searchHint`, `shouldDefer`/`alwaysLoad`, `mapToolResultToToolResultBlockParam()` |
| Harness | `isReadOnly()`, `isConcurrencySafe()`, `isDestructive()`, `isEnabled()`, `checkPermissions()`, `validateInput()`, `getPath()`, `preparePermissionMatcher()`, `toAutoClassifierInput()`, `maxResultSizeChars`, `interruptBehavior()`, `isSearchOrReadCommand()`, `isOpenWorld()`, `backfillObservableInput()` |
| Human | `userFacingName()`, `renderToolUseMessage()`, `renderToolResultMessage()`, `renderToolUseProgressMessage()`, `renderToolUseRejectedMessage()`, `renderToolUseErrorMessage()`, `renderGroupedToolUse()`, `getActivityDescription()`, `getToolUseSummary()`, `isResultTruncated()`, `extractSearchText()` |

Everyone else lands on the same split with less ceremony:

- **OpenCode** returns `{ output, metadata }` from every tool: `output` is
  the model-facing string; `metadata.display` is a typed object for the UI
  (`{type: "file", path, text, lineStart, lineEnd, totalLines, truncated}`).
- **Gemini CLI**'s `ToolResult` has `llmContent` ("content meant to be
  included in LLM history... the factual outcome") and `returnDisplay`
  ("markdown string for user display") as two separate required fields.
- **Zed**'s `AgentTool` trait declares `type Output: Serialize + Into<LanguageModelToolResultContent>`
  — a typed output that knows how to flatten itself for the model — and
  `fn run(...) -> Result<Self::Output, Self::Output>`, with a comment
  spelling out why success and failure share a type: "tool errors are sent
  back to the model as tool results... error output must be structured and
  readable by the agent — not an arbitrary `anyhow::Error`."
- **OpenHands** pairs a Pydantic `Action` (input) with a Pydantic
  `Observation` (output) per tool, and the `Observation` carries a
  `visualize` property producing Rich text for the terminal.
- **MCP** standardises exactly this split in the wire protocol:
  `content[]` (unstructured, model-facing) alongside `structuredContent`
  (JSON, schema-validated), with the spec advising servers that return
  structured content to *also* serialise it into a text block.

**Why it matters for design**: almost every disagreement below ("should the
result be JSON?", "should there be one tool or five?") gets easier once you
stop trying to serve all three consumers with one artifact. The model wants
prose it can pattern-match; the UI wants fields; the permission engine wants
predicates. Claude Code's `FileReadTool` is the clearest demonstration: it
declares a full discriminated-union **output schema** (`text` | `image` |
`notebook` | `pdf` | `parts` | `file_unchanged`, each with typed fields),
and then `mapToolResultToToolResultBlockParam` converts that into what the
model sees — which for the `text` case is just `cat -n`-numbered file
content with no JSON envelope at all.

---

## 2. Granularity: how many tools?

### 2a. The actual spread

Counted from source (`sources.md` for paths), for the *coding* surface only
— excluding MCP/plugin/dynamic tools:

| Source | Tools | Shape |
|---|---|---|
| Manus (leaked JSON) | 29 | one tool per verb (`shell_exec`, `shell_view`, `shell_wait`, `shell_write_to_process`, `shell_kill_process`; 11 `browser_*`) |
| Crush | 30 | incl. **8 separate `lsp_*` tools** |
| Claude Code (leaked source) | 56 tool dirs; 15–16 exposed at once | large registry, heavily gated per mode/deployment |
| Zed | 23 | separate `copy_path`, `move_path`, `delete_path`, `create_directory`, `rename`, `go_to_definition`, `find_references`… |
| Gemini CLI | ~20 | one manifest per model family |
| OpenCode | 17 | `read` also lists directories; **one** `lsp` tool with a 9-value `operation` enum |
| OpenHands (SDK) | ~11 packages | `file_editor` is one tool with a 5-value `command` enum |
| Cline (SDK) | 9 | semantic, plural names: `read_files`, `search_codebase`, `run_commands` |
| Codex CLI | ~6 core | `exec_command` + `write_stdin` + `shell_command` + `apply_patch` + `update_plan` (+ tool search, agents) |
| Goose (`developer`) | **5** | `write`, `edit`, `shell`, `tree`, `read_image` |

### 2b. The same capability at three granularities

Three worked comparisons, all from code read this pass:

**Language-server access.**
Crush ships eight tools (`lsp_definition`, `lsp_references`, `lsp_symbols`,
`lsp_rename`, `lsp_diagnostics`, `lsp_call_hierarchy`, `lsp_replace_symbol`,
`lsp_restart`). OpenCode ships **one** `lsp` tool whose description
enumerates nine operations behind an `operation` parameter, with a shared
`filePath`/`line`/`character` triple. Zed ships five separate ones
(`go_to_definition`, `find_references`, `get_code_actions`,
`apply_code_action`, `rename`). Identical capability, 1 vs 5 vs 8 tools.

**Interactive shell sessions.**
Manus: five tools (`shell_exec`/`view`/`wait`/`write_to_process`/`kill_process`).
Claude Code: three (`Bash` with `run_in_background`, `BashOutput`, `KillBash`).
Codex: **two** (`exec_command` returns either output *or* a `session_id`;
`write_stdin` polls or writes to that session — an empty `chars` string is
the documented way to poll without writing). Gemini CLI: **one** tool plus
an `is_background` boolean. Grok Build (leaked) generalises further —
one poll/kill/wait trio shared by background commands *and* sub-agents.

**File editing.**
OpenHands: one `file_editor` with `command: view|create|str_replace|insert|undo_edit`
(the Anthropic reference `text_editor` shape). Claude Code: `Read` + `Edit` +
`MultiEdit` + `Write` + `NotebookEdit` as separate tools. Goose: `write` +
`edit`, having dropped the command-enum shape. Cline: **one** `editor` tool
that switches behaviour by *which optional fields are present* — no
`old_text` means create, `insert_line` present means insert, otherwise
replace.

### 2c. The two extremes are both mature, and both deliberate

The strongest signal in this section is that the two ends of the axis are
occupied by *serious, actively developed* products that have each written
down their reasoning:

- **Goose** has no read tool, no grep tool, no glob tool. Its `developer`
  extension instructions tell the model: "prefer the flow of using tree to
  understand the codebase structure and file sizes. When you need to search,
  prefer rg which correctly respects gitignored content. Then use cat or sed
  to gather the context you need, always reading before editing." Reading
  and searching are *shell commands*. Codex CLI is the same shape: no
  `read`/`grep`/`glob` tools exist in its registry at all — `exec_command`
  plus `apply_patch` is the entire file surface.
- **Claude Code** goes the other way, explicitly: its `Grep` description
  says "ALWAYS use Grep for search tasks. **NEVER invoke `grep` or `rg` as a
  Bash command.** The Grep tool has been optimized for correct permissions
  and access." Its `Read` description likewise tells the model to use it for
  every file, including screenshots in temp directories.

Neither is a mistake. The trade is legible once you look at what each side
*has to build*:

| | Dedicated tools (Claude Code, Zed, Crush) | Shell-only (Goose, Codex) |
|---|---|---|
| Permissions | Static: `isReadOnly(input)` is a pure function of the schema | Dynamic: you must parse and classify arbitrary command strings |
| Result shaping | You own truncation, line numbers, pagination footers | You get whatever the command printed |
| Caching/state | Can dedupe (see `file_unchanged`, §8) and enforce read-before-edit | Can't tell a read from a write without parsing |
| UI | Rich per-tool rendering (diffs, collapsed reads) | One terminal blob |
| Model familiarity | Must be taught in the description | Already known: `rg`, `sed`, `cat` are in the weights |
| Composability | One call per operation | Pipes, `&&`, loops — many operations per call |
| Cost of the surface | N tool schemas in every request | 1 tool schema |

And the cost of *not* having dedicated tools shows up as code somewhere
else. Measured from the leaked Claude Code tree (directory sizes, so a lower
bound given the known stubs):

```
BashTool/          636 KB   ← incl. bashSecurity.ts 102 KB,
PowerShellTool/    484 KB      readOnlyValidation.ts 68 KB,
AgentTool/         580 KB      pathValidation.ts 43 KB,
FileEditTool/      100 KB      sedValidation.ts + sedEditParser.ts 30 KB
FileReadTool/       80 KB
FileWriteTool/      68 KB
GrepTool/           52 KB
GlobTool/           28 KB   (total src/tools ≈ 3.3 MB)
```

The shell tools are ~34% of the entire tool tree, and most of that is
classification: deciding whether an arbitrary command string is read-only,
whether a `sed` invocation is secretly an edit, whether a path escapes the
workspace. **That is the bill for breadth.** Goose and Codex don't pay it
in tool code because they push it into a sandbox and an approval prompt
instead; Bolt.new pays it as a 39-command allowlist.

### 2d. Anthropic's own guidance points the other way — for a different class of tool

*Writing effective tools for agents* argues for **consolidation**: "build a
few thoughtful tools targeting specific high-impact workflows," a single
`schedule_event` rather than `list_users` + `list_events` + `create_event`,
a `get_customer_context` that returns the joined view. Its examples are all
*domain/API* tools.

That is not in tension with what the coding harnesses do, once you separate
two categories:

- **Workflow tools** wrap a business process. The model should not be
  orchestrating three calls to accomplish one intent, and each round trip
  costs a full model turn. Consolidate.
- **Primitive tools** are the agent's substrate — the things it composes
  *itself*, in ways you can't enumerate in advance. Here the pressure is the
  opposite: keep each one predictable, cheap to describe, and statically
  classifiable.

The practical rule that falls out, and that matches every source read here:
**split a primitive when the split changes the harness's answer, not when it
changes the model's phrasing.** Concretely — split when the two operations
differ in permission class (read vs write), in destructiveness, in
concurrency safety, or in result shape. Don't split when the only difference
is which fields are populated. That rule predicts most of the field:
Claude Code splits `Read`/`Edit`/`Write` (different permission classes) but
keeps 12 ripgrep flags inside one `Grep`; OpenCode keeps 9 LSP operations in
one tool (all read-only, all same result shape) while keeping `read`/`write`
apart; Zed splits `delete_path` from `move_path` (different destructiveness)
but has one `grep`.

It also predicts the one case everyone gets "wrong" on purpose: the shell.
`Bash` is un-classifiable by construction, which is exactly why it's the
tool with a six-figure line count of classifiers behind it.

### 2e. Batching is a third axis, orthogonal to the first two

"How many tools" and "how broad is each tool" leave out **how many
targets one call may name**, and the field splits on it:

- **Batch by parallel tool calls.** Claude Code and OpenCode both keep
  single-target tools and push batching into the model's ability to emit
  several tool calls in one assistant turn — OpenCode's `read.txt` says it
  outright: "Call this tool in parallel when you know there are multiple
  files you want to read." Claude Code's `Glob` description does the same
  for searches ("It is always better to speculatively perform multiple
  searches as a batch").
- **Batch in the schema.** Cline's SDK pluralises *everything*:
  `read_files: {files: [{path, start_line, end_line}]}`,
  `run_commands: {commands: [...]}`, `search_codebase: {queries: [...]}`,
  `fetch_web_content: {requests: [...]}`. Gemini CLI has a separate
  `read_many_files` (glob-driven, no per-file ranges) alongside its
  single-file `read_file`. Claude Code's `MultiEdit` is the same idea for
  one file's worth of edits.

The two are not equivalent. Parallel calls save round trips but not
per-call overhead, and they depend on the model reliably choosing to
parallelise — which is exactly what weaker models don't do. Schema-level
batching forces the win but complicates the result: it needs per-target
blocks, per-target errors that don't fail the whole call, and a size
budget spanning the batch rather than per target. Cline's schema text also
records the failure mode it introduces, in the description itself:
`start_line`/`end_line` "must be on the same object as the path they
apply to, **never in a separate array element**" — i.e. models flatten the
structure when a batch entry has more than one field.

Worth noting what the range parameters look like, since this is where
"just use `sed -n '10,50p'`" comes up. Line ranges are the one place the
shell-only harnesses genuinely do lean on `sed` — Goose's extension
instructions say "use cat or **sed** to gather the context you need" —
but no tool-based harness borrows `sed`'s `10,50p` notation. They split
instead between `offset`+`limit` (Claude Code, OpenCode, Crush) and
`start_line`+`end_line` (Gemini CLI, Cline, Zed; OpenHands uses
`view_range: [start, end]`). The pairs are not equally good in context:
every line number a model has usually came from `cat -n` output, a grep
hit, or a diff hunk, all of which give *positions*, so a start/end pair
is copied while an offset/limit pair is computed — and computed is where
`"3"`-as-a-string and off-by-one errors enter. Offset/limit's one real
advantage is that it matches the continuation footer ("pass `offset: 2001`
to continue"), which start/end can state just as easily.

---

## 3. Parameter design

### 3a. The five styles in use

| Style | Example | Where |
|---|---|---|
| Named typed fields | `{file_path, offset, limit}` | almost everyone, for file tools |
| **CLI-flag-named** fields | `{pattern, glob, type, "-A", "-B", "-C", "-n", "-i", head_limit, offset, multiline}` | **Claude Code `Grep`** |
| One opaque command string | `{command: "..."}` / `{cmd: "..."}` | every shell tool |
| argv array (no shell parsing) | `{command: "python3", args: ["-c", "..."]}` | Cline's `StructuredCommandInput` (accepted alongside the string form) |
| Freeform / grammar-constrained body | `apply_patch` patch text, no JSON wrapper | **Codex** (Lark grammar), OpenCode, Cline |

Claude Code's `Grep` is the interesting hybrid, and it answers the "CLI args
vs params" question directly rather than in the abstract. It does **not**
take an `rg` argument string. It takes *named JSON fields that are literally
called `-A`, `-B`, `-C`, `-n`, `-i`*, each described in terms of the flag it
maps to ("Number of lines to show after each match (rg -A)"), plus
higher-level fields described by their shell equivalent (`head_limit`:
'equivalent to "| head -N"'; `offset`: 'equivalent to "| tail -n +N | head -N"').
So the *knowledge* the model already has about ripgrep is reused, while the
*surface* stays a validated JSON object the harness can inspect. Gemini CLI
reaches the same destination from the other side: semantic names
(`include_pattern`, `max_matches_per_file`, `total_max_matches`) with a
second declaration variant (`grep_search_ripgrep`) carrying ripgrep-only
extras (`fixed_strings`, `context`, `after`, `before`, `no_ignore`) when the
ripgrep backend is available.

**Nobody takes a raw flag string.** The reason is visible in the harness
channel from §1: `isReadOnly(input)`, `getPath(input)`, and permission-rule
matching all need to read the input *without executing it*. A flag string
puts you back in Bash-classifier territory for no benefit.

### 3b. Freeform bodies are the exception, and they're rising

The one place the field genuinely does hand the model an unparsed blob is
**patch application**, and Codex is the most committed: `apply_patch` is
declared as `ToolSpec::Freeform` with `format: {type: "grammar", syntax: "lark", definition: <grammar>}`
and a description that reads, in full, "The `apply_patch` tool can be used
to edit files. This is a FREEFORM tool, so **do not wrap the patch in JSON**."
The grammar itself is 15 lines and encodes the whole V4A envelope
(`*** Begin Patch` / `*** Add File:` / `*** Update File:` / `*** Move to:` /
`@@` / `*** End Patch`).

Why bother? Two reasons, both mechanical:

- **JSON escaping is hostile to code.** A patch body inside a JSON string
  doubles every backslash and turns every newline into `\n`; models make
  more mistakes writing it and it costs more tokens.
- **Grammar-constrained decoding** can make malformed patches *impossible*
  rather than merely detected, when the provider supports it.

Cline reaches the same conclusion empirically and encodes it as routing:
`DEFAULT_MODEL_TOOL_ROUTING_RULES` enables `apply_patch` and **disables** the
`editor` tool when the provider is `openai-native` or the model id contains
`codex`/`gpt`, and does the reverse otherwise. That is the field's clearest
statement that edit-format choice is a *model-family* decision, not a
universal one (see also `coding-agent-approaches.md` §5).

### 3c. Redundant, model-authored parameters that exist to steer, not to compute

A recurring trick worth naming: parameters whose value the tool barely uses,
included because *writing them changes the model's behaviour* or gives the
human something to read.

- **Gemini CLI's `replace`** requires an `instruction` field alongside
  `old_string`/`new_string`: "A clear, semantic instruction for the code
  change, acting as a high-quality prompt for an expert LLM assistant. It
  must be self-contained and explain the goal of the change." The mechanical
  edit doesn't need it; a fallback LLM edit-repair path does, and it makes
  the intent auditable.
- **Claude Code's `Bash`** takes a `description` ("5-10 words"). **Crush**
  makes the same field mandatory and shouts about it: "CRITICAL: The
  `description` parameter is REQUIRED for all bash tool calls."
- **Codex's `justification`** (only meaningful with
  `sandbox_permissions: "require_escalated"`) is the user-facing approval
  question — the model writes the prompt that will be shown to the human.
- **`Task`/`Agent` tools** universally require a 3–5-word `description`
  distinct from the actual `prompt`.

### 3d. Permissions as parameters

Codex is alone in the sources read here in putting escalation *inside the
tool schema*: `exec_command` accepts `sandbox_permissions`
(`use_default` | `with_additional_permissions` | `require_escalated`),
`additional_permissions` (a nested `{network: {enabled}, file_system: {read: [], write: []}}`
profile), `justification`, and `prefix_rule` (`["git", "pull"]` — a reusable
approval prefix). There is also a separate `request_permissions` tool for
requesting a profile out-of-band. Everyone else keeps permissions entirely
in the harness channel and never tells the model the rules — the
cross-cutting finding of `agent-permissions-approval.md`.

### 3e. Advertise strict, accept sloppy

The most transferable implementation detail of this pass. Every mature
harness validates *more loosely than it advertises*, silently normalising
what models actually emit:

- **Cline** advertises `read_files: {files: [{path, start_line, end_line}]}`
  and then parses input against a **13-branch union** that accepts a bare
  string, an array of strings, `{file_paths: [...]}`, `{paths: ...}`,
  `{files: "one/path"}`, and per-entry aliases `file_path`/`filePath` — each
  normalised to the canonical shape. Line numbers use `z.coerce.number()`
  with the comment "Models sometimes emit line numbers as strings; coerce so
  a `"3"` does not reject the whole tool call. **The advertised JSON Schema
  is unaffected.**" `run_commands`, `search_codebase` and `apply_patch` have
  the same treatment (`apply_patch` accepts a bare patch string *or*
  `{input: "..."}`).
- **Claude Code** wraps numeric and boolean fields in `semanticNumber(...)`/
  `semanticBoolean(...)` helpers throughout its schemas — the same
  coercion idea, applied per-field.
- **Zed** clamps rather than rejects: `resolve_line_range` forces
  `start >= 1` with the comment "the model occasionally passes `0` despite
  instructions to be 1-indexed", and forces `end >= start` "so callers
  always read at least one line even when the model passes `end < start`."
- **OpenCode** documents the opposite migration in a code comment: it
  *removed* `z.coerce` from `read`'s `offset`/`limit` because "the runtime
  coercion was useful when the tool was called from a shell but serves no
  purpose in the LLM tool-call path (the model emits typed JSON)" — a
  reminder that this is an empirical question per model, not a law.

The general principle: **a rejected tool call costs a full round trip and
teaches the model nothing; a normalised one costs nothing.** Reject only
what you cannot disambiguate.

### 3f. Tolerance has a floor, and it is arithmetic

"Accept sloppy" is not "accept anything," and Command Code's write-up
supplies the sharpest statement of where the line falls. Its repair layer
takes ten aliases for `file_path` (`filePath`, `absolutePath`,
`target_file`, …) and coerces numeric strings — but coerces them **via
`Number()`, never `parseInt`**, so `"2abc"` is rejected rather than
silently read as `2`, and fractional offsets are rejected rather than
floored. The reasoning is one line and it generalises past this tool:

> a silently wrong window is worse than an error.

That is the missing half of §3e. Alias repair is information-preserving —
`filePath` and `file_path` mean the same thing, and the transform is
reversible. `parseInt("2abc")` is not: it invents a value the caller never
supplied, and the resulting read succeeds, so nothing downstream ever
learns it was wrong. The test to apply per-field is whether a repair can
produce a *plausible wrong answer* rather than an obvious failure; where it
can, reject. Note that the harnesses using off-the-shelf coercion inherit
the opposite behaviour by default: Zod's `z.coerce.number()` (Cline's
choice, §3e) is `Number()`-based and so rejects `"2abc"` too, but it
happily accepts `1.5` for a line number, which then flows into a slice.
Clamping and coercion each need this test applied field by field — Zed
clamping `start >= 1` is safe because 0 has exactly one plausible intent,
whereas rounding 1.5 does not.

### 3g. Below the schema: the tool-call channel is text, and its shape is a choice

*(The per-family detail behind this section has its own doc:
[`agent-tool-call-dialects.md`](./agent-tool-call-dialects.md) — the five
delimiter families, argument encodings compared, result correlation, and
what it costs to drive a model with no function-calling support in-band.
This section is the argument; that doc is the reference.)*

Everything above §3f assumes the provider's native tool channel is a given
and the only question is what to put in it. Two sources added in a later
pass — Can Bölük's ["The Minutiae of
Tool-calling"](https://blog.can.ac/2026/08/03/the-minutiae-of-tool-calling/)
and the harness he builds, [OMP](./omp) — treat the channel itself as a
design variable, which reframes several conclusions in this section.

**The mechanism.** A tool call is not a decision; it is tokens. The tools
array never reaches the model as structured data — each provider's template
renders it into the prompt as text. In OpenAI's Harmony format the tools
arrive as a TypeScript-ish namespace in a *developer* message:

```
## functions
namespace functions {
// Compare one digit guess against the secret door keypad digit
// at a 1-indexed position. Returns -1 too low, 0 exact, +1 too high.
type probe = (_: {
// keypad position, 1 through 5
position: number,
// digit guess, 0 through 9
digit: number,
}) => any;
} // namespace functions
```

and a "call" is the model emitting the family's grammar — for the
Anthropic-style dialect, `<invoke name="…"><parameter name="…">value
</parameter></invoke>`, with parallel calls being additional `<invoke>`
blocks. Hence: "Your schema is documentation; validation happens in your
code" — the `minimum`/`maximum`/`description` fields you write may or may
not be rendered, and may or may not be enforced by the inference stack.
This is the mechanical explanation for why §3e's advertise-strict/
accept-tolerant pattern is universal, and it is a stronger argument than
"models are sloppy."

**The consequence that changes parameter design.** Because the closing
delimiter is a special token, a *primitive* parameter body needs no
escaping — the model emits the raw value and stops. A complex value does
not have that property:

> if it's a complex object or an array? Well, it now has to emit a valid
> JSON escaped value, which needs to be parsed back, or a tool calling
> error happens!

OMP's XML dialect implements exactly this split, using the tool's schema to
decide: a schema-declared string renders verbatim with whitespace
preserved; a number, boolean, `null`, array or object renders as JSON and
is parsed back through a "repair-capable JSON parser," falling back to
treating the body as a string when repair fails. So an array-of-objects
parameter is not merely more tokens — it moves that parameter from a
delimiter-matched channel into a nested one that can fail to parse, on
every call.

**The experiment.** Five interfaces to the same toy task (guess a 5-digit
code in 24 turns, given a per-digit comparison oracle): (A) one comparison
per call; (B) the same batched into an array of objects; (C) "clever"
integer packing (`27` = position 2, digit 7); (D) a flat `check(code)`
returning a sign per position; (E) **no tools at all** — the model replies
`🔍2=7` to probe and `🔑01756` to submit, and the harness scans it out of
the text. E wins on both win-rate and cost; on a frontier model it ties A–D
on win-rate while spending 2–3× fewer tokens, and on a weak model it is the
only interface that works well. B and C are the losers, for the reason
above: they are the two that force JSON into the parameter body. The stated
rule of thumb:

> reliability degrades with nesting × heterogeneity × cleverness, and you
> NEED the harness to handle the common failure modes of the dialect.

**The honest limits**, stated by the author rather than extracted from him:
post-training genuinely does push probability mass toward the native tool
channel, so this is not an argument for shipping emoji — "the moment you
have 10 tools instead of 2, native tool-calls win on ergonomics alone and I
use it like everyone else." But RL teaches *the shapes RL practiced*: "flat
args, boring schemas." A clever encoding is off-distribution for the
tool-use post-training in the same way it was for the base model, and the
tail never reaches zero — "reliability is rate × exposure, and real agents
run thousands of turns, not 24," so a per-turn failure rate too small to
see in a 24-turn demo is a certainty across a real session. The failure
mode to design for is concrete and ugly: sampled garbage in the call
header, e.g. `to=functions.check.commentary (json.Xna 天天送钱 code`, or a
turn that emits no call at all.

**What this argues for**, then, is not a format but a preference order:
flat scalar parameters over nested ones; a single primitive carrying a thin
grammar over a structured object when the grammar is genuinely thin; and a
harness that scans and repairs the dialect's known failure modes rather
than one that treats a parse failure as the model's problem. OMP's `read`
is the applied version — one `path` string whose trailing selector carries
line ranges (`:50-200`), multiple ranges (`:5-16,960-973`), counts
(`:50+150`) and modes (`:raw`), rather than `offset`/`limit` fields or an
array of file objects (`omp/tools/read.md`).

It also cuts directly against §2e's batching argument and against the
`Read` shape this collection's own design adopted (`files:
[{path, start_line, end_line}]`), which is precisely the array-of-objects
case. The two claims are not actually contradictory — batching saves turns,
flat parameters save parse failures — but they trade against each other,
and §2e recorded only one side of it. See `agent-design/future.md` for how
the design resolves that.

### 3h. The repair catalogue, and why it must run *after* validation

§3e establishes that mature harnesses accept more than they advertise;
§3f puts a floor under it; §3g explains mechanically why the sloppiness
exists. What none of the code read here supplies is the *list* — which
malformations actually occur, in what proportion, and in what order to fix
them. Command Code's ["Tool Call
Repairs"](https://commandcode.ai/docs/harness-engineering/tool-call-repairs)
(Ahmad Awais, 3 May 2026) is the only source in this collection that
publishes one, drawn from production traffic across DeepSeek, GLM and Qwen
models and reported as running at roughly **1M repairs per 1T tokens**.

**The failure modes are a small finite compositional set.** Four, each
"~30-100 lines":

| Repair | Model sent | Schema wanted |
|---|---|---|
| `null-for-optional` | `{timeoutMs: null}` | `{}` (omitted) |
| `json-array-parse` | `"[\"a\",\"b\"]"` | `["a","b"]` |
| `empty-placeholder` | `{}` | `["src/index.ts"]` |
| `bare-string-wrap` | `"foo"` | `["foo"]` |

The claim attached is the useful part: "when i hear 'this open source model
can't do tool calls' i now assume one of those four, and so far that's been
right ~90% of the time." Note that all four are container/nullability
errors around *non-scalar* parameters — which is §3g's argument arriving
from the opposite direction, as a bug distribution rather than a token
mechanism.

**They are order-dependent, and the ordering is not arbitrary.**
`json-array-parse` must run before `bare-string-wrap`, or `'["a","b"]'`
gets wrapped into `['["a","b"]']` — **schema-valid, meaning lost**, which
is the worst outcome available because nothing downstream can detect it.
Any harness with more than one normalisation rule has this problem and
mostly hasn't noticed; §3e's sources document *which* transforms they
apply, none of them document a required order.

**The architectural finding: invert preprocess-then-validate into
validate-then-repair.** The first implementation normalised inputs before
the validator ever saw them, and broke immediately — "`writeFile` content
that happened to be json-shaped got rewritten before it hit disk. silent
corruption, easy to miss in a smoke test." The replacement:

1. Parse the input as-is. If it validates, **ship it untouched** — valid
   inputs are never rewritten.
2. On failure, walk the *validator's own issue list*, and at each issue
   path try the four repairs in order until one applies.
3. Parse again. On success log `tool_input_repaired:${toolName}`; on
   failure log `tool_input_invalid:${toolName}` and return a
   model-readable retry message.

> when you preprocess, you encode a prior about what's broken. when you let
> the validator complain first, the schema is the prior, and you only spend
> repair budget at the exact paths the schema actually disagreed at.

That is a genuine correction to how §3e frames the pattern, and to any
design that implements tolerance as a normalisation pass in front of the
validator: a blanket pre-pass cannot distinguish a malformed argument from
a well-formed one that merely *looks* like a malformation, because it runs
before anything has said which fields are wrong. The validator localises
the bug for free, and the repair rate per `(model, tool)` pair falls out as
telemetry — enough to "notice when a model regresses on a specific
contract before users do," which is the measurement §3e's "every
normalisation is counted" rule was reaching for.

**Two failure modes that aren't shape errors at all**, and need different
machinery:

- **Post-training distribution leaking across the tool boundary.**
  DeepSeek-Flash emitted file paths as markdown auto-links —
  `filePath: "/Users/x/proj/[notes.md](http://notes.md)"` — and the write
  tool "obediently tried creating files literally named
  `[notes.md](http://notes.md)`." The diagnosis is better than the fix:
  this is not hallucination but a chat-formatting prior applied where it
  makes no sense, because nothing in `z.string()` says where the string is
  going. Hence `pathString()` instead of `z.string()` — encode the
  destination *in the type*, and every path field on every tool is plugged
  at once. "'tool confusion' is a more useful frame than 'capability
  gap.'"
- **Relational invariants between independently-valid fields.**
  `readFile({absolutePath, limit: 30})` with no `offset` failed a
  "provide both or neither" rule; each field was valid on its own, so no
  input repair can see it. The fix was to extend the tool's semantics —
  `limit` alone implies `offset: 0`, `offset` alone implies
  `limit: 2000` — and then **surface the chosen default in the result**,
  deliberately without an `Error:` prefix: "Note: limit was not provided;
  defaulted to 2000 lines. To read more or fewer lines, retry with both
  offset and limit." Stated as a rule: *repair where you can, extend
  semantics where you can't, surface the choice either way.* This is the
  second time this source lands on relational-invariants-across-valid-
  fields as the interesting bug class (§8b is the first, in a different
  subsystem), and the second time it lands on notes-not-errors (§7b).

**The cross-source convergence is worth stating on its own.** Two
independent teams — Command Code on closed infrastructure serving open
models, OMP on an open harness (§3g, §4a) — arrive at the same thesis in
almost the same words. Command Code: "a lot of what looks like model
capability is actually contract design… the largest commercial models eat
that cost invisibly… open models pay it loudly and get dismissed for it."
OMP: "often the model isn't flaky at understanding the task. it's flaky at
expressing itself. you're blaming the pilot for the landing gear." Both
report the same headline result from acting on it — a much cheaper model
brought level with a frontier one by changing only the harness. Neither
result is independently replicated and both are vendor-run, so the numbers
stay claims; the convergence on *where the loss is* is the finding.

---

## 4. Mimicry: how much should a tool look like a tool the model already knows?

### 4a. `cat -n` won, unanimously

Every source read here numbers lines in file output, and all of them cite
or imitate `cat -n`:

| Source | Format |
|---|---|
| Claude Code | "Results are returned using cat -n format, with line numbers starting at 1"; prefix is `line number + tab` (or the older `spaces + line number + arrow`, flag-controlled) |
| Zed | right-aligned in a 6-char field + tab, with a code comment: "This format matches what the model expects in the edit tool" |
| OpenCode | `<line>: <content>`, spelled out in the description with a worked example |
| Crush | line-numbered `view` output |
| Gemini CLI | line ranges, `start_line`/`end_line` |
| OpenHands | `view` with `view_range: [11, 12]`, 1-indexed |

The interesting part is *why it's load-bearing*: line numbers exist for the
model to cite and to page with — but they immediately create a hazard for
exact-match editing, because the model can echo the prefix back into
`old_string`. All three of Claude Code, Zed and OpenCode carry explicit
prose about this. Claude Code's `Edit` description spends its second bullet
on it: "The line number prefix format is: line number + tab. Everything
after that is the actual file content to match. **Never include any part of
the line number prefix in the old_string or new_string.**" Zed's rationale
lives in a code comment tying the two tools together.

**Implication: read-format and edit-format are one contract, not two.** If
you change how `Read` numbers lines, you must change the `Edit` description
in the same commit.

**The unanimity has one challenger, and it is benchmarked.** OMP's default
read format is not `cat -n` but a per-file *snapshot header* plus bare
numbers:

```
[greet.py#A1B2]
1:def greet(name):
2:    msg = "Hello, " + name
```

`A1B2` is a four-uppercase-hex content hash of the whole normalized file,
recorded in a session snapshot store. Every edit must open with
`[PATH#TAG]` copied from the most recent `read`, `grep` or successful
`edit`; a stale tag means the file changed underneath the model and the
edit is rejected **before** anything is written, rather than corrupting it.
The format's own name for what it buys: the model never has to reproduce
old content — no whitespace, no indentation, no recalled snippet — to prove
it knows what it is editing. It cites `PUT 4.=4:` and supplies only the new
lines.

That is optimistic concurrency control applied to file editing, and it is
the first serious alternative to `cat -n` + exact-match this collection has
found. It is also the only edit format here with a published head-to-head:
its author benchmarked it against `apply_patch` and `str_replace` across 16
models, 180 tasks × 3 runs, fresh session each, on mutations injected into
the React codebase. Reported results, with the caveats in
[`sources.md`](./sources.md) — vendor-run, and one of the two blog posts
that supply OMP's rationale:

- Hashline beat `apply_patch` in **14 of 16** models; a later revision beat
  the first in 12 of 16.
- **The weakest models gain the most.** Grok Code Fast 1 went 6.7% → 68.3%,
  which the author reads as edit-format failures having hidden the model's
  actual coding ability rather than the format adding capability.
- **Patch failure rates on models the format wasn't trained for**: Grok 4
  at 50.7%, GLM-4.7 at 46.2% — the mechanism behind §3g's "RL teaches the
  shapes RL practiced," since `apply_patch` is OpenAI's house format.
- **Two models regressed** (DeepSeek V3.2, −5 points vs patch; GPT-5.2
  Codex, +4.6 vs patch but −0.4 vs replace and +26% output tokens), which
  is the result that keeps this from being a clean win — and which OMP
  itself handles by keeping four edit modes and a model exclusion list that
  falls back to `replace` (§10).
- Output tokens fell for most models (−61% best case) because retry loops
  stopped.

Two further design details worth separating from the benchmark, because
they are independent of it. **Line numbers refer to the original snapshot,
not to earlier hunks in the same call**, which removes the offset
arithmetic every unified-diff format imposes when a call carries several
hunks. And **block anchors** (`PUT 1*:`) resolve a tree-sitter node from
its opening line through its end, so "replace this function" does not
require the model to know where the function ends — with an explicit rule
about the case that actually bites (decorators and doc-comments are
separate nodes: anchor the first decorator to sweep both).

**The independent check: Diff-XYZ.** The obvious weakness of §4a's
numbers is that the format's author ran them. JetBrains Research's
[Diff-XYZ](https://arxiv.org/abs/2510.12487) is the closest thing to a
neutral referee — 1,000 real edits from CommitPackFT, automatic metrics,
published dataset — and it does something neither vendor benchmark does:
it **separates generating an edit from reading one**, via three tasks.
*Apply* (old code + diff → new code) and *anti-apply* (new code − diff →
old code) measure comprehension; *diff generation* (new − old → diff)
measures synthesis. Metrics are stripped exact match, plus, for
generation, parse rate, apply rate, EM/IoU after application, and F1 over
added and deleted lines.

The headline result is the one that matters most for tool design, and it
is not subtle. **The format best at generating edits is the worst at
reading them.** GPT-4.1:

| Format | Apply (EM) | Anti-apply (EM) | Diff generation (EM) |
|---|---|---|---|
| udiff | 0.90 | 0.88 | 0.77 |
| udiff-h (relaxed `@@ … @@` header) | **0.92** | **0.93** | 0.06 |
| udiff-l (`ADD`/`DEL`/`CON` markers) | 0.91 | 0.88 | 0.06 |
| search-replace | 0.57 | 0.56 | **0.95** |

Search-replace — the `old_string`/`new_string` family Claude Code, Cline
and this collection's own design all use — generates near-perfectly and
comprehends badly. Unified diff variants invert it. The paper's summary:
"udiff-based formats work best for Apply and Anti-Apply, search-replace
excels for Diff Generation, but for smaller models modified udiff
variants perform best."

Three things follow.

**It corroborates the vendor benchmarks on the points where they could
most easily have been self-serving.** "No single edit format dominates
across models and use cases" is now a measured finding rather than a
quotation. The model-size interaction is independently confirmed from the
other direction: Stencil found hashline helps weak models most and *lost*
on two strong ones; Diff-XYZ finds search-replace suits larger models
while "for smaller models modified udiff variants perform best." Both say
the same thing — **format choice is model-conditional**, which is exactly
what OMP's `resolveEditMode()` exclusion list implements (§10) and what
almost nobody else does. And the OpenAI-house-format bias that Stencil
asserts turns up here as an incidental observation: GPT-4.1 "is more
sensitive to a task prompt and tends to emit V4A diff format by default."

**It supplies the scaling story the vendor posts only gesture at.**
Reliable apply/anti-apply emerges around the 7B scale, but "none of the
open-source models achieve comparable performance on Diff Generation,"
and the authors draw the inference that "handling diff syntax and
formatting requires substantially more capacity than simply applying
edits" — which "may also help explain why smaller models perform poorly
on complex downstream benchmarks such as SWE-bench, where correctly
generating patches is critical." That is a strong statement of this
section's whole thesis from an independent lab: a measurable share of
what looks like small-model coding weakness is edit-format overhead.

**And it means "which edit format is best" is the wrong question**, because
a coding agent does both jobs. It *writes* edits (generation — favours
search-replace) and, in review or diff-reading modes, *reads* them
(comprehension — favours udiff). A harness that picks one format for both
directions is accepting a measured penalty on one of them. Splitting by
direction costs nothing, since the two never share a wire format anyway.

**The rest of the prior art the harness post assembles** is worth keeping
as a reading list, because it is otherwise the only place in this
collection where the edit-format question is treated as a measured one
rather than a taste one:
Aider's benchmarks, where format choice alone swung GPT-4 Turbo from 26%
to 59% while GPT-3.5 managed only 19% with the same format because it
could not reliably produce valid diffs; **EDIT-Bench**, where only one
model clears 60% pass@1 on realistic editing tasks; and Cursor's
fine-tuned ~70B *apply* model — a whole second model whose only job is
merging a draft edit into a file, which is the strongest evidence
available that this problem is hard, alongside Cursor's own reported
result that "fully rewriting the full file outperforms aider-like diffs
for files under 400 lines." Neither Aider's benchmark harness nor
EDIT-Bench has been read as a source here; both would sharpen the
picture, and EDIT-Bench in particular covers the realistic-task axis
Diff-XYZ's synthetic triples deliberately don't.

The mimicry question this raises is the one §4c answers generally: `cat -n`
wins because the model has seen a billion lines of it, and hashline is
*not* a format any model saw in pre-training. Its author's answer is the
constrained-decoding grammar (`omp/hashline-grammar.lark`, 27 lines — the
same move Codex makes with `apply_patch.lark`) plus a 133-line prompt with
six WRONG/RIGHT anti-pattern pairs. That is the real cost of leaving a
mimicked format: you pay for it in grammar and prompt, and you need a
benchmark to know whether you got it back.

### 4b. Where mimicry pays, and where it doesn't

Pays:

- **`rg` semantics for search.** Claude Code's `Grep` description leans
  entirely on ripgrep knowledge, down to the escaping gotcha it needs to
  correct: "Pattern syntax: Uses ripgrep (not grep) — literal braces need
  escaping (use `interface\{\}` to find `interface{}` in Go code)". (This
  exact worked example is one of the near-verbatim borrowings Grok Build
  ships too — `agent-tool-surfaces.md`'s cross-vendor text-convergence
  finding.)
- **V4A `apply_patch`** for the GPT/Codex family (§3b).
- **`str_replace`** as a concept — the dominant edit primitive across the
  field, inherited from Anthropic's reference `text_editor` tool.

Doesn't pay:

- **`sed`/`awk` as an editing path.** Claude Code has a 9.5 KB `sedEditParser.ts`
  and a 21 KB `sedValidation.ts` purely to *detect* that a Bash call is
  actually an edit. Mimicry you have to police is worse than a tool.
- **`ls` as a tool.** Notably, the older leaked Claude Code capture has an
  `LS` tool (`{path, ignore}`); the current live surface does not, and its
  `Read` description says to use "an ls command via the Bash tool" for
  directories. OpenCode went the other way and folded directory listing into
  `read` itself ("Read a file **or directory**... For directories, entries
  are returned one per line with a trailing `/` for subdirectories"). Crush
  and Gemini CLI keep a dedicated `ls`/`list_directory`. This is the one
  primitive with no convergence at all — weak evidence that it doesn't
  matter much either way.

### 4c. Mimic the *interface*, not the *plumbing*

The pattern that generalises: borrow the vocabulary (flag names, patch
grammar, line-number format, `str_replace` semantics) because it's free
model knowledge — but keep the invocation structured so the harness can
still classify, gate, and shape it. Claude Code's `Grep` is exactly this:
ripgrep's flags, JSON's structure.

---

## 5. Output format: JSON vs XML vs plain text

### 5a. What actually reaches the model

Across every source read, the model-facing payload for file/search/shell
tools is **text**, not JSON — even when a rich typed object exists one layer
up (§1).

| Source | Model-facing result |
|---|---|
| Claude Code | plain text; `cat -n` content; Grep returns `Found 3 files\n<paths>` or raw matching lines; footers like `[Showing results with pagination = ...]` |
| OpenCode | text wrapped in **XML-ish tags**: `<path>…</path><type>file</type><content>…</content>` plus a trailing status line inside `</content>` |
| Gemini CLI | `llmContent` string; on truncation, a preamble block (`IMPORTANT: … Status: … Action: …`) then `--- FILE CONTENT (truncated) ---` |
| Crush | text; typed `ViewResponseMetadata` kept separately for the UI |
| Zed | `Output: Into<LanguageModelToolResultContent>` — typed, flattened to text/markdown |
| OpenHands | `Observation` object → text for the model; shell output additionally carries a `###PS1JSON###…###PS1END###` metadata block **embedded inside the text stream** |
| Goose | `shell` is the exception: declared `with_output_schema::<ShellOutput>()`, description says "Returns an object with **stdout and stderr as separate fields**" |
| Codex | `exec_command`/`write_stdin` declare a JSON `output_schema`: `{chunk_id, wall_time_seconds, exit_code, session_id, original_token_count, output}` |
| MCP | both, formally: `content[]` text + optional `structuredContent` validated against `outputSchema` |

So the split is not "text vs JSON" but **what kind of payload it is**:

- **Prose-shaped payloads** (file bodies, diffs, logs, match lines) go back
  as raw text. Nobody JSON-encodes a file body — escaping inflates tokens
  and, more importantly, breaks the exact-match contract that `Edit` depends
  on (§4a).
- **Fact-shaped payloads** (exit codes, session ids, counts, truncation
  state) increasingly go back as JSON fields — Codex's exec schema and
  Goose's split stdout/stderr are the clearest cases, and both are *shell*
  tools, where the model demonstrably struggles to tell "the command
  printed this to stderr" from "the harness failed".
- **Framing** — when untrusted or heterogeneous content must be delimited,
  XML-style tags are the cheap answer (OpenCode's `<content>`, everyone's
  `<system-reminder>`). This is a security/parsing property, not an
  aesthetic one, and it's the same argument `agent-design/formats.md` makes
  for the task envelope.

Anthropic's own guidance declines to pick a winner — testing "revealed there
is no one-size-fits-all solution. XML, JSON, and Markdown formats showed
varying performance depending on task and agent" — while being specific
about the thing that *does* transfer: return high-signal content, drop
UUIDs/MIME types in favour of names, and offer a verbosity control. Their
worked example is a `response_format` enum (`concise` | `detailed`) where
concise cost **72 tokens vs 206** for the same Slack result.

### 5b. Delimiters and escaping in multi-part results

Once a result carries more than one file, three questions appear that a
single-file tool never has to answer: where does each part start and end,
what happens when file content *looks* like the delimiter, and how is a
partial failure reported. The field's answers are thinner than you'd hope:

- **Gemini CLI's `read_many_files`** concatenates with
  `--- {filePath} ---` before each file and a `--- End of content ---`
  terminator (the matching opener, `--- Content from referenced files ---`,
  is a shared constant used when files are injected as context). Content
  is **not** line-numbered and **not** escaped, so a file that itself
  contains a `--- something ---` line is genuinely ambiguous. Images and
  PDFs are pushed as separate parts with no separator at all. Most
  significant: files that were skipped or failed are itemised in
  `returnDisplay` — the *UI* channel — while the model's `llmContent`
  carries only the successes, with a catch-all message reaching it only
  when *every* file was skipped. The model can therefore ask for six files,
  receive four, and not be told.
- **Cline** labels each read `path:start-end` (`formatReadFileQuery`),
  prefixes content lines with a right-padded number and a pipe
  (`  17 | const x = 1`), marks over-long lines with a trailing
  `[line truncated]`, and closes with `[Showing lines X-Y of N…]`. Each
  file in a batch is its own operation result with its own success/failure,
  so a partial failure survives.
- **OpenCode** wraps a single read in `<path>`/`<type>`/`<content>` tags
  with `N: `-prefixed content — the only tag-framed file result in the
  sources read, and unambiguous for the same reason described below.

**Nobody escapes file content, and nobody should.** Escaping is what would
break the byte-exact match that every `str_replace`-family edit tool
depends on (§4a). The way out is already present in most of these formats
without being stated as its purpose: **line-number prefixes are the
escaping mechanism.** If every content line begins with `<number><TAB>` —
blank lines included — then no line of file content can be mistaken for a
delimiter, because delimiters don't start with digits. The formats that
number lines are safe by construction; the one that doesn't
(`read_many_files`) is the one with a real collision.

The other detail worth copying is **line endings**: Gemini CLI detects the
original file's ending on write and converts the model's `\n` content back
to `\r\n` when the file was CRLF. Normalise on read, restore on write —
otherwise "byte-exact" is a lie on any Windows checkout, and the model
spends turns trying to match invisible `\r`s.

### 5c. The dual-channel result is the actual best practice

Combining §1 and §5a, the pattern to copy is:

1. Tools return a **typed object** internally (Claude Code's `outputSchema`,
   Zed's `Output`, OpenHands's `Observation`, MCP's `structuredContent`).
2. A **single explicit mapping function** flattens it to model-facing text.
3. The UI renders from the typed object, never from the flattened text.

The pay-off is that the model-facing format becomes a *decision you can
change* — Claude Code A/B-tests its own read limits and formats behind
GrowthBook flags (`tengu_amber_wren` gates `maxSizeBytes`/`maxTokens`;
`isCompactLinePrefixEnabled()` switches the line-number prefix, with the
`Edit` description text switching with it) — rather than a shape baked
through the whole codebase.

### 5d. When the payload isn't text at all

Every format decision above assumes the file is text. A read tool is also
the entry point for everything that isn't, and Command Code's teardown is
the only source here that treats that as a format problem rather than an
afterthought. Four rules, each with a stated failure mode:

- **Sniff magic bytes, never the extension.** "garbage in a `.png` must
  never reach the api, real webp must pass." The extension is
  attacker- and accident-controlled; the provider's image endpoint is the
  thing that rejects the call, one round trip later. OpenCode, Kilo Code
  and Grok Build are scored as doing this too.
- **Degrade rather than fail to attach.** Images are compressed down a
  JPEG quality ladder (95 → 80 → 60 → 40 → 20) and attached at the first
  size that fits, so a 4K screenshot arrives degraded instead of not
  arriving. This is the §6 caps argument applied to a binary payload: a
  worse answer beats a missing one, as long as it says so.
- **A downscaled image must disclose its scale factor.** "on disk
  3024x1964 / attached 1092x709 → multiply displayed coords by 2.77."
  Nothing in the pixels records that the image was resized on the way in,
  so every coordinate the model computes off a screenshot is confidently
  wrong and *nothing surfaces the error* — the same invisible-failure class
  as §7b's filenames. The write-up scores only Pi and OpenClaw as doing
  this as well, and it is the one item here that matters mainly to
  computer-use rather than coding runs.
- **Structured documents render as documents, and large cell outputs
  become pointers.** Raw `.ipynb` is "json soup: base64 blobs,
  per-character source arrays"; the tool returns tagged cells with plots
  attached as images, and **any cell output over 10,000 characters is
  replaced by a `jq` pointer** rather than inlined. That last move is the
  transferable one, and it is not really about notebooks: when a payload's
  *existence and shape* are what the model needs and its *contents* are
  not, return an address and the means to query it. One dataframe dump
  cannot then eat the read budget, and the model can still fetch the rows
  it turns out to need. SVG is treated as editable XML (it is text), a
  binary returns its MIME type and nothing else, and PDF returns a
  `pdftotext` hint.

The general shape: for a non-text file the read tool's job is to return the
*smallest thing that preserves the model's ability to act* — an attached
image for something it must see, a MIME line for something it must not
read, a pointer for something it may need to query — and to say which of
those it did.

---

## 6. Limits, truncation and pagination

### 6a. The numbers, and four practices worth lifting

Every source caps output; the differences are in the numbers and, more
importantly, in what the cap *says*.

| Source | Read cap | Line cap | Search cap | Command output cap |
|---|---|---|---|---|
| Claude Code | 2,000 lines; **25,000 tokens** (env-overridable); 256 KB file-size gate | — | `head_limit` default **250** entries, with `offset` | spill to file past `maxResultSizeChars` |
| OpenCode | 2,000 lines; **50 KB** bytes | 2,000 chars | — | — |
| Crush | **200 lines** default; 200 KB | 2,000 chars | max results (templated into the description) | — |
| Cline | 2,000 lines; 48,000 chars | 2,000 chars | 48,000 chars | 48,000 chars, **middle elided** |
| Gemini CLI | truncates with an `Action:` block | per-line cap | grep "Max 100 matches" (in the description) | — |
| OpenHands | — | — | grep "only the first 100 results" | 30,000 chars |
| Goose | — | — | — | 2,000 lines per stream, then "saved to a temporary file" |

Four practices worth lifting verbatim:

**1. Every truncation states the next call.** Gemini CLI:
"Status: Showing lines 5-200 of 4,312 total lines. **Action:** To read more
of the file, you can use the 'start_line' and 'end_line' parameters in a
subsequent 'read_file' call. For example, to read the next section of the
file, use start_line: 201." OpenCode: "(Showing lines 1-2000 of 8123. Use
offset=2001 to continue.)" and, for the byte cap, "(Output capped at 50 KB…
Use offset=N to continue.)". Claude Code's Grep: "[Showing results with
pagination = …]".

**2. Truncation notices live at the edges, never in the elided middle.**
Cline elides the *middle* of long command output and documents why the
notice placement matters: "Provider-request building may re-truncate long
strings with its own (possibly tighter) middle-cut backstop; keeping the
notices at the edges means the recovery guidance survives that cut too."
The same file states the cost model plainly: "Every character returned by an
executor is re-sent to the model on each subsequent request, so oversized
outputs cost **quadratically** over the remaining run."

**3. Spill, don't dump.** Claude Code's `maxResultSizeChars` persists an
oversized result to a file and hands the model a preview plus the path — and
carries an explicit exception for `Read` (`maxResultSizeChars: Infinity`)
because "persisting creates a circular Read→file→Read loop". Goose does the
same for shell output over 2,000 lines.

**4. Throwing beats truncating — measured.** The single most useful
empirical note found this pass, in Claude Code's `FileReadTool/limits.ts`:

> Tested truncating instead of throwing for explicit-limit reads that exceed
> the byte cap (#21841, Mar 2026). Reverted: tool error rate dropped but
> mean tokens rose — the throw path yields a ~100-byte error tool-result
> while truncation yields ~25K tokens of content at the cap.

That is the whole limits debate in three lines: a hard error is a **cheap**
teaching signal; a truncated success is an expensive one. It also implies
the right split — cap *by default* (cheap, the model asked for everything
and gets a page), error on *explicit over-limit requests* (the model asked
for something specific and impossible).

### 6b. Three ceilings, not one

The table in §6a records which sources have a line cap and which have a
byte cap, but not *why a harness needs both plus a third*. Command Code's
write-up supplies the argument, and it is the single most portable idea in
that source:

> every codebase keeps a small zoo of hostile files: the 80,000-line
> lockfile, the minified bundle that's technically one line, the log that
> never stops growing. each ceiling handles one animal.

- The **line window** (2,000) bounds a file that is ordinarily large.
- The **byte budget** (128 KB) bounds a file whose lines are *wide rather
  than many* — the ceiling that catches what the line window lets through.
- The **per-line clamp** (2,000 chars) catches the case the other two both
  miss: *one* minified line that sits comfortably inside the line window
  and, on its own, consumes the entire byte budget. Without it the model
  gets back "a single unusable mega-string that displaced everything the
  model actually needed to see."

The point is that these are not three settings of the same dial; each is
the only defence against one file shape, and they compose. "drop any one
ceiling and there's a shape of file that costs you the whole read. no log
will ever show it, just a turn where the model got nothing and paid full
price for it." Checking §6a's table against this framing is a useful
exercise: OpenCode, Cline and Crush have all three; Claude Code's read has
the line window and the byte gate but no per-line clamp recorded in the
source read here, which is also what Command Code's live probe found (a
3,900-character line "returned whole, no clamp") — the one Claude Code cell
in its scorecard that this collection's own reading independently agrees
with.

The clamp also has a second-order effect worth flagging, because it is
where §6 and §8 collide: a clamped line means the model has *not* seen the
file's bytes, which makes the read partial in a way the line count doesn't
reveal. §8b is what happens when a harness forgets that.

### 6c. The truncation you cannot yet honestly claim

Two implementation details from the same source, both about reads that
stream rather than load the file into memory (OpenCode, Kilo Code and Cline
stream too; Claude Code is scored as not doing so):

**Defer the decision at a chunk boundary.** If the line limit is reached
*exactly* at the end of a chunk, the tool does not yet know whether the
file continues — the answer to "is there more?" hasn't been read yet.
Guessing "more of the file remains" is "a lie roughly half the time, and
it's a lie that costs a turn every time it fires," because the model spends
a call fetching a page that doesn't exist. The rule: **when you can't know
yet, say nothing yet** — carry the truncation claim forward to the next
chunk rather than emitting it at the boundary. This generalises to any
`total` or "N of M" figure a tool reports: a footer that says how much
exists is a claim, and a streaming reader has to have actually established
it.

**Resume offsets are computed by the tool, not the model.** In a reader
that cuts mid-line at the byte cap, byte-capped output resumes **on the
last line shown, not the line after it**, because that line was
incomplete; a line-capped read resumes on the next line. Getting this
backwards silently drops a line from the model's view of the file:

> an off-by-one in a resume hint is a silently corrupted read, which is the
> one bug class here that's worse than a wasted turn.

The better answer is to not have two rules — see the whole-line byte
budget below, which makes every cap resume the same way. But *whichever*
convention a reader picks, it has to be the one its notes actually
describe. Which is also the argument for the tool computing the offset at
all: §6a's "state the next call" rule is usually justified by saving a
round trip, but
the stronger reason is that pagination arithmetic done in the model's
reasoning is both billed and occasionally wrong.

**A byte cap must not cut a codepoint in half — or must not cut inside a
line at all.** The corollary nobody states until it bites: §6b's second
ceiling is measured in *bytes* while the payload is UTF-8, so a naive
slice at 128 KB lands mid-sequence and emits a replacement character or
invalid UTF-8 into the model's context — and into whatever the model
later passes back to `Edit` as a match string. There are two fixes in the
field, and the less obvious one is better:

- **Cut mid-line, carefully.** Command Code binary-searches for the
  longest valid UTF-8 prefix under the cap rather than truncating at the
  byte offset. This is what forces the resume-on-the-cut-line rule above:
  the last line shown is incomplete, so the model must re-read it.
- **Never cut inside a line.** Kilo Code composes the ceilings instead:
  each line is clamped to 2,000 characters *first*, then whole clamped
  lines are appended to a byte budget measured with
  `Buffer.byteLength(text, "utf-8")`, and when the next line would exceed
  the budget the read stops and reports that line as the resume point.
  Because the per-line clamp has already bounded any single line, the
  byte ceiling never needs to cut inside one — which removes the
  mid-codepoint problem from the byte cap entirely *and* removes the
  off-by-one hazard, since the resume point is always a whole line.

The second is the better architecture for any line-oriented reader, and
it is worth noticing that it falls out of §6b's three ceilings *composing*
rather than being three independent checks. The codepoint problem doesn't
disappear, it just moves to the one place that genuinely has to cut inside
a line — the per-line clamp — where it is a bounded, local concern.

**A scorecard cell checked against the code.** Command Code's table marks
Kilo Code's per-line clamp "utf-safe," which is directionally right and
precisely wrong, and the difference is instructive. The clamp itself is
`input.slice(0, MAX_LINE_LENGTH)` on a JavaScript string — 2,000 UTF-16
code *units*, which can split a surrogate pair and leave a lone surrogate
for any astral character (emoji, CJK extensions, mathematical
alphanumerics). What *is* unusually careful is everything around it:
Kilo decodes with `new TextDecoder("utf-8", { fatal: true })` in
**streaming mode**, so a multi-byte sequence split across an I/O chunk
boundary is buffered and reassembled rather than mangled, and `fatal:
true` means invalid UTF-8 raises "File is not valid UTF-8" instead of
silently substituting U+FFFD — the same fail-loudly posture `formats.md`
adopts with its `not_utf8` status. It also sets a `discard` flag once a
pending line passes the clamp while still scanning for a newline, so a
600 MB single line is bounded in *memory*, not just in output. So: the
most careful UTF-8 handling of any read tool read here, with the one
literal cell the table graded left unfixed.

The same family of hygiene, from Command Code, in one line each: strip
the BOM (or it becomes an invisible first character of the first line,
which then fails every exact-match edit against that line), and normalise
CRLF on the way in (§5b, where Gemini CLI's restore-on-write half already
lives). These are individually trivial and collectively the difference
between a read tool that works on other people's repositories and one
that works on yours.

(One incidental note from the same section, for anyone implementing this on
a JS stream: don't `break` out of a `for await` loop — it calls the
iterator's `return()` and destroys the underlying stream.)

### 6d. The ceiling that isn't a number: paths refused before any I/O

`/dev/zero` is an infinitely long file. So is `/dev/urandom`. No line
window, byte budget or per-line clamp helps, because the failure is that
the read never terminates — and a workspace-boundary check doesn't help
either when the working directory is `/`. Command Code refuses
`/dev/zero`, `/dev/urandom`, `/dev/stdin` and `/proc/<pid>/fd/*` **by name,
before any I/O**, and states the consequence plainly: "a read tool that
hangs on `/dev/zero` is a denial of service you shipped yourself." Its
scorecard finds only one other harness of ten with such a list.

This belongs in §6 rather than in a security section because it is a limits
problem wearing a safety costume: the general rule is that a cap can only
bound a read that *finishes*, so anything unbounded has to be refused by
identity instead. It is also cheap — a fixed list checked before `open()` —
and, unlike most safety machinery, it has no false-positive cost, because
nothing a coding agent legitimately does involves reading `/dev/urandom`
through its file-read tool. (A model that genuinely wants entropy has a
shell.)

### 6e. Someone ran the experiment: Hermes's read-tool A/B eval

The §6b–§6d material is reasoning about failure shapes, published by a
vendor about its own product. One of the harnesses in that scorecard
responded by building the measurement — and its `evals/readtool/` is the
most rigorous artifact this collection has found on any tool.

Its motivation is stated plainly, and is the epilogue to §8b's method note:

> Motivated by Command Code's read-tool writeup (Aug 2026), which
> benchmarked ten harnesses on hostile-file handling — and whose Hermes
> column contained several errors (we already ship a per-line clamp,
> did-you-mean suggestions, notebook/docx/xlsx extraction, PDF conversion,
> and a device-path blocklist). This eval tests the failure shapes for
> real, through the real `AIAgent`, instead of trusting anyone's
> capability table.

Two things follow. First, **the correction loop closed**: the Command Code
page now credits Hermes with all six of those, and its changelog records
"Hermes re-read at `8359e760`" on 10 Aug 2026 — the write-up's own promise
to "correct any [errors] that are pointed out," exercised. Read the two
together and the lesson is not that either party was careless but that a
capability table about ten codebases is a perishable artifact, and the
useful response to one is to re-derive the cells you care about.

Second, and more usefully, **the fixture suite is a reusable
specification** — nine deterministic hostile files, each isolating one
failure shape from §6b–§6d:

| Fixture | Shape | What it tests |
|---|---|---|
| `package-lock.json`, 80K lines / 2.7 MB | token tarpit | the line window |
| `src/app.min.js`, one 600 KB line | the case the other ceilings miss | the per-line clamp |
| `logs/server.log`, 150K lines, one ERROR near the tail | needle past the window | paging, or reaching for search |
| `data/report.txt`, 412 lines | offset past EOF | the recovery note, §7b |
| `config/overrides.yaml` | empty file | non-silence |
| `notes/Meeting…PM.txt` | NFD + U+202F + U+2019 in the name | Unicode filename repair, §7b |
| `AGENT.md` beside a real `AGENTS.md` | near-miss name | did-you-mean |
| `logs/live.pipe` | **FIFO inside the workspace** | a read that never returns |
| `data/data.txt` holding PNG bytes | lying extension | magic-byte sniffing, §5d |

Metrics per task are accuracy against planted ground truth *plus*
`api_turns`, `tool_calls`, `read_file_calls`, `total_tokens` and `wall_s`,
which is the combination that makes the results interpretable — most of
these features do not change whether the agent succeeds, only what success
costs.

**The finding that changes a §6d conclusion.** §6d framed unbounded reads
as a *naming* problem solved by a blocklist. The FIFO fixture shows why
that is only half of it: `logs/live.pipe` is an ordinary
repository-relative path, so no blocklist of `/dev/*` and `/proc/*` can
see it — "which cannot see an arbitrary workspace FIFO." The fix is a
`stat` on the resolved path, refusing FIFOs, sockets and char/block
devices by *type*. Measured, 3 reps, both arms same prompt, file-only
toolset:

| `fifo_hang` | baseline | stat-guard | delta |
|---|---|---|---|
| opus-4.8 tokens | 40k | 23k | −43% |
| opus-4.8 turns | 5.7 | 4.0 | −30% |
| qwen3.8-max tokens | 122k | 26k | −79% |
| qwen3.8-max turns | 9.3 | 5.0 | −46% |
| qwen3.8-max wall (worst rep) | 618s | 115s | −81% |
| accuracy (both) | 1.00 | 1.00 | held |

Both models recover *eventually* without the guard — which is exactly why
this class of defect survives in shipped harnesses. Nothing fails; it just
costs 7.5× the tokens and up to ten minutes.

**The methodology is worth copying wholesale**, and is stricter than
anything else cited in this doc:

- **Three reps minimum**, with a stated noise floor: "single-run deltas
  within ±3% are noise, not wins."
- **Two models on purpose** — "a frontier model (opus) that can absorb
  sloppy reads, and a strong open model (qwen-max) where harness quality
  shows. A feature that only helps qwen still counts — that's the
  population the hardening serves." This is the same
  constraint-is-a-feature thesis as §6b and §3h, turned into an
  experimental design.
- **Errored runs score 0 and stay in the accuracy denominator but are
  excluded from efficiency means**, so a crash can't flatter the token
  numbers.
- **Caveats recorded next to the verdict**, including one that invalidates
  a comparison the authors could have quietly kept: the full-toolset
  baseline and stat-guard FIFO numbers "are NOT comparable — the fifo
  prompt was tightened between series," and with a full toolset "models
  dodge the hang by using `stat`/`file` first, so real-world savings
  depend on the model reaching for `read_file` before terminal."

That last caveat is the honest boundary on the whole result, and it
generalises: a hardening measured against a file-only toolset is an upper
bound on what it buys an agent that also has a shell.

---

## 7. Errors are prompts

Tool errors go into the transcript, so they are prompt text that gets
written at exactly the moment the model is paying attention. Every source
read here treats them that way.

### 7a. Five ways the field writes them

- **Fuzzy recovery.** Claude Code's `Read`: "File does not exist. …
  Did you mean `<cwd-relative suggestion>`?", falling back to a
  similar-filename search. OpenCode's `read` does the same: "File not
  found: /x/y\n\nDid you mean one of these?\n…" (up to 3 candidates from the
  parent directory, matched by substring in either direction).
- **State the fix, not the fault.** Claude Code's `Edit`: "Found multiple
  matches for old_string. Provide more surrounding lines in old_string to
  identify the correct match" — and the description pre-teaches both failure
  modes and both remedies (`replace_all` vs more context). Codex: "login
  shell is disabled by config; **omit `login` or set it to false**."
- **Non-content is a message, not emptiness.** Claude Code returns
  `<system-reminder>Warning: the file exists but the contents are empty.</system-reminder>`
  rather than an empty string, and for an over-long offset: "the file exists
  but is shorter than the provided offset (N). The file has M lines."
- **Errors are typed for the harness while staying prose for the model.**
  Gemini CLI attaches a `ToolErrorType` (`PATH_NOT_IN_WORKSPACE`,
  `INVALID_TOOL_PARAMS`, `EXECUTION_FAILED`) alongside the text; Zed forces
  errors through the same `Output` type as success.
- **Timeouts enumerate the recovery moves.** OpenHands's shared timeout
  message lists them: send an empty command to wait longer, send other
  commands, send `C-c`/`C-z`/`C-d`, or raise the timeout parameter.

### 7b. Silence is the expensive answer, and some failures are invisible

Command Code's teardown pushes §7a's principle further in two directions
that no source read as code states outright.

**Every dead end names its own recovery, and the set is enumerable.** The
write-up lists them as a closed table rather than as scattered strings —
empty file → "is empty"; past EOF → "retry smaller"; byte cap →
`offset=1847`; line cap → `offset=2001`; PDF → "pdftotext" — on the
argument that the costliest result a tool can return is an *ambiguous
non-answer*:

> an empty result string is indistinguishable, from inside the model, from
> a broken tool. so it re-reads. widens the window. tries a different path.
> burns three turns learning what one sentence could have told it.

The worked comparison is the clearest statement of §7's whole thesis: the
same call either returns nothing (3 turns, no new information) or returns
`Note: offset 900 is beyond the end of the file (412 lines scanned). Retry
with a smaller offset.` (1 turn, correct next call). Claude Code's
equivalent past-EOF message (§7a) says the same thing in the same shape,
which is the corroboration that matters — this is a convergent design, not
one vendor's idea.

Two details are genuinely new here, though. First, **none of these carry an
`Error:` prefix**: they are notes, so the TUI doesn't paint them red "and
the model doesn't treat a fact about the world as a failure worth
apologizing for." An empty file is not an error; a start line past EOF is
not an error; both are facts, and typing them as errors spends output
tokens on apology and, in a harness with an error-rate circuit breaker,
can trip it. Second, the *catalogue* framing is itself the practice: the
recovery strings are a table with one row per way the tool can decline to
return content, which is auditable in a way that a codebase's worth of
ad-hoc `throw` sites is not.

**Some failures the model provably cannot diagnose, and those are the
tool's job to retry.** The best example in the source, and the one finding
here with no analogue anywhere else in this collection:

> macos names screenshots with a NARROW NO-BREAK SPACE before AM/PM. it
> stores filenames NFD-decomposed. finder renames turn `'` into `’`.

Two byte strings; in a terminal, the same picture. The model reads the path
off the screen, retypes it faithfully, gets "file not found," and **no
amount of reasoning recovers, because the difference isn't rendered**. So
before failing, the tool retries **seven candidate spellings** — narrow
space ↔ regular, NFD, NFC, straight ↔ curly quote, NFD+curly — each one
re-checked against the workspace boundary, "because a repair must never
quietly become an escape hatch." Only then does it fall back to
did-you-mean: substring match *plus a bounded Levenshtein of 2*, which is
what catches `AGENT.md` → `AGENTS.md` where substring matching finds
nothing.

The generalisable rule is the one the write-up states: **when a failure is
invisible to the model, retrying is the tool's job**, because the model
will retry the same wrong bytes forever. That is a sharper test than "be
helpful on errors" — it sorts failures by whether the evidence needed to
fix them is present in what the model can see. A missing file whose name is
merely misspelled is visible (hence did-you-mean is a *suggestion*, handed
back for the model to act on); a missing file whose name differs by a
codepoint that renders identically is not (hence the retry happens inside
the tool, before any error text exists). The same test explains §5d's
coordinate-scale disclosure: a resized image carries no visible evidence
that it was resized, so the tool has to say so.

The security note attached to it is worth keeping as stated: a repair layer
that resolves paths is an attack surface, and re-validating every candidate
spelling against the workspace boundary — rather than validating the
original and then repairing — is the ordering that keeps normalisation from
becoming traversal.

---

## 8. The side channels attached to tool results

A tool result is also the harness's chance to inject policy at the moment
of use.

### 8a. Four kinds of side channel

Three independent implementations of the same idea:

- **Instruction files ride along with reads.** OpenCode appends
  `<system-reminder>` blocks carrying nearby `AGENTS.md`-style instructions
  resolved for the file just read. Gemini CLI calls it JIT context
  (`discoverJitContext` → `appendJitContext`) on every `read_file`. Claude
  Code prefixes memory-file reads with a freshness note (via a `WeakMap`
  side-channel, deliberately kept out of the output schema "which flows into
  SDK types").
- **Policy reminders.** Claude Code appends a malware-analysis reminder to
  *every* file read — and gates it per model (`MITIGATION_EXEMPT_MODELS`
  currently exempts one model), which is a neat illustration that these
  injections are tuned per model, not fixed.
- **Result deduplication.** Claude Code's `Read` has a `file_unchanged`
  output variant that returns only: "File unchanged since last read. The
  content from the earlier Read tool_result in this conversation is still
  current — refer to that instead of re-reading." A re-read of an unchanged
  file costs ~30 tokens instead of thousands. This is the highest
  token-leverage single feature found in this pass, and no other source read
  here has it.
- **State gates.** `Edit` errors if the file was never `Read` in this
  conversation ("You must use your `Read` tool at least once…"), and `Write`
  errors if an existing file wasn't read first. This is enforced in code via
  a per-session `readFileState` cache, not by instruction — the same
  structural-gate principle `agent-design/README.md` already adopts.

### 8b. The bug class no schema catches: relational invariants

Every mechanism in §8a is *stateful*, and §8a describes each one in
isolation. Command Code's write-up is the only source here that describes
what happens when they compose, and it is the most valuable single passage
in it — a production deadlock with no invalid input anywhere in it:

```
read → one clamped line → ledger says partial → write DENIED
  → model re-reads → dedup returns "unchanged" → ↺ forever
```

A file with one very long line is read; the per-line clamp (§6b) fires, so
the ledger records the view as **partial**; `write_file` refuses to
overwrite a file the model has only partly seen (correctly — it would
destroy the unseen part); the model does the only sensible thing and
re-reads; the unchanged-file dedup recognises the identical window and
returns its "unchanged, refer to the earlier result" stub; the ledger still
says partial; repeat. It was hit in the wild, on plan files during plan
review. As the write-up puts it: "every field in every call was valid. the
invariant that broke lived in the relationship between three tools that
never call each other."

The stated fix is three-sided, and each side is a rule worth having
independently:

1. **A clamped read still records the exact raw bytes**, and `write_file`
   accepts an overwrite whenever the ledger's recorded content matches
   what is on disk — *even if the view was flagged partial*. The gate's
   real question is "would this write destroy content the model never
   saw," and byte equality answers it directly; "was the view partial" is
   only a proxy for it.
2. **A genuinely partial view gets its own error** — `Only part of this
   file has been read` — instead of the misleading "has not been read
   yet," which "had been sending models into tiny-window re-read loops."
   §7's error-as-instruction rule applied to a state gate: the message has
   to name the *actual* state, or the model's correct response to it is
   wrong.
3. **The dedup does not stub a from-line-1 re-read unless the ledger holds
   a full view**, and that guard runs *before* the dedup check, because a
   dedup hit consumes its record (below).

The generalisation is the part to keep: **shape invariants are checkable
per field, and every schema you write already checks them; relational
invariants across stateful tools are where the real bugs live**, and they
are only found by watching production traffic. Two of §8a's four side
channels are relational in exactly this sense — the dedup and the state
gates, which is precisely the pair that deadlocked — and the JIT
conventions injection is adjacent, since it keys off which file a read
touched. This collection has been cataloguing them one at a time without
asking what they do to each other.

**And a corollary about the dedup specifically: a cache whose stale hit is
catastrophic should expire itself on use.** The dedup stub points at an
*earlier tool result in the conversation* — but
[`agent-context-compaction.md`](./agent-context-compaction.md) is a whole
doc about that earlier result being summarised away. If compaction ate it,
the model has been told to refer to something it can no longer see, and
nothing about a retry escapes it, because the retry hits the same cache.
The fix is that **a dedup hit consumes its record**, so the natural retry
gets real content:

> cheap miss, catastrophic stale hit → self-expiring cache.

Worst case is one wasted turn instead of an unbounded loop; the premium is
one turn against an unbounded failure. The same source pairs the mechanism
with an operational rule worth generalising: the dedup **ships behind a
kill-switch environment variable**, "because every cache needs one." A
correctness-affecting optimisation that can only be disabled by a release
is one you will be debugging in production with no way to isolate it. This is a real gap in §8a's account
of Claude Code's `file_unchanged` — this collection recorded it as "the
highest token-leverage single feature found in this pass" without noticing
that it creates a dangling reference into a context window another part of
the same harness is actively rewriting. Any harness shipping both dedup and
compaction needs an answer here, and consume-on-hit is the cheapest one.

**A note on the scorecard, and on Claude Code's column.** Command Code
scores Claude Code as having *neither* unchanged-read dedup nor
did-you-mean suggestions. This collection read both in the leaked Claude
Code source (§7a, §8a) — `file_unchanged` is a declared variant of the read
tool's output schema, and the "Did you mean…?" fallback is right there in
the not-found path. Both cannot be right, and the interesting part is that
the disagreement is probably not an error by either side:

- The write-up is explicit that Claude Code's column was **probed live,
  not read** ("claude code ships no source, so its column came from feeding
  the live tool crafted files"), that the probes were four specific files,
  and that "a dash means we looked and did not find it, not that it is
  impossible or unplanned." Dedup was not among the four probes, so that
  cell is a capture gap rather than a measurement. The did-you-mean cell
  *was* probed (a missing `AGENT.md` beside a real `AGENTS.md`) and came
  back with no suggestion.
- This collection has twice found Claude Code features that exist in the
  leaked source but are **flag- or `USER_TYPE === 'ant'`-gated** out of the
  shipped product (`agent-self-verification.md`'s adversarial verification
  subagent; `agent-permissions-approval.md`'s `yoloClassifier.ts`), and
  §5c records that the read tool's own limits and line-prefix format sit
  behind GrowthBook flags. A third instance — code present, behaviour
  absent from a live probe — is exactly the pattern already documented.

Which makes the pair of readings more useful than either alone, and worth
stating as a method note: **source-reading establishes what was built;
probing establishes what is switched on.** They answer different questions,
and where a leak and a probe disagree about a flagged codebase, the
honest reading is "built, not enabled for this account," not "one of them
is wrong." The rest of the scorecard should be read with the same
discipline the source itself asks for — it carries an unusual disclosure
that the benchmark "was produced by AI with little human review, and should
be read that way — we expect errors in it" — so the cells are treated
throughout this doc as claims worth checking, while the failure modes,
which are reproducible reasoning rather than measurement, are treated as
findings.

That posture is now vindicated from an unexpected direction: **another
harness in the same table found errors in its own column, said so, and the
table was corrected** — see §6e, where Hermes documents the six
capabilities it was wrongly marked down on and Command Code's changelog
records the re-read. The Claude Code disagreement above stays unresolved
for the reason given (nobody outside Anthropic can re-derive a flag-gated
cell), but the general case has an answer: a capability table spanning ten
codebases decays, and the response is to re-measure the cells you are
about to make a decision on.

---

## 9. Metadata the model never sees

The harness channel from §1, in practice:

- **Classification**: `isReadOnly`, `isDestructive`, `isConcurrencySafe`,
  `isOpenWorld` (Claude Code) map exactly onto MCP's `annotations`
  (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`),
  which OpenHands and Goose both populate on every tool. MCP's spec adds the
  necessary caveat: clients "MUST consider tool annotations to be untrusted
  unless they come from trusted servers."
- **Parallel-safety by declared resource**: OpenHands's `DeclaredResources`
  is the most advanced version — each tool declares the resource keys its
  call touches, and `grep` declares an empty key set with a comment
  explaining that all its backends are stateless, so it can run lock-free in
  parallel. That's strictly better than a boolean, and it's what you'd want
  for "can these two `Edit`s run at once" (answer: only if their paths
  differ).
- **Scope gating**: Zed's `allow_in_restricted_mode()` and
  `supports_provider()`; Claude Code's `isEnabled()` plus per-agent tool
  filtering.
- **Interrupt semantics**: Claude Code's `interruptBehavior()` —
  `'cancel'` (discard the running tool's result when the user types) vs
  `'block'` (finish first, queue the message).
- **Classifier input**: `toAutoClassifierInput()` produces a compact
  representation of the call for a *second, cheaper model* that decides
  whether it's safe to auto-run (`ls -la` for Bash, `/tmp/x: new content`
  for Edit) — with the default being `''`, i.e. "skip me", and the comment
  "security-relevant tools must override".

---

## 10. The tool set is a runtime artifact, not a constant

Four mechanisms, all found in code:

**Per-model-family declarations.** Gemini CLI's `definitions/` directory
holds `model-family-sets/gemini-3.ts` and `default-legacy.ts`, plus a
`resolver.ts` that merges a base declaration with per-model overrides. The
same `read_file` tool is described to Gemini 3 as "To maintain context
efficiency, you **MUST** use 'start_line' and 'end_line' for targeted,
surgical reads… triggering these limits is considered token-inefficient" and
to legacy models as "If the file is large, the content will be truncated.
The tool's response will clearly indicate if truncation has occurred…". Same
tool, same schema, opposite rhetoric: one warns about cost, the other
reassures about safety. Their `replace` tool differs even more — the legacy
description is a five-point numbered contract, the Gemini 3 one is three
sentences.

**Model-conditional tool *sets*.** Cline's `model-tool-routing.ts` (§3b)
swaps `apply_patch` in and `editor` out by provider/model substring.

**Deferred loading + tool search.** Both leading CLIs now ship it:

- Claude Code: tools carry `shouldDefer`, `alwaysLoad`, and a `searchHint`
  ("One-line capability phrase used by ToolSearch for keyword matching…
  3–10 words, no trailing period. Prefer terms not already in the tool
  name"). MCP tools are deferred *by default* ("always deferred —
  workflow-specific"), and `ToolSearch` itself is never deferred. Deferred
  tools are announced by name only, in `<system-reminder>` blocks; the model
  fetches full schemas with `select:Read,Edit` or a keyword query.
- Codex: `tool_search` over deferred tool metadata using **BM25**, with the
  same instruction to prefer it over `list_mcp_resources`.

The economics come from Anthropic's own published numbers: 150,000 → 2,000
tokens of tool definitions in the extreme case (98.7%). This is the strongest
counter-argument to the "many narrow tools" cost objection in §2 — narrow
tools are cheap if most of them aren't loaded.

**Descriptions assembled at runtime.** Crush stores descriptions as Go
templates (`view.md.tpl`: "…supports offset and line limit (default
`{{ .DefaultReadLimit }}`, max `{{ .MaxViewSizeKB }}`KB…") so the numbers in
the prose cannot drift from the constants in the code. OpenHands appends the
resolved working directory to the `grep` description at construction time.
Claude Code's `renderPromptTemplate` composes the `Read` description from
runtime limits and capability checks (`isPDFSupported()`). Codex swaps the
entire `shell_command` description on Windows, PowerShell examples and all.

**Two more mechanisms, both from OMP, both a level below the four above.**

*The wire dialect is per-model-family, and native tools are optional.* A
`tools.format` setting (default `auto`) selects how tool calls are
serialized for this session, including options that **remove native
structured tools from the provider request entirely**, append an in-band
tool catalogue and format guide to the system prompt, convert prior calls
and results to text, and scan assistant text back into structured
tool-call events. OMP ships eleven such dialect references —
Anthropic-style `<invoke>`, Harmony, Qwen3/Hermes ChatML, Gemma 4's
token-delimited `call:NAME{…}`, GLM-4.5, DeepSeek, Kimi K2, MiniMax,
Gemini, a generic XML dialect, and a lossless `pi-native` gateway transport
— each documenting special-token IDs and parser quirks for one family
(`docs/toolconv/`; compared in
[`agent-tool-call-dialects.md`](./agent-tool-call-dialects.md)). `auto`
resolves by family, and falls back to a known family dialect rather than
the generic one when a model reports `supportsTools: false` — on the
argument that a grammar *some* family was trained on beats a neutral
grammar nobody was.

That is a fifth axis, and the lowest one: not *which* tools (§10's tool
sets), not *what the schema says* (per-family declarations), but **how the
call is encoded on the wire**. §3g is why it matters — the encoding decides
what has to be escaped and therefore what can fail to parse. Two details
are worth copying regardless of whether you ever swap dialects: the scanner
deliberately accepts more than the renderer emits (`<function_calls>` and
`antml:`-prefixed variants as aliases, a bare invoke with no wrapper) —
§3e's advertise-strict/accept-tolerant rule reappearing one layer down; and
the generic XML dialect has **no success/error marker at all**, rendering
`isError: true` in the same `<tool_response>` shape as success, so "the
error must be intelligible from its text." That is §7's errors-are-prompts
rule turned into a hard constraint by the format.

*The edit format is model-conditional, with a benchmarked fallback.*
`resolveEditMode()` picks among `hashline`, `apply_patch`, `patch` and
`replace` — model-specific configured variant, then env var, then config,
then the default — and "unless `PI_STRICT_EDIT_MODE` is set, a short model
exclusion list can replace the default hashline contract with `replace`."
Cline does the same thing by provider substring (§3b); the difference is
that OMP's exclusion list is populated from its own 16-model benchmark
(§4a), including the two models where the default format measurably lost.
The tool's "schema, prompt, examples, renderer, and optional custom Lark
format all switch with the selected mode" — so an edit-format fork is five
artifacts, not one, which is the practical reason this stays rare.

---

## 11. MCP-specific practice

MCP is where "someone else's tools" arrive, and it inverts several defaults:

- **Defer by default.** Both Claude Code and Codex treat MCP tools as
  deferred/searchable rather than always-loaded, with an explicit opt-out
  (`_meta['anthropic/alwaysLoad']`).
- **Servers ship prose, not just schemas.** An MCP server can supply an
  `instructions` block that lands in the system prompt. The GitHub server's
  is a live example (visible in this very session): it explains when to use
  `list_*` vs `search_*`, tells the client to paginate "with batches of 5-10
  items", and advertises a `minimal_output` parameter "if the full
  information is not needed" — i.e. Anthropic's `response_format` verbosity
  control, implemented as a per-tool boolean. It also documents a
  multi-call *workflow* (create pending review → add comments → submit),
  which is the workflow-consolidation advice of §2d showing up as
  documentation because the protocol can't express it.
- **Consolidation is visible in the naming.** The GitHub server's surface
  has collapsed verb-per-endpoint tools into `issue_read`/`issue_write`/
  `pull_request_read`/`pull_request_review_write` with a `method` discriminator
  — the command-enum pattern of §2b, applied to an API surface with dozens
  of endpoints.
- **`structuredContent` + `outputSchema`** give MCP tools the dual-channel
  result of §5c natively, with the compatibility rule that structured
  results should *also* be serialised into a text block.

---

## 12. The checklist

What the evidence supports, stated as rules. Each is backed by at least two
independent implementations (sources in brackets).

**Shape**
1. Give every tool three explicit surfaces: model text, harness metadata,
   human rendering. [Claude Code, Gemini CLI, OpenCode, Zed, OpenHands, MCP]
2. Split a primitive when the split changes a harness answer (permission
   class, destructiveness, concurrency, result shape); otherwise use a
   `command`/`operation` discriminator or optional-field presence.
   [OpenCode `lsp`, OpenHands `file_editor`, GitHub MCP `issue_read`]
3. Consolidate *workflow* tools around intents, not endpoints. [Anthropic
   guidance, GitHub MCP]
4. Expect to pay for shell breadth in classifier code, sandboxing, or an
   allowlist — pick which up front. [Claude Code's 600 KB+ of Bash
   validation, Codex's sandbox, Bolt's allowlist]

**Parameters**
5. Named, typed fields — never a flag string the harness has to re-parse.
   [universal]
6. Borrow flag *names* and semantics the model already knows (`-A`, `-B`,
   `head_limit` ≈ `| head -N`). [Claude Code `Grep`, Gemini `grep_search_ripgrep`]
7. Use a freeform/grammar body only for patch-like payloads, and say
   "do not wrap this in JSON" in the description. [Codex, OpenCode, Cline]
8. Advertise a strict schema; accept a tolerant one (aliases, coercion,
   clamping). Never fail a call you can disambiguate. [Cline, Claude Code,
   Zed]
9. Add a model-authored `description`/`instruction`/`justification` field
   where it steers behaviour or produces the human-facing text.
   [Crush, Claude Code, Gemini CLI, Codex]

**Results**
10. Return prose payloads as raw text; return facts (exit codes, ids,
    counts, truncation state) as fields. [Codex exec schema, Goose shell,
    MCP]
11. Number lines `cat -n`-style, and treat read-format + edit-format as one
    contract changed together. [Claude Code, Zed, OpenCode]
12. Cap everything, and make each cap self-describing: what was cut, how
    much exists, and the exact parameters for the next call.
    [Gemini CLI, OpenCode, Claude Code]
13. Keep truncation notices at the head/tail, elide the middle. [Cline]
14. Spill oversized results to a file and return a preview + path — except
    for the read tool itself. [Claude Code, Goose]
15. Prefer a hard error over a large truncated success when the model asked
    for something explicitly impossible. [Claude Code experiment #21841]
16. Write errors as instructions: what happened, what to do, and a
    did-you-mean when you can compute one. [Claude Code, OpenCode, Codex,
    OpenHands]
17. Never return silent emptiness — say the file is empty, or the offset is
    past EOF, in-band. [Claude Code]

**Lifecycle**
18. Use the tool result as an injection point for just-in-time instructions
    (nearby conventions files, policy reminders, freshness notes).
    [OpenCode, Gemini CLI, Claude Code]
19. Deduplicate re-reads of unchanged files — and **consume the dedup
    record on a hit**, because the stub points into a context window
    compaction may have rewritten. [Claude Code; Command Code for the
    consume rule]
20. Enforce read-before-edit in code, not in prose — and record *what was
    seen* (bytes, and whether the view was partial), not merely *that* a
    read happened. [Claude Code; Command Code]
21. Generate description text from the same constants the code enforces.
    [Crush, OpenHands, Claude Code]
22. Treat the tool *set* as per-model configuration, and be ready to defer
    rarely-used tools behind a search. [Gemini CLI, Cline, Claude Code,
    Codex]

**The read tool specifically** (§5d, §6b–§6d, §7b, §8b — mostly one
source, so marked)
23. Ship three ceilings, not one: a line window, a byte budget, and a
    per-line clamp. Each is the only defence against one file shape.
    [OpenCode, Cline, Crush have all three; Command Code for the argument]
24. Refuse unbounded paths (`/dev/zero`, `/dev/urandom`, `/proc/<pid>/fd/*`)
    by name before any I/O — a cap can only bound a read that finishes.
    [Command Code, Hermes]
25. Compute resume offsets in the tool, and get the off-by-one right: a
    byte-capped read resumes *on* the cut line, a line-capped read on the
    next one. Never claim "more remains" you haven't established — at a
    stream chunk boundary, defer the claim. [Command Code]
26. Retry inside the tool for failures the model cannot see (Unicode
    filename variants: NFC/NFD, narrow space, curly quotes), and *suggest*
    for failures it can (did-you-mean, substring + bounded Levenshtein).
    Re-validate every repaired candidate against the workspace boundary.
    [Command Code]
27. Type "empty file", "past EOF" and "capped" as **notes, not errors** —
    they are facts about the world, and an `Error:` prefix buys apology
    tokens. [Command Code; Claude Code's past-EOF message has the same
    shape]
28. Detect file type by magic bytes, never extension; degrade images down a
    quality ladder rather than failing to attach; disclose the scale factor
    of anything downscaled. [Command Code, OpenCode, Kilo Code, Grok Build]
29. For structured documents, return a pointer rather than the payload once
    a part exceeds a threshold (a `jq` path for a >10K-char notebook cell),
    so the model keeps the ability to query what it didn't receive.
    [Command Code]

**The wire layer** (§3g, §4a, §10 — from OMP and its author's write-ups)
30. Prefer flat scalar parameters. A primitive parameter body is
    delimiter-matched and needs no escaping; an array or object forces
    JSON into the same body, where it can fail to parse on every call.
    [OMP's dialect converters, the keypad experiment]
31. Where a grammar is genuinely thin, put it in one string rather than in
    a structured object (`path:50-200`, `path:5-16,960-973`) — but only
    where thin is true, since this trades §2e's turn savings for parse
    reliability. [OMP `read`]
32. Handle your dialect's failure modes in the harness: malformed call
    headers, a leaked call in output text, a turn with no call at all.
    "There is no fix coming" from the provider. [OMP scanners]
33. Give the model a stable anchor it did not have to reproduce — a content
    hash it cites rather than source text it must retype — and reject a
    stale anchor before writing rather than after. [OMP hashline; and the
    same invariant as Command Code's partial-view write gate, §8b]
34. If you leave a format the model has seen a billion lines of, budget for
    a constrained-decoding grammar, an anti-pattern-heavy prompt, and a
    benchmark — and expect to keep the old format for the models that
    regress. [OMP: 4 edit modes + an exclusion list; Codex `apply_patch.lark`]

---

## 13. What this changes for the design in `agent-design/`

Applied in [`agent-design/tools.md`](./agent-design/tools.md) — see that
file's "Implementation contract" section and the per-tool notes. The design
gains: an explicit three-channel tool contract; the self-describing
truncation/pagination footer rule; caps-by-default with errors on
explicitly-impossible requests; the spill-to-scratch rule; error-as-
instruction wording including did-you-mean; a strict advertised schema over
a three-layer tolerant parser; the `cat -n` + `Edit` shared contract; an
output-format policy (text for prose, fields for facts); read-before-edit
as harness state; per-tool read-only/concurrency/destructive metadata; and
a note that the tool *set* is model-configurable rather than fixed.

Two changes to the surface itself came out of discussing the above rather
than from the sources directly, though both lean on them. `Glob` became
**`List`** — one read-only path tool covering glob matching, directory
listing and a line-counted tree behind an `output` mode, on the argument
that all three are read-only, concurrency-safe and return a set of paths,
so they differ only in rendering (§2, and Goose's five-tool surface keeping
`tree` is the precedent for the tree specifically). And **`Read` became a
batch tool** taking `files: [{path, start_line?, end_line?}]` (§2e), with
Cline's documented "range on the same object as the path" warning carried
into the description verbatim.

Deliberately **not** adopted — including unchanged-file dedup, which is
blocked on cache invalidation a v1 without command-level `Bash` visibility
can't do safely — is recorded in
[`agent-design/README.md`](./agent-design/README.md)'s decision log and
tracked in `agent-design/medium.md`.

**The read-tool pass (§5d, §6b–§6d, §7b, §8b) changed six more things**,
two of which were latent bugs in the design rather than additions:

- **A per-entry byte ceiling** (`read.max_entry_bytes`, 64 KB) — the
  middle of §6b's three ceilings, which the design was missing. It had a
  line window, a per-line clamp and a *call* budget, so a single file of
  2,000 merely-wide lines cleared every per-entry cap and then hit the
  batch rule, which truncates whole entries and would therefore have
  returned nothing at all for a one-file call. The value deviates from
  Command Code's 128 KB because this `Read` is a batch tool and a
  per-entry ceiling above the call budget never fires.
- **`Write` now requires a *full* view, not any view** (§8b). The gate as
  written asked only whether a path had been read this run, so a model
  could read 50 lines of a 2,000-line file and then replace it wholesale,
  destroying 1,950 lines it had never seen. The read-state cache
  correspondingly stops being a boolean and records bytes,
  `(mtime, size)`, and whether the view was partial — with byte equality,
  not the partial flag, as the thing the gate actually tests.
- **Unicode filename repair inside the tool** (§7b), sorted by the rule
  that repair is for failures the model cannot see and suggestion is for
  failures it can — with every candidate re-validated against the working
  tree, and the repaired path echoed back so the model learns the real
  bytes.
- **A refused-path list checked before `open()`** (§6d), plus the note
  that it is extendable and never emptyable.
- **A floor under tolerant parsing** (§3f): coercion is whole-string, so
  `"2abc"` and `1.5` are errors rather than a silently wrong window.
- **Result-format precision** (`formats.md` §8b): which cap fired is
  named, byte-capped reads resume *on* the cut line while line-capped
  reads resume on the next, `empty`/`past_eof`/`truncated` are typed as
  notes rather than errors, and a `total` the harness hasn't established
  is omitted rather than guessed.

The dedup entry in `medium.md` §2g also gained three conditions on the
version that eventually lands (consume-on-hit, ordering against the write
gate, and the interaction with batch reads), because §8b is the account of
a team shipping that exact feature into a harness with this design's exact
combination of clamp, gate and dedup, and finding it deadlocked.
