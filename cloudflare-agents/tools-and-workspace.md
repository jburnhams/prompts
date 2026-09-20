# The tool surface: a filesystem and a git client, as a sandbox API

`packages/shell/src/prompt.ts`, `packages/shell/src/git/provider.ts`,
`docs/shell/index.md` at `c076e4c`. `@cloudflare/shell` is marked
experimental.

The part of this SDK most relevant to the **coding** half of this
collection, and the one a data-focused first read skipped entirely.
`@cloudflare/shell` gives an agent a durable filesystem and a git client
— not as tools, but as **typed globals inside the Code Mode sandbox**.

## `STATE_SYSTEM_PROMPT`, verbatim

```js
export const STATE_SYSTEM_PROMPT = `
You can write JavaScript code that runs inside an isolated sandbox with access to a persistent
virtual filesystem through the \`state\` object.

Rules:
- Write an async function: \`async () => { ... return result; }\`
- Do NOT use TypeScript syntax — no type annotations, interfaces, or generics in your code.
- Do NOT use \`import\` statements — all helpers are available through \`state\`.
- Every \`state\` method takes a single object argument: \`state.readFile({ path: "/x.txt" })\`.
- Always \`return\` the final value you want back.
- For multi-file refactors, prefer \`planEdits()\` + \`applyEditPlan()\` over many individual writes.
- For search-and-replace across a tree, use \`replaceInFiles()\` — it is transactional by default.

Available API (TypeScript reference):

\`\`\`typescript
{{types}}
\`\`\`
`.trim();
```

with, from the file's own doc comment:

```
 * TypeScript declaration for the `state` object injected into every isolate
 * execution. Export this string in prompts so the LLM knows the exact API it
 * can call.
 *
 * Usage:
 *   import { STATE_TYPES, STATE_SYSTEM_PROMPT } from "@cloudflare/shell";
 *   const system = STATE_SYSTEM_PROMPT.replace("{{types}}", STATE_TYPES);
