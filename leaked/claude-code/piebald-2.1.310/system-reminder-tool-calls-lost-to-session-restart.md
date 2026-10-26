<!--
name: "System Reminder: Tool calls lost to session restart"
description: "Lists calls from the previous turn that have no result after a session restart and tells Claude to check whether they ran before issuing them again"
ccVersion: "2.1.309"
variables:
  - "ARE_LOST_CALLS_OMITTED_FROM_TRANSCRIPT"
  - "LOST_CALL_COUNT"
  - "LOST_CALL_LABELS"
-->
${ARE_LOST_CALLS_OMITTED_FROM_TRANSCRIPT?`Besides the tool calls answered above, your previous turn had also issued ${LOST_CALL_COUNT===1?"a call that is no longer shown above and that has":"calls that are no longer shown above and that have"} no result`:`This session restarted during your previous turn. Besides the tool calls answered above, that turn had also issued ${LOST_CALL_COUNT===1?"a call whose result was":"calls whose results were"} lost to the restart`}: ${LOST_CALL_LABELS.join(", ")} — ${LOST_CALL_COUNT===1?"it":"they"} may not have run, or not completely. Check before issuing ${LOST_CALL_COUNT===1?"it":"them"} again, and decide whether ${LOST_CALL_COUNT===1?"it is":"they are"} still needed.
