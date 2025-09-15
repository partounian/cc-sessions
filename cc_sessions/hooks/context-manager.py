#!/usr/bin/env python3
"""
Unified Context Manager Hook for cc-sessions

Combines context preservation, notification handling, and context optimization
into a single, efficient hook that manages all context-related concerns.

This hook replaces:
- pre-compact.py (context preservation before compaction)
- notification-handler.py (intelligent notification handling)

Key features:
- Context preservation before compaction
- Intelligent notification handling
- Context optimization and token management
- Agent context preservation
- Context efficiency monitoring
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add the cc_sessions directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Multi-repo functionality is now integrated into enhanced_shared_state
from hooks.shared_state import SharedState


class ContextManager:
    """Manages context preservation, notifications, and optimization"""

    def __init__(self):
        self.shared_state = SharedState()
        self.context_dir = Path('.claude/state')
        self.agent_context_dir = self.context_dir / 'agent_context'
        self.compaction_dir = self.context_dir / 'compaction'

        # Multi-repo awareness is now handled by enhanced_shared_state
        # self.multi_repo_config = get_multi_repo_config(self.shared_state.workspace_root)

        # Ensure directories exist
        self.agent_context_dir.mkdir(parents=True, exist_ok=True)
        self.compaction_dir.mkdir(parents=True, exist_ok=True)

        # Notification handling configuration
        self.safe_operations = [
            'read_file', 'list_dir', 'grep', 'codebase_search',
            'run_terminal_cmd', 'edit_file', 'search_replace'
        ]
        self.unsafe_operations = [
            'delete_file', 'run_terminal_cmd', 'write'
        ]

    def handle_context_event(self, event_type: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle different types of context events"""
        try:
            if event_type == "pre_compact":
                return self._handle_pre_compact(data)
            elif event_type == "notification":
                return self._handle_notification(data)
            elif event_type == "context_optimization":
                return self._handle_context_optimization(data)
            else:
                return self._handle_unknown_event(event_type, data)

        except Exception as e:
            self._log_error(f"Error handling context event {event_type}: {e}")
            return None

    def _handle_pre_compact(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle context preservation before compaction"""
        try:
            # Extract and preserve agent context
            agent_context = self._extract_agent_context()
            self._save_agent_context_summary(agent_context)

            # Preserve workflow state
            workflow_state = self._extract_workflow_state()
            self._save_workflow_state_summary(workflow_state)

            # Preserve task context
            task_context = self._extract_task_context()
            self._save_task_context_summary(task_context)

            # Create context manifest for post-compaction recovery
            context_manifest = self._create_context_manifest(
                agent_context, workflow_state, task_context
            )
            self._save_context_manifest(context_manifest)

            # Update compaction metadata
            self._update_compaction_metadata(context_manifest)

            return {
                'status': 'success',
                'message': 'Context preserved successfully',
                'timestamp': self._get_timestamp(),
                'preserved_agents': len(agent_context.get('active_agents', [])),
                'context_sources': len(context_manifest.get('priority_context', {}).get('critical_files', []))
            }

        except Exception as e:
            self._log_error(f"Error handling pre-compact: {e}")
            return {
                'status': 'error',
                'message': f'Failed to preserve context: {e}',
                'timestamp': self._get_timestamp()
            }

    def _handle_notification(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle different types of notifications"""
        try:
            notification_type = data.get('notification_type', '')
            notification_data = data.get('data', {})

            if notification_type == "permission_request":
                return self._handle_permission_request(notification_data)
            elif notification_type == "idle_input":
                return self._handle_idle_input(notification_data)
            elif notification_type == "context_warning":
                return self._handle_context_warning(notification_data)
            elif notification_type == "tool_blocked":
                return self._handle_tool_blocked(notification_data)
            else:
                return self._handle_unknown_notification(notification_type, notification_data)

        except Exception as e:
            self._log_error(f"Error handling notification: {e}")
            return None

    def _handle_permission_request(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle permission requests with intelligent approval"""
        try:
            operation = data.get('operation', '')
            tool_name = data.get('tool_name', '')
            parameters = data.get('parameters', {})

            # Check if operation is safe to auto-approve
            if self._is_safe_operation(tool_name, parameters):
                self._log_info(f"Auto-approving safe operation: {tool_name}")
                return {
                    'approved': True,
                    'reason': 'Safe operation detected',
                    'auto_approved': True
                }

            # Check if operation is clearly unsafe
            elif self._is_unsafe_operation(tool_name, parameters):
                self._log_warning(f"Blocking unsafe operation: {tool_name}")
                return {
                    'approved': False,
                    'reason': 'Unsafe operation detected',
                    'auto_blocked': True
                }

            # For ambiguous operations, provide context-aware response
            else:
                return self._provide_context_aware_response(tool_name, parameters)

        except Exception as e:
            self._log_error(f"Error handling permission request: {e}")
            return None

    def _handle_idle_input(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle idle input with context-aware suggestions"""
        try:
            current_context = self._get_current_context()
            suggestions = self._generate_context_suggestions(current_context)

            if suggestions:
                return {
                    'suggestions': suggestions,
                    'context_aware': True,
                    'timestamp': self._get_timestamp()
                }

            return None

        except Exception as e:
            self._log_error(f"Error handling idle input: {e}")
            return None

    def _handle_context_warning(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle context warnings with optimization suggestions"""
        try:
            context_usage = data.get('context_usage', {})
            suggestions = self._generate_context_optimization_suggestions(context_usage)

            return {
                'optimization_suggestions': suggestions,
                'context_usage': context_usage,
                'timestamp': self._get_timestamp()
            }

        except Exception as e:
            self._log_error(f"Error handling context warning: {e}")
            return None

    def _handle_tool_blocked(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle tool blocked notifications with alternative suggestions"""
        try:
            tool_name = data.get('tool_name', '')
            reason = data.get('reason', '')

            alternatives = self._suggest_alternative_tools(tool_name, reason)

            return {
                'alternative_tools': alternatives,
                'blocked_tool': tool_name,
                'reason': reason,
                'timestamp': self._get_timestamp()
            }

        except Exception as e:
            self._log_error(f"Error handling tool blocked: {e}")
            return None

    def _handle_context_optimization(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle context optimization requests"""
        try:
            context_usage = data.get('context_usage', {})
            optimization_suggestions = self._generate_context_optimization_suggestions(context_usage)

            return {
                'optimization_suggestions': optimization_suggestions,
                'context_efficiency': context_usage.get('context_efficiency', 0),
                'timestamp': self._get_timestamp()
            }

        except Exception as e:
            self._log_error(f"Error handling context optimization: {e}")
            return {
                'status': 'error',
                'message': f'Context optimization failed: {e}',
                'timestamp': self._get_timestamp()
            }

    def _handle_unknown_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unknown event types"""
        self._log_warning(f"Unknown context event type: {event_type}")
        return {
            'event_type': event_type,
            'handled': False,
            'timestamp': self._get_timestamp()
        }

    def _handle_unknown_notification(self, notification_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unknown notification types"""
        self._log_warning(f"Unknown notification type: {notification_type}")
        return {
            'notification_type': notification_type,
            'handled': False,
            'timestamp': self._get_timestamp()
        }

    def _extract_agent_context(self) -> Dict[str, Any]:
        """Extract critical agent context that needs preservation"""
        agent_context = {
            'active_agents': [],
            'agent_states': {},
            'agent_results': {},
            'context_requirements': {},
            'agent_dependencies': {}
        }

        try:
            # Check for active agent contexts
            if self.agent_context_dir.exists():
                for agent_type_dir in self.agent_context_dir.iterdir():
                    if agent_type_dir.is_dir():
                        agent_type = agent_type_dir.name
                        agent_context['active_agents'].append(agent_type)

                        # Extract agent state
                        agent_state = self._extract_agent_state(agent_type_dir)
                        agent_context['agent_states'][agent_type] = agent_state

                        # Extract agent results
                        agent_results = self._extract_agent_results(agent_type_dir)
                        agent_context['agent_results'][agent_type] = agent_results

            # Extract context requirements from shared state
            current_task = self.shared_state.get_current_task()
            if current_task:
                agent_context['context_requirements'] = {
                    'current_task': current_task,
                    'context_sources': self._identify_context_sources(),
                    'relevance_filters': self._extract_relevance_filters()
                }

            return agent_context

        except Exception as e:
            self._log_error(f"Error extracting agent context: {e}")
            return agent_context

    def _extract_agent_state(self, agent_dir: Path) -> Dict[str, Any]:
        """Extract state for a specific agent type"""
        agent_state = {
            'files_processed': [],
            'context_chunks': [],
            'processing_status': 'unknown',
            'last_activity': None
        }

        try:
            # Check for state files
            state_file = agent_dir / 'state.json'
            if state_file.exists():
                with open(state_file, 'r') as f:
                    agent_state.update(json.load(f))

            # Check for context chunks
            for chunk_file in agent_dir.glob('chunk_*.json'):
                try:
                    with open(chunk_file, 'r') as f:
                        chunk_data = json.load(f)
                        agent_state['context_chunks'].append({
                            'file': chunk_file.name,
                            'timestamp': chunk_data.get('timestamp'),
                            'size': chunk_data.get('size', 0)
                        })
                except Exception as e:
                    self._log_warning(f"Error reading chunk file {chunk_file}: {e}")

            return agent_state

        except Exception as e:
            self._log_error(f"Error extracting agent state for {agent_dir}: {e}")
            return agent_state

    def _extract_agent_results(self, agent_dir: Path) -> Dict[str, Any]:
        """Extract results from agent execution"""
        results = {
            'outputs': [],
            'metrics': {},
            'errors': []
        }

        try:
            # Check for result files
            result_file = agent_dir / 'results.json'
            if result_file.exists():
                with open(result_file, 'r') as f:
                    results.update(json.load(f))

            # Check for output files
            for output_file in agent_dir.glob('output_*.json'):
                try:
                    with open(output_file, 'r') as f:
                        output_data = json.load(f)
                        results['outputs'].append({
                            'file': output_file.name,
                            'type': output_data.get('type'),
                            'timestamp': output_data.get('timestamp')
                        })
                except Exception as e:
                    self._log_warning(f"Error reading output file {output_file}: {e}")

            return results

        except Exception as e:
            self._log_error(f"Error extracting agent results for {agent_dir}: {e}")
            return results

    def _extract_workflow_state(self) -> Dict[str, Any]:
        """Extract current workflow state"""
        workflow_state = {
            'daic_mode': 'unknown',
            'current_phase': 'unknown',
            'workflow_progress': {},
            'enforcement_state': {}
        }

        try:
            # Get DAIC mode
            daic_mode = self.shared_state.get_daic_mode()
            workflow_state['daic_mode'] = daic_mode

            # Get current task
            current_task = self.shared_state.get_current_task()
            if current_task:
                workflow_state['current_phase'] = current_task.get('phase', 'unknown')
                workflow_state['workflow_progress'] = {
                    'task_id': current_task.get('id'),
                    'task_title': current_task.get('title'),
                    'progress_percentage': current_task.get('progress', 0)
                }

            # Get enforcement state
            enforcement_state = self.shared_state.get_enforcement_state()
            workflow_state['enforcement_state'] = enforcement_state

            return workflow_state

        except Exception as e:
            self._log_error(f"Error extracting workflow state: {e}")
            return workflow_state

    def _extract_task_context(self) -> Dict[str, Any]:
        """Extract current task context"""
        task_context = {
            'current_task': None,
            'task_history': [],
            'related_files': [],
            'dependencies': []
        }

        try:
            # Get current task
            current_task = self.shared_state.get_current_task()
            if current_task:
                task_context['current_task'] = current_task

                # Extract related files
                task_context['related_files'] = self._extract_related_files(current_task)

                # Extract dependencies
                task_context['dependencies'] = current_task.get('dependencies', [])

            # Get task history
            task_context['task_history'] = self._extract_task_history()

            return task_context

        except Exception as e:
            self._log_error(f"Error extracting task context: {e}")
            return task_context

    def _extract_related_files(self, task: Dict[str, Any]) -> List[str]:
        """Extract files related to current task"""
        related_files = []

        try:
            # Get files from task description and details
            task_text = f"{task.get('title', '')} {task.get('description', '')} {task.get('details', '')}"

            # Simple file extraction (could be enhanced with more sophisticated parsing)
            import re
            file_patterns = [
                r'`([^`]+\.(py|js|ts|java|cpp|c|h|go|rs|php|rb|sh|md|json|yaml|yml|toml|xml))`',
                r'([a-zA-Z0-9_/]+\.(py|js|ts|java|cpp|c|h|go|rs|php|rb|sh|md|json|yaml|yml|toml|xml))',
            ]

            for pattern in file_patterns:
                matches = re.findall(pattern, task_text)
                for match in matches:
                    if isinstance(match, tuple):
                        file_path = match[0]
                    else:
                        file_path = match

                    if file_path and file_path not in related_files:
                        related_files.append(file_path)

            return related_files[:20]  # Limit to 20 files

        except Exception as e:
            self._log_error(f"Error extracting related files: {e}")
            return []

    def _extract_task_history(self) -> List[Dict[str, Any]]:
        """Extract recent task history"""
        task_history = []

        try:
            # This would typically come from a task history file
            # For now, return empty list as this is not implemented in current system
            return task_history

        except Exception as e:
            self._log_error(f"Error extracting task history: {e}")
            return []

    def _identify_context_sources(self) -> List[str]:
        """Identify current context sources"""
        context_sources = []

        try:
            # Check for common context sources
            if (self.context_dir / 'current_task.json').exists():
                context_sources.append('current_task')

            if (self.context_dir / 'daic-mode.json').exists():
                context_sources.append('daic_mode')

            # Check for agent context sources
            if self.agent_context_dir.exists():
                for agent_type_dir in self.agent_context_dir.iterdir():
                    if agent_type_dir.is_dir():
                        context_sources.append(f'agent_{agent_type_dir.name}')

            return context_sources

        except Exception as e:
            self._log_error(f"Error identifying context sources: {e}")
            return []

    def _extract_relevance_filters(self) -> Dict[str, Any]:
        """Extract current relevance filters"""
        relevance_filters = {
            'current_task_relevance': True,
            'agent_context_relevance': True,
            'workflow_state_relevance': True
        }

        try:
            # This would typically come from context optimization settings
            # For now, return default values
            return relevance_filters

        except Exception as e:
            self._log_error(f"Error extracting relevance filters: {e}")
            return relevance_filters

    def _save_agent_context_summary(self, agent_context: Dict[str, Any]) -> None:
        """Save agent context summary for post-compaction recovery"""
        try:
            summary_file = self.compaction_dir / 'agent_context_summary.json'

            # Create summary with essential information
            summary = {
                'timestamp': self._get_timestamp(),
                'active_agents': agent_context.get('active_agents', []),
                'agent_states': {
                    agent_type: {
                        'files_processed': state.get('files_processed', []),
                        'processing_status': state.get('processing_status', 'unknown'),
                        'last_activity': state.get('last_activity')
                    }
                    for agent_type, state in agent_context.get('agent_states', {}).items()
                },
                'context_requirements': agent_context.get('context_requirements', {}),
                'agent_dependencies': agent_context.get('agent_dependencies', {})
            }

            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)

            self._log_info(f"Saved agent context summary to {summary_file}")

        except Exception as e:
            self._log_error(f"Error saving agent context summary: {e}")

    def _save_workflow_state_summary(self, workflow_state: Dict[str, Any]) -> None:
        """Save workflow state summary"""
        try:
            summary_file = self.compaction_dir / 'workflow_state_summary.json'

            with open(summary_file, 'w') as f:
                json.dump(workflow_state, f, indent=2)

            self._log_info(f"Saved workflow state summary to {summary_file}")

        except Exception as e:
            self._log_error(f"Error saving workflow state summary: {e}")

    def _save_task_context_summary(self, task_context: Dict[str, Any]) -> None:
        """Save task context summary"""
        try:
            summary_file = self.compaction_dir / 'task_context_summary.json'

            with open(summary_file, 'w') as f:
                json.dump(task_context, f, indent=2)

            self._log_info(f"Saved task context summary to {summary_file}")

        except Exception as e:
            self._log_error(f"Error saving task context summary: {e}")

    def _create_context_manifest(self, agent_context: Dict[str, Any],
                                workflow_state: Dict[str, Any],
                                task_context: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive context manifest for post-compaction recovery"""
        manifest = {
            'timestamp': self._get_timestamp(),
            'compaction_id': self._generate_compaction_id(),
            'agent_context': agent_context,
            'workflow_state': workflow_state,
            'task_context': task_context,
            'recovery_instructions': self._generate_recovery_instructions(
                agent_context, workflow_state, task_context
            ),
            'priority_context': self._identify_priority_context(
                agent_context, workflow_state, task_context
            )
        }

        return manifest

    def _save_context_manifest(self, manifest: Dict[str, Any]) -> None:
        """Save context manifest"""
        try:
            manifest_file = self.compaction_dir / 'context_manifest.json'

            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)

            self._log_info(f"Saved context manifest to {manifest_file}")

        except Exception as e:
            self._log_error(f"Error saving context manifest: {e}")

    def _update_compaction_metadata(self, manifest: Dict[str, Any]) -> None:
        """Update compaction metadata in shared state"""
        try:
            metadata = {
                'last_compaction': self._get_timestamp(),
                'compaction_id': manifest.get('compaction_id'),
                'preserved_agents': manifest.get('agent_context', {}).get('active_agents', []),
                'workflow_phase': manifest.get('workflow_state', {}).get('current_phase'),
                'context_sources': len(manifest.get('agent_context', {}).get('context_requirements', {}).get('context_sources', []))
            }

            self.shared_state.update_compaction_metadata(metadata)

        except Exception as e:
            self._log_error(f"Error updating compaction metadata: {e}")

    def _generate_recovery_instructions(self, agent_context: Dict[str, Any],
                                      workflow_state: Dict[str, Any],
                                      task_context: Dict[str, Any]) -> List[str]:
        """Generate instructions for post-compaction recovery"""
        instructions = []

        try:
            # Agent recovery instructions
            active_agents = agent_context.get('active_agents', [])
            if active_agents:
                instructions.append(f"Restore agent contexts for: {', '.join(active_agents)}")

            # Workflow recovery instructions
            current_phase = workflow_state.get('current_phase')
            if current_phase:
                instructions.append(f"Resume workflow in {current_phase} phase")

            # Task recovery instructions
            current_task = task_context.get('current_task')
            if current_task:
                task_title = current_task.get('title', 'Unknown Task')
                instructions.append(f"Continue with task: {task_title}")

            # Context recovery instructions
            related_files = task_context.get('related_files', [])
            if related_files:
                instructions.append(f"Focus on related files: {', '.join(related_files[:5])}")

            return instructions

        except Exception as e:
            self._log_error(f"Error generating recovery instructions: {e}")
            return ["Recover from context compaction"]

    def _identify_priority_context(self, agent_context: Dict[str, Any],
                                 workflow_state: Dict[str, Any],
                                 task_context: Dict[str, Any]) -> Dict[str, Any]:
        """Identify priority context that should be loaded first after compaction"""
        priority_context = {
            'critical_files': [],
            'active_agents': [],
            'current_task': None,
            'workflow_state': None
        }

        try:
            # Priority files
            related_files = task_context.get('related_files', [])
            priority_context['critical_files'] = related_files[:10]  # Top 10 files

            # Active agents
            priority_context['active_agents'] = agent_context.get('active_agents', [])

            # Current task
            priority_context['current_task'] = task_context.get('current_task')

            # Workflow state
            priority_context['workflow_state'] = {
                'daic_mode': workflow_state.get('daic_mode'),
                'current_phase': workflow_state.get('current_phase')
            }

            return priority_context

        except Exception as e:
            self._log_error(f"Error identifying priority context: {e}")
            return priority_context

    def _is_safe_operation(self, tool_name: str, parameters: Dict[str, Any]) -> bool:
        """Check if operation is safe to auto-approve"""
        try:
            # Check if tool is in safe operations list
            if tool_name not in self.safe_operations:
                return False

            # Additional safety checks based on tool type
            if tool_name == "run_terminal_cmd":
                command = parameters.get('command', '')
                return self._is_safe_command(command)
            elif tool_name == "edit_file":
                file_path = parameters.get('file_path', '')
                return self._is_safe_file_path(file_path)
            elif tool_name == "search_replace":
                file_path = parameters.get('file_path', '')
                return self._is_safe_file_path(file_path)

            return True

        except Exception as e:
            self._log_error(f"Error checking safe operation: {e}")
            return False

    def _is_unsafe_operation(self, tool_name: str, parameters: Dict[str, Any]) -> bool:
        """Check if operation is clearly unsafe"""
        try:
            # Check if tool is in unsafe operations list
            if tool_name in self.unsafe_operations:
                return True

            # Additional safety checks
            if tool_name == "run_terminal_cmd":
                command = parameters.get('command', '')
                return self._is_unsafe_command(command)
            elif tool_name == "delete_file":
                file_path = parameters.get('target_file', '')
                return self._is_critical_file(file_path)

            return False

        except Exception as e:
            self._log_error(f"Error checking unsafe operation: {e}")
            return False

    def _is_safe_command(self, command: str) -> bool:
        """Check if command is safe to execute"""
        safe_patterns = [
            r'^ls\s+', r'^cat\s+', r'^grep\s+', r'^find\s+',
            r'^git\s+(status|log|diff|show)', r'^npm\s+(list|outdated)',
            r'^pip\s+(list|show)', r'^python\s+-m\s+', r'^node\s+--version'
        ]

        import re
        for pattern in safe_patterns:
            if re.match(pattern, command):
                return True

        return False

    def _is_unsafe_command(self, command: str) -> bool:
        """Check if command is unsafe"""
        unsafe_patterns = [
            r'rm\s+-rf', r'dd\s+if=', r'mkfs', r'fdisk',
            r'shutdown', r'reboot', r'halt', r'poweroff',
            r'chmod\s+777', r'chown\s+-R'
        ]

        import re
        for pattern in unsafe_patterns:
            if re.search(pattern, command):
                return True

        return False

    def _is_safe_file_path(self, file_path: str) -> bool:
        """Check if file path is safe"""
        if not file_path:
            return False

        # Check for path traversal
        if '..' in file_path or file_path.startswith('/'):
            return False

        # Check if within project directory
        try:
            project_root = os.getcwd()
            full_path = os.path.abspath(os.path.join(project_root, file_path))
            return full_path.startswith(project_root)
        except:
            return False

    def _is_critical_file(self, file_path: str) -> bool:
        """Check if file is critical and shouldn't be deleted"""
        critical_files = [
            'package.json', 'pyproject.toml', 'requirements.txt',
            'Dockerfile', 'docker-compose.yml', '.gitignore',
            'README.md', 'LICENSE', 'setup.py', 'Cargo.toml',
            'go.mod', 'composer.json', 'pom.xml', 'build.gradle'
        ]

        filename = os.path.basename(file_path)
        return filename in critical_files

    def _provide_context_aware_response(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Provide context-aware response for ambiguous operations"""
        try:
            current_task = self.shared_state.get_current_task()
            workflow_phase = current_task.get('phase', 'unknown') if current_task else 'unknown'

            # Context-aware decision making
            if workflow_phase == 'discussion':
                return {
                    'approved': False,
                    'reason': 'Tool execution not appropriate during discussion phase',
                    'suggestion': 'Complete discussion phase before tool execution'
                }
            elif workflow_phase == 'implementation':
                # More permissive during implementation
                return {
                    'approved': True,
                    'reason': 'Implementation phase - tool execution allowed',
                    'auto_approved': True
                }
            else:
                return {
                    'approved': False,
                    'reason': 'Manual review required',
                    'suggestion': 'Please review this operation manually'
                }

        except Exception as e:
            self._log_error(f"Error providing context-aware response: {e}")
            return {
                'approved': False,
                'reason': 'Error in context analysis',
                'suggestion': 'Manual review required'
            }

    def _get_current_context(self) -> Dict[str, Any]:
        """Get current context for suggestion generation"""
        try:
            context = {
                'current_task': self.shared_state.get_current_task(),
                'daic_mode': self.shared_state.get_daic_mode(),
                'recent_files': self._get_recent_files(),
                'workflow_phase': 'unknown'
            }

            if context['current_task']:
                context['workflow_phase'] = context['current_task'].get('phase', 'unknown')

            return context

        except Exception as e:
            self._log_error(f"Error getting current context: {e}")
            return {}

    def _get_recent_files(self) -> List[str]:
        """Get list of recently accessed files"""
        try:
            # This would typically come from file access logs
            # For now, return empty list as this is not implemented
            return []

        except Exception as e:
            self._log_error(f"Error getting recent files: {e}")
            return []

    def _generate_context_suggestions(self, context: Dict[str, Any]) -> List[str]:
        """Generate context-aware suggestions"""
        suggestions = []

        try:
            current_task = context.get('current_task')
            workflow_phase = context.get('workflow_phase', 'unknown')

            if workflow_phase == 'discussion':
                suggestions.extend([
                    "Consider breaking down the task into smaller subtasks",
                    "Review the requirements and acceptance criteria",
                    "Identify potential risks and mitigation strategies",
                    "Plan the implementation approach and architecture"
                ])
            elif workflow_phase == 'implementation':
                suggestions.extend([
                    "Start with the core functionality implementation",
                    "Write tests for the new features",
                    "Update documentation as you implement",
                    "Consider code review and refactoring opportunities"
                ])
            else:
                suggestions.extend([
                    "Review the current task and requirements",
                    "Check if all dependencies are met",
                    "Consider the next steps in the workflow",
                    "Look for opportunities to optimize the code"
                ])

            # Add task-specific suggestions
            if current_task:
                task_title = current_task.get('title', '')
                if 'test' in task_title.lower():
                    suggestions.append("Consider writing comprehensive test cases")
                elif 'refactor' in task_title.lower():
                    suggestions.append("Ensure all tests pass before refactoring")
                elif 'document' in task_title.lower():
                    suggestions.append("Include code examples in the documentation")

            return suggestions[:5]  # Limit to 5 suggestions

        except Exception as e:
            self._log_error(f"Error generating context suggestions: {e}")
            return []

    def _generate_context_optimization_suggestions(self, context_usage: Dict[str, Any]) -> List[str]:
        """Generate context optimization suggestions"""
        suggestions = []

        try:
            token_usage = context_usage.get('tokens_used', 0)
            token_limit = context_usage.get('token_limit', 160000)
            usage_percentage = (token_usage / token_limit) * 100 if token_limit > 0 else 0

            if usage_percentage > 90:
                suggestions.extend([
                    "Consider using context compaction to reduce token usage",
                    "Focus on the most relevant files and code sections",
                    "Use more specific search queries to find relevant code",
                    "Consider breaking the task into smaller parts"
                ])
            elif usage_percentage > 75:
                suggestions.extend([
                    "Monitor context usage to avoid hitting limits",
                    "Consider summarizing less critical information",
                    "Focus on the current task and related files"
                ])

            return suggestions

        except Exception as e:
            self._log_error(f"Error generating context optimization suggestions: {e}")
            return []

    def _suggest_alternative_tools(self, tool_name: str, reason: str) -> List[Dict[str, str]]:
        """Suggest alternative tools when a tool is blocked"""
        alternatives = []

        try:
            if tool_name == "run_terminal_cmd":
                alternatives.extend([
                    {"tool": "grep", "description": "Search for text patterns in files"},
                    {"tool": "codebase_search", "description": "Search for code patterns"},
                    {"tool": "read_file", "description": "Read specific files"}
                ])
            elif tool_name == "delete_file":
                alternatives.extend([
                    {"tool": "search_replace", "description": "Remove content from files"},
                    {"tool": "edit_file", "description": "Modify file content"},
                    {"tool": "grep", "description": "Find files to modify"}
                ])
            elif tool_name == "write":
                alternatives.extend([
                    {"tool": "edit_file", "description": "Edit existing files"},
                    {"tool": "search_replace", "description": "Replace content in files"}
                ])

            return alternatives

        except Exception as e:
            self._log_error(f"Error suggesting alternative tools: {e}")
            return []

    def _generate_compaction_id(self) -> str:
        """Generate unique compaction ID"""
        import uuid
        return str(uuid.uuid4())[:8]

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        return datetime.now().isoformat()

    def _log_info(self, message: str) -> None:
        """Log info message"""
        print(f"INFO: {message}", file=sys.stderr)

    def _log_warning(self, message: str) -> None:
        """Log warning message"""
        print(f"WARNING: {message}", file=sys.stderr)

    def _log_error(self, message: str) -> None:
        """Log error message"""
        print(f"ERROR: {message}", file=sys.stderr)


def main():
    """Main entry point for Context Manager hook"""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())

        # Determine event type from hook event name
        hook_event_name = input_data.get('hookEventName', '')

        if hook_event_name == 'PreCompact':
            event_type = 'pre_compact'
            data = input_data
        elif hook_event_name == 'Notification':
            event_type = 'notification'
            data = {
                'notification_type': input_data.get('notificationType', ''),
                'data': input_data.get('data', {})
            }
        else:
            # Fallback to direct event_type
            event_type = input_data.get('event_type', '')
            data = input_data.get('data', {})

        if not event_type:
            print(json.dumps({'error': 'No event_type provided'}), file=sys.stderr)
            sys.exit(1)

        # Initialize context manager
        context_manager = ContextManager()

        # Handle context event
        response = context_manager.handle_context_event(event_type, data)

        if response:
            print(json.dumps(response))
            sys.exit(0)
        else:
            # No response needed
            sys.exit(0)

    except json.JSONDecodeError as e:
        print(json.dumps({'error': f'Invalid JSON input: {e}'}), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({'error': f'Unexpected error: {e}'}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
