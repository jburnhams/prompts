# Arquero

- **Type**: in-memory dataframe library for JavaScript · **Vendor**: UW
  Interactive Data Lab (Jeff Heer) · **Licence**: BSD-3-Clause
- **Source**: https://github.com/uwdata/arquero — `main` @ `e8003b4`,
  version `8.0.3` (2025-05-29)
- **Retrieved**: 2026-09-20
- **Dependencies**: `@uwdata/flechette` (Arrow), `acorn` (JS parser)

The other shape a JavaScript data tool can take: **verbs on a table**
rather than a SQL string. Included as the counter-case to
[`../hyperparam/`](../hyperparam), because the two make opposite bets
about what the model should emit, and the difference has a safety
consequence that is easy to miss.

## The API

From the README:

```js
import { all, desc, op, table } from 'arquero';

// Average hours of sunshine per month, from https://usclimatedata.com/.
const dt = table({
  'Seattle': [69,108,178,207,253,268,312,281,221,142,72,52],
  'Chicago': [135,136,187,215,281,311,318,283,226,193,113,106],
  'San Francisco': [165,182,251,281,314,330,300,272,267,243,189,156]
});

// Sorted differences between Seattle and Chicago.
// Table expressions use arrow function syntax.
dt.derive({
    month: d => op.row_number(),
    diff:  d => d.Seattle - d.Chicago
  })
  .select('month', 'diff')
  .orderby(desc('diff'))
  .print();

// Aggregate statistics per city, as output objects.
// Reshape (fold) the data to a two column layout: city, sun.
dt.fold(all(), { as: ['city', 'sun'] })
  .groupby('city')
  .rollup({
    min:  d => op.min(d.sun),
    max:  d => op.max(d.sun),
    avg:  d => op.average(d.sun),
    med:  d => op.median(d.sun),
    skew: ({sun: s}) => (op.mean(s) - op.median(s)) / op.stdev(s) || 0
  })
  .objects()
```

> The core abstractions in Arquero are *data tables*, which model each
> column as an array of values, and *verbs* that transform data and return
> new tables. Verbs are table methods, allowing method chaining for
> multi-step transformations. Though each table is unique, many verbs
> reuse the underlying columns to limit duplication.

Columnar, immutable-by-verb, with column reuse between derived tables.
`fold` / `pivot` / `spread` cover the reshaping that
[`squirreling`](../hyperparam/engine-contracts.md) lacks, and `op.*`
carries statistical aggregates (`corr`, `stdev`, quantiles) that it also
lacks.

## The interesting part: expressions are a restricted DSL, not JavaScript

`d => d.Seattle - d.Chicago` **looks** like a callback and is not one.
`src/expression/parse-expression.js` parses the arrow function's source
with `acorn` (`ecmaVersion: 11`), walks the AST, and rejects anything
outside a permitted vocabulary. The error constants are the spec:

```js
const NO = msg => (node, ctx) => ctx.error(node, msg + ' not allowed');
const ERROR_AGGREGATE   = NO('Aggregate function');
const ERROR_WINDOW      = NO('Window function');
const ERROR_ARGUMENT    = 'Invalid argument';
const ERROR_COLUMN      = 'Invalid column reference';
const ERROR_AGGRONLY    = ERROR_COLUMN + ' (must be input to an aggregate function)';
const ERROR_FUNCTION    = 'Invalid function call';
const ERROR_MEMBER      = 'Invalid member expression';
const ERROR_OP_PARAMETER = 'Invalid operator parameter';
const ERROR_PARAM       = 'Invalid param reference';
const ERROR_VARIABLE    = 'Invalid variable reference';
const ERROR_VARIABLE_OP = 'Variable not accessible in operator call';
const ERROR_DECLARATION = 'Unsupported variable declaration';
const ERROR_DESTRUCTURE = 'Unsupported destructuring pattern';
const ERROR_CLOSURE     = 'Table expressions do not support closures';
const ERROR_ESCAPE      = 'Use aq.escape(fn) to use a function as-is (including closures)';
```

So: no closures, no free variables, no arbitrary function calls — only
`op.*`, column references off the row parameter, literals, and `$`
params. The parsed AST is then compiled by `src/expression/codegen.js`,
which errors on anything it does not recognise:

```js
: error(`Unsupported expression construct: ${node.type}`);
```

**Two readings of this, and both matter for an agent design.**

The optimistic one: an Arquero expression is about as constrained as a
SQL expression. A model emitting `d => op.mean(d.revenue)` is emitting
data-in-the-shape-of-code, validated against a closed operator set before
anything runs. It is not a general JavaScript escape.

The cautious one: `aq.escape(fn)` exists specifically to opt *out* — it
takes a real closure and runs it as-is. And unlike squirreling, Arquero's
path ends in **code generation**: the verified AST is compiled to a
function. The safety therefore rests on the completeness of the
verifier rather than on the absence of an interpreter, which is a
strictly weaker position (`../../agent-data-analysis.md` §10b makes the
same allowlist-versus-absence argument about SQL).

For a harness, the practical consequence is that **Arquero expressions
are model-writable, `aq.escape` is not** — and that distinction has to be
enforced by the harness, because nothing in the library draws it.

## Verbs or SQL?

| | Arquero verbs | Squirreling SQL |
|---|---|---|
| Model emits | a chained JS expression | a SQL string |
| Validation | AST walk against `op.*`, then codegen | parse to AST, interpret |
| Ends in codegen? | **yes** | no |
| Reshaping (`fold`/`pivot`) | yes | no |
| Stats (`corr`, `stdev`, quantiles) | yes | partial |
| Window functions | full | `ROW_NUMBER`, `LAG`, `LEAD` |
| Streaming / async | no — in-memory, synchronous | yes — `AsyncGenerator` rows |
| Remote sources | load first, then operate | scan with pushdown |
| Async UDFs (an `llm()` call) | **no** | yes |
| Dependencies | 2 | 0 |

The split is cleaner than it looks. Arquero is the better **in-memory
analytical** library: more reshaping, more statistics, better window
support. Squirreling is the better **agent** engine: async to the core,
streams from remote columnar files, and has somewhere to put a
model-backed UDF.

And for the specific question of what a model should write, SQL has an
advantage that has nothing to do with capability — a model that emits
SQL is emitting a string that the harness can plan, inspect, cost and
allowlist *before execution*
([`squirreling-mcp`](../hyperparam/squirreling-mcp-tools.md) already
walks the plan for scan nodes). A chained verb expression has to be
parsed by the library to learn the same things, and the library parses it
on the way to running it.

## Also in this space, not read as source

- **tidy.js** (`pbeshai/tidy`) — tidyverse-shaped, pure TS, smaller scope.
- **Danfo.js** — pandas-shaped, but carries TensorFlow.js.
- **Data-Forge** — LINQ-shaped, TS.
- **Perspective** (FINOS) — streaming analytics with a WASM core and a
  virtualized grid; the closest thing to `hightable` + an engine in one.

None was read from source in this pass. Arquero was chosen as the
representative because it is the most widely used, has the clearest
expression-safety story to examine, and comes from the same lab as
Vega-Lite — which matters for
[`../../agent-design/data.md`](../../agent-design/data.md) §2e, where the
chart contract is a Vega-Lite spec.
