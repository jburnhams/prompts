# Anthropic — "Code execution with MCP"

- **Type**: published design pattern, not a readable implementation ·
  **Vendor**: Anthropic
- **Source**:
  [anthropic.com/engineering/code-execution-with-mcp](https://www.anthropic.com/engineering/code-execution-with-mcp)
  (November 2025), read 2026-09-20
- **Status**: prose and illustrative code. No repository ships this; it
  is a pattern description, and everything below is quoted from the post
  rather than read from source.

Kept because it states the *why* more crisply than the implementations
do, and because its answer to progressive disclosure — a **filesystem**
— is different from Cloudflare's (`search`/`describe`) and worth having
side by side.

## The two problems

> Tool definitions overload the context window

> Most MCP clients load all tool definitions upfront directly into
> context.

and

> Every intermediate result must pass through the model.

with a worked cost:

> the full call transcript flows through twice. For a 2-hour sales
> meeting, that could mean processing an additional 50,000 tokens.

The second is the one this collection has been circling from several
directions — `../agent-tool-result-transport.md` §7 ("the school that
avoids the question by not putting results in context at all"),
`../deepseek-harness/`'s "intermediate tool results never enter the
conversation", and `../agent-data-analysis.md` §6c's preview-plus-handle
pattern, which is the *non*-Code-Mode answer to the same problem.

## Tools as files

```
servers
├── google-drive
│   ├── getDocument.ts
│   └── index.ts
├── salesforce
│   ├── updateRecord.ts
│   └── index.ts
```

Each leaf is a thin typed wrapper over the MCP call:

```typescript
export async function getDocument(input: GetDocumentInput): Promise<GetDocumentResponse> {
  return callMCPTool<GetDocumentResponse>('google_drive__get_document', input);
}
```

and the model writes a program that imports them:

```typescript
import * as gdrive from './servers/google-drive';
import * as salesforce from './servers/salesforce';

const transcript = (await gdrive.getDocument({ documentId: 'abc123' })).content;
await salesforce.updateRecord({...});
```

> reduces the token usage from 150,000 tokens to 2,000 tokens—a time and
> cost saving of 98.7%

That figure is one vendor-chosen workflow and should be read as an
illustration of the mechanism rather than an expected ratio.

## The four claimed benefits

1. **Progressive disclosure** — models "navigate filesystems and load
   definitions on-demand rather than upfront".
2. **Context-efficient results** — agents can "filter and transform
   results in code before returning them".
3. **Privacy** — "Intermediate results stay in the execution environment
   by default".
4. **State persistence** — progress maintained across operations through
   file storage.

## Why the filesystem framing is the interesting one

Cloudflare solves discovery with two methods the model calls
(`codemode.search()`, `codemode.describe()`). Anthropic solves it with a
directory the model already knows how to explore — `ls`, `cat`, `grep`,
and an import path.

The second reuses a skill the model has in abundance and a tool surface
the harness already has. For a coding agent with `Read` / `Grep` / `List`
this is close to free: **the tool catalogue becomes a repository**, and
everything the collection already knows about reading a repository
efficiently (outlines before bodies, ranged reads, search before read)
applies unchanged.

The cost is that it only works where there *is* a filesystem and the
agent can read it — which is true of a coding agent and false of a
browser tab, where Cloudflare's method-call discovery is the available
shape. The two are not competing; they are the same idea bound to
whatever substrate is present.

Point 3 is also the one that reads differently depending on deployment.
"Intermediate results stay in the execution environment" is a privacy
claim about a server-side sandbox. Run the same pattern in the user's
browser and it becomes something stronger — the intermediate results
never leave the user's machine at all, because the execution environment
*is* the machine. See [`../agent-local-compute.md`](../agent-local-compute.md)
§6.
