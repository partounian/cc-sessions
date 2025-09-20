#!/usr/bin/env python3
"""
Unified Workflow Manager Hook for cc-sessions

Combines DAIC workflow enforcement, post-tool-use reminders, and subagent context management
into a single, efficient hook that handles all workflow-related concerns.

This hook replaces:
- sessions-enforce.py (DAIC enforcement)
- post-tool-use.py (DAIC reminders)

Key features:
- DAIC workflow enforcement and tool blocking
- Branch consistency enforcement
- Subagent context management
- Post-tool-use reminders
- Tool parameter validation
- Emergency stop functionality
"""

import json
import re
import subprocess
import sys
from pathlib import Path

from shared_state import (check_daic_mode_bool, get_project_root,
                          get_task_state, set_daic_mode, get_shared_state)

# Load configuration from project's .claude directory
PROJECT_ROOT = get_project_root()
CONFIG_FILE = PROJECT_ROOT / "sessions" / "sessions-config.json"

# Default configuration (used if config file doesn't exist)
DEFAULT_CONFIG = {
    "trigger_phrases": ["make it so", "run that"],
    "blocked_tools": ["Edit", "Write", "MultiEdit", "NotebookEdit"],
    "branch_enforcement": {
        "enabled": True,
        "task_prefixes": ["implement-", "fix-", "refactor-", "migrate-", "test-", "docs-"],
        "branch_prefixes": {
            "implement-": "feature/",
            "fix-": "fix/",
            "refactor-": "feature/",
            "migrate-": "feature/",
            "test-": "feature/",
            "docs-": "feature/"
        }
    },
    "read_only_bash_commands": [
        "ls", "ll", "pwd", "cd", "echo", "cat", "head", "tail", "less", "more",
        "grep", "rg", "find", "which", "whereis", "type", "file", "stat",
        "du", "df", "tree", "basename", "dirname", "realpath", "readlink",
        "whoami", "env", "printenv", "date", "cal", "uptime", "ps", "top",
        "wc", "cut", "sort", "uniq", "comm", "diff", "cmp", "md5sum", "sha256sum",
        "git status", "git log", "git diff", "git show", "git branch",
        "git remote", "git fetch", "git describe", "git rev-parse", "git blame",
        "docker ps", "docker images", "docker logs", "npm list", "npm ls",
        "pip list", "pip show", "yarn list", "curl", "wget", "jq", "awk",
        "sed -n", "tar -t", "unzip -l",
        # Windows equivalents
        "dir", "where", "findstr", "fc", "comp", "certutil -hashfile",
        "Get-ChildItem", "Get-Location", "Get-Content", "Select-String",
        "Get-Command", "Get-Process", "Get-Date", "Get-Item"
    ]
}

def get_hook_event_name(input_data: dict) -> str:
    """Return the hook event name from runner input.

    Prefer the canonical "hookEventName" key but also support the
    documented "hook_event_name" variant for robustness.
    """
    return input_data.get("hookEventName") or input_data.get("hook_event_name") or ""

