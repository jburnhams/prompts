# Anthropic Agent Skills (the generative/creative set)

- **Type**: Agent Skills · **Vendor**: Anthropic · **Status**: published
  (mixed licensing, see below)
- **Source**: https://github.com/anthropics/skills — `main` @ `41bbe19`
  (2026-09-03), plus the live skills mount `/mnt/skills/` read inside a
  claude.ai container on 2026-09-10 (see "Two distribution channels")
- **Retrieved**: 2026-09-10

A fourth *kind* of source for this collection. The existing
[`skills/`](../skills) folder holds **Claude Code plugins** — slash
commands and subagents that wrap a coding/review workflow. This folder
holds Anthropic's **general-purpose creative skills**: the ones that
teach a model to make a *thing* — an image, a poster, an animated GIF, a
generative-art viewer, an interactive React page, a themed deck — rather
than to change code. They are the source material for
[`../agent-generative-output.md`](../agent-generative-output.md).

Only the skills relevant to **making artifacts** are stored here. The
repo also ships `claude-api`, `skill-creator`, `mcp-builder`,
`internal-comms`, `academy-guide` and `discernment-nudge`, which are
covered adequately elsewhere in this collection or are out of scope.

## Licensing — read this before copying anything out

`anthropics/skills` is **not uniformly licensed**, and the split matters:

| Tier | Skills | Licence |
|---|---|---|
| Open source | `algorithmic-art`, `brand-guidelines`, `canvas-design`, `frontend-design`, `slack-gif-creator`, `theme-factory`, `web-artifacts-builder`, `webapp-testing`, `mcp-builder`, `skill-creator`, `claude-api`, `internal-comms`, `academy-guide`, `discernment-nudge` | Apache-2.0 (`LICENSE.txt` in each folder) |
| Source-available | `docx`, `pdf`, `pptx`, `xlsx` | Anthropic Commercial/Consumer Terms. Explicitly: *"users may not extract these materials from the Services or retain copies … outside the Services"*, *"reproduce or copy"*, or *"create derivative works"* |

**Everything stored in this folder is from the Apache-2.0 tier.** The four
document skills are analysed in
[`../agent-generative-output.md`](../agent-generative-output.md) §7 by
description and file inventory only — no text from them is reproduced
here, deliberately. That is a real restriction, not caution theatre: the
same four skills carry an *additional* restrictions clause the Apache
ones don't.

`paint/` is a special case — see below.

## Two distribution channels, and they don't match

The same skills reach a model through two different mounts, and the sets
differ:

- **`github.com/anthropics/skills`** — 19 skills, the public reference
  implementation.
- **`/mnt/skills/`** inside a claude.ai container — split into
  `public/` (7: `docx`, `pdf`, `pptx`, `xlsx`, `frontend-design`,
  `file-reading`, `pdf-reading`) and `examples/` (33). Twenty-three of
  the `examples/` skills **are not on GitHub at all**, including
  `paint`, `pages`, `deep-research`, `morning`, `computer-use`,
  `chrome-browser`, `built-in-browser`, `learn`, `google-workspace`,
  `setup-writing-style`, and a whole consumer-task family
  (`grocery-shopping`, `prescription-refill`, `meal-delivery`,
  `call-to-book`, `file-expenses`, `return-refund`, …).

Six of the container-only skills ship **no `LICENSE.txt` at all**
(`deep-research`, `doc-coauthoring`, `google-workspace`,
`import-memory`, `morning`, `pages`, `setup-writing-style`) — those are
described, never copied.

`paint/` **does** carry an Apache-2.0 `LICENSE.txt` on the container
mount but has no GitHub counterpart, so it is stored here with that
provenance stated: read from `/mnt/skills/examples/paint/` on
2026-09-10. It is the single most useful file in this folder for the
question this collection's generative-output doc is about, so it is worth
the asterisk.

## Files

| Path | What it is |
|---|---|
| `paint/SKILL.md`, `paint/reference.md` | **Paint an image by writing code, not by calling an image model.** A Python OpenCV watercolour toolkit (`paintkit.Canvas`), a seeded render, a look-and-critique loop, and an explicit transcript-hygiene rule. Apache-2.0, container mount only |
| `canvas-design/SKILL.md` | Posters/art as `.png`/`.pdf`. Two-step: write a *design philosophy* as a `.md` file, then express it on a canvas. Ends with a prompted fake user turn (see below) |
| `algorithmic-art/SKILL.md`, `viewer.html`, `generator_template.js` | Generative p5.js art as a single self-contained HTML page. The template is a **fixed-chrome / variable-payload** contract: named FIXED regions must survive verbatim, only marked VARIABLE regions are replaced |
| `web-artifacts-builder/SKILL.md`, `scripts/*.sh` | Multi-file React + Tailwind + shadcn/ui project → Parcel + `html-inline` → **one self-contained `bundle.html`** that is the artifact |
| `frontend-design/SKILL.md` | The long-form design brief for building UI in code. Near-sibling of Claude Code's bundled `artifact-design` skill (see [`../leaked/claude-code/artifact-skills/`](../leaked/claude-code/artifact-skills)) |
| `webapp-testing/SKILL.md` | Playwright verification of a locally-served app. Carries the clearest statement of the black-box-script rule in the field |
| `theme-factory/SKILL.md` | Ten named colour/type themes applied to an already-built artifact, plus on-the-fly theme generation. A `theme-showcase.pdf` is *shown* to the user to pick from |
| `brand-guidelines/SKILL.md` | Anthropic's own palette/type, applied through `python-pptx`'s `RGBColor` |
| `slack-gif-creator/SKILL.md` | Animated GIFs under Slack's emoji constraints, drawn frame-by-frame with PIL `ImageDraw` |

