#!/usr/bin/env python3

# ===== IMPORTS ===== #

## ===== STDLIB ===== ##
import subprocess, json, sys, re, shlex, os
from typing import Optional
from pathlib import Path
##-##

## ===== 3RD-PARTY ===== ##
##-##

## ===== LOCAL ===== ##
from shared_state import (
    edit_state,
    load_state,
    Mode,
    PROJECT_ROOT,
    load_config,
    find_git_repo,
    CCTools,
)
##-##

#-#

# ===== GLOBALS ===== #
# Load input
input_data = json.load(sys.stdin)
tool_name = input_data.get("tool_name", "")
tool_input = input_data.get("tool_input", {})

file_path = None
file_path_string = tool_input.get("file_path", "")
if file_path_string: file_path = Path(file_path_string)

STATE = load_state()
CONFIG = load_config()

if tool_name == "Bash": command = tool_input.get("command", "").strip()
if tool_name == "TodoWrite": incoming_todos = tool_input.get("todos", [])

## ===== PATTERNS ===== ##
READONLY_FIRST = {
    # Basic file reading
    'cat', 'less', 'more', 'head', 'tail', 'wc', 'nl', 'tac', 'rev',
    # Text search and filtering
    'grep', 'egrep', 'fgrep', 'rg', 'ripgrep', 'ag', 'ack',
    # Text processing (all safe for reading)
    'sort', 'uniq', 'cut', 'paste', 'join', 'comm', 'column',
    'tr', 'expand', 'unexpand', 'fold', 'fmt', 'pr', 'shuf', 'tsort',
    # Comparison
    'diff', 'cmp', 'sdiff', 'vimdiff',
    # Checksums
    'md5sum', 'sha1sum', 'sha256sum', 'sha512sum', 'cksum', 'sum',
    # Binary inspection
    'od', 'hexdump', 'xxd', 'strings', 'file', 'readelf', 'objdump', 'nm',
    # File system inspection
    'ls', 'dir', 'vdir', 'pwd', 'which', 'type', 'whereis', 'locate', 'find',
    'basename', 'dirname', 'readlink', 'realpath', 'stat',
    # User/system info
    'whoami', 'id', 'groups', 'users', 'who', 'w', 'last', 'lastlog',
    'hostname', 'uname', 'arch', 'lsb_release', 'hostnamectl',
    'date', 'cal', 'uptime', 'df', 'du', 'free', 'vmstat', 'iostat',
    # Process monitoring
    'ps', 'pgrep', 'pidof', 'top', 'htop', 'iotop', 'atop',
    'lsof', 'jobs', 'pstree', 'fuser',
    # Network monitoring
    'netstat', 'ss', 'ip', 'ifconfig', 'route', 'arp',
    'ping', 'traceroute', 'tracepath', 'mtr', 'nslookup', 'dig', 'host', 'whois',
    # Environment
    'printenv', 'env', 'set', 'export', 'alias', 'history', 'fc',
    # Output
    'echo', 'printf', 'yes', 'seq', 'jot',
    # Testing
    'test', '[', '[[', 'true', 'false',
    # Calculation
    'bc', 'dc', 'expr', 'factor', 'units',
    # Modern tools
    'jq', 'yq', 'xmlstarlet', 'xmllint', 'xsltproc',
    'bat', 'fd', 'fzf', 'tree', 'ncdu', 'exa', 'lsd',
    'tldr', 'cheat',
    # Code search and analysis tools
    'ast-grep', 'sg', 'ast_grep',  # Syntax-aware code search
    # Note: awk/sed are here but need special argument checking
    'awk', 'sed', 'gawk', 'mawk', 'gsed',
}

READONLY_FIRST.update(CONFIG.blocked_actions.bash_read_patterns)

