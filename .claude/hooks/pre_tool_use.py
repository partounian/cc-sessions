"""
PreToolUse Hook for cc-sessions

Validates and modifies tool parameters before execution to ensure safety
and optimize for context efficiency. This hook runs after Claude generates
tool parameters but before executing the tool call.

This hook adds unique value by:
- Validating tool safety before execution
- Optimizing tool parameters for context efficiency
- Preventing unsafe operations
- Enhancing tool execution with agent analysis when needed
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add the cc_sessions directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hooks.shared_state import SharedState


class ToolParameterValidator:
    """Validates and modifies tool parameters for safety and efficiency"""

    def __init__(self):
        self.shared_state = SharedState()
        self.unsafe_commands = [
            'rm -rf /', 'rm -rf /*', 'rm -rf /home', 'rm -rf /etc',
            'dd if=/dev/zero', 'mkfs', 'fdisk', 'format',
            'shutdown', 'reboot', 'halt', 'poweroff',
            'chmod 777', 'chown -R', 'chmod -R 777'
        ]
        self.unsafe_patterns = [
            r'rm\s+-rf\s+/[^/]',  # rm -rf with root path
            r'dd\s+if=/dev/',     # dd with device files
            r'mkfs\s+',           # filesystem creation
            r'fdisk\s+',          # disk partitioning
            r'format\s+',         # disk formatting
        ]

    def validate_tool_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> bool:
        """Validate tool parameters for safety and correctness"""
        try:
            if tool_name == "run_terminal_cmd":
                return self._validate_terminal_command(parameters)
            elif tool_name == "edit_file":
                return self._validate_file_edit(parameters)
            elif tool_name == "search_replace":
                return self._validate_search_replace(parameters)
            elif tool_name == "delete_file":
                return self._validate_file_deletion(parameters)
            elif tool_name == "write":
                return self._validate_file_write(parameters)

            # For other tools, allow by default but log
            self._log_tool_usage(tool_name, parameters)
            return True

        except Exception as e:
            self._log_error(f"Error validating tool {tool_name}: {e}")
            return False

    def _validate_terminal_command(self, parameters: Dict[str, Any]) -> bool:
        """Validate terminal command parameters for safety"""
        command = parameters.get('command', '')

        # Check for unsafe commands
        for unsafe_cmd in self.unsafe_commands:
            if unsafe_cmd in command:
                self._log_warning(f"Unsafe command blocked: {command}")
                return False

        # Check for unsafe patterns
        for pattern in self.unsafe_patterns:
            if re.search(pattern, command):
                self._log_warning(f"Unsafe command pattern blocked: {command}")
                return False

        # Check for commands that might affect system files
        if self._affects_system_files(command):
            self._log_warning(f"System file modification blocked: {command}")
            return False

        # Log command for audit
        self._log_command_execution(command)
        return True

    def _validate_file_edit(self, parameters: Dict[str, Any]) -> bool:
        """Validate file edit parameters"""
        file_path = parameters.get('file_path', '')

        # Check if file path is safe
        if not self._is_safe_file_path(file_path):
            self._log_warning(f"Unsafe file path blocked: {file_path}")
            return False

        # Check if file is within project directory
        if not self._is_within_project_directory(file_path):
            self._log_warning(f"File outside project directory blocked: {file_path}")
            return False

        return True

    def _validate_search_replace(self, parameters: Dict[str, Any]) -> bool:
        """Validate search and replace parameters"""
        file_path = parameters.get('file_path', '')

        # Validate file path
        if not self._is_safe_file_path(file_path) or not self._is_within_project_directory(file_path):
            return False

        # Check for potentially dangerous replacements
        old_string = parameters.get('old_string', '')
        new_string = parameters.get('new_string', '')

        if self._is_dangerous_replacement(old_string, new_string):
            self._log_warning(f"Potentially dangerous replacement blocked")
            return False

        return True

    def _validate_file_deletion(self, parameters: Dict[str, Any]) -> bool:
        """Validate file deletion parameters"""
        target_file = parameters.get('target_file', '')

        # Check if file path is safe
        if not self._is_safe_file_path(target_file):
            return False

        # Check if file is within project directory
        if not self._is_within_project_directory(target_file):
            return False

        # Check if file is critical (e.g., configuration files)
        if self._is_critical_file(target_file):
            self._log_warning(f"Critical file deletion blocked: {target_file}")
            return False

        return True

    def _validate_file_write(self, parameters: Dict[str, Any]) -> bool:
        """Validate file write parameters"""
        file_path = parameters.get('file_path', '')

        # Check if file path is safe
        if not self._is_safe_file_path(file_path):
            return False

        # Check if file is within project directory
        if not self._is_within_project_directory(file_path):
            return False

        return True

    def _affects_system_files(self, command: str) -> bool:
        """Check if command affects system files"""
        system_paths = ['/etc/', '/usr/', '/bin/', '/sbin/', '/lib/', '/var/']
        for path in system_paths:
            if path in command:
                return True
        return False

    def _is_safe_file_path(self, file_path: str) -> bool:
        """Check if file path is safe (no path traversal)"""
        if not file_path:
            return False

        # Check for path traversal attempts
        if '..' in file_path or file_path.startswith('/'):
            return False

        # Check for absolute paths outside project
        if os.path.isabs(file_path):
            return False

        return True

    def _is_within_project_directory(self, file_path: str) -> bool:
        """Check if file is within project directory or workspace"""
        try:
            # Get project and workspace roots
            project_root = self.shared_state.project_root
            workspace_root = self.shared_state.workspace_root

            # Resolve relative path
            full_path = os.path.abspath(os.path.join(os.getcwd(), file_path))

            # Allow files within project root or workspace root
            return (full_path.startswith(str(project_root)) or
                    full_path.startswith(str(workspace_root)))
        except Exception:
            return False

    def _is_dangerous_replacement(self, old_string: str, new_string: str) -> bool:
        """Check if replacement is potentially dangerous"""
        # Check for removal of important patterns
        dangerous_patterns = [
            r'import\s+',  # Removing imports
            r'def\s+',     # Removing function definitions
            r'class\s+',   # Removing class definitions
            r'if\s+__name__',  # Removing main guard
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, old_string) and not re.search(pattern, new_string):
                return True

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

    def optimize_tool_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize tool parameters for context efficiency"""
        try:
            if tool_name == "edit_file":
                return self._optimize_edit_parameters(parameters)
            elif tool_name == "search_replace":
                return self._optimize_search_replace_parameters(parameters)
            elif tool_name == "run_terminal_cmd":
                return self._optimize_command_parameters(parameters)

            return parameters

        except Exception as e:
            self._log_error(f"Error optimizing tool {tool_name}: {e}")
            return parameters

    def _optimize_edit_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize edit file parameters for context efficiency"""
        # Ensure old_string and new_string are not excessively long
        old_string = parameters.get('old_string', '')
        new_string = parameters.get('new_string', '')

        # Truncate very long strings to prevent context bloat
        max_length = 10000  # 10k characters max per string

        if len(old_string) > max_length:
            parameters['old_string'] = old_string[:max_length] + "\n... [truncated]"

        if len(new_string) > max_length:
            parameters['new_string'] = new_string[:max_length] + "\n... [truncated]"

        return parameters

    def _optimize_search_replace_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize search and replace parameters"""
        # Similar optimization as edit parameters
        return self._optimize_edit_parameters(parameters)

    def _optimize_command_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize command parameters"""
        command = parameters.get('command', '')

        # Add context about current task if available
        current_task = self.shared_state.get_current_task()
        if current_task and 'explanation' not in parameters:
            parameters['explanation'] = f"Executing command for task: {current_task.get('title', 'Unknown')}"

        return parameters

    def _log_tool_usage(self, tool_name: str, parameters: Dict[str, Any]) -> None:
        """Log tool usage for audit"""
        try:
            log_entry = {
                'timestamp': self._get_timestamp(),
                'tool_name': tool_name,
                'parameters': self._sanitize_parameters(parameters)
            }

            # Log to shared state
            self.shared_state.log_tool_usage(log_entry)

        except Exception as e:
            self._log_error(f"Error logging tool usage: {e}")

    def _log_command_execution(self, command: str) -> None:
        """Log command execution for audit"""
        try:
            log_entry = {
                'timestamp': self._get_timestamp(),
                'command': command,
                'type': 'command_execution'
            }

            self.shared_state.log_command_execution(log_entry)

        except Exception as e:
            self._log_error(f"Error logging command execution: {e}")

    def _log_warning(self, message: str) -> None:
        """Log warning message"""
        print(f"WARNING: {message}", file=sys.stderr)
        self.shared_state.log_warning(message)

    def _log_error(self, message: str) -> None:
        """Log error message"""
        print(f"ERROR: {message}", file=sys.stderr)
        self.shared_state.log_error(message)

    def _sanitize_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize parameters for logging (remove sensitive data)"""
        sanitized = {}
        for key, value in parameters.items():
            if key in ['password', 'token', 'key', 'secret']:
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, str) and len(value) > 1000:
                sanitized[key] = value[:1000] + '... [truncated]'
            else:
                sanitized[key] = value
        return sanitized

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()

def main():
    """Main entry point for PreToolUse hook"""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())

        tool_name = input_data.get('tool_name')
        parameters = input_data.get('parameters', {})

        if not tool_name:
            print(json.dumps({'error': 'No tool_name provided'}), file=sys.stderr)
            sys.exit(1)

        validator = ToolParameterValidator()

        # Validate tool parameters
        is_valid = validator.validate_tool_parameters(tool_name, parameters)

        if not is_valid:
            # Block the tool execution
            print(json.dumps({
                'error': 'Tool execution blocked due to safety concerns',
                'tool_name': tool_name,
                'reason': 'Unsafe parameters detected'
            }), file=sys.stderr)
            sys.exit(2)  # Exit code 2 = block execution

        # Optimize parameters for context efficiency
        optimized_parameters = validator.optimize_tool_parameters(tool_name, parameters)

        # Return optimized parameters
        result = {
            'tool_name': tool_name,
            'parameters': optimized_parameters,
            'validated': True,
            'optimized': optimized_parameters != parameters
        }

        print(json.dumps(result))
        sys.exit(0)

    except json.JSONDecodeError as e:
        print(json.dumps({'error': f'Invalid JSON input: {e}'}), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({'error': f'Unexpected error: {e}'}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
