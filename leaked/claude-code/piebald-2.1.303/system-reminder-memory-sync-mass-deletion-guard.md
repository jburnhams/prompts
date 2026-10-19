<!--
name: "System Reminder: Memory sync mass-deletion guard"
description: "Reports that memory sync withheld all shared-memory deletions because too many synced memory files vanished from local disk at once, and how to remove memories deliberately in small spaced batches"
ccVersion: "2.1.280"
variables:
  - "MISSING_MEMORY_FILE_COUNT"
  - "MAX_DELETIONS_PER_BATCH"
-->
Memory sync did NOT delete anything from shared memory this cycle: ${MISSING_MEMORY_FILE_COUNT} synced memory files went missing from this session's disk at once, which almost always means the local memory folder was wiped rather than deliberately cleared. Shared memory is unchanged and the missing files will be restored on the next sync. If you really do intend to remove that many memories, wait until the missing files have been restored, then delete at most ${MAX_DELETIONS_PER_BATCH} at a time with about a minute between batches so memory sync can apply each one.
