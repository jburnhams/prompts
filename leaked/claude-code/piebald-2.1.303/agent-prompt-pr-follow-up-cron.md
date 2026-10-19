<!--
name: "Agent Prompt: PR follow-up cron"
description: "Cron prompt for checking a pull request created in the session and fixing failures, comments, or conflicts"
ccVersion: "2.1.284"
variables:
  - "PR_INSTRUCTIONS_PREFIX"
  - "PR_REFERENCE"
  - "PR_NUMBER"
  - "GITHUB_REPOSITORY"
  - "IS_PR_STEWARD_ENABLED"
  - "CRON_DELETE_TOOL_NAME"
  - "PR_STEWARD_LABEL_CHECK_BLOCK"
  - "PR_COMMON_OPERATIONS_NOTE"
-->
${PR_INSTRUCTIONS_PREFIX}${PR_REFERENCE} (created in this session). Check state with `gh pr view ${PR_NUMBER} -R ${GITHUB_REPOSITORY} --json state,mergeable,mergeStateStatus,statusCheckRollup${IS_PR_STEWARD_ENABLED?",labels":""}` and new review comments with `gh api --paginate repos/${GITHUB_REPOSITORY}/pulls/${PR_NUMBER}/comments`. If MERGED or CLOSED, delete this cron with ${CRON_DELETE_TOOL_NAME} and report the outcome.${PR_STEWARD_LABEL_CHECK_BLOCK} If CI is failing, comments are unaddressed, or there are merge conflicts, fix and push.${PR_COMMON_OPERATIONS_NOTE} Otherwise nothing to do — complete the turn without commentary.
