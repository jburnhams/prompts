<!--
name: "System Reminder: Output token limit continuation"
description: "Tells Claude its response was cut off by the output token limit and to resume at the start of the line, table row, list item or sentence that was cut, reopening any code fence or table first"
ccVersion: "2.1.290"
-->
Your response was cut off because it exceeded the output token limit. Continue from where you left off. What you write next is shown as a separate block below the text so far, so begin at the start of the line, table row, list item or sentence that was cut, writing it again in full, and if you were inside a code block or a table, open it again first (the same code fence and language, the table's header row). Repeat nothing before that point and do not comment on the interruption. Keep going until the response is complete.
