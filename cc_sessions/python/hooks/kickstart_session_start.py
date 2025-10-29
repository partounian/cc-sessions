#!/usr/bin/env python3

# ===== IMPORTS ===== #

## ===== STDLIB ===== ##
import sys
import json
import os
from datetime import datetime
from pathlib import Path
##-##

## ===== 3RD-PARTY ===== ##
##-##

## ===== LOCAL ===== ##
# Add sessions to path if CLAUDE_PROJECT_DIR is available (symlink setup)
if 'CLAUDE_PROJECT_DIR' in os.environ:
    sessions_path = os.path.join(os.environ['CLAUDE_PROJECT_DIR'], 'sessions')
    hooks_path = os.path.join(sessions_path, 'hooks')
    if hooks_path not in sys.path:
        sys.path.insert(0, hooks_path)

try:
    # Try direct import (works with sessions in path or package install)
    from shared_state import load_state, PROJECT_ROOT, edit_state
except ImportError:
    # Fallback to package import
    from cc_sessions.hooks.shared_state import load_state, PROJECT_ROOT, edit_state
##-##

#-#

# ===== GLOBALS ===== #

## ===== CI DETECTION ===== ##
def is_ci_environment():
    """Check if running in a CI environment (GitHub Actions)."""
    ci_indicators = [
        'GITHUB_ACTIONS',         # GitHub Actions
        'GITHUB_WORKFLOW',        # GitHub Actions workflow
        'CI',                     # Generic CI indicator (set by GitHub Actions)
        'CONTINUOUS_INTEGRATION', # Generic CI (alternative)
    ]
    return any(os.getenv(indicator) for indicator in ci_indicators)

# Skip kickstart session start hook in CI environments
if is_ci_environment():
    sys.exit(0)
##-##

## ===== MODULE SEQUENCES ===== ##
FULL_MODE_SEQUENCE = [
    '01-discussion.md',
    '02-implementation.md',
    '03-tasks-overview.md',
    '04-task-creation.md',
    '05-task-startup.md',
    '06-task-completion.md',
    '07-compaction.md',
    '08-agents.md',
    '09-api.md',
    '10-advanced.md',
    '11-graduation.md'
]

SUBAGENTS_MODE_SEQUENCE = [
    '01-agents-only.md'
]
##-##

#-#

# ===== FUNCTIONS ===== #

def load_protocol_file(relative_path: str) -> str:
    """Load protocol markdown from protocols directory."""
    protocol_path = PROJECT_ROOT / 'sessions' / 'protocols' / relative_path
    if not protocol_path.exists():
        return f"Error: Protocol file not found: {relative_path}"
    return protocol_path.read_text()

#-#

"""
Kickstart SessionStart Hook

Handles onboarding flow for users who chose kickstart in installer:
- Checks for kickstart metadata (should ALWAYS exist if this hook is running)
- Loads first module on first run, resumes from current_index on subsequent runs
- Sequences determined by mode (full or subagents)
"""

# ===== EXECUTION ===== #

#!> 1. Load state and check kickstart metadata
STATE = load_state()

# Get kickstart metadata (should ALWAYS exist if this hook is running)
kickstart_meta = STATE.metadata.get('kickstart')

# NEW: Handle missing metadata gracefully (cleanup window detection)
if not kickstart_meta:
    # Metadata missing - exit silently (could be cleanup window or hook shouldn't be here)
    sys.exit(0)

# NEW: Check if kickstart is marked complete
if kickstart_meta.get('onboarding_complete') is True:
    # Kickstart completed - exit silently, allow normal session
    sys.exit(0)

mode = kickstart_meta.get('mode')  # 'full' or 'subagents'
if not mode:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "ERROR: kickstart metadata exists but no mode specified. This is an installer bug."
        }
    }))
    sys.exit(1)
#!<

#!> 2. Initialize or load sequence
# Determine sequence based on mode
if mode == 'full':
    sequence = FULL_MODE_SEQUENCE
elif mode == 'subagents':
    sequence = SUBAGENTS_MODE_SEQUENCE
else:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": f"ERROR: Invalid kickstart mode '{mode}'. Expected 'full' or 'subagents'."
        }
    }))
    sys.exit(1)

# Initialize sequence on first run
current_index = kickstart_meta.get('current_index', 0)
if 'sequence' not in kickstart_meta:
    with edit_state() as s:
        s.metadata['kickstart']['sequence'] = sequence
        s.metadata['kickstart']['current_index'] = 0
        s.metadata['kickstart']['completed'] = []
    current_index = 0
    protocol_content = load_protocol_file(f'kickstart/{sequence[0]}')
else:
    # Load current protocol from sequence
    protocol_content = load_protocol_file(f'kickstart/{sequence[current_index]}')
#!<

#!> 2.5. Check cooldown and progress-aware logic
last_shown = kickstart_meta.get('last_shown')
now = datetime.now()

# If kickstart is in progress (current_index > 0), check cooldown
if current_index > 0 and last_shown:
    try:
        last_shown_time = datetime.fromisoformat(last_shown.replace('Z', '+00:00'))
        # Handle timezone-aware datetime
        if last_shown_time.tzinfo:
            now_aware = datetime.now(last_shown_time.tzinfo)
        else:
            now_aware = now
        hours_since_shown = (now_aware - last_shown_time).total_seconds() / 3600

        # If shown within last hour, skip instructions but update last_active
        if hours_since_shown < 1:
            with edit_state() as s:
                s.metadata['kickstart']['last_active'] = datetime.now().isoformat()
            sys.exit(0)  # Exit silently, allow normal session
    except (ValueError, AttributeError):
        # If timestamp parsing fails, continue to show instructions
        pass

# If we reach here, we should show instructions
# Update last_shown timestamp when displaying instructions
with edit_state() as s:
    s.metadata['kickstart']['last_shown'] = datetime.now().isoformat()
    s.metadata['kickstart']['last_active'] = datetime.now().isoformat()
#!<

#!> 3. Append user instructions and output
protocol_content += """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USER INSTRUCTIONS:
Just say 'kickstart' and press enter to begin
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": protocol_content
    }
}))
sys.exit(0)
#!<
