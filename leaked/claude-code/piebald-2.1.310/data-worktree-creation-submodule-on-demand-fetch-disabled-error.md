<!--
name: "Data: Worktree creation submodule on-demand fetch disabled error"
description: "Error text appended when worktree creation hits a missing git object with on-demand fetching off in a submodule whose git folder is sandbox-writable, telling the user to inspect that folder for tampering and fetch the commit's objects themselves"
ccVersion: "2.1.309"
variables:
  - "SUBMODULE_GIT_DIR_PATH"
  - "SAFE_DISPLAY_PATH_FN"
  - "BASE_COMMIT_SHORT_SHA"
-->

This checkout ran with git's on-demand fetching switched off, and git needed an object this repository does not have. This repository is a git submodule, and its git folder${SUBMODULE_GIT_DIR_PATH?`, "${SAFE_DISPLAY_PATH_FN(SUBMODULE_GIT_DIR_PATH)}",`:' (the folder its ".git" file points to)'} is kept inside the superproject's git folder, where commands running in the Bash sandbox can write. Because any git command run in the submodule follows what that folder holds, Claude Code fetched nothing ahead of time and cannot safely suggest a command to run there; while a sandboxed session that can write there is still running, the folder cannot be trusted at all. Once no such session is running, look through that folder for settings that should not be there — for example, in "config" (and "config.worktree", if present) a changed remote address, an upload-pack or ssh command, or an include line; a file named "commondir"; scripts in "hooks" that you did not install; or any other setting you did not make — and remove those. Then fetch the missing objects for commit ${BASE_COMMIT_SHORT_SHA} in the submodule yourself and try again.
