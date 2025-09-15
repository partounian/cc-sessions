#!/usr/bin/env python3
"""
Notification Handler Hook for cc-sessions

Handles Claude Code notifications such as permission requests and idle input
to provide automated responses and context-aware assistance.

This hook adds unique value by:
- Automating safe permission requests
- Providing context-aware suggestions during idle periods
- Enhancing user experience with intelligent responses
- Reducing manual intervention for routine operations
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add the cc_sessions directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hooks.shared_state import SharedState


class NotificationHandler:
    """Handles Claude Code notifications with intelligent responses"""

    def __init__(self):
        self.shared_state = SharedState()
        self.safe_operations = [
            'read_file', 'list_dir', 'grep', 'codebase_search',
            'run_terminal_cmd', 'edit_file', 'search_replace'
        ]
        self.unsafe_operations = [
            'delete_file', 'run_terminal_cmd', 'write'
        ]
        self.context_suggestions = []

    def handle_notification(self, notification_type: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle different types of notifications"""
        try:
            if notification_type == "permission_request":
                return self._handle_permission_request(data)
            elif notification_type == "idle_input":
                return self._handle_idle_input(data)
            elif notification_type == "context_warning":
                return self._handle_context_warning(data)
            elif notification_type == "tool_blocked":
                return self._handle_tool_blocked(data)
            else:
                return self._handle_unknown_notification(notification_type, data)

        except Exception as e:
            self._log_error(f"Error handling notification {notification_type}: {e}")
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

    def _handle_unknown_notification(self, notification_type: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle unknown notification types"""
        self._log_warning(f"Unknown notification type: {notification_type}")
        return {
            'notification_type': notification_type,
            'handled': False,
            'timestamp': self._get_timestamp()
        }

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

    def _log_info(self, message: str) -> None:
        """Log info message"""
        print(f"INFO: {message}", file=sys.stderr)

    def _log_warning(self, message: str) -> None:
        """Log warning message"""
        print(f"WARNING: {message}", file=sys.stderr)

    def _log_error(self, message: str) -> None:
        """Log error message"""
        print(f"ERROR: {message}", file=sys.stderr)

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()

def main():
    """Main entry point for Notification Handler hook"""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())

        notification_type = input_data.get('notification_type')
        data = input_data.get('data', {})

        if not notification_type:
            print(json.dumps({'error': 'No notification_type provided'}), file=sys.stderr)
            sys.exit(1)

        # Initialize notification handler
        handler = NotificationHandler()

        # Handle notification
        response = handler.handle_notification(notification_type, data)

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
