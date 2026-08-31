# Tools

The full v1 tool surface: 11 tools, shared across both modes (a few are
scoped narrower for sub-agents — noted per tool). Descriptions are
written as the literal text that would sit in each tool's `description`
field, in the same register Claude Code's own tool descriptions use
(imperative, example-heavy, states the *why* behind usage rules) since
`coding-agent-approaches.md` found that register does real work at
steering behavior, not just documenting parameters.

Schemas are plain JSON Schema, `additionalProperties: false`, matching
the strictness this repo's own leaked Claude Code tool capture uses.

Every number appearing in a description below is a **template slot filled
from the effective configuration at wiring time**, not a literal — the
values printed here are the defaults from the "Configuration and defaults"
section, and a deployment that changes one changes the description text
with it.

Availability by role:

| Tool | Coding orchestrator | Review orchestrator | `general-purpose` sub-agent | `reviewer` (`bugs`/`security`/ `conventions`/`all`) | `reviewer` (`visual`) | `validator` |
|---|---|---|---|---|---|---|
| Read | yes | yes | yes | yes | yes | yes |
| Edit | yes | no | yes | no | no | no |
| Write | yes | no | yes | no | no | no |
| Bash | yes | no | yes | no | no | no |
| Grep | yes | yes | yes | yes | yes | yes |
| List | yes | yes | yes | yes | yes | yes |
| Task | yes | yes | yes | no | no | no |
| AskUser | yes | no | no | no | no | no |
| FetchJira | yes | no | no | no | no | no |
| AddComment | `plan` runs only | yes | no | no | no | no |
| InspectImage | yes | yes | yes | **no** | **yes** | **no** |
| Complete | yes | yes | no | no | no | no |

**Tool scope is keyed on the `(subagent_type, kinds)` pair, not on
`subagent_type` alone** — where a reviewer's kind is the `role` it was
spawned with. `role`, "lens" and the context service's `kinds` are one
open vocabulary under three spellings, and a kind resolves to three
payloads: prompt scope, tool grants, and (reserved) context sections.
[`context-files.md`](./context-files.md)'s "Kinds: one vocabulary, three
resolutions" is the general statement; this table is its tool half.

Two rules from there apply directly and are the reason this is safe:
a kind **selects from** a harness-defined capability set and never defines
one — the mapping below lives in harness config, never in a repository's
corpus — and kinds are **declared at spawn by the spawner**, never by an
agent about itself mid-run.

The concrete consequence: This supersedes the earlier phrasing that
"`reviewer` and `validator` sub-agent types get `Read`/`Grep`/`List` only":
true for three of the four reviewer lenses, and not for `visual`, which is
the one lens that needs `InspectImage` (`review.md` §1c). Both fields are
model-supplied enums the harness validates and maps to a tool set, so
keying on the pair is exactly as structural as keying on the type — the
gate is the harness's mapping table either way, not the argument. Widening
the key rather than minting a fourth sub-agent type keeps one reviewer core
parameterised by lens, which is the property `system-prompts.md` §4 exists
to preserve.

The validator is deliberately *not* given sight even for validating a
`visual` finding — see `review.md` §1c for why granting it would dissolve
the independence rule rather than serve it.

