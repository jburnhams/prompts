# Keel: API

The resources and operations, summarised. The wire contract is `openapi.yaml`. Part of [Keel](./README.md). Section numbers are shared across Keel's files, so a reference like §7f means the same section everywhere; [the README](./README.md#files) lists which file holds each.

---

## 12. API

[`openapi.yaml`](./openapi.yaml). Problem+json errors with the
closed `RefusalCode` vocabulary (the same codes tool results use,
`../generative.md` §2b). `Idempotency-Key` on every create. Cursor
pagination. `:verb` for actions.

| Resource | Operations |
|---|---|
| MCP servers | CRUD, `:discover` (new snapshot + diff), `snapshots/{digest}` |
| Tool groups | versions: draft create/replace, get, `:publish` (pins snapshots, checks R13), `:preview` (each tool as the model sees it) |
| Prompts, report schemas | versioned create, get |
| Templates | list, versions, draft create/replace, `:validate`, `:publish`, `:deprecate`, `:render` |
| Pipelines | list, versions, draft create, get, `:publish` (P1–P8) |
| Pipeline runs | list (by state, subject, and `health=` for `../orchestration.md` §7's queries), get, stage `:link` (the committer's PR), stage `:retry`, `:abandon`, `:stop` |
| Runs | create for a template, a pipeline or an `adhoc` body (or `dry_run`), get, list (by template, state, principal, root, pipeline run), `events` (SSE), `transcript`, `artifacts`, `:stop`, delivery `:retry` |
| Gates | list (`answerable_by=me`), get, `replies`, `:cancel` |
| Triggers | CRUD, `:fire` (test by default), `:pause`, `:resume`, `firings` |
| Events | `POST /v1/events/{provider}`: signed inbound webhooks; gate replies arriving as comments go through here too |
| Delegations | create (with a consent URL), list own, get, revoke |
| Deployment | get, put (operators) |

Two deliberate absences. There's **no endpoint that edits a published
template**, and **no endpoint that changes a running run's spec**. The
only things that act on a running run are `:stop` (which goes through
the nudge) and a delegation revoke (which fails its next OBO call).