WRITE_FIRST = {
    # File operations
    'rm', 'rmdir', 'unlink', 'shred',
    'mv', 'rename', 'cp', 'install', 'dd',
    'mkdir', 'mkfifo', 'mknod', 'mktemp', 'touch', 'truncate',
    # Permissions
    'chmod', 'chown', 'chgrp', 'umask',
    'ln', 'link', 'symlink',
    'setfacl', 'setfattr', 'chattr',
    # System management
    'useradd', 'userdel', 'usermod', 'groupadd', 'groupdel',
    'passwd', 'chpasswd', 'systemctl', 'service',
    # Package managers
    'apt', 'apt-get', 'dpkg', 'snap', 'yum', 'dnf', 'rpm',
    'pip', 'pip3', 'npm', 'yarn', 'gem', 'cargo',
    # Build tools
    'make', 'cmake', 'ninja', 'meson',
    # Other dangerous
    'sudo', 'doas', 'su', 'crontab', 'at', 'batch',
    'kill', 'pkill', 'killall', 'tee',
}

WRITE_FIRST.update(CONFIG.blocked_actions.bash_write_patterns)

# Enhanced redirection detection (includes stderr redirections)
REDIR_PATTERNS = [
    r'(?:^|\s)(?:>>?|<<?|<<<)\s',           # Basic redirections
    r'(?:^|\s)\d*>&?\d*(?:\s|$)',            # File descriptor redirections (2>&1, etc)
    r'(?:^|\s)&>',                           # Combined stdout/stderr redirect
]
REDIR = re.compile('|'.join(REDIR_PATTERNS))
##-##

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
##-##

#-#

# ===== WORKFLOW EVENT LOGGING ===== #
def _append_event(event: dict) -> None:
    """Append a workflow event as JSONL under sessions/.

    Lightweight streaming logger; avoids loading entire file.
    """
    try:
        from datetime import datetime
        event = dict(event or {})
        if "timestamp" not in event:
            event["timestamp"] = datetime.now().isoformat()
        events_file = PROJECT_ROOT / "sessions" / "sessions-events.jsonl"
        events_file.parent.mkdir(parents=True, exist_ok=True)
        with open(events_file, "a", encoding="utf-8", errors="backslashreplace") as f:
            f.write(json.dumps(event) + "\n")
    except Exception:
        # Best-effort only; never block on analytics
        pass

"""
╔══════════════════════════════════════════════════════════════════════════════╗
║ ██████╗ █████╗ ██████╗ ██████╗ █████╗  █████╗ ██╗      ██╗ ██╗██████╗██████╗ ║
║ ██╔══██╗██╔═██╗██╔═══╝ ╚═██╔═╝██╔══██╗██╔══██╗██║      ██║ ██║██╔═══╝██╔═══╝ ║
║ ██████╔╝█████╔╝█████╗    ██║  ██║  ██║██║  ██║██║      ██║ ██║██████╗█████╗  ║
║ ██╔═══╝ ██╔═██╗██╔══╝    ██║  ██║  ██║██║  ██║██║      ██║ ██║╚═══██║██╔══╝  ║
║ ██║     ██║ ██║██████╗   ██║  ╚█████╔╝╚█████╔╝███████╗ ╚████╔╝██████║██████╗ ║
║ ╚═╝     ╚═╝ ╚═╝╚═════╝   ╚═╝   ╚════╝  ╚════╝ ╚══════╝  ╚═══╝ ╚═════╝╚═════╝ ║
╚══════════════════════════════════════════════════════════════════════════════╝
PreToolUse Hook

Trigger conditions:
- Write/subagent tool invocation (Bash, Write, Edit, MultiEdit, Task, TodoWrite)

Enforces DAIC (Discussion, Alignment, Implementation, Check) workflow:
- Blocks write tools in discussion mode
- Validates TodoWrite operations for proper scope management
- Enforces git branch consistency with task requirements
- Protects system state files from unauthorized modification
"""

# ===== FUNCTIONS ===== #

