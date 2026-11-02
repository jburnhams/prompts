<!--
name: "Data: Untrusted folder environment variables ignored warning"
description: "Warns that an untrusted folder's unsupported environment settings are ignored when the session cannot show a trust dialog and explains where the user can set them"
ccVersion: "2.1.314"
variables:
  - "IGNORED_ENVIRONMENT_VARIABLE_NAMES"
  - "SETTINGS_SOURCE_KEY"
  - "IGNORED_PERSISTED_TRUST_REASON"
-->
Ignoring ${IGNORED_ENVIRONMENT_VARIABLE_NAMES.join(", ")} in the env block of ${SETTINGS_SOURCE_KEY==="localSettings"?".claude/settings.local.json":".claude/settings.json"}: ${IGNORED_PERSISTED_TRUST_REASON}, and this session cannot show a trust dialog, so this folder's settings files may set only a short list of variables, each to certain values only, such as DISABLE_TELEMETRY=1. The repository's author chose the ignored values, not you. If your setup needs an ignored variable, set it yourself in user or managed settings, or in the environment that Claude Code is started with. On a self-hosted runner, user settings are settings.json in the runner host's config directory (SELF_HOSTED_RUNNER_HOST_CONFIG_DIR): restart the runner afterwards.
