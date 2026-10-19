<!--
name: "System Reminder: Background command quiet check-in"
description: "Tells the model to inspect silent background commands for progress or hangs, stop stuck work, and end its turn for healthy long-running tasks"
ccVersion: "2.1.293"
variables:
  - "FORMAT_DURATION_FN"
  - "NEXT_CHECKIN_SILENCE_MS"
  - "OTHER_SILENT_COMMANDS_BLOCK"
-->

This is a check-in, not a completion. The command may be working quietly, or it may be hung: waiting on a lock, on input, or on a process that will never exit. Find out which before you wait any longer: read its output file and look at its processes. If it is stuck, stop this task and get the work done another way. If it is making progress, or is meant to keep running (a server, a watcher), leave it and end your turn. The next check-in comes after another ${FORMAT_DURATION_FN(NEXT_CHECKIN_SILENCE_MS)} of silence.${OTHER_SILENT_COMMANDS_BLOCK&&`
It speaks for your other background commands too, which get none of their own. Look at any that has been silent for longer than it should:${OTHER_SILENT_COMMANDS_BLOCK}`}
