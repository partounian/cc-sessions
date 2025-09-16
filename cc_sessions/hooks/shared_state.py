#!/usr/bin/env python3
"""
Enhanced Shared State Management for Claude Code Sessions hooks.

Integrates multi-repository support, workspace awareness, and comprehensive
state management into a single, efficient module.

This enhanced version replaces:
- shared_state.py (basic state management)
- multi_repo_config.py (multi-repository configuration)
- workspace_task_manager.py (cross-repo task coordination)

Key features:
- Multi-repository workspace detection and management
- Cross-repository task coordination
- Enhanced state persistence and management
- Workspace-aware context sharing
- Agent state management
- Performance monitoring and analytics
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class EnhancedSharedState:
    """Enhanced shared state management with multi-repository support"""

    def __init__(self):
        self.project_root = self._get_project_root()
        self.workspace_root = self._get_workspace_root()
        self.state_dir = self.project_root / ".claude" / "state"
        self.workspace_state_dir = self.workspace_root / ".claude" / "workspace_state"

        # Core state files
        self.daic_state_file = self.state_dir / "daic-mode.json"
        self.task_state_file = self.state_dir / "current_task.json"
        self.session_start_file = self.state_dir / "session_start.json"

        # Multi-repo configuration
        self.multi_repo_config_file = self.workspace_state_dir / "multi_repo_config.json"
        self.workspace_context_file = self.workspace_state_dir / "workspace_context.json"

        # Analytics and monitoring
        self.analytics_dir = self.state_dir / "analytics"
        self.tool_usage_log_file = self.state_dir / "tool_usage_log.json"
        self.context_usage_log_file = self.state_dir / "context_usage_log.json"
        self.error_log_file = self.state_dir / "error_log.json"
        self.workflow_events_file = self.state_dir / "workflow_events.json"

        # Ensure directories exist
        self._ensure_directories()

        # Initialize multi-repo configuration
        self.multi_repo_config = self._load_multi_repo_config()

    def _get_project_root(self) -> Path:
        """Find project root by looking for .claude directory."""
        current = Path.cwd()
        while current.parent != current:
            if (current / ".claude").exists():
                return current
            current = current.parent
        return Path.cwd()

    def _get_workspace_root(self) -> Path:
        """Find workspace root (parent of project root) for multi-repo awareness."""
        project_root = self.project_root

        # First, check if the project root itself contains multiple repositories
        git_dirs = list(project_root.glob('*/.git'))
        if len(git_dirs) > 1:
            return project_root

        # Look for common workspace indicators in parent directories
        workspace_indicators = ['.vscode', 'workspace.code-workspace', '.idea']
        current = project_root.parent
        while current.parent != current:
            if any((current / indicator).exists() for indicator in workspace_indicators):
                return current
            current = current.parent

        # If no workspace indicators found, use project root as workspace root
        return project_root

    def _ensure_directories(self) -> None:
        """Ensure all necessary directories exist."""
        directories = [
            self.state_dir,
            self.workspace_state_dir,
            self.analytics_dir,
            self.state_dir / "agent_context",
            self.state_dir / "compaction",
            self.workspace_state_dir / "workspace_tasks"
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def _load_multi_repo_config(self) -> Dict[str, Any]:
        """Load multi-repository configuration"""
        default_config = {
            'workspace_name': 'Multi-Repo Workspace',
            'repositories': {},
            'shared_agents': [],
            'cross_repo_tasks': True,
            'context_sharing': True,
            'git_integration': True,
            'excluded_directories': ['.git', 'node_modules', '__pycache__', '.venv', 'venv'],
            'included_file_types': ['.py', '.js', '.ts', '.md', '.json', '.yaml', '.yml', '.toml'],
            'workspace_agents': {
                'cross_repo_analyzer': {
                    'enabled': True,
                    'description': 'Analyzes relationships between repositories'
                },
                'dependency_tracker': {
                    'enabled': True,
                    'description': 'Tracks dependencies across repositories'
                },
                'workspace_coordinator': {
                    'enabled': True,
                    'description': 'Coordinates tasks across multiple repositories'
                }
            }
        }

        if self.multi_repo_config_file.exists():
            try:
                with open(self.multi_repo_config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception:
                return default_config

        return default_config

    def save_multi_repo_config(self) -> None:
        """Save multi-repository configuration to file"""
        self.multi_repo_config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.multi_repo_config_file, 'w') as f:
            json.dump(self.multi_repo_config, f, indent=2)

    def register_repository(self, repo_path: Path, repo_name: str,
                          repo_type: str = 'unknown', description: str = '') -> None:
        """Register a repository in the workspace"""
        repo_info = {
            'name': repo_name,
            'path': str(repo_path),
            'type': repo_type,
            'description': description,
            'last_accessed': None,
            'active': True
        }

        self.multi_repo_config['repositories'][str(repo_path)] = repo_info
        self.save_multi_repo_config()

    def get_repositories(self) -> Dict[str, Dict]:
        """Get all registered repositories"""
        return self.multi_repo_config['repositories']

    def get_active_repositories(self) -> Dict[str, Dict]:
        """Get only active repositories"""
        return {k: v for k, v in self.multi_repo_config['repositories'].items() if v.get('active', True)}

    def detect_workspace_repositories(self) -> List[Path]:
        """Detect repositories in workspace, excluding cache and system directories"""
        repositories = []

        # Directories to exclude from repository detection
        excluded_patterns = [
            '.cache', 'cache', '__pycache__', 'node_modules', '.npm', '.yarn', '.pnpm',
            '.local', '.config', 'Library', 'AppData', '.vscode', '.idea', '.vs',
            'build', 'dist', '.uv', '.cargo', '.rustup', '.gem', '.pip',
            'lazy', 'checkpoints', 'globalStorage', 'Application Support'
        ]

        # Use a more efficient approach - limit search depth and add early termination
        max_repos = 10
        search_depth = 1  # Limit recursion depth

        def _search_repos(path: Path, depth: int = 0) -> None:
            if depth > search_depth or len(repositories) >= max_repos:
                return

            try:
                for item in path.iterdir():
                    if len(repositories) >= max_repos:
                        break

                    if item.is_dir():
                        if item.name == '.git':
                            repo_path = item.parent
                            path_str = str(repo_path).lower()
                            if not any(pattern.lower() in path_str for pattern in excluded_patterns):
                                repositories.append(repo_path)
                        elif not item.name.startswith('.') and item.name not in excluded_patterns:
                            _search_repos(item, depth + 1)
            except (PermissionError, OSError):
                # Skip directories we can't access
                pass

        _search_repos(self.workspace_root)

        # Sort by modification time (most recent first)
        try:
            repositories.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        except OSError:
            pass  # If we can't stat files, keep original order

        return repositories[:10]  # Ensure we never return more than 10 repositories

    def setup_workspace_awareness(self) -> Dict[str, Any]:
        """Set up workspace awareness for cc-sessions"""
        # Auto-detect repositories
        detected_repos = self.detect_workspace_repositories()
        for repo_path in detected_repos:
            repo_name = repo_path.name
            self.register_repository(
                repo_path,
                repo_name,
                'git',
                f'Auto-detected repository: {repo_name}'
            )

        # Create workspace context
        workspace_context = {
            'initialized_at': self._get_timestamp(),
            'workspace_root': str(self.workspace_root),
            'project_root': str(self.project_root),
            'repositories': [str(repo) for repo in detected_repos],
            'multi_repo_config': self.get_workspace_context(),
            'task_manager_initialized': True
        }

        with open(self.workspace_context_file, 'w') as f:
            json.dump(workspace_context, f, indent=2)

        return workspace_context

    def get_workspace_context(self) -> Dict[str, Any]:
        """Get workspace-wide context information"""
        return {
            'workspace_name': self.multi_repo_config['workspace_name'],
            'repository_count': len(self.get_active_repositories()),
            'repositories': self.get_active_repositories(),
            'shared_agents': self.multi_repo_config['shared_agents'],
            'cross_repo_tasks_enabled': self.multi_repo_config['cross_repo_tasks'],
            'context_sharing_enabled': self.multi_repo_config['context_sharing']
        }

    def should_include_file(self, file_path: Path) -> bool:
        """Check if a file should be included in workspace context"""
        # Check if file is in excluded directory
        for excluded in self.multi_repo_config['excluded_directories']:
            if excluded in str(file_path):
                return False

        # Check if file type is included
        file_suffix = file_path.suffix.lower()
        return file_suffix in self.multi_repo_config['included_file_types']

    def get_workspace_agents(self) -> Dict[str, Dict]:
        """Get workspace-level agents"""
        return self.multi_repo_config['workspace_agents']

    # DAIC Mode Management
    def check_daic_mode_bool(self) -> bool:
        """Check if DAIC (discussion) mode is enabled. Returns True for discussion, False for implementation."""
        self._ensure_state_dir()
        try:
            with open(self.daic_state_file, 'r') as f:
                data = json.load(f)
                return data.get("mode", "discussion") == "discussion"
        except (FileNotFoundError, json.JSONDecodeError):
            # Default to discussion mode if file doesn't exist
            self.set_daic_mode(True)
            return True

    def check_daic_mode(self) -> str:
        """Check if DAIC (discussion) mode is enabled. Returns mode message."""
        self._ensure_state_dir()
        try:
            with open(self.daic_state_file, 'r') as f:
                data = json.load(f)
                mode = data.get("mode", "discussion")
                return self._get_daic_mode_message(mode)
        except (FileNotFoundError, json.JSONDecodeError):
            # Default to discussion mode if file doesn't exist
            self.set_daic_mode(True)
            return self._get_daic_mode_message("discussion")

    def set_daic_mode(self, value: str | bool) -> str:
        """Set DAIC mode to a specific value."""
        self._ensure_state_dir()
        if value == True or value == "discussion":
            mode = "discussion"
            name = "Discussion Mode"
        elif value == False or value == "implementation":
            mode = "implementation"
            name = "Implementation Mode"
        else:
            raise ValueError(f"Invalid mode value: {value}")

        with open(self.daic_state_file, 'w') as f:
            json.dump({"mode": mode}, f, indent=2)
        return name

    def toggle_daic_mode(self) -> str:
        """Toggle DAIC mode and return the new state message."""
        self._ensure_state_dir()
        # Read current mode
        try:
            with open(self.daic_state_file, 'r') as f:
                data = json.load(f)
                current_mode = data.get("mode", "discussion")
        except (FileNotFoundError, json.JSONDecodeError):
            current_mode = "discussion"

        # Toggle and write new value
        new_mode = "implementation" if current_mode == "discussion" else "discussion"
        with open(self.daic_state_file, 'w') as f:
            json.dump({"mode": new_mode}, f, indent=2)

        # Return appropriate message
        return self._get_daic_mode_message(new_mode)

    def _get_daic_mode_message(self, mode: str) -> str:
        """Get DAIC mode message for the given mode."""
        if mode == "discussion":
            return "You are now in Discussion Mode and should focus on discussing and investigating with the user (no edit-based tools)"
        else:
            return "You are now in Implementation Mode and may use tools to execute the agreed upon actions - when you are done return immediately to Discussion Mode"

    # Task State Management
    def get_current_task(self) -> Dict[str, Any]:
        """Get current task state."""
        try:
            with open(self.task_state_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"task": None, "branch": None, "services": [], "updated": None}

    def update_current_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Update current task state."""
        state = {
            "task": task.get("task", ""),
            "branch": task.get("branch", ""),
            "services": task.get("services", []),
            "updated": self._get_timestamp()
        }
        self._ensure_state_dir()
        with open(self.task_state_file, 'w') as f:
            json.dump(state, f, indent=2)
        return state

    def add_service_to_task(self, service: str) -> Dict[str, Any]:
        """Add a service to the current task's affected services list."""
        state = self.get_current_task()
        if service not in state.get("services", []):
            state["services"].append(service)
            self._ensure_state_dir()
            with open(self.task_state_file, 'w') as f:
                json.dump(state, f, indent=2)
        return state

    # Cross-Repository Task Management
    def create_cross_repo_task(self, task_name: str, description: str,
                             affected_repos: List[str], priority: str = 'medium') -> Dict[str, Any]:
        """Create a task that spans multiple repositories"""
        task_id = f"workspace_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        task = {
            'id': task_id,
            'name': task_name,
            'description': description,
            'type': 'cross_repo',
            'affected_repositories': affected_repos,
            'priority': priority,
            'status': 'pending',
            'created_at': self._get_timestamp(),
            'updated_at': self._get_timestamp(),
            'subtasks': [],
            'dependencies': [],
            'context_requirements': {
                'repositories': affected_repos,
                'shared_context': True,
                'cross_repo_analysis': True
            }
        }

        # Save workspace task
        task_file = self.workspace_state_dir / "workspace_tasks" / f"{task_id}.json"
        with open(task_file, 'w') as f:
            json.dump(task, f, indent=2)

        # Create project-specific subtasks
        for repo in affected_repos:
            subtask = self._create_repo_subtask(task, repo)
            task['subtasks'].append(subtask)

        return task

    def _create_repo_subtask(self, parent_task: Dict, repo_path: str) -> Dict[str, Any]:
        """Create a subtask for a specific repository"""
        subtask_id = f"{parent_task['id']}_{Path(repo_path).name}"

        subtask = {
            'id': subtask_id,
            'parent_task_id': parent_task['id'],
            'name': f"{parent_task['name']} - {Path(repo_path).name}",
            'description': f"Repository-specific work for {parent_task['name']}",
            'repository': repo_path,
            'status': 'pending',
            'created_at': self._get_timestamp(),
            'dependencies': [],
            'context_requirements': {
                'repository': repo_path,
                'parent_context': True
            }
        }

        # Save subtask in repository
        repo_tasks_dir = Path(repo_path) / '.claude' / 'state'
        repo_tasks_dir.mkdir(parents=True, exist_ok=True)

        subtask_file = repo_tasks_dir / f"{subtask_id}.json"
        with open(subtask_file, 'w') as f:
            json.dump(subtask, f, indent=2)

        return subtask

    def get_workspace_tasks(self) -> List[Dict[str, Any]]:
        """Get all workspace-level tasks"""
        tasks = []
        workspace_tasks_dir = self.workspace_state_dir / "workspace_tasks"

        if workspace_tasks_dir.exists():
            for task_file in workspace_tasks_dir.glob('*.json'):
                try:
                    with open(task_file, 'r') as f:
                        task = json.load(f)
                        tasks.append(task)
                except Exception:
                    continue

        return sorted(tasks, key=lambda x: x['created_at'], reverse=True)

    # Session Management
    def get_session_start_time(self) -> Optional[str]:
        """Get session start time"""
        try:
            if self.session_start_file.exists():
                with open(self.session_start_file, 'r') as f:
                    data = json.load(f)
                    return data.get('start_time')
        except Exception:
            pass
        return None

    def set_session_start_time(self, start_time: str = None) -> None:
        """Set session start time"""
        if start_time is None:
            start_time = self._get_timestamp()

        self._ensure_state_dir()
        with open(self.session_start_file, 'w') as f:
            json.dump({'start_time': start_time}, f, indent=2)

    # Logging and Analytics
    def log_tool_usage(self, log_entry: Dict[str, Any]) -> None:
        """Log tool usage for analytics"""
        self._append_to_log_file(self.tool_usage_log_file, log_entry)

    def log_command_execution(self, log_entry: Dict[str, Any]) -> None:
        """Log command execution for analytics"""
        self._append_to_log_file(self.tool_usage_log_file, log_entry)

    def log_context_usage(self, log_entry: Dict[str, Any]) -> None:
        """Log context usage for analytics"""
        self._append_to_log_file(self.context_usage_log_file, log_entry)

    def log_warning(self, message: str) -> None:
        """Log warning message"""
        log_entry = {
            'timestamp': self._get_timestamp(),
            'level': 'warning',
            'message': message
        }
        self._append_to_log_file(self.error_log_file, log_entry)

    def log_error(self, message: str) -> None:
        """Log error message"""
        log_entry = {
            'timestamp': self._get_timestamp(),
            'level': 'error',
            'message': message
        }
        self._append_to_log_file(self.error_log_file, log_entry)

    def log_workflow_event(self, event: Dict[str, Any]) -> None:
        """Log workflow event"""
        self._append_to_log_file(self.workflow_events_file, event)

    def _append_to_log_file(self, log_file: Path, entry: Dict[str, Any]) -> None:
        """Append entry to log file"""
        try:
            # Load existing log entries
            if log_file.exists():
                with open(log_file, 'r') as f:
                    log_entries = json.load(f)
            else:
                log_entries = []

            # Add new entry
            log_entries.append(entry)

            # Keep only last 1000 entries to prevent file from growing too large
            if len(log_entries) > 1000:
                log_entries = log_entries[-1000:]

            # Save updated log
            with open(log_file, 'w') as f:
                json.dump(log_entries, f, indent=2)

        except Exception as e:
            print(f"Error logging to {log_file}: {e}", file=sys.stderr)

    # Getters for compatibility
    def get_tool_usage_log(self) -> List[Dict[str, Any]]:
        """Get tool usage log"""
        return self._load_log_file(self.tool_usage_log_file)

    def get_context_usage_log(self) -> List[Dict[str, Any]]:
        """Get context usage log"""
        return self._load_log_file(self.context_usage_log_file)

    def get_error_log(self) -> List[Dict[str, Any]]:
        """Get error log"""
        return self._load_log_file(self.error_log_file)

    def get_workflow_events(self) -> List[Dict[str, Any]]:
        """Get workflow events"""
        return self._load_log_file(self.workflow_events_file)

    def _load_log_file(self, log_file: Path) -> List[Dict[str, Any]]:
        """Load log file entries"""
        try:
            if log_file.exists():
                with open(log_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    # Compatibility methods
    def get_daic_mode(self) -> str:
        """Get current DAIC mode (compatibility method)"""
        return self.check_daic_mode()

    def get_enforcement_state(self) -> Dict[str, Any]:
        """Get enforcement state (compatibility method)"""
        return {"enforcement_active": False}

    def get_compaction_metadata(self) -> Dict[str, Any]:
        """Get compaction metadata (compatibility method)"""
        return {"last_compaction": None}

    def update_compaction_metadata(self, metadata: Dict[str, Any]) -> None:
        """Update compaction metadata (compatibility method)"""
        # In a real implementation, this would update compaction metadata
        pass

    def _ensure_state_dir(self) -> None:
        """Ensure the state directory exists."""
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        return datetime.now().isoformat()


# Global instance for compatibility
_shared_state_instance = None

def get_shared_state() -> EnhancedSharedState:
    """Get the global shared state instance"""
    global _shared_state_instance
    if _shared_state_instance is None:
        _shared_state_instance = EnhancedSharedState()
    return _shared_state_instance

# Compatibility functions for existing code
def get_project_root() -> Path:
    """Get project root (compatibility function)"""
    return get_shared_state().project_root

def get_workspace_root() -> Path:
    """Get workspace root (compatibility function)"""
    return get_shared_state().workspace_root

def check_daic_mode_bool() -> bool:
    """Check DAIC mode boolean (compatibility function)"""
    return get_shared_state().check_daic_mode_bool()

def check_daic_mode() -> str:
    """Check DAIC mode (compatibility function)"""
    return get_shared_state().check_daic_mode()

def set_daic_mode(value: str | bool) -> str:
    """Set DAIC mode (compatibility function)"""
    return get_shared_state().set_daic_mode(value)

def get_task_state() -> Dict[str, Any]:
    """Get task state (compatibility function)"""
    return get_shared_state().get_current_task()

def set_task_state(task: str, branch: str, services: list) -> Dict[str, Any]:
    """Set task state (compatibility function)"""
    return get_shared_state().update_current_task({
        "task": task,
        "branch": branch,
        "services": services
    })

def add_service_to_task(service: str) -> Dict[str, Any]:
    """Add service to task (compatibility function)"""
    return get_shared_state().add_service_to_task(service)

def ensure_state_dir() -> None:
    """Ensure state directory exists (compatibility function)"""
    get_shared_state()._ensure_state_dir()

# Legacy SharedState class for backward compatibility
class SharedState(EnhancedSharedState):
    """Legacy SharedState class for backward compatibility"""
    pass
