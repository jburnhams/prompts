<!--
name: "System Reminder: Auto mode deny rules without safety result"
description: "Explains why auto-mode deny rules prevent a fallback approval prompt when the safety check is unavailable and directs the agent to report blocked work"
ccVersion: "2.1.314"
variables:
  - "REQUESTED_TOOL"
  - "CLASSIFIER_RESULT_UNAVAILABLE_REASON"
  - "RETRY_OR_CONTINUE_GUIDANCE"
-->
${REQUESTED_TOOL.name} was not run: auto mode's safety check ${CLASSIFIER_RESULT_UNAVAILABLE_REASON===void 0?"does not run for this session":"gave no result"}, and nobody is asked to approve it in its place, because the settings hold auto mode deny rules, which only the automatic check applies. This is not a judgment that the action is unsafe. ${CLASSIFIER_RESULT_UNAVAILABLE_REASON===void 0?"Other actions that need the check will be denied too, and retrying won't help. Finish what you can without them, then tell the user what is blocked and why.":`${RETRY_OR_CONTINUE_GUIDANCE} then tell the user that it was not run and why.`}