## ===== HELPERS ===== ##
def block_with_permission_reason(tool_name: str, reason: str, remediation: str, mode: str):
    """Block tool with structured feedback for Claude Code UI.
    
    Args:
        tool_name: Name of the blocked tool
        reason: Why the tool was blocked
        remediation: How to proceed (actionable guidance)
        mode: Current mode (Plan, Discussion, Implementation)
    """
    # Print to stderr for backwards compatibility
    print(f"[DAIC: Tool Blocked] {reason}", file=sys.stderr)
    print(f"{remediation}", file=sys.stderr)
    
    # Structured output for Claude Code UI
    output = {
        "hookEventName": "PreToolUse",
        "hookSpecificOutput": {
            "permissionDecisionReason": reason,
            "suggestedAction": remediation,
            "currentMode": mode,
            "blockedTool": tool_name
        }
    }
    print(json.dumps(output), file=sys.stdout)
    
    _append_event({
        "type": "tool_blocked",
        "reason": "permission_denied",
        "tool": tool_name,
        "mode": mode,
    })
    sys.exit(2)

def is_work_artifact_path(file_path: Optional[Path]) -> bool:
    """Check if file path is a work artifact (plans, logs, docs) allowed in Plan/Discussion modes.
    
    Args:
        file_path: Path to check
        
    Returns:
        True if path is a work artifact that can be created/edited in Plan/Discussion modes
    """
    if not file_path:
        return False
    
    # Convert to string for easier checking
    path_str = str(file_path)
    
    # Allowed directories for work artifacts
    allowed_prefixes = [
        'sessions/',
        '.claude/',
        'docs/',
        'plans/',
        'notes/',
        'logs/',
    ]
    
    # Check if path starts with any allowed prefix (relative to project root)
    try:
        rel_path = file_path.relative_to(PROJECT_ROOT) if file_path.is_absolute() else file_path
        rel_path_str = str(rel_path)
        return any(rel_path_str.startswith(prefix) for prefix in allowed_prefixes)
    except (ValueError, AttributeError):
        # If we can't determine relative path, check the string directly
        return any(prefix in path_str for prefix in allowed_prefixes)

def check_command_arguments(parts):
    """Check if command arguments indicate write operations"""
    if not parts: return True

    cmd = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []

    # Check sed for in-place editing
    if cmd in ['sed', 'gsed']:
        for arg in args:
            if arg.startswith('-i') or arg == '--in-place':
                return False  # sed -i is a write operation

    # Check awk for file output operations
    if cmd in ['awk', 'gawk', 'mawk']:
        script = ' '.join(args)
        # Check for output redirection within awk script
        if re.search(r'>\s*["\'].*["\']', script):  # > "file" or > 'file'
            return False
        if re.search(r'>>\s*["\'].*["\']', script):  # >> "file" or >> 'file'
            return False
        if 'print >' in script or 'print >>' in script:
            return False
        if 'printf >' in script or 'printf >>' in script:
            return False

    # Check find for dangerous operations
    if cmd == 'find':
        if '-delete' in args:
            return False
        for i, arg in enumerate(args):
            if arg in ['-exec', '-execdir']:
                if i + 1 < len(args):
                    exec_cmd = args[i + 1].lower()
                    if exec_cmd in WRITE_FIRST or exec_cmd in ['rm', 'mv', 'cp', 'shred']:
                        return False

    # Check xargs for dangerous commands
    if cmd == 'xargs':
        for write_cmd in WRITE_FIRST:
            if write_cmd in args:
                return False
        # Check for sed -i through xargs
        if 'sed' in args:
            sed_idx = args.index('sed')
            if sed_idx + 1 < len(args) and args[sed_idx + 1].startswith('-i'):
                return False

    return True

