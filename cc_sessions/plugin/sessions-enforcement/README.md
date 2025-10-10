# Sessions Enforcement Plugin (MVP)

This plugin packages cc-sessions DAIC workflow controls and helper content in a Claude Code plugin-friendly layout.

Contents:
- commands/ markdown commands that expose DAIC/state controls as slash commands
- agents/ prompts that can be used as specialized subagents
- Optional adapter: cc_sessions/plugin/enforcement_plugin.py to map plugin events to existing hooks (session_start, user_messages, sessions_enforce, post_tool_use)

Install (developer workflow):
1) Copy or symlink cc_sessions/plugin/sessions-enforcement/ into your Claude Code plugins folder
2) Reload Claude Code or run the plugins refresh command

Notes:
- This MVP defers all enforcement to the existing Python hooks to avoid duplication. As Claude Code plugin APIs expand, logic can be migrated behind the plugin events directly.
- All analytics are best-effort and non-blocking.
