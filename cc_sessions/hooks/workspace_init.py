#!/usr/bin/env python3
"""
Workspace initialization for multi-repository cc-sessions setup

This script initializes workspace awareness for cc-sessions
when working with multiple connected repositories.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add the cc_sessions directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hooks.multi_repo_config import (detect_workspace_repositories,
                                     setup_workspace_awareness)
from hooks.shared_state import get_project_root, get_workspace_root
from hooks.workspace_task_manager import WorkspaceTaskManager


def initialize_workspace_awareness():
    """Initialize workspace awareness for cc-sessions"""
    print("Initializing workspace awareness for cc-sessions...")

    # Get workspace and project roots
    project_root = get_project_root()
    workspace_root = get_workspace_root()

    print(f"Project root: {project_root}")
    print(f"Workspace root: {workspace_root}")

    # Set up multi-repo configuration
    config = setup_workspace_awareness(workspace_root)

    # Detect repositories
    repositories = detect_workspace_repositories(workspace_root)
    print(f"Detected {len(repositories)} repositories:")

    for repo in repositories:
        print(f"  - {repo.name} ({repo})")

    # Initialize workspace task manager
    task_manager = WorkspaceTaskManager(workspace_root, project_root)

    # Create workspace context file
    workspace_context = {
        'initialized_at': str(Path(__file__).stat().st_mtime),
        'workspace_root': str(workspace_root),
        'project_root': str(project_root),
        'repositories': [str(repo) for repo in repositories],
        'multi_repo_config': config.get_workspace_context(),
        'task_manager_initialized': True
    }

    context_file = workspace_root / '.claude' / 'workspace_context.json'
    context_file.parent.mkdir(parents=True, exist_ok=True)

    with open(context_file, 'w') as f:
        json.dump(workspace_context, f, indent=2)

    print(f"Workspace context saved to: {context_file}")
    print("Workspace awareness initialized successfully!")

    return workspace_context

def create_workspace_agent_configs():
    """Create workspace-specific agent configurations"""
    workspace_root = get_workspace_root()
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

def main():
    """Main initialization function"""
    try:
        # Initialize workspace awareness
        workspace_context = initialize_workspace_awareness()

        # Create workspace agent configurations
        create_workspace_agent_configs()

        print("\n🎉 Workspace awareness setup complete!")
        print("\nNext steps:")
        print("1. Use 'Create a cross-repo task for: [description]' to create workspace tasks")
        print("2. Use 'Analyze workspace relationships' to understand repo connections")
        print("3. Use 'Coordinate changes across repos' for multi-repo workflows")

        return True

    except Exception as e:
        print(f"❌ Error initializing workspace awareness: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
