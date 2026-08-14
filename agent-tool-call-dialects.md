# Tool-call dialects: the wire format under "the model called a tool"

Every other doc in this collection sits above a line it never questions:
that the model receives a list of tools and emits a call. This one is
below that line. What actually crosses the wire is **text** — a grammar
the model was post-trained on, rendered into the prompt by the provider's
chat template and scanned back out of the model's output by a parser. The
tools array is a rendering step. The call is a parsing step. Both are
someone's code, and on an open-weights model that someone can be you.

This matters practically in three situations, which is why it is worth a
doc rather than a paragraph:

1. **A model with no function-calling support at all** — you want tools
   anyway, so you have to supply the grammar and the parser yourself.
2. **A model whose native tool support is worse than its text** — the
   provider's parser is lossy, or the tuned format is off-distribution
   for what you're asking, and driving the model in-band beats the
   official channel.
3. **A model whose native support is fine** — where knowing the
   underlying encoding still explains failures you would otherwise file
   as "the model is bad at tools" (`agent-tool-implementations.md` §3g,
   §3h).

**Sources and their limits.** The per-family detail here comes from
[OMP](./omp)'s `docs/toolconv/` — eleven dialect references maintained
alongside a working converter for each, and themselves verified against
tokenizer configs, `chat_template.jinja` files rendered locally, vendor
function-calling guides, and the vLLM/SGLang parser sources (paths and
commit in [`sources.md`](./sources.md)). The reasoning about *why* the
encoding matters comes from that project's author's write-up, ["The
Minutiae of Tool-calling"](https://blog.can.ac/2026/08/03/the-minutiae-of-tool-calling/).
This doc is a synthesis of those references and OMP's implementation —
**it is not an independent verification against the tokenizers**, and
token IDs, template details and vendor formats all drift. Treat specific
bytes as "true at that commit, check before you depend on it."

---

## 1. There is no "the model decided to call a tool"

A language model computes a probability distribution over the next token.
Everything above that — system prompts, user turns, tool calls — is
delimiters in one flat sequence. The consequences are unintuitive in a
useful way:

**The model never receives your tools array as data.** The provider's
template renders it into the prompt as text. Under OpenAI's Harmony format
that text is a TypeScript-ish namespace in a *developer* message; under
Qwen3's it is a `<tools>` block of one JSON object per line in the system
turn; under Gemini's Pythonic convention it is prose describing Python
functions.

**Therefore your schema is documentation.** The `description`, `minimum`,
`enum` and `required` fields may or may not be rendered into that text,
and may or may not be enforced by anything. Validation is your code's job.
This is the mechanical reason every mature harness validates more loosely
than it advertises (`agent-tool-implementations.md` §3e) — the model is
pattern-matching against rendered prose, not filling a typed form.

**And a "call" is just the model emitting the grammar.** Parallel calls
are two of them in a row. Nothing magical happens; a parser scans them
out. Which means the format is a variable you control on any model where
you own the prompt.

---

## 2. Five ways to delimit a call, and the tokenizer decides which

The families sort by *what kind of thing* the delimiters are. This is the
distinction that predicts most parser behaviour.

| Family | Examples | Delimiters are | Consequence |
|---|---|---|---|
| **Dedicated special tokens** | Harmony (`<\|start\|>`, `<\|call\|>`, `<\|constrain\|>`), DeepSeek (`<｜tool▁calls▁begin｜>`), Kimi K2 (`<\|tool_calls_section_begin\|>`), Gemma 4 (`<\|tool_call>` … `<tool_call\|>`) | single vocabulary entries, flagged special | unambiguous and unforgeable in content; stripped by `skip_special_tokens`; you need tokenizer support to emit them |
| **Single tokens, deliberately *not* special** | Qwen3/Hermes (`<tool_call>`, `<think>`), GLM-4.5/4.6 (`<tool_call>`, `<arg_key>`) | one token each, `special: false` | cheap to emit *and* they survive a `skip_special_tokens=True` decode — which is exactly why a regex parser can recover them from decoded text |
| **Pure prompt convention, no tokenizer support** | Gemini / Gemma 3 (`print(default_api.f(...))` in a ` ```tool_code ` fence) | ordinary text that BPE-splits | works across hosted and open weights with no template support — and leaks into normal output |
| **Owned in-band XML** | OMP's generic `xml` dialect, MiniMax (`<minimax:tool_call>`), Anthropic-style `<invoke>` | ordinary text, delimiter-matched | the harness supplies grammar, prompt and parser; works on anything that can follow instructions |
| **Structured transport** | `pi-native` (not a textual dialect at all) | JSON over HTTP/SSE | lossless for canonical types; only available when both ends are yours |

Two details worth internalising.

**`special: true` vs `special: false` is a design decision, not an
accident.** Qwen3 registers `<|im_start|>`/`<|im_end|>` as special and
`<tool_call>`/`</tool_call>`/`<think>` as non-special. The turn markers
are structural and must never be forgeable from content; the tool markers
are meant to *survive decoding* so an ordinary text-mode parser can find
them. GLM makes the same split. If you are choosing markers for your own
in-band dialect, you are making this same call without a tokenizer to
enforce it — and you have only the second option.

**Pipe placement and character variants are real hazards.** DeepSeek uses
**fullwidth** pipes (`｜`, U+FF5C) with `▁` word joiners; Qwen3 uses ASCII
`|` and has no fullwidth variants; Gemma 4 uses *asymmetric* placement
where an opener carries the pipe on the left (`<|tool_call>`) and its
closer carries it on the right (`<tool_call|>`). A parser written against
one family will silently fail to match another that looks identical in a
terminal — the same class of invisible-difference bug as the Unicode
filename problem in `agent-tool-implementations.md` §7b.

---

## 3. Argument encoding is where reliability is won or lost

The delimiter style is mostly cosmetic. **How arguments are encoded is
not**, because it decides whether the model has to produce valid escaped
JSON mid-generation or can emit raw text and stop. Ordered roughly from
least to most demanding:

**No JSON at all.** GLM emits the function name on the opening tag's own
line, then alternating element pairs:

```text
<tool_call>get_weather
<arg_key>location</arg_key>
<arg_value>Beijing</arg_value>
<arg_key>unit</arg_key>
<arg_value>celsius</arg_value>
</tool_call>
```

Every value is a delimiter-matched body. Nothing needs escaping, nothing
can fail to parse. It is also the most verbose, and it has no native way
to express a nested object — which is a feature if you believe §3g and a
limitation otherwise. (OMP's reference flags the anatomy here as "the
single most error-prone part" to *implement*: the name is the text
between `<tool_call>` and the first newline, with no wrapping tag and no
space.)

**A token as the string delimiter.** Gemma 4 writes
`call:NAME{key:value,…}` with every string wrapped in a `<|"|>` token, so
"values may contain raw ASCII quotes and commas without escaping — only a
literal `<|"|>` token sequence cannot appear inside a string." This is
the cleanest solution available to a family that controls its own
tokenizer: the escaping problem is solved by making the delimiter
unforgeable rather than by escaping.

**Schema-directed bodies.** OMP's XML dialect uses the tool's declared
schema to decide: a declared string renders verbatim with whitespace
preserved; a number, boolean, `null`, array or object renders as JSON and
is parsed back through a repair-capable parser, falling back to a string
if repair fails. Primitives are free; structure is not. A per-parameter
`string="true"`/`"false"` override exists for the cases where the schema
is wrong.

**A JSON blob per call.** The most common shape, and the one that puts a
parse failure on every call carrying structure:

- DeepSeek: `{name}<｜tool▁sep｜>{json_args}` inside a batch wrapper.
- Kimi K2: `functions.{name}:{idx}<|tool_call_argument_begin|>{json}` —
  note the function name is **recovered by parsing it back out of the
  call ID**, not carried in a field of its own.
- Qwen3/Hermes: `<tool_call>\n{json}\n</tool_call>`, where `arguments`
  is a genuinely nested object, not a stringified one.
- Harmony: a JSON body announced by `<|constrain|>json` in the header.

**Python source.** Gemini and Gemma 3 emit a call expression, and a
robust parser has to normalise at least four attested spellings —
`print(default_api.NAME(kwargs))` (hosted canonical), the same without
`print`, a bare `NAME(kwargs)`, and `result = NAME(kwargs)`. Arguments
are Python keyword arguments, so the escaping rules are Python's.

The through-line, which is `agent-tool-implementations.md` §3g stated
from the format side: **the encodings that make the model emit escaped
JSON are the ones that fail**, and they fail proportionally to how much
structure your parameters have. A tool with three scalar parameters is
nearly encoding-independent. A tool taking an array of objects is at the
mercy of whichever of the above your model speaks.

---

## 4. How tools get advertised

Three shapes, and they are not interchangeable in cost:

- **One compact JSON object per line inside `<tools>…</tools>`**, placed
  in the system turn. Qwen3's template does this natively; OMP's owned
  dialects reuse the same shape. Cheapest to generate, and the closest
  thing to sending the schema verbatim.
- **A TypeScript-ish namespace.** Harmony's `# Tools` / `namespace
  functions { … }` block, with descriptions as `//` comments above
  `type NAME = (_: {…}) => any;`. More readable to the model, more tokens,
  and lossy about JSON-Schema constructs that TypeScript can't express.
  OMP renders its own verbose inventory in this shape too.
- **Prose plus examples.** Gemini/Gemma 3's Pythonic prompts describe the
  functions in documentation form. The most tokens, and the only option
  when there is no template support at all.

The practical note: when a harness takes over the tool channel it must
also take over advertising, and the catalogue then costs prompt tokens
*every turn* — which is the standing argument against in-band dialects,
and the reason deferred tool loading (`agent-tool-implementations.md`
§10) matters more here than on a native channel.

**A fourth shape, and the one that goes furthest: a compiling `.d.ts`.**
DeepSeek Harness's Code Mode
([`deepseek-harness/system-prompt-code-mode.md`](./deepseek-harness/system-prompt-code-mode.md))
advertises its tools as generated TypeScript — `interface ToolArgsMap`,
`interface ToolOutputMap`, `declare class ToolCallError`, `declare const
tools` — with every parameter and every *return* type declared, JSDoc
comments carrying the descriptions, and the model asked for the body of
an async function instead of a call. It looks like Harmony's namespace
shape one size up, but it differs on the thing that matters: Harmony
declares `=> any`, so the model is told what it may send and nothing
about what comes back, while `ToolOutputMap` declares the exact canonical
return type of every tool. That is what makes a *program* writable rather
than a single call — you cannot branch on `result.exitCode` or
`.filter(Boolean)` a list of handles against `any`.

The cost is severe and worth stating plainly: the plain assembled prompt
for the same deployment is ~3.4 KB, and the Code Mode one is ~28 KB, the
overwhelming majority of it this declaration block. That buys back
something no dialect in §2 can offer — *"ONLY what you print or return
comes back to you — intermediate tool results never enter the
conversation"* — so a fan-out over fifty files costs one result in
context instead of fifty. The trade is therefore not tokens-vs-tokens but
**a fixed per-turn prompt cost against a variable per-result transcript
cost**, which is a different curve from every other row in this section
and only wins above some fan-out. That the same harness ships both modes
(and a `both-mode-turn` snapshot carrying each) suggests DeepSeek treats
it as a per-deployment choice rather than a replacement.

Two consequences for the result protocol in §5 fall out of it, and are
easy to miss: correlation ceases to exist as a wire concern (the program
holds the value in a variable; there is no id to match), and an error
stops being an envelope field and becomes a **catchable exception** —
`ToolCallError`, with `toolName` and a human-readable `message`, so a
program can `try/catch` a failed call and continue. The schema
deliberately exposes nothing else: "programs can inspect only its `name`,
`toolName`, and human-readable `message`, not internal error codes or a
failure union."

---

## 5. Results: correlation, envelope, and whether an error can be seen

Sending a result back is a second protocol, and the families disagree
more here than on calls.

**Correlation** is either by ID or by position. Harmony carries a
recipient in the header; Kimi mints `functions.{name}:{idx}`; Anthropic
uses `tool_use_id`. OMP's generic XML and MiniMax dialects carry **no IDs
at all** — "results must preserve call order because `<tool_response>` has
neither id nor name." If you are designing an in-band dialect, this is the
first thing to decide, and ordering-only is a real choice: it is simpler
and it makes a dropped or reordered result a silent corruption rather
than a loud one.

**The envelope role varies more than you'd expect.** Qwen3 maps every
`role: "tool"` message into a `<|im_start|>user` turn carrying
`<tool_response>` blocks — and coalesces consecutive results into one user
turn — where classic Hermes 2 Pro used a dedicated `tool` turn. GLM uses
a distinct `<|observation|>` role marker. Harmony sets the message's
*author* to the tool's own name (`functions.get_weather`), not the literal
word `tool`. A harness that assumes "results go in a tool role" will
produce subtly wrong history on at least three of these.

**Error signalling is frequently absent.** OMP's generic XML dialect
renders `isError: true` in exactly the same `<tool_response>` shape as a
success: "the model must never generate `<tool_response>` itself," and
"the error must be intelligible from its text." That is
`agent-tool-implementations.md` §7's errors-are-prompts principle
promoted from good practice to hard requirement — in a dialect with no
error channel, prose *is* the channel.

---

## 6. Reasoning rides the same wire

Every current family multiplexes a reasoning stream through the same
token sequence, and it interacts with tool parsing:

- Qwen3, GLM: `<think>…</think>` at the start of an assistant turn.
- Gemma 4: a dedicated `<|channel>thought … <channel|>` block *before*
  any reply text or tool call; OMP's scanner routes it to thinking events
  and still parses calls that follow it.
- Harmony: a mandatory `channel` field on every assistant message
  (`analysis` / `commentary` / `final`), with tool calls carrying a
  recipient.

Two implementation consequences. **Re-rendering history has to decide
whether to include prior thinking**, and the families have different
rules — get it wrong and you either leak reasoning into a context that
was trained without it, or drop a block the template expects. And
**thinking is where a leaked tool call usually appears first**, because
the model is rehearsing the grammar before committing to it.

---

## 7. What implementing one actually costs

Collected from OMP's converters, this is the checklist for driving a
model in-band:

1. **A renderer and a scanner, and the scanner must be wider.** OMP's
   generic XML renderer emits bare consecutive `<invoke>` blocks; its
   scanner also accepts a `<tool_calls>` wrapper, `<function_calls>` as
   an alias, `antml:`-prefixed variants, and a bare invoke with no
   wrapper. This is `agent-tool-implementations.md` §3e's
   advertise-strict/accept-tolerant rule one layer down, and it is not
   optional — models blend dialects they have seen.
2. **Call-ID minting**, if the dialect has none, plus strict ordering
   discipline on results.
3. **Streaming.** Delimiters arrive split across chunks; a scanner has to
   hold partial matches without emitting them, and OMP projects owned
   dialects through a dedicated streaming layer for exactly this.
4. **History conversion in both directions** — prior structured calls and
   results must be re-rendered into the dialect's text when the
   conversation is replayed, or the model sees a format it never emits.
5. **Prompt assembly**: the tool catalogue plus a format guide, appended
   to the system prompt, costing tokens every turn.
6. **Failure handling for the dialect's own pathologies** (§8).

What you give up by leaving the native channel: provider-side constrained
decoding (the thing that makes Codex's `apply_patch` Lark grammar and
Harmony's `<|constrain|>json` reliable), any server-side validation, and
the post-training prior — "RL teaches the shapes RL practiced." What you
get: it works on models with no tool API at all, the format becomes a
variable you can benchmark, and you can repair failure modes nobody else
will fix for you.

**Selection should be per model family, and "unknown" is not the same as
"generic."** OMP's `tools.format` defaults to `auto`; notably, when a
model reports `supportsTools: false`, `auto` picks *a known family
dialect* (or GLM's, as a default) rather than the generic XML one —
because a grammar some model family was actually trained on beats a
neutral grammar nobody was. The generic dialect is for when you
explicitly need it.

---

## 8. The failure modes, and why the leak is diagnostic

**Prompt-convention formats leak into ordinary output.** Gemini's
Pythonic form surfaces on Vertex and AI Studio as
`finish_reason = MALFORMED_FUNCTION_CALL`, and OMP's reference points out
that this leak is "the clearest public evidence of the format" — the
reverse-engineered hosted-Gemini syntax was recovered from bug reports
containing partial emissions like `Malformed function call:
print(default_api.`. A format with no special tokens cannot distinguish
"I am calling a tool" from "I am writing about calling a tool," so the
harness must.

**Sampled garbage in the call header.** Real, ugly, and unfixable at the
provider: `to=functions.check.commentary (json.Xna 天天送钱 code`. A
harness has to fail this legibly rather than crash on it.

**No call at all.** The model answers in prose when it should have acted
— a per-turn failure rate too small to see in a demo and a certainty
across a long session, since "reliability is rate × exposure."

**Version drift inside a family.** DeepSeek V3.1's on-the-wire tool
syntax is *not* the same as V3-0324's and R1-0528's, despite a shared
tokenizer family. A dialect is versioned even when the vendor doesn't say
so.

The disposition that follows is the one worth taking from this whole
area: these are your protocol's shortcomings, not the model's, and
"there is no fix coming" from the provider.

---

## What this changes for the design in `agent-design/`

Forge targets one model family on a managed API, so it uses the native
channel and inherits the provider SDK's parser — the right call, and
nothing here argues otherwise. Three things carry over anyway:

- **Parameter shape is a reliability decision, not just a token cost**
  (§3). Already recorded against the batch `Read` shape in
  `agent-design/README.md`'s decision log, with the flat spelling tracked
  in `future.md`.
- **Errors must be legible as prose**, because the weakest dialect in the
  field has no error channel and the design's own results already commit
  to this (`formats.md` §8f).
- **Results correlate by position** in the design's batch `Read` — one
  block per requested entry, in request order (`formats.md` §8b). That is
  the ordering-only choice from §5, and it inherits that choice's
  fragility: it is why "a block exists for every request" is an
  invariant rather than a nicety.

If Forge is ever pointed at open-weights models, §7 is the build list and
`agent-design/future.md`'s dialect-aware scanning entry is where it
starts.
