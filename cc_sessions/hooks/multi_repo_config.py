#!/usr/bin/env python3
"""
Multi-repository configuration for cc-sessions hooks

This module provides configuration and utilities for working with
multiple connected repositories in a workspace environment.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Set


class MultiRepoConfig:
    """Configuration manager for multi-repository workspaces"""

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.config_file = workspace_root / '.claude' / 'multi_repo_config.json'
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load multi-repo configuration"""
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

        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception:
                return default_config

        return default_config

    def save_config(self):
        """Save configuration to file"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def register_repository(self, repo_path: Path, repo_name: str,
                          repo_type: str = 'unknown', description: str = ''):
        """Register a repository in the workspace"""
        repo_info = {
            'name': repo_name,
            'path': str(repo_path),
            'type': repo_type,
            'description': description,
            'last_accessed': None,
            'active': True
        }

        self.config['repositories'][str(repo_path)] = repo_info
        self.save_config()

    def get_repositories(self) -> Dict[str, Dict]:
        """Get all registered repositories"""
        return self.config['repositories']

    def get_active_repositories(self) -> Dict[str, Dict]:
        """Get only active repositories"""
        return {k: v for k, v in self.config['repositories'].items() if v.get('active', True)}

    def find_related_repositories(self, current_repo: Path) -> List[Dict]:
        """Find repositories related to the current one"""
        related = []
        current_str = str(current_repo)

        for repo_path, repo_info in self.get_active_repositories().items():
            if repo_path != current_str:
                # Check for common patterns that might indicate relationship
                if self._are_repositories_related(current_repo, Path(repo_path)):
                    related.append(repo_info)

        return related

    def _are_repositories_related(self, repo1: Path, repo2: Path) -> bool:
        """Check if two repositories are related"""
        try:
            # Check for common dependencies
            for repo in [repo1, repo2]:
                package_files = ['package.json', 'requirements.txt', 'pyproject.toml', 'Cargo.toml']
                for pkg_file in package_files:
                    if (repo / pkg_file).exists():
                        # Simple heuristic: if both have similar package files, they might be related
                        return True

            # Check for shared configuration files
            config_files = ['.vscode', '.idea', 'docker-compose.yml', 'Makefile']
            for config_file in config_files:
                if ((repo1 / config_file).exists() and
                    (repo2 / config_file).exists()):
                    return True

            return False
        except Exception:
            return False

    def get_workspace_context(self) -> Dict:
        """Get workspace-wide context information"""
        return {
            'workspace_name': self.config['workspace_name'],
            'repository_count': len(self.get_active_repositories()),
            'repositories': self.get_active_repositories(),
            'shared_agents': self.config['shared_agents'],
            'cross_repo_tasks_enabled': self.config['cross_repo_tasks'],
            'context_sharing_enabled': self.config['context_sharing']
        }

    def should_include_file(self, file_path: Path) -> bool:
        """Check if a file should be included in workspace context"""
        # Check if file is in excluded directory
        for excluded in self.config['excluded_directories']:
            if excluded in str(file_path):
                return False

        # Check if file type is included
        file_suffix = file_path.suffix.lower()
        return file_suffix in self.config['included_file_types']

    def get_workspace_agents(self) -> Dict[str, Dict]:
        """Get workspace-level agents"""
        return self.config['workspace_agents']

    def update_repository_access(self, repo_path: Path):
        """Update last accessed time for a repository"""
        repo_str = str(repo_path)
        if repo_str in self.config['repositories']:
            from datetime import datetime
            self.config['repositories'][repo_str]['last_accessed'] = datetime.now().isoformat()
            self.save_config()

def get_multi_repo_config(workspace_root: Path) -> MultiRepoConfig:
    """Get multi-repo configuration for workspace"""
    return MultiRepoConfig(workspace_root)

def detect_workspace_repositories(workspace_root: Path) -> List[Path]:
    """Detect repositories in workspace"""
    repositories = []

    # Look for git repositories
    for git_dir in workspace_root.rglob('.git'):
        if git_dir.is_dir():
            repo_path = git_dir.parent
            repositories.append(repo_path)

    return repositories

def setup_workspace_awareness(workspace_root: Path) -> MultiRepoConfig:
    """Set up workspace awareness for cc-sessions"""
    config = MultiRepoConfig(workspace_root)

    # Auto-detect repositories
    detected_repos = detect_workspace_repositories(workspace_root)
    for repo_path in detected_repos:
        repo_name = repo_path.name
        config.register_repository(
            repo_path,
            repo_name,
            'git',
            f'Auto-detected repository: {repo_name}'
        )

    return config
