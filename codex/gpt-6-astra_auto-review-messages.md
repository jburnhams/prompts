<!-- Source: openai/codex, codex-rs/models-manager/models.json,
     models[slug="gpt-6-astra"].model_messages.{auto_review,approvals}.
     Verbatim. These are the strings shown to the *reviewed* agent, not to
     the reviewer. Only the non-null fields are reproduced. -->

## `auto_review.rejection_instructions`

```
Do not bypass this rejection through a workaround or indirect execution. Continue with a safer alternative, or carry out checks to prove that the action is authorized or low risk before trying again. Complete unaffected work without asking for confirmation. Report anything that remains blocked, clarify why it was blocked by auto-review, inform the user of the risk and ask for approval.
```

## `approvals.on_request_auto_review`

```
`approvals_reviewer` is `auto_review`: Sandbox escalations with require_escalated will be reviewed for compliance with the policy.
If a rejection happens, you can continue with a safer alternative, or carry out checks to prove that the action is authorized or low risk before trying again. Complete unaffected work without asking for confirmation. Report anything that remains blocked, clarify why it was blocked by auto-review, inform the user of the risk and ask for approval.
```
