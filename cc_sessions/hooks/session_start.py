#!/usr/bin/env python3
"""
Enhanced Session Start Hook for cc-sessions

Integrates session initialization, workspace awareness setup, and multi-repository
detection into a single, comprehensive hook.

This enhanced version replaces:
- session-start.py (basic session initialization)
- workspace_init.py (workspace awareness setup)

Key features:
- Session initialization and task state management
- Multi-repository workspace detection and setup
- Workspace-aware context sharing
- Agent configuration setup
- Enhanced developer experience with comprehensive setup guidance
"""

import json
import os
import sys
from pathlib import Path

# Add the cc_sessions directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared_state import (ensure_state_dir, get_project_root,
                                   get_shared_state, get_task_state)


def _log_warning(shared_state, message: str) -> None:
    """Best-effort warning logger for this module."""
    try:
        if shared_state is not None:
            shared_state.log_warning(f"session_start: {message}")
            return
    except Exception:
        pass
    print(f"WARNING: session_start: {message}", file=sys.stderr)


def initialize_session():
    """Initialize enhanced session with workspace awareness"""
    # Session initialization (quiet mode - details in context output)

    # Get shared state instance
    shared_state = get_shared_state()

    try:
        CONFIG_FILE = get_project_root() / 'sessions' / 'sessions-config.json'
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                developer_name = config.get('developer_name', 'the developer')
        else:
            developer_name = 'the developer'
    except Exception as exc:
        developer_name = 'the developer'
        _log_warning(shared_state, f"Failed to load developer name: {exc}")

    # Initialize context
    context = f"""You are beginning a new context window with {developer_name}.

"""

    # Quick configuration checks
    needs_setup = False
    quick_checks = []

    # 1. Check if daic command exists
    try:
        import shutil

        # Cross-platform command detection
        if os.name == 'nt':
            # Windows - check for .cmd or .ps1 versions
            if not (shutil.which('daic.cmd') or shutil.which('daic.ps1') or shutil.which('daic')):
                needs_setup = True
                quick_checks.append("daic command")
        else:
            # Unix/Mac - use which command
            if not shutil.which('daic'):
                needs_setup = True
                quick_checks.append("daic command")
    except Exception as exc:
        needs_setup = True
        quick_checks.append("daic command")
        _log_warning(shared_state, f"Failed daic command check: {exc}")

    # 2. Check if tiktoken is installed (required for subagent transcript chunking)
    try:
        import tiktoken
    except ImportError:
        needs_setup = True
        quick_checks.append("tiktoken (pip install tiktoken)")

    # 3. Check if DAIC state file exists (create if not)
    ensure_state_dir()
    daic_state_file = get_project_root() / '.claude' / 'state' / 'daic-mode.json'
    if not daic_state_file.exists():
        # Create default state
        with open(daic_state_file, 'w') as f:
            json.dump({"mode": "discussion"}, f, indent=2)

    # 4. Clear context warning flags for new session
    warning_75_flag = get_project_root() / '.claude' / 'state' / 'context-warning-75.flag'
    warning_90_flag = get_project_root() / '.claude' / 'state' / 'context-warning-90.flag'
    if warning_75_flag.exists():
        warning_75_flag.unlink()
    if warning_90_flag.exists():
        warning_90_flag.unlink()

    # 4b. Clear any lingering subagent context
    try:
        shared_state.clear_subagent_state()
    except Exception as exc:
        _log_warning(shared_state, f"clear_subagent_state failed: {exc}")

    # 5. Initialize workspace awareness
    workspace_context = initialize_workspace_awareness(shared_state)

    # 6. Check if sessions directory exists
    sessions_dir = get_project_root() / 'sessions'
    if sessions_dir.exists():
        context = _append_task_context(context, shared_state, sessions_dir)
    else:
        # Sessions directory doesn't exist - likely first run
        context += """Sessions system is not yet initialized.

Run the install script to set up the sessions framework:
.claude/sessions-setup.sh

Or follow the manual setup in the documentation.
"""

    # Add workspace information if multi-repo setup is available
    if workspace_context.get('repositories'):
        # TODO: might need to enable
        # repos = workspace_context.get('repositories', [])
        context += f"""

## Workspace Information

**Workspace Root:** {workspace_context.get('workspace_root', 'Unknown')}
**Detected Repositories:** {len(workspace_context.get('repositories', []))}

"""
        for repo_path in workspace_context.get('repositories', []):
            repo_name = Path(repo_path).name
            context += f"  • {repo_name} ({repo_path})\n"

        context += """
**Multi-Repository Features Available:**
- Cross-repository task coordination
- Workspace-aware context sharing
- Repository relationship analysis
- Coordinated change management

To use multi-repository features:
- Create cross-repo tasks: "Create a cross-repo task for: [description]"
- Analyze relationships: "Analyze workspace relationships"
- Coordinate changes: "Coordinate implementation across repos"
"""

    # If setup is needed, provide guidance
    if needs_setup:
        context += f"""
[Setup Required]
Missing components: {', '.join(quick_checks)}

To complete setup:
1. Run the cc-sessions installer
2. Ensure the daic command is in your PATH

The sessions system helps manage tasks and maintain discussion/implementation workflow discipline.
"""

    return context


def _append_task_context(context: str, shared_state, sessions_dir: Path) -> str:
    task_state = get_task_state()
    if task_state.get("task"):
        return _append_active_task_context(context, shared_state, sessions_dir, task_state)
    return _append_available_tasks_context(context, sessions_dir)


def _append_active_task_context(context: str, shared_state, sessions_dir: Path, task_state: dict) -> str:
    task_file = sessions_dir / 'tasks' / f"{task_state['task']}.md"
    if task_file.exists():
        return _append_existing_task(context, shared_state, task_state, task_file)
    return _append_missing_task_file_context(context, shared_state)


def _append_existing_task(context: str, shared_state, task_state: dict, task_file: Path) -> str:
    task_updated = False
    try:
        task_content, task_updated = _ensure_task_status(task_file)
        context += _render_task_state(task_state, task_content)
    except Exception as exc:
        _log_warning(shared_state, f"Failed to update or read task file '{task_file}': {exc}")
        task_content = None

    if task_content is None:
        context += "\n[Warning] Could not read task file content. Check logs for details.\n"

    context = _append_resume_plan(context, shared_state)
    return _append_task_resume_guidance(context, task_updated)


def _ensure_task_status(task_file: Path) -> tuple[str, bool]:
    task_content = task_file.read_text()
    if not task_content.startswith('---'):
        return task_content, False

    lines = task_content.split('\n')
    task_updated = False
    for index, line in enumerate(lines[1:], 1):
        if line.startswith('---'):
            break
        if line.startswith('status: pending'):
            lines[index] = 'status: in-progress'
            task_updated = True
            task_file.write_text('\n'.join(lines))
            task_content = '\n'.join(lines)
            break

    return task_content, task_updated


def _render_task_state(task_state: dict, task_content: str) -> str:
    return f"""Current task state:
```json
{json.dumps(task_state, indent=2)}
```

Loading task file: {task_state['task']}.md
{"=" * 60}
{task_content}
{"=" * 60}
"""


def _append_resume_plan(context: str, shared_state) -> str:
    try:
        comp_dir = get_project_root() / '.claude' / 'state' / 'compaction'
        manifest_file = comp_dir / 'context_manifest.json'
        if manifest_file.exists():
            resume_instructions = json.loads(manifest_file.read_text()).get('recovery_instructions') or []
            if resume_instructions:
                context += """

Resume plan from last compaction:

"""
                for instruction in resume_instructions[:5]:
                    context += f"- {instruction}\n"
    except Exception as exc:
        _log_warning(shared_state, f"Failed to read compaction manifest: {exc}")
    return context


def _append_task_resume_guidance(context: str, task_updated: bool) -> str:
    if task_updated:
        return context + """
[Note: Task status updated from 'pending' to 'in-progress']
Follow the task-startup protocol to create branches and set up the work environment.
"""
    return context + """
Review the Work Log at the end of the task file above.
Continue from where you left off, updating the work log as you progress.
"""


def _append_missing_task_file_context(context: str, shared_state) -> str:
    try:
        comp_dir = get_project_root() / '.claude' / 'state' / 'compaction'
        manifest_file = comp_dir / 'context_manifest.json'
        if manifest_file.exists():
            resume_instructions = json.loads(manifest_file.read_text()).get('recovery_instructions') or []
            if resume_instructions:
                context += """

Resume plan from last compaction:

"""
                for instruction in resume_instructions[:5]:
                    context += f"- {instruction}\n"
    except Exception as exc:
        _log_warning(shared_state, f"Failed to read compaction manifest for missing task file: {exc}")
    return context


def _append_available_tasks_context(context: str, sessions_dir: Path) -> str:
    tasks_dir = sessions_dir / 'tasks'
    task_files = []
    if tasks_dir.exists():
        task_files = sorted([path for path in tasks_dir.glob('*.md') if path.name != 'TEMPLATE.md'])

    if task_files:
        context += """No active task set. Available tasks:

"""
        context += ''.join(_render_task_summary(task_file) for task_file in task_files)
        context += """
To select a task:
1. Update .claude/state/current_task.json with the task name
2. Or create a new task following sessions/protocols/task-creation.md
"""
        return context

    return context + """No tasks found.

To create your first task:
1. Copy the template: cp sessions/tasks/TEMPLATE.md sessions/tasks/[priority]-[task-name].md
   Priority prefixes: h- (high), m- (medium), l- (low), ?- (investigate)
2. Fill in the task details
3. Update .claude/state/current_task.json
4. Follow sessions/protocols/task-startup.md
"""


def _render_task_summary(task_file: Path) -> str:
    with open(task_file, 'r') as file_handle:
        lines = file_handle.readlines()[:10]
    task_name = task_file.stem
    status = 'unknown'
    for line in lines:
        if line.startswith('status:'):
            status = line.split(':')[1].strip()
            break
    return f"  • {task_name} ({status})\n"

def initialize_workspace_awareness(shared_state):
    """Initialize workspace awareness for multi-repository support"""
    try:
        print("Setting up workspace awareness...")

        # Set up workspace awareness
        workspace_context = shared_state.setup_workspace_awareness()

        # Detect repositories (with timeout protection)
        try:
            repositories = shared_state.detect_workspace_repositories()
            print(f"Detected {len(repositories)} repositories:")

            # Show all detected repositories (max 10)
            for repo in repositories:
                print(f"  - {repo.name} ({repo})")

        except Exception as e:
            print(f"Warning: Repository detection failed: {e}")
            repositories = []

        # Create workspace agent configurations
        create_workspace_agent_configs(shared_state)

        print("Workspace awareness initialized successfully!")

        return workspace_context

    except Exception as e:
        print(f"Error initializing workspace awareness: {e}")
        return {
            'workspace_root': str(shared_state.workspace_root),
            'project_root': str(shared_state.project_root),
            'repositories': [],
            'error': str(e)
        }

def create_workspace_agent_configs(shared_state):
    """Create workspace-specific agent configurations"""
    try:
        workspace_root = shared_state.workspace_root
        agents_dir = workspace_root / '.claude' / 'agents'
        agents_dir.mkdir(parents=True, exist_ok=True)

        # Cross-repo analyzer agent
        cross_repo_analyzer = {
            'name': 'cross_repo_analyzer',
            'description': 'Analyzes relationships and dependencies between repositories',
            'capabilities': [
                'dependency_analysis',
                'code_relationship_mapping',
                'cross_repo_impact_assessment',
                'shared_pattern_detection'
            ],
            'context_requirements': {
                'multi_repo_awareness': True,
                'dependency_graphs': True,
                'shared_configurations': True
            },
            'prompt_template': """
You are a cross-repository analyzer agent. Your role is to:

1. Analyze relationships between repositories in this workspace
2. Identify shared dependencies and patterns
3. Assess impact of changes across repositories
4. Suggest coordination strategies for multi-repo tasks

Current workspace context:
- Workspace root: {workspace_root}
- Active repositories: {repositories}
- Current task: {current_task}

Analyze the current context and provide insights about cross-repository relationships and dependencies.
"""
        }

        # Workspace coordinator agent
        workspace_coordinator = {
            'name': 'workspace_coordinator',
            'description': 'Coordinates tasks and changes across multiple repositories',
            'capabilities': [
                'task_coordination',
                'change_impact_assessment',
                'dependency_management',
                'workflow_orchestration'
            ],
            'context_requirements': {
                'multi_repo_awareness': True,
                'task_management': True,
                'git_integration': True
            },
            'prompt_template': """
You are a workspace coordinator agent. Your role is to:

1. Coordinate tasks across multiple repositories
2. Manage dependencies between repositories
3. Ensure consistent changes across related projects
4. Orchestrate complex multi-repo workflows

Current workspace context:
- Workspace root: {workspace_root}
- Active repositories: {repositories}
- Current task: {current_task}

Coordinate the current task across the relevant repositories and suggest a workflow.
"""
        }

        # Save agent configurations
        with open(agents_dir / 'cross_repo_analyzer.json', 'w') as f:
            json.dump(cross_repo_analyzer, f, indent=2)

        with open(agents_dir / 'workspace_coordinator.json', 'w') as f:
            json.dump(workspace_coordinator, f, indent=2)

        print(f"Workspace agent configurations created in: {agents_dir}")

    except Exception as e:
        print(f"Error creating workspace agent configurations: {e}")

def main():
    """Main entry point for Enhanced Session Start hook"""
    try:
        # Initialize enhanced session
        context = initialize_session()

        # Output human-readable context only (no JSON for SessionStart)
        # Wrap in a simple tag so the runner can still collapse the block if desired.
        print(f"<session-start>\n{context}\n</session-start>")

    except Exception as e:
        error_output = {
            "hookSpecificOutput": {
                "hookEventName": "EnhancedSessionStart",
                "error": f"Failed to initialize enhanced session: {e}",
                "additionalContext": "Session initialization failed. Please check the setup and try again."
            }
        }
        print(json.dumps(error_output), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
