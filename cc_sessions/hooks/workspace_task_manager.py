#!/usr/bin/env python3
"""
Workspace-aware task management for multi-repository environments

This module provides task management that works across multiple
connected repositories in a workspace.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class WorkspaceTaskManager:
    """Manages tasks across multiple repositories in a workspace"""

    def __init__(self, workspace_root: Path, project_root: Path):
        self.workspace_root = workspace_root
        self.project_root = project_root
        self.workspace_tasks_dir = workspace_root / '.claude' / 'workspace_tasks'
        self.project_tasks_dir = project_root / '.claude' / 'state'

        # Ensure directories exist
        self.workspace_tasks_dir.mkdir(parents=True, exist_ok=True)
        self.project_tasks_dir.mkdir(parents=True, exist_ok=True)

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
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'subtasks': [],
            'dependencies': [],
            'context_requirements': {
                'repositories': affected_repos,
                'shared_context': True,
                'cross_repo_analysis': True
            }
        }

        # Save workspace task
        task_file = self.workspace_tasks_dir / f"{task_id}.json"
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
            'created_at': datetime.now().isoformat(),
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

        for task_file in self.workspace_tasks_dir.glob('*.json'):
            try:
                with open(task_file, 'r') as f:
                    task = json.load(f)
                    tasks.append(task)
            except Exception:
                continue

        return sorted(tasks, key=lambda x: x['created_at'], reverse=True)

    def get_repo_tasks(self, repo_path: str) -> List[Dict[str, Any]]:
        """Get tasks for a specific repository"""
        tasks = []
        repo_tasks_dir = Path(repo_path) / '.claude' / 'state'

        if not repo_tasks_dir.exists():
            return tasks

        for task_file in repo_tasks_dir.glob('*.json'):
            try:
                with open(task_file, 'r') as f:
                    task = json.load(f)
                    if task.get('type') != 'cross_repo':  # Only repo-specific tasks
                        tasks.append(task)
            except Exception:
                continue

        return sorted(tasks, key=lambda x: x.get('created_at', ''), reverse=True)

    def update_task_status(self, task_id: str, status: str, repo_path: Optional[str] = None):
        """Update task status"""
        if repo_path:
            # Update repository-specific task
            task_file = Path(repo_path) / '.claude' / 'state' / f"{task_id}.json"
        else:
            # Update workspace task
            task_file = self.workspace_tasks_dir / f"{task_id}.json"

        if task_file.exists():
            try:
                with open(task_file, 'r') as f:
                    task = json.load(f)

                task['status'] = status
                task['updated_at'] = datetime.now().isoformat()

                with open(task_file, 'w') as f:
                    json.dump(task, f, indent=2)

                # If this is a subtask, update parent task
                if repo_path and 'parent_task_id' in task:
                    self._update_parent_task_status(task['parent_task_id'])

            except Exception as e:
                print(f"Error updating task status: {e}")

    def _update_parent_task_status(self, parent_task_id: str):
        """Update parent task status based on subtasks"""
        parent_task_file = self.workspace_tasks_dir / f"{parent_task_id}.json"

        if not parent_task_file.exists():
            return

        try:
            with open(parent_task_file, 'r') as f:
                parent_task = json.load(f)

            # Check subtask statuses
            subtask_statuses = []
            for subtask in parent_task.get('subtasks', []):
                subtask_file = Path(subtask['repository']) / '.claude' / 'state' / f"{subtask['id']}.json"
                if subtask_file.exists():
                    with open(subtask_file, 'r') as f:
                        subtask_data = json.load(f)
                        subtask_statuses.append(subtask_data['status'])

            # Determine parent status
            if all(status == 'completed' for status in subtask_statuses):
                parent_task['status'] = 'completed'
            elif any(status == 'in_progress' for status in subtask_statuses):
                parent_task['status'] = 'in_progress'
            else:
                parent_task['status'] = 'pending'

            parent_task['updated_at'] = datetime.now().isoformat()

            with open(parent_task_file, 'w') as f:
                json.dump(parent_task, f, indent=2)

        except Exception as e:
            print(f"Error updating parent task status: {e}")

    def get_workspace_context(self) -> Dict[str, Any]:
        """Get workspace-wide context for tasks"""
        workspace_tasks = self.get_workspace_tasks()
        active_tasks = [t for t in workspace_tasks if t['status'] in ['pending', 'in_progress']]

        return {
            'workspace_root': str(self.workspace_root),
            'project_root': str(self.project_root),
            'total_tasks': len(workspace_tasks),
            'active_tasks': len(active_tasks),
            'recent_tasks': workspace_tasks[:5],
            'cross_repo_tasks': [t for t in active_tasks if t.get('type') == 'cross_repo']
        }

    def cleanup_completed_tasks(self, days_old: int = 30):
        """Clean up completed tasks older than specified days"""
        cutoff_date = datetime.now().timestamp() - (days_old * 24 * 60 * 60)

        for task_file in self.workspace_tasks_dir.glob('*.json'):
            try:
                with open(task_file, 'r') as f:
                    task = json.load(f)

                if (task.get('status') == 'completed' and
                    datetime.fromisoformat(task['updated_at']).timestamp() < cutoff_date):
                    task_file.unlink()

            except Exception:
                continue
