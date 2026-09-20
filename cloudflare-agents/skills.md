# Skills: a third implementation, and the first with capability gating

`packages/agents/src/skills/` (2,623 lines across 9 files) and
`packages/think/README.md` at `c076e4c`.

The collection already has two skill implementations to compare —
Anthropic's (`../anthropic-skills/`, `../skills/`) and DeepSeek's
(`../deepseek-harness/`). This is the third, it follows the same
[agentskills.io](https://agentskills.io/) directory format, and it adds
the thing neither of the others has: **a skill's script runs with an
explicitly gated capability context, and the skill declares its own tool
scope.**

## Three tools, generated from the registry

`registry.ts` builds an AI SDK `ToolSet` from whatever skills are loaded.
Verbatim descriptions:

```ts
tools.activate_skill = tool({
  description:
    "Activate a skill by name. Use this when the user's task matches one of the available skills.",
  inputSchema: z.object({
    name: z.enum(modelSkillNames as [string, ...string[]])
  }),
  …
});
```

```ts
tools.read_skill_resource = tool({
  description:
    "Read a bundled resource from an available skill by relative path. Pass name and path, or use a qualified path like skill-name/references/file.md.",
  inputSchema: z.object({
    name: z.enum(modelSkillNames as [string, ...string[]]).optional(),
    path: z.string().min(1)
  }),
  …
});
```

```ts
tools.run_skill_script = tool({
  description:
    "Run a bundled script resource from an available skill. Use only when a skill instructs you to run a script.",
  inputSchema: z.object({
    name: z.enum(modelSkillNames as [string, ...string[]]),
    path: z.string().min(1),
    input: z.unknown().default({})
  }),
  …
});
```

Four things to note:

- **`z.enum(modelSkillNames)`** — the skill name is a runtime-constrained
  enum, so the model cannot name a skill that is not loaded. The third
  independent instance of this move in this pass, after Open Interpreter's
  `language` and Data Formulator's `load_skill`.
- **`run_skill_script` only exists if `this.scriptRunner` is set.** No
  runner, no tool. Capability-gated tool exposure, again generated rather
  than configured.
- **"Use only when a skill instructs you to run a script"** — the model
  is told not to freelance script execution. Compare
  `../code-mode/`'s position that the model *should* write programs; here
  scripts are the skill author's, and the model is a caller.
- **Every failure returns a string, never throws** — `Skill not found:`,
  `Script not found:`, `Resource is not a script:`,
  `Script resource must be text, got base64:`, `Skill script failed: …`.
  A closed refusal vocabulary in all but name, and the same
  outcome-as-data discipline the Code Mode runtime uses.

## The catalog prompt

```ts
catalogPrompt: catalog.length
  ? [
      "Available skills. When a task matches a skill, use activate_skill with its name before proceeding.",
      ...(this.workspaceFiles
        ? [`Skill files are available at ${this.workspaceFiles.root}. Workspace edits affect later activations and resource reads.`]
        : []),
      "",
      ...catalog
    ].join("\n")
  : null
```

where each catalog line is:

```ts
catalog.push(`- ${descriptor.name}: ${descriptor.description}`);
```

**One line per skill, name and description only.** The body never enters
the prompt until `activate_skill` fires. That is the same progressive
disclosure Anthropic's skills use, expressed as ~40 lines of code, and
the whole always-on cost is one line per skill.

`null` when there are no skills — the section disappears rather than
rendering an empty heading, matching the context-blocks rule
([`context-blocks.md`](./context-blocks.md)) that an empty read-only
block is skipped.

The conditional second line is a nice touch: when skills are backed by a
workspace, the model is told **where they live and that editing them
changes later activations**. A skill surface the agent can modify is a
self-modifying prompt, and saying so is better than letting it be
discovered.

## Activation returns a tagged envelope

```ts
return [
  `<skill_content name="${skill.name}"${version}>`,
  skill.body.trim(),
  resourceList,
  "</skill_content>"
].join("\n");
```

with the resource manifest nested inside:

```
<skill_resources>
  <file kind="reference" encoding="text" size="2048">references/style-guide.md</file>
  <file kind="script" encoding="text">scripts/build.ts</file>
</skill_resources>
```

and a resource read coming back as:

```ts
`<skill_resource name="${target.name}" path="${resource.path}" kind="${resource.kind}" encoding="${encoding}"${mimeType}>`,
resource.content,
"</skill_resource>"
```

**The skill body arrives inside a named, attributed envelope** —
activating a skill visibly inserts *that skill's* text rather than
blending it into the conversation. Compare
`../agent-context-file-loading.md`'s clean negative, where OpenClaw ships
an `<untrusted-text>` wrapper and still injects `AGENTS.md`/`MEMORY.md`
raw. This is closer to right — though note the envelope is
**attributional, not an escaping wrapper**: nothing stops a skill body
containing `</skill_content>` and closing its own tag early. The
attributes are also unescaped string interpolation. For first-party
skills that is fine; for a skill loaded from R2 that someone else can
write to, it is the gap `agent-context-file-loading.md` keeps finding.

Listing the resources at activation time, rather than making the model
guess paths, is what makes `read_skill_resource` usable without a
directory listing tool.

## `SkillRunContext` — the part nobody else has

```ts
export interface SkillRunContext {
  /** Metadata for the skill that owns this script. */
  skill: SkillDescriptor;
  /** Text bundled resources by relative path (e.g. `references/style-guide.md`). */
  files: Record<string, string>;
  /** Workspace access, gated by the runner's `workspace` permission. */
  workspace: {
    readFile(path: string): Promise<string | null>;
    listFiles(path?: string): Promise<unknown>;
    glob(pattern: string): Promise<unknown>;
    stat(path: string): Promise<{ type: string; size: number } | null>;
    writeFile(path: string, content: string): Promise<void>;
  };
  /** Explicitly granted tools: `tools.call(name, input)` or `tools.<name>(input)`. */
  tools: {
    call(name: string, input?: unknown): Promise<unknown>;
  } & Record<string, (input?: unknown) => Promise<unknown>>;
  /** Scratch artifacts returned to the model as `outputFiles`. */
  output: {
    writeFile(name: string, content: string): Promise<void>;
  };
}
```

with the gating stated in the type's own doc comment:

> Capabilities are gated by the runner: `workspace` throws unless
> workspace access is enabled, and `tools` only resolves tools the runner
> was given.

This is the answer to a question `../agent-design/generative.md` §2e
raised and left open. That section adopted the rule that **a skill's
instructions are read and its code is executed, never `Read` into
context**, with the corollary that "an executable invoked without reading
is a trust decision". Cloudflare's answer to the trust decision is:
*the executable gets a capability object, and the runner decides what is
in it.*

Three consequences worth carrying:

- **A skill script cannot reach tools it was not handed.** `tools` only
  resolves what the runner was given — the same calling-convention
  property as Code Mode's providers-as-parameters, applied to skills.
- **`output.writeFile` produces artifacts**, returned to the model as
  `outputFiles`. So a script's result is not just a return value; it can
  mint files the model then refers to. That is the artifact channel
  arriving inside the skill system.
- **`workspace` throws rather than being absent** when disabled, which is
  the noisier and better choice — a skill that assumed filesystem access
  fails loudly instead of silently doing nothing.

`SkillDescriptor` also carries **`allowedTools`**, alongside `license`,
`compatibility` and `version`. The skill declares its own tool scope in
frontmatter. Neither Anthropic's nor DeepSeek's format has a
machine-enforced equivalent.

## No bundler in the runtime, and the consequence

```ts
/**
 * Set when a script resource was compiled to a self-contained JavaScript
 * module ahead of time — by the Agents Vite plugin for bundled skills, or via
 * `compileSkillScript` from `agents/skills/compile` for R2/dynamic skills. The
 * runtime runs precompiled scripts directly; the runtime ships no in-Worker
 * bundler, so non-precompiled TypeScript or multi-file scripts cannot run.
 */
precompiled?: boolean;
```

A constraint with a real upside: **a skill script is a single
self-contained module, compiled ahead of time**, so what runs is what was
reviewed. A skill that could `npm install` at activation time would be a
supply-chain surface inside a prompt. This one cannot.

Compare `../anthropic-skills/`, where a skill ships ~1.1 MB of XSD and
875-line validators as ordinary files and runs whatever the container
has.

## Sources, fingerprints and path safety

```ts
export interface SkillSource {
  id: string;
  fingerprint: string;
  list(): Promise<SkillDescriptor[]>;
  load(name: string): Promise<SkillContent | null>;
  readResource?(name: string, path: string): Promise<SkillResource | null>;
  refresh?(): Promise<void>;
}
```

Pluggable, with two shipped: a build-time manifest (`fromManifest`, wired
by the Vite plugin through an `agents:skills` import specifier) and
**R2** — skills loaded from object storage at runtime, refreshable.

**`fingerprint` on both the source and the registry snapshot** is the
cache key. It is what lets the catalog prompt be stable across turns —
and it is the same prefix-stability concern `freezeSystemPrompt()`
handles for context blocks ([`context-blocks.md`](./context-blocks.md)).
A skill set that changes fingerprint invalidates the cached prefix, which
is the honest cost of runtime-loadable skills and is at least made
visible.

Path traversal is handled once, structurally:

```ts
export function validateSkillResourcePath(path: string): string | null {
  if (
    path.startsWith("/") ||
    path.includes("\0") ||
    path.split("/").some((part) => part === "" || part === "." || part === "..")
  ) {
    return `Skill resource path must be a normalized relative path: ${path}`;
  }
  return null;
}
```

No leading slash, no NUL, no empty or dot segments. Small, complete, and
in one place — which matters because `read_skill_resource` accepts a
**qualified cross-skill path** (`release-notes/references/style-guide.md`),
so one skill can reference another's resources and the traversal surface
is wider than it first looks.

Frontmatter is standard YAML between `---` fences, parsed with the `yaml`
package rather than by regex beyond the fence match — so the format is
interoperable with the other two implementations.

## Where skills sit relative to context blocks

From `packages/think/README.md`:

> **Skills are on-demand instructions, not always-on system prompt text.**
> The model sees the catalog first, then calls `activate_skill` when a
> user task matches a skill description. Use a context block from
> `configureContext()` for behavior that should apply to every turn,
> especially when the agent also uses skills. `getSystemPrompt()` is a
> legacy fallback and is ignored once context blocks are configured.

That is the cleanest statement in the collection of **when something
should be a skill and when it should be standing context**, and it is the
distinction `../agent-context-file-loading.md` keeps circling: a skill is
matched against a task, a context block applies unconditionally. Getting
it wrong in either direction is expensive — always-on instructions that
should have been a skill burn tokens every turn; a skill that should have
been always-on fires only when the description happens to match.

## Against the other two implementations

| | Anthropic | DeepSeek | **Cloudflare** |
|---|---|---|---|
| Format | agentskills.io | repo-resident | agentskills.io |
| Disclosure | catalog → `SKILL.md` | assembled per request | catalog → `activate_skill` |
| Body arrives | inline | inline | **in a named envelope** |
| Scripts | run in the container, full access | — | **precompiled, gated capability context** |
| Declared tool scope | — | — | **`allowedTools`** |
| Runtime-loadable | no (mounted) | no | **yes (R2), with fingerprint** |
| Cross-skill resources | — | — | **qualified paths** |

The two columns that matter for a design are the last four. Cloudflare is
the only one of the three where **a skill is a capability grant rather
than a document**, and that is the version worth stealing — not because
the sandbox is strong (it is a Worker isolate, not a security boundary
against a determined skill author) but because it makes the question
*"what can this skill do?"* answerable by reading a type instead of
reading the script.