```

Seven rules, and **the last two are the interesting ones** — they are not
syntax constraints, they are *editing methodology*:

> - For multi-file refactors, prefer `planEdits()` + `applyEditPlan()` over many individual writes.
> - For search-and-replace across a tree, use `replaceInFiles()` — it is transactional by default.

`agent-tool-implementations.md` catalogues edit formats as a choice
between whole-file rewrite, search/replace blocks, and diffs, and treats
multi-file refactors as *n* independent edit calls. This prompt says:
**plan the whole refactor, then apply it as one transaction.** That is a
different shape from anything in the collection's edit-format section,
and it is reachable only because the "tools" are an API — a plan object
is an ordinary value you can build, inspect and hand back.

The two prohibitions match Code Mode's browser path word for word ("Do
NOT use TypeScript syntax"), for the same reason: the string goes through
`new Function`.

## The `state.*` API

24 methods in the injected declaration:

| Group | Methods |
|---|---|
| Capability probe | `getCapabilities` |
| Read/write | `readFile`, `readFileBytes`, `writeFile`, `writeFileBytes`, `appendFile` |
| JSON-aware | `readJson`, `writeJson`, **`queryJson`**, **`updateJson`** |
| Metadata | `exists`, `stat`, `lstat` |
| Directory | `mkdir`, `readdir`, `readdirWithFileTypes`, `rm` |
| Traversal | `find`, `walkTree`, **`summarizeTree`** |
| Search | `searchText`, `searchFiles` |
| Edit | `replaceInFile`, **`replaceInFiles`** |

plus `planEdits()` / `applyEditPlan()` named in the prompt.

Four observations against the collection's existing tool analysis:

**`getCapabilities()` is capability discovery as a call.**

```ts
type StateCapabilities = { chmod: boolean; utimes: boolean; hardLinks: boolean };
```

The backing store is SQLite or D1, not a POSIX filesystem, so some
operations genuinely do not exist. The agent asks rather than
discovering by failure — the same move as
[`../data-agents/matlab-mcp/`](../data-agents/matlab-mcp)'s
`detect_matlab_toolboxes`, and the answer Python harnesses give
statically in a prompt allowlist.

**`summarizeTree` is the outline-before-bodies read, at directory
level.** `agent-tool-implementations.md` records OMP's `read.summarize`
(declarations with bodies elided) as the only instance of returning a
skeleton rather than content. This is the same idea one level up, and it
exists for the same reason: a whole tree does not fit.

**Transactionality is a first-class option, not a convention.**

```ts
type StateReplaceInFilesOptions = StateSearchOptions & {
  dryRun?: boolean;
  rollbackOnError?: boolean;
};
type StateApplyEditsOptions = { dryRun?: boolean; rollbackOnError?: boolean };
```

`dryRun` and `rollbackOnError` on every multi-file mutation. A partial
multi-file refactor is one of the worst states a coding agent can leave a
tree in — half-renamed symbols, a build that fails for a reason unrelated
to the change — and no harness in this collection offers either flag.
`dryRun` in particular is the counterfactual tool
[`../data-agents/postgres-mcp/`](../data-agents/postgres-mcp)'s
`explain_query` provides for SQL: *what would this do*, answerable
without doing it.

**Search returns structured matches, not grep output.**

```ts
type StateTextMatch = {
  line: number; column: number; match: string; lineText: string;
  beforeLines?: string[];  // …
};
type StateSearchOptions = {
  caseSensitive?: boolean; regex?: boolean; wholeWord?: boolean;
  contextBefore?: number; contextAfter?: number; maxMatches?: number;
};
```

Compare `agent-design/formats.md` §8a, which has to solve "how do match
lines stay distinguishable from structural lines" because the result is
*text*. Here the result is an object and the question does not arise —
which is the general advantage of the Code Mode framing, and the reason
`agent-tool-implementations.md` §5's rule that **"Code Mode must never
parse"** a human-readable string is satisfiable at all.

`maxMatches` is the cap, as a parameter rather than a harness default the
model cannot see.

## `git.*` — a git client in the sandbox

`packages/shell/src/git/provider.ts` exposes fourteen methods:

```
add  branch  checkout  clone  commit  diff  fetch  init
log  pull  push  remote  rm  status
```

**This is a whole VCS surface reached without a shell.** Every coding
agent in this collection runs git through `Bash` —
`agent-git-vcs.md` is largely an analysis of *shell invocations* and the
parsing and safety problems that follow: quoting, `--force` detection,
parsing porcelain output, the difference between "the command failed" and
"the command succeeded and said something you did not expect".

A typed `git.status()` returning an object removes an entire class of
that. It also removes the escape hatch: there is no `git` flag you can
reach for that the provider did not implement, and no `git rev-parse`
plumbing call for the odd case.

The trade is the same one `agent-tool-surfaces.md` draws between a
general shell and focused tools, arriving in the one place the
collection had assumed a shell was mandatory. Worth stating plainly
because it is a live design question rather than a settled one: **a git
API is safer and less capable; a git shell is more capable and needs
every guard `agent-git-vcs.md` catalogues.**

## Workspace: the durable filesystem underneath

`docs/shell/index.md`:

> Workspace provides a durable virtual filesystem backed by SQLite and
> optional R2 large-file storage. It works with any Durable Object that
> has SQLite storage, D1 databases, or custom SQL backends.

```typescript
class MyAgent extends Agent<Env> {
  workspace = new Workspace({
    sql: this.ctx.storage.sql,
    name: () => this.name
  });
}
```

| Option | Default | Description |
|---|---|---|
| `sql` | **required** | `SqlStorage \| D1Database \| SqlBackend` |
| `namespace` | `"default"` | Table namespace for isolation |
| `r2` | `null` | R2 bucket for large files |
| `inlineThreshold` | `1_500_000` | **Byte size above which files spill to R2** |
| `onChange` | `undefined` | Callback on create, update, delete |

Two things worth lifting:

**`inlineThreshold` is the spill rule, as configuration.** Small files
live in SQL rows; past 1.5 MB they go to object storage, transparently.
That is exactly the artifact-spill contract
[`../agent-design/artifacts.md`](../agent-design/artifacts.md) §4
specifies for tool results, applied to a filesystem, with the threshold
as a tunable rather than a constant.

**`onChange` makes mutation observable.** A harness that wants to show
the user what an agent touched, or maintain an index, or gate on a path
pattern, has one hook rather than having to wrap every write.

And a small, real detail about the substrate:

> In Durable Objects, `this.name` may not be resolvable at class field
> initialization time (for example, reading it throws when the object was
> addressed by raw id instead of by name). Pass a function to defer
> evaluation.

The `SqlBackend` interface is two methods (`query`, `run`), either sync
or async — so the same Workspace runs on Durable Object SQLite, on D1, or
on anything you can wrap. Same pluggable-resolver shape as
[`../data-agents/hyperparam/`](../data-agents/hyperparam)'s
`AsyncDataSource`, for files rather than tables.

## Why this matters to the collection

Read together, `state.*` + `git.*` + Workspace is **a complete coding-agent
tool surface expressed as a typed API rather than as tools** — file
read/write, structured search, transactional multi-file edit, tree
summarisation, and version control, with `dryRun` on the dangerous ones.

Everything `agent-tool-implementations.md` says about Read/Edit/Write/Grep
— the caps, the truncation notices, the delimiter problems, the
stale-line-number hazard — is a consequence of those tools returning
**text to a model**. This is the same capability set with the text
removed, and the interesting question it raises is which of those
problems were essential and which were artefacts of the transport.

The honest limits: it is a *virtual* filesystem, so nothing outside it
exists; there is no process execution, so no build, no test run, no
linter; and `@cloudflare/shell` is experimental. It is a tool surface for
an agent that edits and commits, not one that verifies.
