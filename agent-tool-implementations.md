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

### 5b. The dual-channel result is the actual best practice

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

---

## 6. Limits, truncation and pagination

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

---

## 7. Errors are prompts

Tool errors go into the transcript, so they are prompt text that gets
written at exactly the moment the model is paying attention. Every source
read here treats them that way:

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

---

## 8. The side channels attached to tool results

A tool result is also the harness's chance to inject policy at the moment
of use. Three independent implementations of the same idea:

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
  result of §5b natively, with the compatibility rule that structured
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
19. Deduplicate re-reads of unchanged files. [Claude Code]
20. Enforce read-before-edit in code, not in prose. [Claude Code]
21. Generate description text from the same constants the code enforces.
    [Crush, OpenHands, Claude Code]
22. Treat the tool *set* as per-model configuration, and be ready to defer
    rarely-used tools behind a search. [Gemini CLI, Cline, Claude Code,
    Codex]

---

## 13. What this changes for the design in `agent-design/`

Applied in [`agent-design/tools.md`](./agent-design/tools.md) — see that
file's "Implementation contract" section and the per-tool notes. In summary,
the design gains: an explicit three-channel tool contract; the
self-describing truncation/pagination footer rule; the spill-to-scratch rule
for oversized results; error-as-instruction wording including did-you-mean;
tolerant input parsing with a strict advertised schema; the `cat -n` +
`Edit` shared-contract statement; a stated output-format policy (text for
prose, fields for facts); read-before-edit and unchanged-file dedup as
harness state; and a note that the tool *set* is model-configurable rather
than fixed.

Deliberately **not** adopted, and why, is recorded in the decision log in
[`agent-design/README.md`](./agent-design/README.md).