# Check if a bash command is read-only (no writes, no redirections)
def is_bash_read_only(command: str, extrasafe: bool = CONFIG.blocked_actions.extrasafe or True) -> bool:
    """Determine if a bash command is read-only.

    Enhanced to check command arguments for operations like:
    - sed -i (in-place editing)
    - awk with file output
    - find -delete or -exec rm
    - xargs with write commands

    Args:
        command (str): The bash command to evaluate.
        extrasafe (bool): If True, unrecognized commands are treated as write-like."""
    extrasafe = CONFIG.blocked_actions.extrasafe if CONFIG.blocked_actions.extrasafe is not None else True

    s = (command or '').strip()
    if not s:
        return True

    if REDIR.search(s):
        return False

    for segment in re.split(r'(?<!\|)\|(?!\|)|&&|\|\|', s):  # Split on |, && and ||
        segment = segment.strip()
        if not segment: continue
        try:
            parts = shlex.split(segment)
        except ValueError:
            return not extrasafe
        if not parts: continue

        first = parts[0].lower()
        if first == 'cd': continue

        # Special case: Commands with read-only subcommands
        if first in ['pip', 'pip3']:
            subcommand = parts[1].lower() if len(parts) > 1 else ''
            if subcommand in ['show', 'list', 'search', 'check', 'freeze', 'help']:
                continue  # Allow read-only pip operations
            return False  # Block write operations

        if first in ['npm', 'yarn']:
            subcommand = parts[1].lower() if len(parts) > 1 else ''
            if subcommand in ['list', 'ls', 'view', 'show', 'search', 'help']:
                continue  # Allow read-only npm/yarn operations
            return False  # Block write operations

        if first in ['python', 'python3']:
            # Allow python -c for simple expressions and python -m for module execution
            if len(parts) > 1 and parts[1] in ['-c', '-m']:
                continue  # These are typically read-only operations in our context
            # Block other python invocations as potentially write-like
            return False

        if first in WRITE_FIRST: return False

        # Check command arguments for write operations
        if not check_command_arguments(parts): return False

        # Check if command is in user's custom readonly list
        if first in CONFIG.blocked_actions.bash_read_patterns: continue  # Allow custom readonly commands

        # If extrasafe is on and command not in readonly list, block it
        if first not in READONLY_FIRST and extrasafe: return False

    return True
##-##

#-#

# ===== EXECUTION ===== #

# Skip DAIC enforcement in CI environments
if is_ci_environment():
    sys.exit(0)

# Plan mode entry
if tool_name == CCTools.PLAN.value and not getattr(STATE.flags, "bypass_mode", False):
    with edit_state() as s:
        try:
            current_mode = s.mode if isinstance(s.mode, Mode) else Mode(s.mode)
        except ValueError:
            current_mode = Mode.NO

        if current_mode is not Mode.PLAN and 'plan_prev_mode' not in s.metadata:
            s.metadata['plan_prev_mode'] = current_mode.value

        if s.todos.active and not s.metadata.get('plan_stashed_count'):
            stashed = 0
            if not s.todos.stashed:
                stashed = s.todos.stash_active(force=False)
            if stashed:
                s.metadata['plan_stashed_count'] = stashed

        s.mode = Mode.PLAN

    print("[Plan Mode] Entered plan mode. Only planning operations are allowed until you exit plan mode.", file=sys.stderr)
    sys.exit(0)

# Plan mode exit
if tool_name == CCTools.EXITPLANMODE.value and not getattr(STATE.flags, "bypass_mode", False):
    with edit_state() as s:
        prev_mode_value = s.metadata.pop('plan_prev_mode', Mode.NO.value)
        stashed_count = s.metadata.pop('plan_stashed_count', 0)

        if stashed_count:
            s.todos.restore_stashed()

        try:
            target_mode = Mode(prev_mode_value)
        except ValueError:
            target_mode = Mode.NO

        if target_mode is Mode.GO:
            target_mode = Mode.NO

        s.mode = target_mode

    print("[Plan Mode] Exited plan mode. You are back in discussion mode.", file=sys.stderr)
    sys.exit(0)

