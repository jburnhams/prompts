# LibreChat (artifacts)

- **Type**: self-hosted chat UI with an agent framework · **Vendor**:
  Danny Avila / community · **Licence**: MIT
- **Source**: https://github.com/danny-avila/LibreChat — `main` @
  `b356c3d` (2026-09-10)
- **Retrieved**: 2026-09-10

Included for one thing only: it is the clearest **open-source
implementation of an artifact channel** — the mechanism by which a chat
model's output stops being a message and becomes a rendered, re-editable
page. Every other artifact system in this collection
(Claude Code's `Artifact` tool, Claude.ai's, Bolt's, v0's) is closed;
this one you can read.

Only the artifact-relevant files are stored:

| File | Upstream path | What it is |
|---|---|---|
| `artifacts.js` | `api/app/clients/prompts/artifacts.js` | The whole prompt layer: three artifact prompts and the function that picks between them |
| `artifacts.ts` | `client/src/common/artifacts.ts` | The client-side artifact type, including the `ArtifactDownload` escape hatch |

## The delivery format: a fenced directive, not a tool call

LibreChat's artifacts are **in-band**. There is no artifact tool; the
model emits a remark-directive block inside its ordinary message text:

```
:::artifact{identifier="unique-identifier" type="mime-type" title="Artifact Title"}
````
Your artifact content here
````
:::
```

The harness scans messages for those delimiters (`ARTIFACT_START` /
`ARTIFACT_END`, `findAllArtifacts`, `replaceArtifactContent` in
`api/server/services/Artifacts/update.js`) and lifts the block into a
side panel. That places it squarely in the in-band half of
[`../agent-tool-call-dialects.md`](../agent-tool-call-dialects.md)'s
taxonomy — a delimiter grammar rendered into the prompt and scanned back
out — applied to *output* rather than to tool calls, and it inherits the
same fragility. The prompt has to teach fence arithmetic explicitly:
*"Use a backtick fence longer than any backtick fence in the artifact
content. Use a 4-backtick fence by default; if the artifact content
contains a 4-backtick fence, use 5 backticks, and so on."*

Compare Claude Code's answer, which is a first-class `Artifact` tool
taking a `file_path`: the payload never enters the assistant message at
all, and there is no fence to get wrong.

## Two prompts, chosen by provider family

`generateArtifactsPrompt({ endpoint, artifacts })` returns:

- `artifactsPrompt` when `endpoint === anthropic`,
- `artifactsOpenAIPrompt` otherwise,
- `null` when the mode is `ArtifactModes.CUSTOM` (the operator supplies
  their own),
- either of the first two **plus** `generateShadcnPrompt({ components })`
  when the mode is `SHADCNUI`.

The two provider prompts carry the same rules and differ in *rendering*:
the Anthropic one wraps its rules in `<artifact_instructions>` and
`<examples>`/`<example_docstring>` XML; the OpenAI one uses
`## Artifact Instructions` / `## Examples` Markdown headings — and adds a
block the Anthropic variant has no counterpart for:

> **b. Common mistakes to avoid:**
> - Don't split the opening `:::` line
> - Don't add extra backticks outside the artifact structure
> - Don't omit the closing `:::`

A per-model-family dialect where the *weaker delimiter-follower gets
error-recovery hints baked into its prompt*. This collection has the same
pattern one layer down, in OMP's eleven tool-call dialects
([`../omp/`](../omp)) and in
[`../agent-tool-implementations.md`](../agent-tool-implementations.md)'s
per-model-family schemas (Gemini CLI, Cline) — but this is the first
instance of it applied to an artifact format, and it is a strong hint
that the delimiter grammar is the load-bearing risk in an in-band
artifact channel.

The `shadcn/ui` mode is worth a note of its own: it appends **generated
component documentation** to the prompt (`shadcn-docs/generate` over a
`components` list), and takes a `useXML` flag so the appended docs match
the host prompt's dialect. Compare `web-artifacts-builder`
([`../anthropic-skills/`](../anthropic-skills)), which solves the same
problem by *shipping the components in a tarball* the model scaffolds
rather than by describing them in the prompt.

## The deprecated V1 prompt is Claude's own, near-verbatim

`artifactsPromptV1` is still in the file, marked `@deprecated`. Its
opening lines —

> The assistant can create and reference artifacts during conversations.
> Artifacts are for substantial, self-contained content that users might
> modify or reuse, displayed in a separate UI window for clarity.
> # Good artifacts are... - Substantial content (>15 lines) …

