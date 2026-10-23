# Keel: authority

Principals, on-behalf-of, delegations, and permissions in the RBAC system. Part of [Keel](./README.md). Section numbers are shared across Keel's files, so a reference like §7f means the same section everywhere; [the README](./README.md#files) lists which file holds each.

---

## 8. Principals and on-behalf-of

Every run records three identities:

| Field | Meaning | Example |
|---|---|---|
| `principal` | on whose behalf it acts; whose authority downstream systems check | the engineer who moved the ticket |
| `requested_by` | who caused it | the API caller, the trigger owner, the person who approved a gate |
| `actor` | the agent's own identity, as it appears in downstream audit logs | `forge-bot` |

**Effective authority = template grant ∩ principal entitlement ∩
delegation scopes.** The template says what the job may ever do. The
principal's own permissions bound it to what that person could do. A
delegation, if one is used, narrows it further.

How the intersection is enforced depends on the server's auth mode:

- **`obo`**: the credential broker exchanges the principal's credential
  for an audience-scoped token, per call (RFC 8693 token exchange).
  Downstream enforces the principal's entitlement. The token never
  enters context. This is the default for anything user-facing; it's
  what makes `Expand` able to reveal only "what the user is already
  granted" (`../models.md` §4a) without the harness keeping a copy of
  everyone's permissions.
- **`service`**: calls run as the service principal. Downstream sees
  `forge-bot` and enforces nothing about the user. That's correct for
  review runs, which belong to no user, and it's a **confused deputy**
  in any template a user may run: they would act with the bot's rights,
  not their own. R12 rejects a template that a user may run
  (`authority.run_as` includes `user`) and that grants a non-read-only
  tool on a service-credentialed server, unless the server declares
  `entitlement_check: harness_policy`. With that set, the harness checks
  the principal against the resource before each write call.
- **`none`**: public or local tools.

**Delegation is how a user acts while absent.** A schedule at 07:47 on a
Monday, a Jira event, or a continuation that starts after the user has
gone home has no live session to exchange. A `Delegation` is the user's
stored consent:

- it is for one template or one pipeline, from `min_version`;
- it carries OBO scopes per server, within what the template declares;
- it can constrain params ("only repository X");
- it carries `consented_spec_digest`, a digest of the servers, scopes
  and write tools the user was shown;
- it has an expiry, capped by the template's `max_ttl_days`.

A later template version whose consent-relevant digest differs needs
re-consent (`:publish` lists the delegations affected). A delegation is
created only by the user it names, in an interactive session, because
the IdP may need them to approve the scopes. Revoking it is immediate.

Triggers choose `run_as`:

- `service`: the review trigger.
- `delegation`: the weekly digest. It names a delegation its owner
  granted.
- `event_actor`: the Jira trigger. The person who assigned the ticket
  is the principal, but only if they hold a delegation for this
  pipeline; otherwise `fallback: refuse`. This is deliberately not "run as
  whoever commented". Mapping a provider account to an IdP subject is
  necessary, and it isn't sufficient: consent is still needed.
- `invoker`: the chat trigger, and `manual` sources only. The user is
  present, so no stored consent is needed. But a pipeline's later stages
  may outlive the chat request, so the harness mints a **session
  delegation**: scoped to this one pipeline run, the user's current
  session scopes, the template's or pipeline's declared scopes, and
  expiring when the pipeline run ends or after 24 hours, whichever is
  first (the deployment's `session_delegation_max_s`). It's created from the
  live session, so there is nothing for the user to approve, and it
  can't be reused by any other request.

  **A gate answered after the session has ended doesn't revive it.** If
  the follow-up needs to act for the user, it needs a stored delegation
  from them; otherwise the edge refuses with `delegation_missing` and
  the stage is blocked. The approver's own session is never used to act
  for someone else. That keeps one rule: a run acts with the authority
  of the person it's for, or with the service identity, and never with
  the authority of whoever happened to click.

**Gates use the same identities.** Who may answer is a
`PrincipalSetRule` list (`principal`, `requested_by`,
`issue_assignee`, `issue_reporter`, `pr_author`, `trigger_owner`, a
named principal, an RBAC team). It's resolved when the reply arrives,
not when the question was asked, exactly as `../formats.md` §5a specifies.
An empty resolved set is said in the posted question.

---

## 12a. Permissions and RBAC

Authorisation is the RBAC system's, and it's outside this spec. There,
a **role** is a set of permission groups, assigned to a **team**, and a
user has what their teams' roles grant. That's the only meaning of
"role" anywhere in this spec ([`taxonomy.md`](./taxonomy.md)).
Keel names the permissions it checks, and RBAC decides who has them:

| Permission | Lets the holder |
|---|---|
| `templates:write`, `templates:publish` | draft, and publish or deprecate, templates (likewise `pipelines:*`, `tool-groups:*`) |
| `servers:write` | register MCP servers and run `:discover` |
| `runs:create` (per template or pipeline) | start runs of it as themselves |
| `runs:adhoc` | run an unsaved spec |
| `runs:as-service` (per template) | start runs, or create triggers, with `run_as: service` |
| `runs:read`, `runs:transcript` | see runs; read full transcripts, separately audited |
| `triggers:write` | create triggers they own |
| `pipeline-runs:operate` | stage `:retry`, `:abandon`, `:stop` on runs they didn't start |
| `stages:link` | write a stage's links back (held by the committer's service identity) |
| `deployment:write` | change the tier map and ceilings |

Two things RBAC does **not** decide, deliberately:

- **What a run may do.** That's the template's grant intersected with
  the principal's own access downstream (OBO, §8). Holding
  `runs:create` on `coding.java` lets you start it, and nothing more.
- **Who may answer a gate.** That's the gate's principal set (assignee,
  reporter, a named principal, or a `team`), resolved when the reply
  arrives. A team in a principal set is an RBAC team, read for
  membership only.