#!> Bash command handling
# For Bash commands, check if it's a read-only operation
if tool_name == "Bash" and STATE.mode in (Mode.NO, Mode.PLAN) and not STATE.flags.bypass_mode:
    # Special case: Allow sessions.api commands in discussion mode
    if command and ('sessions ' in command or 'python -m cc_sessions.scripts.api' in command):
        # API commands are allowed in discussion mode for state inspection and safe config operations
        sys.exit(0)

    if not is_bash_read_only(command):
        mode_name = "Plan" if STATE.mode == Mode.PLAN else "Discussion"
        trigger_phrases = ', '.join(CONFIG.trigger_phrases.implementation_mode[:3])
        block_with_permission_reason(
            tool_name="Bash",
            reason=f"Write-like bash command blocked in {mode_name} mode. Only the user can activate implementation mode.",
            remediation=f"Explain what you want to do and seek alignment first. To proceed, user should say: {trigger_phrases}\n\nNote: Configure allowed commands with:\n  - sessions config read list\n  - sessions config read add <command>",
            mode=STATE.mode.value
        )
    else:
        _append_event({
            "type": "tool_allowed",
            "tool": "Bash",
            "reason": "read_only_command",
            "command": command,
        })
        sys.exit(0)
#!<

#!> Block any attempt to modify sessions-state.json directly
if file_path and all([
    tool_name == "Bash",
    file_path.name == 'sessions-state.json',
    file_path.parent.name == 'sessions']):
    # Check if it's a modifying operation
    if not is_bash_read_only(command):
        print("[Security] Direct modification of sessions-state.json is not allowed. "
                "This file should only be modified through the TodoWrite tool and approved commands.", file=sys.stderr); sys.exit(2)
#!<

# --- All commands beyond here contain write patterns (read patterns exit early) ---

#!> Discussion/plan mode guard (block write tools)
if STATE.mode in (Mode.NO, Mode.PLAN) and not STATE.flags.bypass_mode:
    # Allow work artifact writes (plans, logs, docs) in Plan/Discussion modes
    if tool_name in ["Write", "Edit", "MultiEdit"] and is_work_artifact_path(file_path):
        print(f"[{STATE.mode.value.title()} Mode] Allowing {tool_name} for work artifact: {file_path}", file=sys.stderr)
        _append_event({
            "type": "tool_allowed",
            "reason": "work_artifact_in_planning",
            "tool": tool_name,
            "file_path": str(file_path),
        })
        sys.exit(0)  # Allow work artifact writes
    
    # Block code modifications
    if CONFIG.blocked_actions.is_tool_blocked(tool_name):
        mode_name = "Plan" if STATE.mode == Mode.PLAN else "Discussion"
        trigger_phrases = ', '.join(CONFIG.trigger_phrases.implementation_mode[:3])
        block_with_permission_reason(
            tool_name=tool_name,
            reason=f"You're in {mode_name} mode. The {tool_name} tool is blocked for code changes.",
            remediation=f"Work artifacts (plans, logs, docs) can be created in sessions/, .claude/, docs/, plans/ directories.\n\nFor code changes, seek alignment and get approval by saying: {trigger_phrases}",
            mode=STATE.mode.value
        )
    else: sys.exit(0)  # Allow read-only tools
#!<

#!> TodoWrite tool handling
if tool_name == "TodoWrite" and not STATE.flags.bypass_mode:
    # Check for name mismatch first (regardless of completion state)
    if STATE.todos.active:
        active_names = STATE.todos.list_content('active')
        incoming_names = [t.get('content','') for t in incoming_todos]

        if active_names != incoming_names:
            # Todo names changed - safety violation
            with edit_state() as s: s.todos.clear_active(); s.mode = Mode.NO; STATE = s
            print("[DAIC: Blocked] Todo list changed - this violates agreed execution boundaries. "
                  "Previous todos cleared and returned to discussion mode. "
                  "If you need to change the task list, propose the updated version. "
                  "If this was an error, re-propose your previously planned todos.", file=sys.stderr)
            sys.exit(2)

    with edit_state() as s:
        if not s.todos.store_todos(incoming_todos): print("[TodoWrite Error] Failed to store todos - check format", file=sys.stderr); sys.exit(2)
        else: STATE = s