— match the widely-circulated capture of Claude.ai's own original
Artifacts prompt, down to the "Don't use artifacts for…" list and the
`/api/placeholder/400/320` placeholder-image convention. Two details in
it did not survive into the current prompts and are worth recording
because they are unusual:

- *"If asked to generate an image, the assistant can offer an SVG
  instead. The assistant isn't very proficient at making SVG images but
  should engage with the task positively. **Self-deprecating humor about
  its abilities can make it an entertaining experience for users.**"* —
  a prompted *affect* prescription attached to a capability gap.
- *"If a user asks the assistant to 'draw an SVG' or 'make a website,'
  the assistant does not need to explain that it doesn't have these
  capabilities."* — an instruction not to disclaim a capability the
  harness supplies. Both are gone from the live prompts.

The lineage matters for this collection's method: it is a documented case
of a closed vendor's artifact prompt being adopted wholesale by an
open-source host, then diverging. Where the current LibreChat prompt and
Claude's differ, the difference is a decision someone made, not a gap in
the capture. (Compare [`../leaked/grok-build/`](../leaked/grok-build),
the other near-verbatim cross-vendor match in this collection — there it
was tool descriptions rather than an output format.)

## Types, and where they hit runtime reality

The current prompts admit `text/html`, `image/svg+xml`,
`application/vnd.mermaid` and `application/vnd.react`, with rules that
are all about the *runtime's* limits rather than about design:

- HTML must be one file, JS and CSS inline; the only permitted external
  script origin is `https://cdnjs.cloudflare.com`.
- React must have a default export and no required props; Tailwind
  classes only, and **no arbitrary values** (`h-[600px]` is banned);
  imports limited to `react`, `lucide-react@0.263.1`, `recharts`, and
  `shadcn/ui` from `/components/ui/name` — *"NO OTHER LIBRARIES … ARE
  INSTALLED OR ABLE TO BE IMPORTED."*
- Web images are forbidden; a local placeholder endpoint stands in.
- And the fallback: *"If you are unable to follow the above requirements
  for any reason, don't use artifacts and use regular code blocks
  instead, which will not attempt to render the component."*

The pinned `lucide-react@0.263.1` and the single-CDN allowlist are the
same shape of constraint as the Artifact tool's CSP allowlist
(`cdnjs`, `jsdelivr/npm`, `cdn.tailwindcss.com`, `code.jquery.com`,
Google Fonts, nothing else). Two independent artifact runtimes, two
allowlists, both centred on cdnjs.

`recharts` being in the allowed set is the answer to "how does this host
draw a chart": the model writes JSX against a charting library the
sandbox already has. Google's AI Studio vibe-coder prompt
([`../leaked/google-gemini/`](../leaked/google-gemini)) says the same
thing in one line — *"Use `recharts` for charts"* — as does the
Anthropic-lineage prompt above. Three unrelated hosts, one library.

Rendering has moved around underneath all this: artifacts render through
CodeSandbox **Sandpack**, with Monaco replacing Sandpack's own editor for
the code tab, and Markdown artifacts moved *off* the React renderer to a
self-contained static HTML page after the `react-markdown` dependency
chain's Node subpath imports proved unresolvable by Sandpack's bundler —
a failure that "silently failed" rather than erroring. That is the same
class of defect this collection keeps finding in generative paths:
[`../agent-vision-multimodal.md`](../agent-vision-multimodal.md)'s
image-in-a-tool-result bug, which also never errors.

## `ArtifactDownload` — the artifact/file distinction, in a type

The most interesting eight lines in `artifacts.ts`:

```ts
/**
 * Original-file download metadata for artifacts backed by a real
 * code-interpreter file (e.g. an office document whose panel preview is
 * a server-rendered HTML render, not the binary itself). When present,
 * the panel download button fetches this file instead of serializing
 * the rendered preview `content`.
 */
export interface ArtifactDownload { filepath?; file_id?; source?; user?; }
```

An artifact can be a *view* of a file that exists elsewhere. The panel
shows a server-rendered HTML preview; the download button fetches the
real `.docx`. The model produced the file, not the preview, and neither
one passed through the conversation. That is the same separation
Anthropic's document skills make (write a real `.docx` with
`python-docx`, hand back a path) and the same one MCP Apps makes between
`content` and `structuredContent` — arrived at here for a purely
practical reason.