## Scaffolding notes — what these actually do

Per this collection's convention, the interesting part is not the prose
but the machinery around it.

**Where the pixels come from.** Not one of these skills calls an
image-generation model. `paint` renders OpenCV; `canvas-design` and
`slack-gif-creator` render PIL/reportlab; `algorithmic-art` renders p5.js
in the viewer's browser. The vendor with the largest set of published
creative skills ships **zero diffusion-model tool calls** in them. Every
image here is the output of a program the model wrote.

**Two-step: philosophy first, artefact second.** `canvas-design` and
`algorithmic-art` share a structure — write a 4–6 paragraph *design
philosophy* / *algorithmic philosophy* to a `.md` file, then, as a
separate act, express it. The philosophy file is a real deliverable
shipped alongside the artwork. v0's `GenerateDesignInspiration` tool
(`../leaked/v0/Tools.json`) is the same idea reached independently and
implemented as a **tool call** rather than a prompted step, down to the
same enforcement clause: *"If you generate a design brief, you MUST
follow it."*

**The prompted fake user turn.** `canvas-design`'s FINAL STEP reads, in
full: *"**IMPORTANT**: The user ALREADY said 'It isn't perfect enough. It
must be pristine, a masterpiece if craftsmanship, as if it were about to
be displayed in a museum.'"* — a synthetic critique injected to force a
second pass, followed by an instruction that the second pass must
*refine, not add* ("If the instinct is to call a new function or draw a
new shape, STOP"). Nothing else in this collection fabricates a user
utterance to drive a revision loop.

**Fixed-chrome templating.** `algorithmic-art` does not ask for an HTML
page; it ships `templates/viewer.html` and says *"Use that file as the
LITERAL STARTING POINT"*, enumerating FIXED sections (layout, branding,
seed navigation, action buttons) against VARIABLE ones (the p5.js
algorithm, the parameter object, the parameter controls). The seed
controls are fixed because reproducibility is the point: *"Same seed
ALWAYS produces identical output."* Claude Code's `artifact-*` skill
family (dashboard, report, data-table, explainer) is the same contract
with `<!-- SLOT: … -->` markers instead of prose regions.

**Bundling as the delivery step.** `web-artifacts-builder` is the only
skill here that admits an artifact is a build product: it scaffolds a
real Vite/React/Tailwind project with 40+ shadcn components, and the
delivery step is `bundle-artifact.sh` — `pnpm add -D parcel
@parcel/config-default parcel-resolver-tspaths html-inline`, build with
Parcel, then inline every asset into one `bundle.html`. The model
authors many files and ships one; nothing about the bundle passes through
its context. It also gates itself: *"not for simple single-file HTML/JSX
artifacts."*

**Verification is optional and deliberately deferred.** Same skill,
step 5: *"avoid testing the artifact upfront as it adds latency between
the request and when the finished artifact can be seen. Test later, after
presenting the artifact, if requested or if issues arise."* That is a
straight inversion of this collection's
[`../agent-self-verification.md`](../agent-self-verification.md) norm,
and the justification is time-to-first-pixel rather than confidence.
`paint`, by contrast, makes looking mandatory — see below.

**The black-box script rule.** `webapp-testing`: *"Always run scripts
with `--help` first … DO NOT read the source until you try running the
script first and find that a customized solution is absolutely necessary.
These scripts can be very large and thus pollute your context window.
They exist to be called directly as black-box scripts rather than
ingested into your context window."* This is the cleanest statement
anywhere in this collection of the principle that makes skills
context-cheap: **a skill's code is executed, not read.**

**`paint`'s look-and-critique loop.** The only skill here that closes the
perceptual loop, and it says why it has to: *"`bash_tool` returns only
stdout, so without this step you never see what you drew."* The loop is
write `scene.py` → render at `--scale 0.5` → call `view` on the PNG →
*"Name the two things that read worst … and edit only those lines"* →
re-render → full size → `present_files` on both the image **and
`scene.py`**. Because geometry is seeded, "make the sky darker" is an
edit to an existing file, not a new painting. It also carries an explicit
transcript rule — *"Keeping the transcript clean … Do not paste scene
source into the chat as prose; a collapsed tool call is a few lines in
the transcript"* — and a stated budget (one CPU, 300 s wall clock,
~1 s for an 18-element scene at 1600×900).

**Tool names differ from Claude Code's.** `paint` names `bash_tool`,
`view` and `present_files`; `webapp-testing` assumes a Python runtime and
Playwright. These are the claude.ai container's surface, not the CLI's
(`Bash`, `Read`, `SendUserFile`). The same skill text therefore does not
run unmodified in both harnesses — worth knowing before treating
"skills" as portable.

**`pages` is a null skill, on purpose.** `/mnt/skills/examples/pages/SKILL.md`
is two sentences long: *"Everything about pages is served by the pages
tools themselves. Call `guide(["topic.index"])` before your first pages
call and follow what it returns."* A skill whose entire body is a
redirect to a tool that serves its own instructions — progressive
disclosure taken to the point where the disclosed file discloses nothing.