def load_config():
    """Load configuration from file or use defaults."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_CONFIG

def find_git_repo(path: Path) -> Path:
    """Walk up directory tree to find .git directory."""
    current = path if path.is_dir() else path.parent

    while current.parent != current:  # Stop at filesystem root
        if (current / ".git").exists():
            return current
        current = current.parent
    return None

def is_read_only_bash_command(command: str, config: dict) -> bool:
    """Check if a bash command is read-only."""
    # Check for write patterns
    write_patterns = [
        r'>\s*\S',
        r'>>\s*\S',
        r'\btee\b',
        r'\bmv\b',
        r'\bcp\b',
        r'\brm\b',
        r'\bmkdir\b',
        r'\btouch\b',
        r'\bsed\s+-i',
        r'curl\b.*(-o|--output)\b',
        r'wget\b.*-O\b',
        r'tar\s+-x',
        r'unzip\s+-o',
        r'dd\s+of=',
        r'\bnpm\s+install',
        r'\bpip\s+install',
        r'\bapt\s+install',
        r'\byum\s+install',
        r'\bbrew\s+install',
    ]

    has_write_pattern = any(re.search(pattern, command) for pattern in write_patterns)

    if has_write_pattern:
        return False

    # Check if ALL commands in chain are read-only
    command_parts = re.split(r'(?:&&|\|\||;|\|)', command)

    for part in command_parts:
        part = part.strip()
        if not part:
            continue

        # Check against configured read-only commands
        is_part_read_only = any(
            part.startswith(prefix)
            for prefix in config.get("read_only_bash_commands", DEFAULT_CONFIG["read_only_bash_commands"])
        )

        if not is_part_read_only:
            return False

    return True


def log_tool_event(tool_name: str, tool_input: dict, success: bool, reason: str | None = None) -> None:
    try:
        get_shared_state().log_tool_usage({
            'tool_name': tool_name,
            'success': bool(success),
            'reason': reason,
            'parameters': tool_input,
            'timestamp': None
        })
    except Exception:
        pass

def enforce_branch_consistency(tool_name: str, tool_input: dict, config: dict):
    """Enforce branch consistency for file editing operations."""
    branch_config = config.get("branch_enforcement", DEFAULT_CONFIG["branch_enforcement"])
    if not branch_config.get("enabled", True) or tool_name not in ["Write", "Edit", "MultiEdit"]:
        return True

    file_path = tool_input.get("file_path", "")
    if not file_path:
        return True

    file_path = Path(file_path)

    # Get current task state
    task_state = get_task_state()
    expected_branch = task_state.get("branch")
    affected_services = task_state.get("services", [])

    if not expected_branch:
        return True

    # Find the git repo for this file
    repo_path = find_git_repo(file_path)

    if not repo_path:
        return True

    try:
        # Get current branch
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=2
        )
        current_branch = result.stdout.strip()

        # Get project root (parent of .claude directory)
        project_root = Path.cwd()
        while project_root.parent != project_root:
            if (project_root / ".claude").exists():
                break
            project_root = project_root.parent

        # Check if we're in a submodule
        try:
            # Try to make repo_path relative to project_root
            repo_path.relative_to(project_root)
            is_submodule = (repo_path != project_root)
        except ValueError:
            # Not a subdirectory
            is_submodule = False

        if is_submodule:
            # We're in a submodule
            service_name = repo_path.name

            # Check both conditions: branch status and task inclusion
            branch_correct = (current_branch == expected_branch)
            in_task = (service_name in affected_services)

            # Handle all four scenarios with clear, specific error messages
            if in_task and branch_correct:
                # Scenario 1: Everything is correct - allow to proceed
                return True
            elif in_task and not branch_correct:
                # Scenario 2: Service is in task but on wrong branch
                print(f"[Branch Mismatch] Service '{service_name}' is part of this task but is on branch '{current_branch}' instead of '{expected_branch}'.", file=sys.stderr)
                print(f"Please run: cd {repo_path.relative_to(project_root)} && git checkout {expected_branch}", file=sys.stderr)
                try:
                    get_shared_state().log_workflow_event({'type': 'branch_mismatch', 'service': service_name, 'expected': expected_branch, 'actual': current_branch})
                except Exception:
                    pass
                return False
            elif not in_task and branch_correct:
                # Scenario 3: Service not in task but already on correct branch
                print(f"[Service Not in Task] Service '{service_name}' is on the correct branch '{expected_branch}' but is not listed in the task file.", file=sys.stderr)
                print(f"Please update the task file to include '{service_name}' in the services list.", file=sys.stderr)
                try:
                    get_shared_state().log_workflow_event({'type': 'service_not_in_task', 'service': service_name, 'branch': current_branch})
                except Exception:
                    pass
                return False
            else:  # not in_task and not branch_correct
                # Scenario 4: Service not in task AND on wrong branch
                print(f"[Service Not in Task + Wrong Branch] Service '{service_name}' has two issues:", file=sys.stderr)
                print(f"  1. Not listed in the task file's services", file=sys.stderr)
                print(f"  2. On branch '{current_branch}' instead of '{expected_branch}'", file=sys.stderr)
                print(f"To fix: cd {repo_path.relative_to(project_root)} && git checkout -b {expected_branch}", file=sys.stderr)
                print(f"Then update the task file to include '{service_name}' in the services list.", file=sys.stderr)
                try:
                    get_shared_state().log_workflow_event({'type': 'service_not_in_task_and_wrong_branch', 'service': service_name, 'expected': expected_branch, 'actual': current_branch})
                except Exception:
                    pass
                return False
        else:
            # Single repo or main repo
            if current_branch != expected_branch:
                print(f"[Branch Mismatch] Repository is on branch '{current_branch}' but task expects '{expected_branch}'. Please checkout the correct branch.", file=sys.stderr)
                try:
                    get_shared_state().log_workflow_event({'type': 'branch_mismatch', 'service': 'main', 'expected': expected_branch, 'actual': current_branch})
                except Exception:
                    pass
                return False

    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        # Can't check branch, allow to proceed but warn
        print(f"Warning: Could not verify branch: {e}", file=sys.stderr)

    return True

def check_subagent_boundaries(tool_name: str, tool_input: dict, input_data: dict):
    """Check if subagents are trying to modify system state files."""
    project_root = get_project_root()
    # Determine if we're inside a subagent using shared state tracker
    session_id = input_data.get("session_id") or "default"
    try:
        in_subagent = get_shared_state().is_subagent_active(session_id)
    except Exception:
        in_subagent = False

    if not in_subagent or tool_name not in ["Write", "Edit", "MultiEdit"]:
        return True

    file_path_str = tool_input.get("file_path", "")
    if not file_path_str:
        return True

    file_path = Path(file_path_str)
    state_dir = project_root / '.claude' / 'state'

    try:
        # Check if file_path is under the state directory
        file_path.resolve().relative_to(state_dir.resolve())
        # If we get here, the file is under .claude/state
        print(f"[Subagent Boundary Violation] Subagents are NOT allowed to modify .claude/state files.", file=sys.stderr)
        print(f"Stay in your lane: You should only edit task-specific files, not system state.", file=sys.stderr)
        return False
    except ValueError:
        # Not under .claude/state, which is fine
        return True

def handle_post_tool_use(tool_name: str, tool_input: dict, cwd: str):
    """Handle post-tool-use reminders and context management."""
    # Check if we're in a subagent context via shared state tracker is handled in boundary check
    in_subagent = False

    # If this is the Task tool completing, don't show reminder
    if tool_name == "Task" and in_subagent:
        return False

    # Check current mode
    discussion_mode = check_daic_mode_bool()

    # Only remind if in implementation mode AND not in a subagent
    implementation_tools = ["Edit", "Write", "MultiEdit", "NotebookEdit"]
    if not discussion_mode and tool_name in implementation_tools and not in_subagent:
        # Output reminder
        print("[DAIC Reminder] When you're done implementing, run: daic", file=sys.stderr)
        return True

    # Check for cd command in Bash operations
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if "cd " in command:
            print(f"[CWD: {cwd}]", file=sys.stderr)
            return True

    return False

def main():
    """Main entry point for Workflow Manager hook."""
    try:
        # Load input
        input_data = json.load(sys.stdin)
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        cwd = input_data.get("cwd", "")

        # Load configuration
        config = load_config()

        # Determine hook event type reliably
        event_name = get_hook_event_name(input_data)
        # Primary signal: explicit event name
        is_post_tool_use = (event_name == "PostToolUse")
        # Fallback: presence of tool_response implies PostToolUse in older runners
        if not is_post_tool_use and "tool_response" in input_data:
            is_post_tool_use = True

        if is_post_tool_use:
            # Handle post-tool-use functionality
            mod = handle_post_tool_use(tool_name, tool_input, cwd)
            # Log tool event as successful execution side-effect if not modified
            log_tool_event(tool_name, tool_input, True)
            if mod:
                sys.exit(2)  # Exit code 2 feeds stderr back to Claude
            else:
                sys.exit(0)

        # Pre-tool-use enforcement logic
        # For Bash commands, check if it's a read-only operation
        if tool_name == "Bash":
            command = tool_input.get("command", "").strip()

            if is_read_only_bash_command(command, config):
                # Allow read-only commands without checks
                log_tool_event(tool_name, tool_input, True)
                sys.exit(0)

        # Check current mode
        discussion_mode = check_daic_mode_bool()

        # Block 'daic' command in discussion mode
        if discussion_mode and tool_name == "Bash":
            command = tool_input.get("command", "").strip()
            if 'daic' in command:
                print(f"[DAIC: Command Blocked] The 'daic' command is not allowed in discussion mode.", file=sys.stderr)
                print(f"You're already in discussion mode. Be sure to propose your intended edits/plans to the user and seek their explicit approval, which will unlock implementation mode.", file=sys.stderr)
                log_tool_event(tool_name, tool_input, False, reason='blocked_daic_command')
                sys.exit(2)  # Block with feedback

        # Block configured tools in discussion mode (except task selection)
        if discussion_mode and tool_name in config.get("blocked_tools", DEFAULT_CONFIG["blocked_tools"]):
            # Allow task selection operations even in DAIC mode
            if tool_name == "Edit" and "current_task.json" in tool_input.get("path", ""):
                pass  # Allow task selection
            else:
                print(f"[DAIC: Tool Blocked] You're in discussion mode. The {tool_name} tool is not allowed. You need to seek alignment first.", file=sys.stderr)
                log_tool_event(tool_name, tool_input, False, reason='blocked_by_daic')
                sys.exit(2)  # Block with feedback

        # Check subagent boundaries
        if not check_subagent_boundaries(tool_name, tool_input, input_data):
            log_tool_event(tool_name, tool_input, False, reason='subagent_boundary')
            sys.exit(2)  # Block with feedback

        # Enforce branch consistency
        if not enforce_branch_consistency(tool_name, tool_input, config):
            log_tool_event(tool_name, tool_input, False, reason='branch_enforcement')
            sys.exit(2)  # Block with feedback

        # Allow tool to proceed
        log_tool_event(tool_name, tool_input, True)
        sys.exit(0)

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # Log the error for debugging
        error_msg = f"Error: Unexpected error in workflow manager: {e}"
        print(error_msg, file=sys.stderr)

        # Try to log to shared state if possible
        try:
            from hooks.shared_state import SharedState
            shared_state = SharedState()
            shared_state.log_error(error_msg)
        except:
            pass  # If logging fails, continue gracefully

        # In case of critical errors, allow tool to proceed rather than blocking completely
        # This prevents the system from becoming completely unusable
        if "critical" not in str(e).lower():
            print("Warning: Allowing tool execution due to hook error", file=sys.stderr)
            sys.exit(0)  # Allow execution
        else:
            sys.exit(1)  # Block execution for critical errors

if __name__ == "__main__":
    main()