#!<

#!> TodoList modification guard
# Get the file path being edited
if not file_path: sys.exit(0) # No file path, allow to proceed

# Block direct modification of state file via Write/Edit/MultiEdit
if all([    tool_name in ["Write", "Edit", "MultiEdit", "NotebookEdit"],
            file_path.name == 'sessions-state.json',
            file_path.parent.name == 'sessions',
            not STATE.flags.bypass_mode]):
    print("[Security] Direct modification of sessions-state.json is not allowed. "
        "This file should only be modified through the TodoWrite tool and approved commands.", file=sys.stderr)
    sys.exit(2)
#!<

#!> Git branch/task submodules enforcement
if not (expected_branch := STATE.current_task.branch): sys.exit(0) # No branch/task info, allow to proceed

# Check if branch enforcement is enabled
if not CONFIG.features.branch_enforcement:
    sys.exit(0)  # Branch enforcement disabled, allow to proceed

else:
    repo_path = find_git_repo(file_path.parent)

    if repo_path:
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=2
            )
            current_branch = result.stdout.strip()

            # Extract the submodule name from the repo path
            submodule_name = repo_path.name

            # Check both conditions: branch status and task inclusion
            branch_correct = (current_branch == expected_branch)
            in_task = (STATE.current_task.submodules and submodule_name in STATE.current_task.submodules)
            if repo_path == PROJECT_ROOT: in_task = True # Root repo - always considered in task

            # Scenario 1: Everything is correct - allow to proceed
            if in_task and branch_correct:
                pass

            # Scenario 2: Submodule is in task but on wrong branch
            elif in_task and not branch_correct:
                print(f"[Branch Mismatch] Submodule '{submodule_name}' is part of this task but is on branch '{current_branch}' instead of '{expected_branch}'.", file=sys.stderr)
                print(f"Please run: cd {repo_path.relative_to(PROJECT_ROOT)} && git checkout {expected_branch}", file=sys.stderr)
                _append_event({
                    "type": "branch_mismatch",
                    "service": submodule_name,
                    "expected": expected_branch,
                    "actual": current_branch,
                })
                sys.exit(2)

            # Scenario 3: Submodule not in task but already on correct branch
            elif not in_task and branch_correct:
                print(f"[Submodule Not in Task] Submodule '{submodule_name}' is on the correct branch '{expected_branch}' but is not listed in the task file.", file=sys.stderr)
                print(f"Please update the task file to include '{submodule_name}' in the submodules list.", file=sys.stderr)
                _append_event({
                    "type": "service_not_in_task",
                    "service": submodule_name,
                    "branch": current_branch,
                })
                sys.exit(2)

            # Scenario 4: Submodule not in task AND on wrong branch
            else:
                print(f"[Submodule Not in Task + Wrong Branch] Submodule '{submodule_name}' has two issues:", file=sys.stderr)
                print(f"  1. Not listed in the task file's submodules", file=sys.stderr)
                print(f"  2. On branch '{current_branch}' instead of '{expected_branch}'", file=sys.stderr)
                print(f"To fix: cd {repo_path.relative_to(PROJECT_ROOT)} && git checkout -b {expected_branch}", file=sys.stderr)
                print(f"Then update the task file to include '{submodule_name}' in the submodules list.", file=sys.stderr)
                _append_event({
                    "type": "service_not_in_task_and_wrong_branch",
                    "service": submodule_name,
                    "expected": expected_branch,
                    "actual": current_branch,
                })
                sys.exit(2)
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            # Can't check branch, allow to proceed but warn
            print(f"Warning: Could not verify branch for {repo_path.name}: {e}", file=sys.stderr)
#!<

#-#

# Allow tool to proceed
sys.exit(0)