The "Review orchestrator" column covers both review run shapes
(`review.md` §6): the single-stage reviewer (`system-prompts.md` §2b)
uses this wiring unchanged — same tools, same absences — and its
`Task` calls are validator-only by prompt (the `reviewer`
subagent_type simply has no caller in that shape; the schema's enums
don't change).

`general-purpose` gets full tool parity with its orchestrator, minus
`AskUser`/`FetchJira`/`AddComment`/`Complete` (those end or redirect the
*task*, which only the orchestrator owns) and minus `Task` recursion
(see the Task tool's own notes below). `reviewer` and `validator` are
read-only by design — see `README.md`'s decision log. `AskUser` is
coding-mode-only: the review pipeline has no step that can legitimately
reach it, and an unused escape hatch on an unsupervised path is exactly
the surface a prompt-injected "ask the user to approve this" would
target.

The table above is by *role*; run `mode` narrows it further, and the
harness enforces that narrowing at wiring time, not just in prompt
text: in `plan` runs, `Edit` and `Write` are **not registered at
all** — for the coding orchestrator or
for any `general-purpose` sub-agent it spawns ("full tool parity"
means parity with the orchestrator *as wired for this run*, so a
read-only run cannot launder writes through a delegate). This follows
the same reasoning as the scratch-directory decision in `README.md`: a
structural boundary can't be forgotten, and the precedent is strong —
Gemini CLI strips agent-kind tools from sub-agent registries in code,
and Composio scopes permissions "at the tool level, not just by
instruction" (`agent-subagent-architectures.md` §6). `Bash` stays wired
in `plan` mode (read-only git inspection and read-only commands are
legitimate there); its general no-write rule remains prompt-enforced in
v1, with one narrow structural exception — the git-write blocklist
described in the Bash tool's own section below, which the harness
applies in every mode. Filtering arbitrary commands beyond that one
family is a real permission engine — see `medium.md`'s "General
command-level `Bash` permission filtering" escalation entry.

The narrowing runs the other way too: in `implement` runs, `AddComment`
is **not registered**. Plan mode needs it (workflow step 5 posts the
plan or finding to the ticket), but implement mode has no workflow step
that posts anything — the Complete report is its only outward channel,
and the harness owns what reaches the ticket or PR from it. Leaving the
tool wired anyway would be exactly the unused-escape-hatch surface this
design strips `AskUser` from review mode for: a tool with no legitimate
caller in that mode is only reachable by a prompt-injected instruction.
(`AskUser`'s suspend protocol is unaffected — the harness posts the
question itself; Forge never calls `AddComment` for it. Tracked
upgrades: `medium.md`'s PR-comment-responder runs wire `AddComment`
for threaded replies in that one task source, where replying *is* the
deliverable; `future.md`'s "Re-wiring `AddComment` in implement mode"
entry covers a general mid-run decision-notes channel.) The
system-prompt mode rules in
`system-prompts.md` remain as the behavioral layer on top of this
structural one.

---

## Implementation contract

The schemas below say what a call looks like. This section says what every
tool must do *around* the call — the rules
[`agent-tool-implementations.md`](../agent-tool-implementations.md) found
running through every mature harness's source, adopted here as a single
contract rather than restated per tool. Its §12 checklist is the source for
each rule; only the deviations are argued again below.

The rules here are policy. The exact byte-level shape of every result —
block delimiters, the line-number prefix, status vocabulary, how a
partially-failed batch renders, how truncation notes are marked — is
specified in [`formats.md`](./formats.md) §8, which this section assumes
throughout. Both documents describe the agent we want, independent of what
it is built on; where a specific substrate can't deliver something stated
here, the gap and its workaround belong in [`adk.md`](./adk.md), not in a
weakened rule. The one rule worth stating in both places, because everything
else depends on it: **inside a block carrying file content, every content
line is prefixed with its line number and a tab, and no structural line
ever starts with a digit.** That invariant is why no content ever needs
escaping, and why a file containing something that looks like a delimiter
cannot break the frame.

**Three channels per tool.** Every tool produces three things, and they are
built separately: the **model result** (text, per the format policy below),
the **harness record** (a typed object: what changed, what was truncated,
what path was touched — this is what the post-run `git status` cross-check
and the `Complete` report reconcile against), and, where a human is
watching, a **rendering**. Forge's prompts only ever see the first. This is
the split Claude Code makes with `outputSchema` +
`mapToolResultToToolResultBlockParam`, Gemini CLI with
`llmContent`/`returnDisplay`, and MCP with `content`/`structuredContent`.

**The model result is exactly one text block, and nothing else.** Not one
block per file, not a structured field alongside it, not an image, not an
embedded resource. This looks like a transport detail and belongs here
because it isn't one: a tool result crosses a process boundary and is
*projected* into the conversation by client code the tool author does not
own, and every client projects differently. Of the seven projections
compared in [`../agent-tool-result-transport.md`](../agent-tool-result-transport.md)
§3f, three serialise the whole result envelope into the model's context,
two silently discard content types they don't handle, and one errors on
anything that isn't text. A single text block is the only shape that
survives all of them unchanged — the intersection, not a preference. Its
corollaries: the multi-file `Read` result is *one* block containing
several `<file>` sections (`formats.md` §8b), never several blocks;
fact-shaped payloads are named fields **inside** that text, not a
parallel structured channel; and the harness record travels out of band
entirely (`adk.md` §3), because the obvious wire slot for it is the one
clients disagree about most. The rule was derived on ADK (`adk.md` §2)
and bites hardest there, but it is not a substrate workaround and should
not be filed as one.

**Output format policy.** Prose-shaped payloads — file contents, diffs,
search matches, command output — are returned as **raw text**, never
JSON-encoded. Fact-shaped payloads — exit codes, counts, truncation state,
ids, comment URLs — are returned as **named fields** (either a small JSON
object, or `key: value` lines when they accompany prose). No tool returns a
file body inside a JSON string: escaping inflates tokens and breaks the
byte-exact match `Edit` depends on. Untrusted or heterogeneous content
inside a result is delimited with XML-style tags, the same device
`formats.md` §1 uses for the task envelope, for the same reason.

**Every cap is self-describing.** Any truncation, page, or elision appends
a footer stating three things: what was shown, how much exists, and the
exact next call. Not "output truncated" but "showed lines 1-2000 of 8123 —
pass `start_line: 2001` to continue." Three independent implementations
(Gemini CLI's `Action:` block, OpenCode's `Use offset=N to continue`,
Claude Code's pagination note) converge on this, and a cap without a
continuation instruction is the one failure mode that reliably turns into a
retry loop. Notices go at the head or tail of a result, never in an elided
middle, so they survive any later re-truncation.

**Caps by default, errors on impossible explicit requests.** A call that
omits limits and gets a large result is capped and told so. A call that
*explicitly* asks for more than a cap allows fails with a short error
instead of returning a capped success. The reasoning is measured, not
aesthetic: Claude Code tested truncating instead of throwing on exactly
this case (`FileReadTool/limits.ts`, experiment #21841) and reverted —
tool-error rate fell but mean tokens rose, because an error result costs
~100 bytes and a capped success costs a full page of content the model
didn't want.

**Spill, don't dump.** A result past the harness's size ceiling is written
to a file in the scratch directory (`{{SCRATCH_DIR}}`, `formats.md` §1a) and
the model receives a preview plus that path. `Read` is the deliberate
exception — spilling a read to a file the model then reads back is circular — and the exemption extends to every tool that *reads the artifact
store*: `Read` over `artifact://`, and every `InspectImage` op. A tool whose
job is reading artifacts must never mint one (`artifacts.md` §5.1)
— so `Read` self-bounds via its own limits instead.

Two constraints on the spilled file itself, both of which exist because a
spill is a pointer into state with a lifetime of its own:

- **The filename is derived from the invocation's tool-call id**, not
  from a timestamp, a counter, or the command. A transport-level retry
  re-executes the tool (`adk.md` §4), and a retry-safe spill has to
  overwrite the previous attempt's file rather than leave two on disk
  with the model holding a path to whichever one finished last. This is
  the same identifier the idempotency key uses, and once that key is in
  place the retry returns the first attempt's result and path and the
  question stops arising — but the naming rule is what makes the two
  mechanisms agree in the meantime.
- **The preview is a stub, and a stub states shape**: how much exists,
  not just how much was cut, and the exact call that retrieves the rest.
  A path on its own defers the decision without informing it. `formats.md`
  §8e specifies the wording for `Bash`, the only v1 tool that spills.

**Some reads are refused before any I/O, by name *and* by type.** A cap can
only bound a read that *finishes*, so anything unbounded has to be refused
up front, and that takes two independent checks:

1. **A name blocklist.** `Read` (and `List`'s line-counting pass, which
   opens files for the same reason) checks the resolved path against a
   fixed list — `/dev/zero`, `/dev/urandom`, `/dev/random`, `/dev/stdin`,
   `/proc/<pid>/fd/*` — and returns `refused_path` without calling
   `open()`. The working-tree boundary is not a substitute: it doesn't
   apply when the working directory is `/`, and these paths are reachable
   by absolute path regardless.
2. **A `stat` on the resolved path**, refusing FIFOs, sockets, and
   character/block devices whatever they are called. This is the check
   that actually matters, because **a name blocklist cannot see a FIFO
   sitting inside the working tree** — `logs/live.pipe` is an ordinary
   repository-relative path that blocks forever on `open()`. Hermes added
   exactly this guard after its own read-tool eval
   (`agent-tool-implementations.md` §6e) and measured it: on a
   FIFO-in-workspace task, a strong open model spent 122k tokens and up to
   ten minutes of wall clock recovering without the guard versus 26k
   tokens with it (−79% tokens, −81% worst-case wall), and a frontier
   model −43% tokens — with task accuracy unchanged at 1.00 in both arms,
   since both models do eventually recover. The guard is pure efficiency,
   which is precisely why it is easy to ship without and never notice. The false-positive cost is nil — nothing a coding
or review run legitimately does reads `/dev/urandom` through a file-read
tool, and a model that wants entropy has `Bash` — which makes this the
cheapest safety rule in the document, and the only one whose absence is a
denial of service the harness shipped itself
(`agent-tool-implementations.md` §6d).

**Errors are instructions.** Every tool error states what happened, what to
do about it, and — where the harness can compute one — a concrete
suggestion. "File does not exist. Did you mean `src/parser/index.ts`?" beats
"ENOENT". "Found 3 matches for `old_string`; add surrounding lines or set
`replace_all`" beats "ambiguous match". Nothing ever returns silent
emptiness: an empty file, a start line past EOF, and a search with no hits
each say so in words.

**And they travel as tool-execution errors, never as protocol errors.**
Where the transport distinguishes the two — MCP's `isError: true` result
versus a JSON-RPC error — every error this design defines is the first
kind. All of them are things the model can act on, which is the
distinction the MCP specification itself draws: tool-execution errors are
"actionable feedback that language models can use to self-correct" and
clients **SHOULD** pass them to the model, while protocol errors are for
malformed requests and unknown tools and clients only **MAY**. A rule
about what an error *says* is worth nothing if the channel it travels on
lets a client drop it. On the intended substrate there is a second,
sharper reason — a protocol error is an exception, and an exception is
what the client's retry policy keys off, so the design's most frequent
errors would become its most retried ones (`adk.md` §4).

**Advertise strict, accept tolerant.** The schemas below are the advertised
contract and stay strict (`additionalProperties: false`) — a strict schema
is what makes provider-side strict tool-calling and the model's own
pattern-matching work. Tolerance lives entirely in the harness, in four
declared layers, never as ad-hoc rescue code inside a tool.

**All four run *after* validation fails, never before it.** The input is
validated as-is first; if it passes, it is shipped **untouched**, and no
repair ever runs against a well-formed call. Only on failure does the
harness walk the validator's own issue list and try repairs at the paths
the schema actually disagreed at. This ordering is not a detail: a
normalisation pass in front of the validator encodes a prior about what is
broken before anything has said what is broken, and the failure it
produces is silent. Command Code shipped the pre-pass version first and
reverted it after a `write` whose `content` was legitimately JSON-shaped
got rewritten on the way to disk (`agent-tool-implementations.md` §3h) —
which this design is equally exposed to, since `Write.content` and
`Edit.old_string` both routinely carry text that looks like the shapes the
repairs match. Validating first makes the schema the prior and confines
the blast radius to fields that were already wrong.

**Repairs are ordered, and the order is part of the contract.** Within a
failing field, JSON-string parsing runs before scalar-to-array wrapping,
or `'["a","b"]'` becomes `['["a","b"]']` — schema-valid, meaning lost, and
undetectable downstream. Every layer-1 transform below is listed in
application order for this reason.

1. **Generic normalisations**, applied to a failing tool input,
   implemented once: parse an input that arrived as a JSON
   *string* (or fenced in Markdown) rather than an object; coerce
   stringified scalars (`"3"` → `3`, `"true"` → `true`) **whole-string
   only** — `"2abc"` is an error, never a silent `2`, and a fractional
   line number is an error, never floored; treat explicit
   `null` on an optional field as absent; unwrap a one-element array where
   a scalar is expected and wrap a scalar where an array is expected; trim
   whitespace and stray quotes/backticks from path-shaped strings; and
   match keys case- and separator-insensitively against the canonical
   names (`filePath`, `file-path`, `FilePath` → `file_path`).
2. **Per-tool accepted forms** — a short, *declared* list of alternative
   input shapes per tool, each with a pure transform to the canonical
   shape, so they are enumerable and testable rather than scattered. For
   v1 that list is small:

   | Tool | Also accepted | Normalised to |
   |---|---|---|
   | Read | a bare path string; an array of path strings; `{path: …}`; `file_path`/`filePath` per entry; `paths`/`file_paths` instead of `files` | `{files: [{path, start_line?, end_line?}]}` |
   | Read | `offset`/`limit` on an entry | `start_line = offset`, `end_line = offset + limit - 1` |
   | List | a bare glob string | `{pattern: …}` |
   | List | a call named `Glob` with `{pattern, path}` | `{pattern, path, output: "paths"}` |
   | Grep | a bare pattern string; `include`/`file_pattern` | `{pattern}` / `glob` |
   | Bash | a bare command string; `cmd`; `{command, args: []}` | `{command}` |
   | Edit | `old_str`/`new_str`; `path` | `old_string`/`new_string`/`path` |
   | Complete, AddComment, AskUser | nothing — these carry structured reports and post externally; guessing intent here is not recoverable | — |
3. **Clamp, don't reject, on ranges**: `start_line: 0` becomes 1,
   `end_line < start_line` reads one line, a `start_line` past EOF returns
   the explicit past-EOF marker rather than an error. (Zed does exactly
   this in code, with a comment noting the model "occasionally passes 0
   despite instructions to be 1-indexed.")
4. **Repair, inside the tool, the failures the model cannot see.** A
   missing path is retried against a small fixed set of Unicode
   respellings before it is allowed to fail — NFC ↔ NFD, narrow no-break
   space ↔ regular space, straight ↔ curly apostrophe, and NFD+curly —
   because these render *identically* in a terminal and in a diff, so a
   model that copied the name off the screen has no evidence to reason
   from and will retype the same wrong bytes indefinitely. macOS supplies
   all three variants natively (NFD-decomposed storage, a narrow no-break
   space before AM/PM in screenshot names, Finder's curly-quote renames),
   so this is ordinary traffic, not an edge case. **Every candidate is
   re-validated against the working-tree boundary**, not just the original
   — a repair layer that resolves paths must not become a traversal
   primitive. Only after all candidates miss does the read fail, with the
   did-you-mean suggestion described under `Read` below.

Two rules that cut across all four layers, both from the production
catalogue in `agent-tool-implementations.md` §3h:

- **Encode a field's destination in its type, not in its description.** A
  path parameter is declared as a path type rather than a bare string, so
  every path field on every tool gets the same repairs at once — trimming
  quotes and backticks, and unwrapping the degenerate markdown auto-link
  (`[notes.md](http://notes.md)`, where the link text equals the URL minus
  its protocol) that some models emit because chat formatting leaks across
  the tool boundary. Real markdown links pass through untouched. The
  general form: where a family of parameters shares a destination, give
  them a shared type and repair the family, not the instance.
- **Where fields are individually valid but jointly wrong, extend the
  semantics rather than erroring, and say what you did.** No input repair
  can see a relational problem, because every field validates. `Read`'s
  accepted `offset`/`limit` pair is the case here: `limit` alone means
  `start_line: 1`, `offset` alone means "to the default line cap." The
  chosen default is stated in the result as a `!` note — not an error —
  so the model sees what was picked and can correct on the next call.

The sorting rule behind items 3 and 4, worth stating because it decides
future cases: **repair silently what the model has no evidence to fix, and
suggest what it does.** A misspelled path is visible in the transcript, so
the tool hands back a suggestion and lets the model choose; a path
differing by a codepoint that renders identically is not, so the retry
happens inside the tool before any error text exists.

Two limits keep this from becoming a pile of hidden formats.
**Normalise only when the transform is information-preserving and
unambiguous** — the operative test being whether a repair can produce a
*plausible wrong answer* rather than an obvious failure. `filePath` →
`file_path` cannot: the transform is reversible and means one thing.
`parseInt("2abc")` → `2` can: it invents a value the caller never supplied,
the read then succeeds, and nothing downstream ever learns it was wrong.
A silently wrong window is worse than an error, which is why the coercion
above is whole-string and why clamping is confined to ranges, where 0 and
an inverted pair each have exactly one plausible intent. A bare string for
`Read` has one plausible meaning, but an
unrecognised key that might carry real intent (a `recursive: true` on a
tool with no such behaviour) is an *error naming the unknown key*, because
proceeding would silently do something other than what was asked. And
**every normalisation is counted**, per `(model, tool)` pair and split
into repaired-and-ran versus failed-and-returned: a fired alternate means
either the description or the schema is wrong for this model, so the
telemetry is the input to fixing it upstream — and a repair rate that
moves on one contract is how a model regression surfaces before users
report it — promote a frequent alternate into the
advertised schema, and delete one that never fires. Both directions are
observed in the field: Cline's SDK parses `read_files` against a
thirteen-branch union while advertising one shape, and OpenCode *removed*
its numeric coercion once the tool became LLM-only, with a code comment
explaining it no longer earned its keep.

One implementation detail worth copying: normalisation must not silently
rewrite what the permission layer and the transcript see. Claude Code
applies its input backfill to *copies* — "before observers see it (SDK
stream, transcript, canUseTool, PreToolUse/PostToolUse hooks)... The
original API-bound input is never mutated (preserves prompt cache)." Forge
follows the same rule: the normalised input is what gets logged, gated and
reported; the original is what stays in the conversation the model sees.

**Line numbering is one contract shared by Read and Edit.** `Read` returns
`cat -n`-style output: the 1-indexed line number, a tab, then the line's
exact bytes. `Edit`'s `old_string` matches against the bytes *after* the
tab. These two facts are a single decision — changing the prefix format
means changing both tools' descriptions in the same edit — and both
descriptions below state it explicitly, because echoing the prefix back
into `old_string` is the most common way an exact-match edit fails.

**Tool results are an injection point.** Two things ride along with results
rather than living in the system prompt: when `Read` returns a file that has
a project-conventions file governing its directory, that file's content is
appended inside a `<system-reminder>` block (OpenCode, Gemini CLI and Claude
Code each do a version of this); and any content originating outside the
repository is sanitized before it lands, per `formats.md` §1.

**Read-before-edit is harness-side state, and the state is *what was
seen*.** `Edit` and `Write` fail on a path this run has not `Read` (for
`Write`, only when the file already exists), enforced by a per-run
read-state cache rather than by prompt text — the same structural-gate
principle as the git-write blocklist. That cache is also what a later
unchanged-file read dedup would be built on (`medium.md` §2g); v1 keeps
the cache and not the dedup.

The cache entry is **not a boolean**. Per path it records the bytes
returned, `(mtime, size)` at read time, and whether the view was
**partial** — a range read, a line-window truncation, a line the per-line
clamp cut, or an **outlined** read (below), which is the most partial view
of all and the easiest to mistake for a complete one. That distinction is what the two gates actually need,
and they need different answers from it:

- **`Edit` accepts a partial view.** Its `old_string` must match the file
  byte-for-byte and uniquely, so the match anchors the change to bytes
  that demonstrably exist; content the model never saw is not at risk.
- **`Write` requires a *full* view** — replacing a file wholesale after
  seeing 50 of its 2,000 lines destroys 1,950 lines the model never read,
  and a gate that only asks "was this path read at all" waves that
  through. The check that decides it is byte equality, not the partial
  flag: a `Write` is permitted when the cache's recorded content matches
  what is on disk *now*, which a clamped-but-complete read satisfies (the
  clamp affects what was *displayed*; the cache records the raw bytes) and
  a 50-line window does not. Where it fails, the error names the actual
  state — "only part of this file has been read; re-read it in full before
  replacing it" — rather than the misleading "has not been read yet."

Both refinements come from a production deadlock reported by Command Code
(`agent-tool-implementations.md` §8b) in a harness with this design's exact
combination of features: a per-line clamp marks a read partial → the write
gate refuses → the model re-reads → a dedup returns "unchanged" → forever.
Every field in every call was valid; the invariant that broke lived
*between* three tools. The deadlock needs all three of clamp, gate and
dedup to close, so v1 (no dedup) cannot hit it — but v1 is the version that
gets the state shape right, because §2g's dedup lands on top of this cache
and inherits whatever it recorded.

**Per-tool harness metadata.** Every tool declares, in code, whether it is
read-only, whether it is safe to run concurrently with another call, and
whether it is destructive. These are what `plan`-mode wiring, parallel
dispatch, and the completion gate key off — not prompt text. For v1:

| Tool | Read-only | Concurrency-safe | Destructive |
|---|---|---|---|
| Read, Grep, List, FetchJira | yes | yes | no |
| Edit, Write | no | only for disjoint paths | no |
| Bash | unknown (assume no) | no | assume yes |
| Task | inherits the child's wiring | yes | no |
| AddComment | no (external) | no | yes (a post is not retractable) |
| AskUser, Complete | terminal | n/a | n/a |

"Assume no / assume yes" is the fail-closed default every source surveyed
uses for an unclassifiable shell.

**The tool set is configuration, not a constant.** Nothing in this document
should be read as "these eleven tools, this text, for every model." Gemini
CLI ships per-model-family schemas and descriptions for identical tools;
Cline routes `apply_patch` to GPT/Codex-family models and a string-replace
editor to everything else. Forge's v1 ships one set because it targets one
model family; the descriptions below are the artifact a per-model variant
would fork, and `medium.md` tracks the edit-format fork as the first likely
one.

---

## Configuration and defaults

Every number in this document is a **default, not a constant** — and every
number that appears in a tool *description* is rendered from the same
config value the code enforces, so the prose cannot drift from the
behaviour. Crush is the precedent worth copying literally: its tool
descriptions are Go templates (`view.md.tpl`: "…default
`{{ .DefaultReadLimit }}`, max `{{ .MaxViewSizeKB }}`KB…") evaluated
against the real constants. Claude Code composes its `Read` description
the same way, from limits resolved at startup.

The defaults below are opinionated. Where the field converged, the
convergent value wins; where it didn't, the value is chosen and the
reasoning stated, because "make it configurable" is not a decision and a
deployment that has to pick eleven numbers before it can start has been
handed a problem rather than a design.

### Tunables

| Key | Default | Why this value |
|---|---|---|
| `read.default_lines` | 2000 | Claude Code, OpenCode and Cline independently converged on 2000; Crush's 200 is the outlier and reflects an interactive UI where a human scrolls, not an unsupervised run that pays a turn per re-read |
| `read.max_line_chars` | 2000 | Universal across every source read. Minified and generated files are the target; a legitimate source line never approaches it |
| `read.max_entry_bytes` | 65,536 (64 KB) | Enforced by **whole lines** — the read stops before the first line that would exceed the budget, never cutting inside one, which is what keeps the byte ceiling from splitting a codepoint or shifting the resume point (`formats.md` §8b). The middle of the three ceilings, and the one this design originally skipped. The line window bounds a file with *many* lines and the per-line clamp bounds a *single* wide line; neither bounds a file whose lines are merely wide — 2,000 lines of 900 characters clears both caps and returns 1.8 MB (`agent-tool-implementations.md` §6b). The value deviates from Command Code's 128 KB and OpenCode's 50 KB deliberately: this `Read` is a batch tool, so a per-entry ceiling above `read.call_budget_chars` would never bind. 64 KB lets one large file take most of a call without letting it take more than the call has |
| `read.summarize` | on | A whole-file read of a large source file returns its **declarations with bodies elided** rather than its first 2000 lines. OMP's default, and the only source that does this; it fits a turn-budgeted hands-off agent better than the interactive tools it came from, because the alternative to a skeleton here is not "the human scrolls" but "the model spends a turn discovering the file was the wrong one" |
| `read.summarize.min_lines` | 100 | Below this a file is cheaper to return whole than to summarise and then re-read in pieces. OMP's value |
| `read.summarize.max_bytes` | 2,097,152 (2 MiB) | Summarising means parsing. Past this, fall back to the ordinary windowed read rather than paying to parse a generated file |
| `read.max_entries` | 20 | New here — no source has a batch read to cap. Past ~20 files the model is fanning out rather than reading, which is what `List`/`Grep` are for, and a 200-entry call would blow the call budget before the first file finished |
| `read.call_budget_chars` | 80,000 (≈20k tokens) | A batch should not cost more than one large single read. Claude Code caps a single read at 25,000 tokens; Cline caps at 48,000 chars per read. This sits between them and is measured in characters deliberately — a real tokenizer call per read is a round trip the gate does not justify |
| `read.file_size_gate_bytes` | 262,144 (256 KB) | Claude Code's value. This is the *explicit-request* gate: past it a read errors instead of truncating, per the implementation contract |
| `list.default_depth` | 3 | Deep enough that one call shows a typical `src/<area>/<file>` layout, shallow enough that a monorepo root doesn't blow the entry cap. Below 3, the first call is almost always followed by a second |
| `list.max_entries` | 200 | Roughly the point at which a tree stops being an orientation aid and becomes something to search instead. Crush caps its `ls` similarly (its own value is templated into its description, so the model always knows) |
| `list.line_counts` | on | The counts are what make the tree an input to the whole-file-vs-range decision `Read` asks for. Goose keeps exactly this in a five-tool surface |
| `list.line_count_max_bytes` | 1,048,576 (1 MB) | Counting lines means reading the file. Above this, show `-` rather than pay the IO |
| `list.line_count_max_entries` | 500 | If a listing has more entries than this, counts are dropped wholesale with a `!` note. A 5,000-file listing should not trigger 5,000 file reads for a number nobody will read |
| `grep.head_limit` | 250 | Claude Code's default. Gemini CLI's 100 is stated in its description too; 250 is the more generous of two converged-on values and pages cleanly with `offset` |
| `grep.max_line_chars` | 2000 | Same reasoning as `read.max_line_chars`, and the same value so the model only learns one number |
| `grep.context_before` / `grep.context_after` | 0 | Context is cheap to ask for and expensive to receive by default; ripgrep's own default is 0 |
| `bash.timeout_ms` | 120,000 (max 600,000) | Already in the Bash schema; matches the field's common shape |
| `bash.output_cap_chars` | 30,000 | OpenHands's `MAX_CMD_OUTPUT_SIZE` exactly; Cline's 48,000 is the nearest neighbour. Head and tail are kept, the middle is elided, and the full output always spills to scratch |
| `spill_threshold_chars` | 30,000 | Any tool result past this is written to scratch and previewed, per the implementation contract — except `Read`, which is exempt because spilling a read to a file the model then reads back is circular |
| `vision.max_dimension` | 2000 | Longest edge an image is downscaled to before it reaches the model. Claude Code's `IMAGE_MAX_WIDTH/HEIGHT`; OpenHands's many-image ceiling is the same number. The scale factor is always disclosed in the frame (`vision.md` §3d) |
| `vision.max_bytes_encoded` | 5 MB | Per-image cap after encoding. Claude Code's `API_IMAGE_MAX_BASE64_SIZE`; Cline's is identical |
| `vision.max_pinned_images` | 2 | Images held in context beyond the turn that loaded them. A pinned mockup plus a pinned annotated flow is a plausible specification; five is a context leak. Exceeding it is an error naming which to release |
| `vision.model` | (a small, fast sighted model) | The sub-model `InspectImage`'s `ask` op calls — single-turn, no tools. Unset disables `ask` and `view`, and both drop out of the advertised schema (`vision.md` §6) |
| `artifacts.max_fetch_bytes` | 25 MB | Cap enforced on the response stream when fetching attachment bytes, before decode (`artifacts.md` §6) |
| `tolerance.enabled` | on | The alternate-forms table above is data, so a deployment can prune it; turning tolerance off entirely is available and is the wrong default, per the decision log |

Three derived rules the harness validates at startup, rather than trusting
the config: `read.max_entry_bytes` must not exceed `read.call_budget_chars`,
or the per-entry ceiling never fires and a single wide file is cut by the
batch rule instead — which truncates whole entries and so would return
nothing at all for a one-file call; `read.max_line_chars` ×
`read.default_lines` should be recognised as *not* a bound (it is 4 MB at
the defaults, which is the whole reason the byte ceiling exists) so no rule
is written against it; and no cap may be set to zero, which would make a
tool silently return nothing. Claude Code validates each of its limit fields
individually and falls back to the hardcoded default on anything invalid,
with a comment noting there is deliberately "no route to cap=0" — the same
posture applies here.

### Precedence

Built-in default → model-family profile → deployment config → per-run
override, each layer setting only what it means to change. The per-run
layer exists because run shapes genuinely differ (a review run reading
around a large diff wants more read budget than a small `plan` run), but
**it does not appear in the task envelope**: Forge learns the effective
limits the way it learns everything else about a tool — from the
description text rendered for this run, and from the footers on results
that hit a cap. There is no configuration the model reads and reasons
about, which keeps `formats.md` §1 unchanged and keeps the model from
negotiating with its own limits.

### What is deliberately *not* configurable

Being opinionated cuts both ways. These are contracts other things depend
on, and a deployment that could flip them would produce combinations no
one has tested:

- **The `cat -n` prefix format** (`<decimal><TAB>`) — `Edit`'s matching
  rule is written against it, so a deployment that "just" padded line
  numbers would break editing.
- **The block framing and escaping invariants** (`formats.md` §8a),
  including line-ending normalisation on read and restoration on write.
- **The per-entry status vocabulary**, request-order blocks, and
  partial-failure-never-fails-the-call.
- **Caps must self-describe** — a deployment may change *what* the limit
  is, never whether the result says it was hit and how to continue.
- **Read-before-edit** (including the full-view requirement on `Write`),
  and the git-write blocklist.
- **The refused-path list**, which a deployment may extend and may never
  empty — it is the only defence against a read that never returns, and a
  configurable-to-zero denial of service is not a tunable.

The line between the two lists is exactly the model channel versus the
harness channel: numbers are facts the model is told at the moment they
matter, so they can vary; formats are contracts it was trained on across a
whole run, so they cannot.

---

## Read

> Reads one or more files from the working tree. Paths are absolute, or
> relative to the working directory named in `<env>`.
>
> A path may be any **ref** — one address space covers the working tree,
> other repositories at a pinned ref, dependency source, stored artifacts
> and past runs, and all of them read the same way:
>
> | Ref | What it names |
> |---|---|
> | `src/parser/index.ts` | a file in the working tree — the common case, and the shortest form |
> | `file:///tmp/.../repro.py` | an absolute local path, scratch directory included |
> | `git://acme/payments@a1b2c3d/src/Bill.java` | a file in another repository at a branch, tag or commit |
> | `dep://com.acme:billing:4.2.1/com/acme/Bill.java` | source of a dependency of this build |
> | `artifact://txt_04d1e8f2` | a stored payload — an attachment, or an earlier result too large to inline |
> | `run://2026-08-14T09-22Z-7f3a/transcript` | a past run |
>
> **Read local first, always.** A remote scheme is for code that is *not*
> in the tree, never a second way to read code that is — it costs a
> network round trip where a path costs nothing. A read against a moving
> ref (`@main`) reports back the commit it actually resolved to.
>
> **Anything readable comes back as text.** A PDF returns its text (pages
> selectable), a spreadsheet its sheets, a `.docx` its prose, an image the
> text in it, an archive its member list. The result always says which
> conversion happened — an OCR'd screenshot and a PDF with a real text
> layer are not equally trustworthy, and you need to know which you got.
> Append `:raw` to any ref to skip conversion.
>
> Selectors narrow a read and go on the end of the ref: `:120-260` for
> lines, `:p4-6` for PDF pages, `:Sheet2` or `:Sheet2!A1:D80` for a
> spreadsheet, `:path/inside` for an archive member. A line range may also
> be given as `start_line`/`end_line` on the entry, which is the same
> thing.
>
> **A large result comes back as a reference, not a wall of text.** You
> get a preview plus an `<artifact>` block naming the whole thing, and the
> note tells you the exact next call — `Read artifact://txt_x:2001-4000`.
> That reference is a snapshot: paging through it cannot be disturbed by
> the underlying file changing under you. Images are the one thing you
> cannot page this way — use `InspectImage` to look at one.
>
> **Read several files in one call** whenever you already know what you
> need — a caller and its callee, a module and its test, every file a
> review finding touches. One call with five entries costs a fraction of
> five calls, and this agent's run budget is counted in turns.
>
> Each entry may carry `start_line`/`end_line` to read only part of that
> file. The range belongs on the **same object as the path it applies to** —
> `{"path": "src/a.ts", "start_line": 40, "end_line": 120}` — never as a
> separate element of the array. Line numbers are 1-indexed and inclusive,
> and they are the same numbers the results, Grep hits, and diff hunks
> show you, so a range around a known line needs no arithmetic. Omit both
> to read the whole file.
>
> Contents come back in `cat -n` format: the 1-indexed line number, a tab,
> then the line exactly as it appears in the file. Everything after the tab
> is the real content — when you later pass a span of this output to Edit
> as `old_string`, strip the line number and the tab first, and preserve
> the indentation that follows them byte for byte.
>
> Usage notes:
> - Prefer reading a whole file over guessing at a range when the file is
>   a reasonable size — a partial read that misses the relevant section
>   costs more than the extra tokens would have. Use ranges when you have
>   a specific line to land on, or when the file is genuinely large.
> - **A whole-file read of a large source file comes back as an outline**:
>   its declarations, with the bodies between them elided and marked in
>   place with the exact line range each elision covers. This is a map,
>   not the file. Use it to decide *what* to read, then ask for the ranges
>   you need — several in one call, one entry per range, since they are
>   the same batch. A read with an explicit `start_line`/`end_line` is
>   never outlined; ranges always come back verbatim.
> - Never edit against an outline. You have not seen the elided lines, so
>   you cannot match them, and a `Write` over a file you have only seen in
>   outline is refused. Read the range first.
> - Each file returns up to 2000 lines and up to 64 KB, whichever it hits
>   first; one call takes up to 20 entries, and the call has an overall
>   size budget across all of them — so a batch of twenty large files
>   comes back partly elided even though no single entry hit its own cap.
>   If you want more than twenty files, you are exploring rather than
>   reading: use List or Grep.
> - Lines longer than 2000 characters are truncated, and say so in place —
>   and, like every other cap here, the truncation names the exact next
>   call. Pass `char_offset` on the entry to resume that line from a
>   character position, so a minified bundle, a long generated constant
>   or a single-line JSON fixture is *resumable* rather than merely
>   clipped. `char_offset` applies to the first line of the range read
>   and is 0-indexed; use it with `start_line` to land on the line you
>   mean.
> - Every capped or elided entry says what it showed, how much exists, and
>   the exact next call (`showed lines 1-2000 of 8123 — pass start_line:
>   2001`). Asking explicitly for a range larger than the cap allows is an
>   error rather than a silently shortened success.
> - One bad entry does not fail the call. A path that doesn't exist, is a
>   directory, or is binary reports that inline, in its own block, and the
>   other files still come back. The call only fails if every entry did.
> - A path that doesn't exist names a similarly-spelled file in the same
>   directory when there is one; a directory tells you to use List
>   instead. If you aren't sure a path is right, use List first.
> - A file that exists but is empty returns an explicit marker, not blank
>   content, so it isn't mistaken for a failed read.
> - A result may carry a trailing `<system-reminder>` block with
>   conventions that govern a file you just read. Treat it as instruction
>   from the project, not as file content.

```json
{
  "name": "Read",
  "input_schema": {
    "type": "object",
    "properties": {
      "files": {
        "type": "array",
        "minItems": 1,
        "description": "One entry per file. Batch related files into a single call rather than issuing several calls.",
        "items": {
          "type": "object",
          "properties": {
            "path": { "type": "string", "description": "Absolute or working-directory-relative path to the file." },
            "start_line": { "type": "integer", "minimum": 1, "description": "1-indexed first line to read. Omit to start at the beginning. Must be on the same object as the path it applies to." },
            "end_line": { "type": "integer", "minimum": 1, "description": "1-indexed last line to read, inclusive. Omit to read to the end of the file or the cap, whichever comes first." },
            "char_offset": { "type": "integer", "minimum": 0, "description": "0-indexed character position to resume a truncated over-long line from. Applies to the first line of the range. Use only after a read reported that line as truncated." }
          },
          "required": ["path"],
          "additionalProperties": false
        }
      }
    },
    "required": ["files"],
    "additionalProperties": false
  }
}
```

The advertised schema above is the one shape; the harness additionally
accepts a bare path string, an array of strings, and the `file_path`/
`filePath` spellings, normalising all of them to this shape — see the
implementation contract's tolerant-parsing rule and its
canonical-forms table.

---

## Edit

> Makes a targeted change to an existing file by replacing one exact,
> contiguous span of text with another.
>
> `old_string` must match the file's actual current content byte for
> byte — same whitespace, same line endings — and must be **unique**
> within the file. If it matches more than once, the call fails rather
> than guessing which occurrence you meant; include enough surrounding
> context (a few lines before/after the change, not just the changed
> line) to make it unambiguous — usually two to four adjacent lines is
> enough, and ten is a sign you should be editing somewhere more specific.
>
> Read the file (or the relevant section of it) before editing it: this
> tool fails on a path you have not Read in this run, because an
> `old_string` written from memory is the single most common way an edit
> fails. Read returns `cat -n` output — line number, tab, content — so
> when you build `old_string` from what you just read, drop the number and
> the tab and keep everything after them unchanged. Never include any part
> of that prefix in `old_string` or `new_string`.
>
> Set `replace_all: true` to replace every occurrence instead of
> requiring uniqueness — use this for a deliberate rename across a file,
> never as a workaround for an `old_string` you couldn't make unique.
>
> To insert new content, include a line of existing surrounding context
> in `old_string` and repeat it (extended) in `new_string`. To delete,
> set `new_string` to the content that should remain, omitting the
> deleted span. This tool cannot create a new file — use Write for that.

```json
{
  "name": "Edit",
  "input_schema": {
    "type": "object",
    "properties": {
      "path": { "type": "string", "description": "Absolute or working-directory-relative path to an existing file." },
      "old_string": { "type": "string", "description": "The exact text to replace. Must uniquely match within the file unless replace_all is set." },
      "new_string": { "type": "string", "description": "The text to replace it with. Must differ from old_string." },
      "replace_all": { "type": "boolean", "description": "Replace every occurrence of old_string instead of requiring a unique match. Default false." }
    },
    "required": ["path", "old_string", "new_string"],
    "additionalProperties": false
  }
}
```

---

## Write

> Creates a new file, or fully overwrites an existing one.
>
> Prefer Edit for any change to a file that already has content worth
> preserving — Write replaces the entire file, so using it on an
> existing file discards everything not repeated in `content`. Use Write
> for genuinely new files, or when a rewrite is so extensive that
> reconstructing it via Edit calls would be less reliable than writing
> it fresh. Overwriting a file you have not Read **in full** in this run
> fails — a range read or a truncated read is not enough, because the
> lines you never saw are exactly the ones a rewrite would destroy.
> Creating a new file has no such requirement.
>
> Only write into the repository working tree for files meant to be
> part of the actual change. Anything throwaway — a reproduction
> script, a scratch note, exploratory output — goes in the scratch
> directory named in `<env>` instead, never in the repository, even
> temporarily (see the coding system prompt's workflow, step 2).

```json
{
  "name": "Write",
  "input_schema": {
    "type": "object",
    "properties": {
      "path": { "type": "string", "description": "Absolute or working-directory-relative path." },
      "content": { "type": "string", "description": "The full file contents to write." }
    },
    "required": ["path", "content"],
    "additionalProperties": false
  }
}
```

---

## Bash

> Executes a command in a persistent shell session (state — cwd,
> environment variables, background jobs — carries over between calls
> within one task).
>
> Usage notes:
> - Use this for git, running tests/linters, package-manager commands,
>   and anything else with no dedicated tool. Do not use it for search
>   or plain file reads — use Grep/List/Read instead; they're faster and
>   don't spend context on output you don't need.
> - Quote paths containing spaces.
> - Default timeout is 120000ms; pass `timeout_ms` up to 600000 for a
>   command that legitimately needs longer.
> - Set `run_in_background: true` for a long-running process (a dev
>   server, a watch task) you need to keep running while you do other
>   work. The tool result returns the process id and the path of a log
>   file (in the scratch directory) its output streams to; check on it
>   with ordinary shell commands in later calls — the session is
>   persistent, so `kill -0 <pid>` answers "still running?" and Read on
>   the log file (or `tail` of it) shows progress. There is no separate
>   polling tool in v1.
> - Output over 30000 characters comes back with its head and tail intact
>   and the middle elided; the full output is written to a file in the
>   scratch directory and the result names that path, so you can Read the
>   part you actually need. If you already know the output will be large
>   and you only want a slice of it, filter in the command itself
>   (`| tail -50`, `| grep …`) rather than spending a Read on it.
>   Never redirect command output into the repository working tree.
> - The result echoes the command, reports the exit code as a named
>   field, and interleaves stdout and stderr in the order the process
>   wrote them, the way a terminal would. A command that prints to
>   stderr and exits 0 succeeded; check the exit code, not the presence
>   of output. Redirect explicitly (`2>/dev/null`, `2>&1 | tee`) if you
>   need the streams separated.
> - Before a command that creates a new directory or file, confirm the
>   parent exists (List or a quick `ls`) rather than assuming.
>
> Git in v1: read-only inspection only (`status`, `diff`, `log`,
> `blame`, `show`) to understand what's already changed and orient
> yourself in the repository's history. Never run a git command that
> writes repository or branch state — `commit`, `add`, `push`,
> `branch`, `checkout`, `reset`, `merge`, `rebase`, or anything
> equivalent. The task's target branch is already checked out before
> your run starts; leaving a finished, uncommitted working tree is the
> entire delivery mechanism (see the coding system prompt's workflow) —
> whatever invoked you owns turning it into a commit.
>
> The git-write rule is not only prompt text: the harness rejects Bash
> commands matching git write subcommands before they reach the shell,
> returning an error naming the rule. This is a narrow substring/
> pattern blocklist on one command family, not a general permission
> engine (that stays deferred — `medium.md`'s escalation triggers): the precedent is Augment
> SWE-bench Agent's hardcoded `banned_command_strs` check, the only
> code-level git restriction found anywhere in this repo's collection
> (`agent-git-vcs.md` §2), and it's a few lines of harness code
> protecting the design's single most load-bearing invariant. Like any
> blocklist it's bypassable in principle (a git write can be laundered
> through a script), so the prompt rule and the post-run `git status`
> cross-check remain as the layers around it — but the common case
> can't happen by accident or by prompt injection naming the command
> directly.

```json
{
  "name": "Bash",
  "input_schema": {
    "type": "object",
    "properties": {
      "command": { "type": "string", "description": "The shell command to execute." },
      "description": { "type": "string", "description": "A 5-10 word description of what this command does." },
      "timeout_ms": { "type": "integer", "description": "Maximum time to allow, up to 600000. Defaults to 120000." },
      "run_in_background": { "type": "boolean", "description": "Run without blocking; poll for output separately. Default false." }
    },
    "required": ["command"],
    "additionalProperties": false
  }
}
```

---

## Grep

> Searches file contents using ripgrep's regex syntax. Prefer this over
> Bash for any content search — it's faster and its output is
> pre-shaped for you.
>
> - `output_mode: "files_with_matches"` (default) returns matching file
>   paths only; `"content"` returns matching lines, always prefixed with
>   their 1-indexed line numbers (no flag needed) and supporting
>   `context_before`/`context_after`; `"count"` returns per-file match
>   counts.
> - Filter with `glob` (e.g. `"*.ts"`) or `type` (e.g. `"python"`).
> - Patterns are ripgrep regex, not shell-glob — escape literal braces
>   (`interface\{\}`) etc.
> - `multiline: true` lets `.` match newlines, for a pattern that spans
>   lines.
> - Results are capped at 250 entries unless you set `head_limit`
>   (equivalent to `| head -N`); `offset` skips that many entries first
>   (equivalent to `| tail -n +N | head -N`), so a search with more hits
>   than fit can be paged rather than re-run with a narrower pattern you
>   had to guess at. When the cap applies, the result says so and gives
>   the `offset` to continue from.
> - A search with no matches says so; it never returns an empty result.

```json
{
  "name": "Grep",
  "input_schema": {
    "type": "object",
    "properties": {
      "pattern": { "type": "string", "description": "Regex pattern to search for." },
      "path": { "type": "string", "description": "File or directory to search. Defaults to the working directory." },
      "glob": { "type": "string", "description": "Glob to filter which files are searched, e.g. \"*.ts\"." },
      "type": { "type": "string", "description": "File type filter, e.g. \"python\", \"go\"." },
      "output_mode": { "type": "string", "enum": ["content", "files_with_matches", "count"], "description": "Defaults to files_with_matches." },
      "context_before": { "type": "integer", "description": "Lines of context before each match. Content mode only." },
      "context_after": { "type": "integer", "description": "Lines of context after each match. Content mode only." },
      "case_insensitive": { "type": "boolean" },
      "multiline": { "type": "boolean", "description": "Allow . to match newlines for cross-line patterns." },
      "head_limit": { "type": "integer", "description": "Cap the number of results returned, equivalent to \"| head -N\". Defaults to 250." },
      "offset": { "type": "integer", "description": "Skip this many results before applying head_limit, equivalent to \"| tail -n +N | head -N\". Defaults to 0." }
    },
    "required": ["pattern"],
    "additionalProperties": false
  }
}
```

---

## List

> Lists paths in the working tree. One tool covers the three things you
> actually want from a filesystem: *what is in this directory*, *what does
> this part of the repository look like*, and *where is the file called
> roughly this*. Use Grep instead when you know what's **inside** a file
> rather than what it's called.
>
> - `output: "tree"` (the default) renders a directory tree with a line
>   count beside each file. This is the orientation view — read it before
>   reading files, and use the line counts to decide whether a file is
>   small enough to Read whole or wants a range.
> - `output: "paths"` returns a flat list of matching paths, most recently
>   modified first. This is the view to use when you're feeding paths into
>   a batch Read, or when "what changed lately" is the question.
> - `pattern` filters by glob against repository-relative paths
>   (`"src/**/*.tsx"`, `"**/*parser*"`). Omit it to list everything under
>   `path`.
> - `depth` bounds how far the tree descends; it defaults to 3, which is
>   deep enough to show a typical `src/<area>/<file>` layout and shallow
>   enough that a large repository still fits. Going deeper should be a
>   decision you make after seeing the top of it.
> - Hidden files, common build/vendor directories, and anything the
>   repository's ignore rules exclude are skipped unless you set
>   `include_ignored: true`. Node modules and build output are almost never
>   what you meant.
> - Results are capped at 200 entries; `head_limit`/`offset` page through
>   them on the same terms as Grep. When entries are elided, the result
>   says how many, at what depth, and what to pass to see them —
>   narrowing with `path` or `pattern` is usually better than raising the
>   limit.

```json
{
  "name": "List",
  "input_schema": {
    "type": "object",
    "properties": {
      "path": { "type": "string", "description": "Directory to list under. Defaults to the working directory." },
      "pattern": { "type": "string", "description": "Optional glob filtering which paths are listed, e.g. \"src/**/*.tsx\"." },
      "output": { "type": "string", "enum": ["tree", "paths"], "description": "\"tree\" (default) renders a directory tree with per-file line counts; \"paths\" returns a flat list, most recently modified first." },
      "depth": { "type": "integer", "minimum": 1, "description": "Maximum directory depth to descend in tree mode. Defaults to a shallow value." },
      "include_ignored": { "type": "boolean", "description": "Include hidden files and paths excluded by the repository's ignore rules. Default false." },
      "head_limit": { "type": "integer", "description": "Cap the number of entries returned, equivalent to \"| head -N\"." },
      "offset": { "type": "integer", "description": "Skip this many entries before applying head_limit. Defaults to 0." }
    },
    "additionalProperties": false
  }
}
```

No field is required: `List` with no arguments is "show me this
repository," which is the call a run's first investigation step wants.

This tool replaces the `Glob` in earlier drafts, and folds in the
directory listing that would otherwise have needed either an `LS` tool or
a `Bash ls` (the latter unavailable to review sub-agents, which have no
`Bash` at all). The merge follows the implementation contract's splitting
rule: globbing, listing and tree-walking are all read-only,
concurrency-safe, non-destructive, and produce the same thing — a set of
paths — so they differ only in rendering, which is a parameter, not a
tool. The precedent for keeping the tree specifically: Goose cuts its
whole developer surface to five tools with no read, grep or glob among
them, and `tree` ("list a directory tree with line counts") is one of the
five, with its extension instructions telling the model to start there to
understand "the codebase structure and file sizes"; Crush's `ls` is a tree
too. Per-file line counts are worth their cost here because they feed the
whole-file-vs-range decision `Read` asks the model to make.

Because models trained around other harnesses reach for `Glob` by name,
the harness accepts `Glob` as an alias for this tool and maps its
`pattern`/`path` arguments onto the equivalent `List` call with
`output: "paths"` — the same backwards-compatibility affordance Claude
Code's own tool contract carries an `aliases` field for.

---

## Task

> Launches a sub-agent to handle a self-contained piece of work in its
> own context window, returning only its final report to you. Each
> invocation is stateless — you cannot send it a follow-up message, and
> it cannot ask you anything mid-task, so `prompt` must be a complete,
> self-contained brief including exactly what you want back.
>
> Available `subagent_type` values depend on which orchestrator is
> calling: `general-purpose` (coding mode only — full tool parity,
> for open-ended search/investigation you're not confident a direct
> Read/Grep/List will resolve quickly); `reviewer` (review mode only —
> read-only, takes a `role` field selecting which lens to review
> through); `validator` (review mode only — read-only, checks exactly
> one candidate finding).
>
> Usage notes:
> - Launch multiple independent sub-agents in the same turn rather than
>   one at a time — review mode's specialist and validator steps always
>   do this. The harness caps how many run concurrently (a small fixed
>   number; Codex CLI's default of 16 and OpenHands's 5-8 are the
>   field's code-enforced precedents — `agent-subagent-architectures.md`
>   §5) and queues the rest, so a validator fan-out larger than the cap
>   is safe to dispatch in one turn — it just won't all run at once.
> - Never launch two sub-agents in the same turn if their write targets
>   could overlap (only relevant for `general-purpose`, since `reviewer`/
>   `validator` never write). If you're not sure their file sets are
>   disjoint, run them sequentially instead.
> - A sub-agent's report should generally be trusted for `general-purpose`
>   research tasks. For `reviewer` output specifically, treat it as a
>   *candidate* only — that's what the validator step is for; don't
>   act on a specialist's finding directly.
> - `general-purpose` cannot itself call Task — no recursive delegation
>   in v1 (see `future.md`'s "Addressable/resumable sub-agents" entry).

```json
{
  "name": "Task",
  "input_schema": {
    "type": "object",
    "properties": {
      "subagent_type": { "type": "string", "enum": ["general-purpose", "reviewer", "validator"] },
      "description": { "type": "string", "description": "A short (3-5 word) label for this call." },
      "prompt": { "type": "string", "description": "The complete, self-contained task for the sub-agent, including exactly what it should return." },
      "role": { "type": "string", "enum": ["bugs", "security", "conventions", "visual"], "description": "Required when subagent_type is \"reviewer\": the lens that specialist reviews through. \"visual\" is spawned only when the PR carries an image artifact or touches UI-classified paths, and is the one lens whose specialist is wired with InspectImage." },
      "finding": { "type": "object", "description": "Required when subagent_type is \"validator\": the single candidate finding to check, in the review-finding schema (see formats.md)." }
    },
    "required": ["subagent_type", "description", "prompt"],
    "additionalProperties": false,
    "allOf": [
      {
        "if": { "properties": { "subagent_type": { "const": "reviewer" } } },
        "then": { "required": ["role"] }
      },
      {
        "if": { "properties": { "subagent_type": { "const": "validator" } } },
        "then": { "required": ["finding"] }
      }
    ]
  }
}
```

The `allOf`/`if`/`then` block makes the two conditional requirements
schema-enforced, not just prose the model has to remember: a `reviewer`
call missing `role`, or a `validator` call missing `finding`, fails
validation before it ever reaches Forge — rather than being accepted and
only failing at runtime when the sub-agent doesn't get the parameter it
needs. (Both keywords are plain JSON Schema draft-07+, so this doesn't
change the schema dialect used elsewhere in this document.)

---

## AskUser

> Raises a blocking question back to a human and **ends the current
> run** — see `formats.md`'s AskUser protocol for the full suspend/resume
> mechanics. Use this only when the task genuinely cannot proceed
> correctly without a human decision: contradictory requirements, a
> destructive/irreversible choice with no clear right answer in the
> task, or a precondition the task assumed that turns out to be false in
> a way that changes what "done" means.
>
> Do not use this for anything you could reasonably decide yourself —
> routine implementation choices, style preferences, or ambiguity you
> can resolve by reading more code. Note any judgment call you made
> instead of asking in your final Complete report, so it's visible and
> reviewable even though it didn't block you.
>
> Calling this tool is the last action in a run — do not call any other
> tool afterward, and do not call Complete in the same turn. It posts
> your question through AddComment automatically; you do not need to
> call AddComment yourself first.

```json
{
  "name": "AskUser",
  "input_schema": {
    "type": "object",
    "properties": {
      "question": { "type": "string", "description": "The specific question that needs a human answer." },
      "context": { "type": "string", "description": "Why this is blocking, and what you've already tried or ruled out." },
      "options": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Optional: 2-4 concrete choices, if the question reduces to one. Omit for an open-ended question."
      }
    },
    "required": ["question", "context"],
    "additionalProperties": false
  }
}
```

---

## FetchJira

> Fetches a Jira issue by key and returns its full content: title,
> description, status, issue type, priority, labels, acceptance
> criteria (if the project uses that field), comments in chronological
> order, and any linked issues. Coding-mode-only — review mode doesn't
> take a Jira issue as input, only a PR.
>
> Pass `fields` to limit the response to specific top-level fields (e.g.
> `["description", "comments"]`) when you only need part of the issue
> and want to keep the response small; omit it to get everything.

```json
{
  "name": "FetchJira",
  "input_schema": {
    "type": "object",
    "properties": {
      "issue_key": { "type": "string", "description": "The Jira issue key, e.g. \"PROJ-1234\"." },
      "fields": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Optional subset of fields to return. Omit for the full issue."
      }
    },
    "required": ["issue_key"],
    "additionalProperties": false
  }
}
```

Output shape is documented in `formats.md`.

---

## AddComment

> Posts a comment — a new top-level comment, an inline comment anchored
> to a specific file/line on a PR, or a threaded reply to an existing
> comment — on a Jira issue or a pull request (Bitbucket or GitHub).
> One tool for every platform, per the brief; platform differences are
> handled by which optional fields you set and by harness-side
> capability handling, not by separate tools. Wired in review runs and
> `plan`-mode coding runs only — an `implement` run's sole outward
> channel is its Complete report (see the availability notes at the top
> of this document). `body` is always plain
> Markdown regardless of target — converting it to whatever the target
> platform actually needs (e.g. Jira Cloud's ADF, or legacy wiki markup)
> is a harness-side concern, not something this schema or Forge itself
> handles; see `README.md`'s decision log ("Comment body format").
>
> - `target.platform: "jira"` + `target.id` (an issue key): posts a
>   Jira comment. `in_reply_to` is honored as a best-effort @-mention
>   reference — Jira's own comment model isn't fully threaded, so a true
>   nested reply isn't always possible; the tool falls back to a
>   plain comment prefixed with a reference to the original if the
>   target platform can't thread it.
> - `target.platform: "bitbucket_pr"` + `target.id`
>   (`"workspace/repo-slug#123"`): posts a Bitbucket PR comment.
>   Bitbucket PR comments are natively threaded, so `in_reply_to`
>   (a comment id) produces a true nested reply.
> - `target.platform: "github_pr"` + `target.id` (`"owner/repo#123"`):
>   posts a GitHub PR comment. Set `in_reply_to` (a comment id) to
>   reply within an existing review thread rather than starting a new
>   one.
> - On either PR platform, set `anchor` (file + line, optionally a
>   `line_end` for a range) for an inline review comment; omit it for a
>   general PR comment. Anchor line numbers are **new-file (post-change)
>   line numbers** — the same side the review-finding schema uses.
> - An inline comment can only attach to lines that appear in the PR's
>   diff. The harness validates the anchor before posting; if it isn't
>   commentable, the comment is posted as a general PR comment prefixed
>   with `file:line` instead of being dropped, and the tool result says
>   which happened — so a mis-derived line number degrades visibly, not
>   silently.
> - `suggestion` wraps `body` in the platform's committable suggestion
>   block, replacing the full anchored line range. Only set this when
>   applying it verbatim fully resolves the issue — never for a fix that
>   needs a follow-up step. Requires `anchor` (schema-enforced below).
>   When set, `body` must contain **only the exact replacement source
>   lines** — no prose, no Markdown fences, no explanation. The platform
>   commits the block's contents verbatim over the anchored range, so
>   any explanatory text inside it becomes a syntax error in someone's
>   codebase when they click "apply." Put the explanation in a separate
>   unanchored or prose comment if one is needed, or skip the
>   suggestion and describe the fix in prose instead. Suggestion-block
>   support varies by platform deployment; where the target can't apply
>   one, the harness posts the same content as a plain fenced code block
>   labeled as a suggested replacement, and the tool result says so —
>   the same degrade-visibly pattern anchor validation uses.
>
> Returns the posted comment's id and URL, which a caller can use as a
> later `in_reply_to` value. On PR targets the result also reports
> `head_moved: true` when the PR's head has advanced past the
> envelope's `Head SHA` since the run started — the comment still
> posts, anchored to the reviewed commit; see `review.md` §8 for the
> race policy this serves.

(Phase 2 reserves one additional field on this schema:
`resolve_thread`, a boolean valid only with `in_reply_to`, used by
re-review reconciliation to reply-and-resolve in one call — see
`review.md` §7c and `medium.md` §3f. Not part of the v1 schema below.)

```json
{
  "name": "AddComment",
  "input_schema": {
    "type": "object",
    "properties": {
      "target": {
        "type": "object",
        "properties": {
          "platform": { "type": "string", "enum": ["jira", "bitbucket_pr", "github_pr"] },
          "id": { "type": "string", "description": "Jira issue key, \"workspace/repo-slug#pr_number\" for a Bitbucket PR, or \"owner/repo#pr_number\" for a GitHub PR." }
        },
        "required": ["platform", "id"],
        "additionalProperties": false
      },
      "body": { "type": "string", "description": "Comment text, Markdown. The harness converts to the target platform's native format if needed (e.g. Jira ADF) — this schema always carries Markdown." },
      "in_reply_to": { "type": "string", "description": "Optional: id of an existing comment to reply to." },
      "anchor": {
        "type": "object",
        "description": "Optional, PR targets only: anchors the comment to a specific new-file line or line range.",
        "properties": {
          "file": { "type": "string" },
          "line": { "type": "integer", "description": "New-file (post-change) line number. The start of the range when line_end is set." },
          "line_end": { "type": "integer", "description": "Optional: new-file line number ending the range, inclusive. Omit for a single-line anchor." }
        },
        "required": ["file", "line"],
        "additionalProperties": false
      },
      "suggestion": { "type": "boolean", "description": "Wrap body as a committable suggestion block replacing the anchored line range. PR targets, anchored comments only." }
    },
    "required": ["target", "body"],
    "additionalProperties": false,
    "allOf": [
      {
        "if": { "properties": { "suggestion": { "const": true } } },
        "then": { "required": ["anchor"] }
      }
    ]
  }
}
```

The `allOf` block makes `suggestion` without an `anchor` a schema
error rather than a runtime surprise — same device the Task tool uses
for its conditional requirements.

---

---

## InspectImage

> Looks at an image artifact — the full tool description, schema,
> operations and result formats are specified in
> [`vision.md`](./vision.md) §3, and the store it reads from in
> [`artifacts.md`](./artifacts.md).

Summarised here so the tool set reads complete in one place:

- **Ops.** `extract_text` (OCR; no image and no model call), `ask` (a
  tool-less sighted sub-model answers a specific question, returns text),
  `view` (the image enters context for this turn only).
- **`region`** crops before the operation, taken from the original bytes so
  a crop is sharper than the whole downscaled image.
- **`pin`** keeps a viewed image for the rest of the run — the exception,
  budgeted at `vision.max_pinned_images` (default 2).
- **Why it is a separate tool and not part of `Read`:** the granularity rule
  admits a split when the existing tool's reducing grammar does not apply.
  `Read` reduces by line range; an image has no lines.
- **Degrades, not fails:** with no sighted model configured, only
  `extract_text` is advertised — `ask` and `view` are absent from the
  schema rather than present and erroring.

---

## Complete

> Ends the task. This is the only way a run finishes successfully —
> stopping without calling it (running out of turns, trailing off) is a
> failure mode to avoid, not an alternate ending. Carries the structured
> report described in `formats.md`'s completion schema: status, a short
> human-readable summary (Forge does not post this anywhere itself —
> whether and how it reaches a PR, a Jira comment, a CI summary, or
> nowhere at all is entirely the invoking harness's call),
> and mode-specific detail (files changed and verification run, for
> `implement`; the full finding list, for review mode; the plan itself,
> for `mode: plan`).
>
> Calling this is always the last action in a run. `status: "planned"`
> is `plan`-mode-only, for the case where the investigation found an
> actual change to make — it means a plan was produced and posted, not
> that any code changed; it says nothing about whether an `implement`
> run will follow, since that's decided outside this run. A `plan`-mode
> run that instead concludes no code change is needed uses
> `status: "done"` with an empty `steps` list in `report` — the finding
> was still posted per the same workflow, there's just nothing to hand
> off. `status: "blocked"` is for a run resuming after AskUser that
> still didn't fully resolve things; within a single run, use AskUser
> directly instead of reaching Complete with status `blocked`.
> `status: "budget_exhausted"` is what the final-turn nudge asks for when
> a run hits its turn or context budget (`formats.md` §7): the report is
> partial and honest, but running out of room is a different fact from
> being unable to do the work, and only one of them is worth retrying
> with a bigger budget. Do not use it for a run that is genuinely stuck.
>
> `report.spun_off` is where you record work you found **outside this
> run's `paths` scope and deliberately did not do**. File it; do not
> stretch to cover it. Use `relation: "blocks_this"` (with
> `status: "blocked"`) when you could not finish without that work, and
> `relation: "follows_this"` when you finished your own scope and
> something else also needs doing. At most two entries, and none at all
> if this run's own task was itself spun off — see `formats.md` §3a.
>
> In `implement` mode, the **first** `Complete(status: "done")` call
> does not complete the run. It returns a fixed checklist as the tool
> result instead — re-run your verification commands now and confirm
> they still pass; run `git status` and confirm every changed or
> untracked path is intended; confirm nothing throwaway leaked out of
> the scratch directory — and only a second `Complete` call actually
> ends the run. This is deliberate and deterministic (no extra model
> call), directly following SWE-agent's `review_on_submit_m` gate
> (`agent-self-verification.md` §2): a mechanical gate can't be talked
> out of firing, and false completion claims are the best-measured
> failure mode in this design's source research. Other statuses and
> other modes complete on the first call. The harness resets this
> gate (requiring the checklist again) if Edit, Write, or Bash is
> called after the first Complete call — Bash included because it can
> modify the working tree just as freely as Edit (a package-manager
> run, a formatter, a code-generation script), and v1 has no
> command-level filter to tell a read-only invocation from a mutating
> one, so the reset has to be conservative.

```json
{
  "name": "Complete",
  "input_schema": {
    "type": "object",
    "properties": {
      "status": { "type": "string", "enum": ["done", "planned", "skipped", "failed", "blocked", "budget_exhausted"] },
      "summary": { "type": "string", "description": "Short, human-readable. This is what a person reads first." },
      "report": { "type": "object", "description": "Full structured report. Shape depends on mode — see formats.md." }
    },
    "required": ["status", "summary", "report"],
    "additionalProperties": false
  }
}
```
