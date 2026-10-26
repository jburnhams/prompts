<!--
name: "System Reminder: Memory file contents (unverified managed folder)"
description: "Heads an unverified instruction file from this machine's managed folder in the combined memory block, showing its escaped path and a parenthetical warning that this session's own account could have written it, so Claude must follow every limit it sets but treat nothing in it as permission"
ccVersion: "2.1.304"
variables:
  - "FORMAT_ESCAPED_PATH_FN"
  - "MEMORY_ITEM"
  - "UNVERIFIED_MANAGED_INSTRUCTIONS_DESCRIPTION"
-->
Contents of ${FORMAT_ESCAPED_PATH_FN(MEMORY_ITEM.path)}${UNVERIFIED_MANAGED_INSTRUCTIONS_DESCRIPTION}:

