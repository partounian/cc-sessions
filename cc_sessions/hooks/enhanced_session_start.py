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
import subprocess
import sys
from pathlib import Path

from enhanced_shared_state import (ensure_state_dir, get_project_root,
                                   get_shared_state, get_task_state)


def initialize_enhanced_session():
    """Initialize enhanced session with workspace awareness"""
    print("Initializing enhanced cc-sessions with workspace awareness...")

    # Get shared state instance
    shared_state = get_shared_state()

    # Get developer name from config
    try:
        CONFIG_FILE = get_project_root() / 'sessions' / 'sessions-config.json'
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                developer_name = config.get('developer_name', 'the developer')
        else:
            developer_name = 'the developer'
    except:
        developer_name = 'the developer'

    # Initialize context
    context = f"""You are beginning a new context window with {developer_name}.

"""

    # Quick configuration checks
    needs_setup = False
    quick_checks = []

    # 1. Check if daic command exists
    try:
        import os
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
    except:
        needs_setup = True
        quick_checks.append("daic command")

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

    # 5. Initialize workspace awareness
    workspace_context = initialize_workspace_awareness(shared_state)

    # 6. Check if sessions directory exists
    sessions_dir = get_project_root() / 'sessions'
    if sessions_dir.exists():
        # Check for active task
        task_state = get_task_state()
        if task_state.get("task"):
            task_file = sessions_dir / 'tasks' / f"{task_state['task']}.md"
            if task_file.exists():
                # Check if task status is pending and update to in-progress
                task_content = task_file.read_text()
                task_updated = False

                # Parse task frontmatter to check status
                if task_content.startswith('---'):
                    lines = task_content.split('\n')
                    for i, line in enumerate(lines[1:], 1):
                        if line.startswith('---'):
                            break
                        if line.startswith('status: pending'):
                            lines[i] = 'status: in-progress'
                            task_updated = True
                            # Write back the updated content
                            task_file.write_text('\n'.join(lines))
                            task_content = '\n'.join(lines)
                            break

                # Output the full task state
                context += f"""Current task state:
```json
{json.dumps(task_state, indent=2)}
```

Loading task file: {task_state['task']}.md
{"=" * 60}
{task_content}
{"=" * 60}
"""

                if task_updated:
                    context += """
[Note: Task status updated from 'pending' to 'in-progress']
Follow the task-startup protocol to create branches and set up the work environment.
"""
                else:
                    context += """
Review the Work Log at the end of the task file above.
Continue from where you left off, updating the work log as you progress.
"""
        else:
            # No active task - list available tasks
            tasks_dir = sessions_dir / 'tasks'
            task_files = []
            if tasks_dir.exists():
                task_files = sorted([f for f in tasks_dir.glob('*.md') if f.name != 'TEMPLATE.md'])

            if task_files:
                context += """No active task set. Available tasks:

"""
                for task_file in task_files:
                    # Read first few lines to get task info
                    with open(task_file, 'r') as f:
                        lines = f.readlines()[:10]
                        task_name = task_file.stem
                        status = 'unknown'
                        for line in lines:
                            if line.startswith('status:'):
                                status = line.split(':')[1].strip()
                                break
                        context += f"  • {task_name} ({status})\n"

                context += """
To select a task:
1. Update .claude/state/current_task.json with the task name
2. Or create a new task following sessions/protocols/task-creation.md
"""
            else:
                context += """No tasks found.

To create your first task:
1. Copy the template: cp sessions/tasks/TEMPLATE.md sessions/tasks/[priority]-[task-name].md
   Priority prefixes: h- (high), m- (medium), l- (low), ?- (investigate)
2. Fill in the task details
3. Update .claude/state/current_task.json
4. Follow sessions/protocols/task-startup.md
"""
    else:
        # Sessions directory doesn't exist - likely first run
        context += """Sessions system is not yet initialized.

Run the install script to set up the sessions framework:
.claude/sessions-setup.sh

Or follow the manual setup in the documentation.
"""

    # Add workspace information if multi-repo setup is available
    if workspace_context.get('repositories'):
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

            # Limit output to prevent overwhelming the console
            for i, repo in enumerate(repositories[:10]):  # Show only first 10
                print(f"  - {repo.name} ({repo})")
            
            if len(repositories) > 10:
                print(f"  ... and {len(repositories) - 10} more repositories")
                
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
        context = initialize_enhanced_session()

        output = {
            "hookSpecificOutput": {
                "hookEventName": "EnhancedSessionStart",
                "additionalContext": context
            }
        }
        print(json.dumps(output))

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
