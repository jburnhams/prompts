<!--
name: "System Reminder: Resume agents interrupted by container restart"
description: "Lists interrupted agents whose results were lost and asks the parent to resume them from saved transcripts before relaunching"
ccVersion: "2.1.299"
variables:
  - "INTERRUPTED_AGENT_LIST"
  - "SEND_MESSAGE_TOOL_NAME"
-->
The container was restarted in the middle of a turn. You launched each agent in this list in that turn. Each is now stopped, and its result never reached you.
${INTERRUPTED_AGENT_LIST.join(`
`)}
If you still need an agent's result, resume it rather than launch it again: send a message to its agent id with the ${SEND_MESSAGE_TOOL_NAME} tool. It continues from its saved transcript, which still holds its task, so it is enough to ask it to continue from where it stopped. You get its result when it is done. If the resume fails, launch the agent again.
