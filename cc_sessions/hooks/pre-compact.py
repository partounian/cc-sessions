#!/usr/bin/env python3
"""
PreCompact Hook for cc-sessions

Prepares and preserves critical context before Claude Code initiates a compact
operation. This hook runs before context compaction to ensure essential agent
context and workflow state is preserved.

This hook adds unique value by:
- Preserving critical agent context that would be lost in compaction
- Creating context summaries for agent continuity
- Maintaining workflow state across context resets
- Optimizing context for post-compaction agent execution
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add the cc_sessions directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hooks.multi_repo_config import get_multi_repo_config
from hooks.shared_state import SharedState


class ContextPreservationManager:
    """Manages context preservation before compaction"""

    def __init__(self):
        self.shared_state = SharedState()
        self.context_dir = Path('.claude/state')
        self.agent_context_dir = self.context_dir / 'agent_context'
        self.compaction_dir = self.context_dir / 'compaction'

        # Multi-repo awareness
        self.multi_repo_config = get_multi_repo_config(self.shared_state.workspace_root)

        # Ensure directories exist
        self.agent_context_dir.mkdir(parents=True, exist_ok=True)
        self.compaction_dir.mkdir(parents=True, exist_ok=True)

    def preserve_critical_context(self) -> bool:
        """Preserve critical context before compaction"""
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

            return True

        except Exception as e:
            self._log_error(f"Error preserving context: {e}")
            return False

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

    def _generate_compaction_id(self) -> str:
        """Generate unique compaction ID"""
        import uuid
        return str(uuid.uuid4())[:8]

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
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
    """Main entry point for PreCompact hook"""
    try:
        # Read input from stdin (if any)
        try:
            input_data = json.loads(sys.stdin.read())
        except:
            input_data = {}

        # Initialize context preservation manager
        preservation_manager = ContextPreservationManager()

        # Preserve critical context
        success = preservation_manager.preserve_critical_context()

        if success:
            result = {
                'status': 'success',
                'message': 'Context preserved successfully',
                'timestamp': preservation_manager._get_timestamp()
            }
            print(json.dumps(result))
            sys.exit(0)
        else:
            result = {
                'status': 'error',
                'message': 'Failed to preserve context',
                'timestamp': preservation_manager._get_timestamp()
            }
            print(json.dumps(result), file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        result = {
            'status': 'error',
            'message': f'Unexpected error: {e}',
            'timestamp': preservation_manager._get_timestamp() if 'preservation_manager' in locals() else 'unknown'
        }
        print(json.dumps(result), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
