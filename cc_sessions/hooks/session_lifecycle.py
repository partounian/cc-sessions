#!/usr/bin/env python3
"""
Unified Session Lifecycle Hook for cc-sessions

Combines session stop analytics and session end cleanup into a single, efficient hook
that handles all session lifecycle management.

This hook replaces:
- session-stop.py (session analytics and cleanup)
- session-end.py (complete session closure and metrics)

Key features:
- Comprehensive session analytics and metrics collection
- Session cleanup and state persistence
- Project metrics updates
- Agent context cleanup
- Session archiving
- Performance analysis and recommendations
"""

import json
import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add the cc_sessions directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hooks.shared_state import SharedState


class SessionLifecycleManager:
    """Manages complete session lifecycle including analytics, cleanup, and archiving"""

    def __init__(self):
        self.shared_state = SharedState()
        self.state_dir = Path('.claude/state')
        self.temp_dir = Path('.claude/temp')
        self.analytics_dir = Path('.claude/state/analytics')
        self.project_metrics_file = Path('.claude/state/project_metrics.json')

        # Ensure directories exist
        self.analytics_dir.mkdir(parents=True, exist_ok=True)
        self.session_metrics = {}

    def handle_session_lifecycle(self, is_session_end: bool = False) -> bool:
        """Handle session lifecycle events (stop or end)"""
        try:
            # Clear lingering subagent state at session stop/end
            try:
                self.shared_state.clear_subagent_state()
            except Exception as exc:
                self._log_warning(f"clear_subagent_state failed: {exc}")

            # Collect session metrics
            self._collect_session_metrics()

            # Generate session report
            self._generate_session_report()

            # Save metrics and report
            self._save_session_metrics()

            # Clean up agent contexts
            self._cleanup_agent_contexts()

            # Trigger garbage collection for memory management
            self._trigger_memory_cleanup()

            if is_session_end:
                # Additional end-of-session processing
                self._persist_final_state()
                self._update_project_metrics()
                self._cleanup_temp_files()
                self._archive_session_data()
                self._final_cleanup()

            return True

        except Exception as e:
            self._log_error(f"Error handling session lifecycle: {e}")
            return False

    def _collect_session_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive session metrics"""
        try:
            metrics = {
                'session_info': self._collect_session_info(),
                'tool_usage': self._collect_tool_usage_metrics(),
                'agent_performance': self._collect_agent_performance_metrics(),
                'context_usage': self._collect_context_usage_metrics(),
                'workflow_metrics': self._collect_workflow_metrics(),
                'error_metrics': self._collect_error_metrics(),
                'performance_metrics': self._collect_performance_metrics()
            }

            self.session_metrics = metrics
            return metrics

        except Exception as e:
            self._log_error(f"Error collecting session metrics: {e}")
            return {}

    def _collect_session_info(self) -> Dict[str, Any]:
        """Collect basic session information"""
        try:
            session_info = {
                'session_id': self._generate_session_id(),
                'start_time': self._get_session_start_time(),
                'end_time': self._get_timestamp(),
                'duration_seconds': self._calculate_session_duration(),
                'daic_mode': self.shared_state.get_daic_mode(),
                'current_task': self.shared_state.get_current_task()
            }

            return session_info

        except Exception as e:
            self._log_error(f"Error collecting session info: {e}")
            return {}

    def _collect_tool_usage_metrics(self) -> Dict[str, Any]:
        """Collect tool usage metrics"""
        try:
            tool_metrics = {
                'total_tools_used': 0,
                'tools_by_type': {},
                'successful_tools': 0,
                'failed_tools': 0,
                'blocked_tools': 0,
                'tool_execution_times': {},
                'most_used_tools': []
            }

            # Get tool usage from shared state
            tool_usage_log = self.shared_state.get_tool_usage_log()

            for tool_entry in tool_usage_log:
                tool_name = tool_entry.get('tool_name', 'unknown')
                tool_metrics['total_tools_used'] += 1

                # Count by type
                tool_metrics['tools_by_type'][tool_name] = tool_metrics['tools_by_type'].get(tool_name, 0) + 1

                # Count success/failure
                if tool_entry.get('success', True):
                    tool_metrics['successful_tools'] += 1
                else:
                    tool_metrics['failed_tools'] += 1

                # Track execution times
                execution_time = tool_entry.get('execution_time', 0)
                if execution_time > 0:
                    if tool_name not in tool_metrics['tool_execution_times']:
                        tool_metrics['tool_execution_times'][tool_name] = []
                    tool_metrics['tool_execution_times'][tool_name].append(execution_time)

            # Calculate most used tools
            tool_metrics['most_used_tools'] = sorted(
                tool_metrics['tools_by_type'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]

            return tool_metrics

        except Exception as e:
            self._log_error(f"Error collecting tool usage metrics: {e}")
            return {}

    def _collect_agent_performance_metrics(self) -> Dict[str, Any]:
        """Collect agent performance metrics"""
        try:
            agent_metrics = {
                'active_agents': [],
                'agent_execution_times': {},
                'agent_success_rates': {},
                'agent_context_usage': {},
                'agent_output_quality': {}
            }

            # Check for agent context directories
            agent_context_dir = Path('.claude/state/agent_context')
            if agent_context_dir.exists():
                for agent_type_dir in agent_context_dir.iterdir():
                    if agent_type_dir.is_dir():
                        agent_type = agent_type_dir.name
                        agent_metrics['active_agents'].append(agent_type)

                        # Collect agent-specific metrics
                        agent_data = self._collect_agent_data(agent_type_dir)
                        agent_metrics['agent_execution_times'][agent_type] = agent_data.get('execution_times', [])
                        agent_metrics['agent_success_rates'][agent_type] = agent_data.get('success_rate', 0)
                        agent_metrics['agent_context_usage'][agent_type] = agent_data.get('context_usage', 0)
                        agent_metrics['agent_output_quality'][agent_type] = agent_data.get('output_quality', 0)

            return agent_metrics

        except Exception as e:
            self._log_error(f"Error collecting agent performance metrics: {e}")
            return {}

    def _collect_agent_data(self, agent_dir: Path) -> Dict[str, Any]:
        """Collect data for a specific agent"""
        try:
            agent_data = {
                'execution_times': [],
                'success_rate': 0,
                'context_usage': 0,
                'output_quality': 0
            }

            # Check for metrics file
            metrics_file = agent_dir / 'metrics.json'
            if metrics_file.exists():
                with open(metrics_file, 'r') as f:
                    agent_data.update(json.load(f))

            # Check for execution logs
            for log_file in agent_dir.glob('execution_*.json'):
                try:
                    with open(log_file, 'r') as f:
                        log_data = json.load(f)
                        if 'execution_time' in log_data:
                            agent_data['execution_times'].append(log_data['execution_time'])
                except Exception as e:
                    self._log_warning(f"Error reading agent log {log_file}: {e}")

            return agent_data

        except Exception as e:
            self._log_error(f"Error collecting agent data for {agent_dir}: {e}")
            return {}

    def _collect_context_usage_metrics(self) -> Dict[str, Any]:
        """Collect context usage metrics"""
        try:
            context_metrics = {
                'total_tokens_used': 0,
                'context_warnings': 0,
                'compaction_events': 0,
                'context_efficiency': 0,
                'peak_context_usage': 0,
                'context_sources': []
            }

            # Get context usage from shared state
            context_usage_log = self.shared_state.get_context_usage_log()

            for usage_entry in context_usage_log:
                context_metrics['total_tokens_used'] += usage_entry.get('tokens_used', 0)

                if usage_entry.get('warning_triggered', False):
                    context_metrics['context_warnings'] += 1

                if usage_entry.get('compaction_triggered', False):
                    context_metrics['compaction_events'] += 1

                peak_usage = usage_entry.get('peak_usage', 0)
                if peak_usage > context_metrics['peak_context_usage']:
                    context_metrics['peak_context_usage'] = peak_usage

            # Calculate context efficiency
            if context_metrics['total_tokens_used'] > 0:
                context_metrics['context_efficiency'] = min(100,
                    (context_metrics['total_tokens_used'] / 160000) * 100
                )

            return context_metrics

        except Exception as e:
            self._log_error(f"Error collecting context usage metrics: {e}")
            return {}

    def _collect_workflow_metrics(self) -> Dict[str, Any]:
        """Collect workflow-related metrics"""
        try:
            workflow_metrics = {
                'daic_transitions': 0,
                'task_completions': 0,
                'workflow_phase_changes': 0,
                'enforcement_actions': 0,
                'workflow_efficiency': 0
            }

            # Get workflow events from shared state
            workflow_events = self.shared_state.get_workflow_events()

            for event in workflow_events:
                event_type = event.get('type', '')

                if event_type == 'daic_transition':
                    workflow_metrics['daic_transitions'] += 1
                elif event_type == 'task_completion':
                    workflow_metrics['task_completions'] += 1
                elif event_type == 'phase_change':
                    workflow_metrics['workflow_phase_changes'] += 1
                elif event_type == 'enforcement_action':
                    workflow_metrics['enforcement_actions'] += 1

            return workflow_metrics

        except Exception as e:
            self._log_error(f"Error collecting workflow metrics: {e}")
            return {}

    def _collect_error_metrics(self) -> Dict[str, Any]:
        """Collect error and failure metrics"""
        try:
            error_metrics = {
                'total_errors': 0,
                'errors_by_type': {},
                'error_recovery_rate': 0,
                'critical_errors': 0,
                'warning_count': 0
            }

            # Get error log from shared state
            error_log = self.shared_state.get_error_log()

            for error_entry in error_log:
                error_metrics['total_errors'] += 1

                error_type = error_entry.get('type', 'unknown')
                error_metrics['errors_by_type'][error_type] = error_metrics['errors_by_type'].get(error_type, 0) + 1

                if error_entry.get('critical', False):
                    error_metrics['critical_errors'] += 1

                if error_entry.get('level') == 'warning':
                    error_metrics['warning_count'] += 1

            return error_metrics

        except Exception as e:
            self._log_error(f"Error collecting error metrics: {e}")
            return {}

    def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect overall performance metrics"""
        try:
            performance_metrics = {
                'session_duration_seconds': 0,
                'average_tool_execution_time': 0,
                'total_operations': 0,
                'operations_per_minute': 0,
                'memory_usage_mb': 0,
                'cpu_usage_percent': 0
            }

            # Calculate session duration
            start_time = self._get_session_start_time()
            if start_time:
                duration = (datetime.now() - datetime.fromisoformat(start_time)).total_seconds()
                performance_metrics['session_duration_seconds'] = duration

                # Calculate operations per minute
                total_operations = self.session_metrics.get('tool_usage', {}).get('total_tools_used', 0)
                performance_metrics['total_operations'] = total_operations
                performance_metrics['operations_per_minute'] = total_operations / (duration / 60) if duration > 0 else 0

            return performance_metrics

        except Exception as e:
            self._log_error(f"Error collecting performance metrics: {e}")
            return {}

    def _generate_session_report(self) -> Dict[str, Any]:
        """Generate comprehensive session report"""
        try:
            report = {
                'session_summary': self._generate_session_summary(),
                'performance_analysis': self._generate_performance_analysis(),
                'recommendations': self._generate_recommendations(),
                'insights': self._generate_insights(),
                'timestamp': self._get_timestamp()
            }

            return report

        except Exception as e:
            self._log_error(f"Error generating session report: {e}")
            return {}

    def _generate_session_summary(self) -> Dict[str, Any]:
        """Generate session summary"""
        try:
            session_info = self.session_metrics.get('session_info', {})
            tool_usage = self.session_metrics.get('tool_usage', {})

            summary = {
                'duration_minutes': session_info.get('duration_seconds', 0) / 60,
                'tools_used': tool_usage.get('total_tools_used', 0),
                'success_rate': self._calculate_success_rate(),
                'daic_mode': session_info.get('daic_mode', 'unknown'),
                'current_task': session_info.get('current_task', {}).get('title', 'No active task')
            }

            return summary

        except Exception as e:
            self._log_error(f"Error generating session summary: {e}")
            return {}

    def _generate_performance_analysis(self) -> Dict[str, Any]:
        """Generate performance analysis"""
        try:
            analysis = {
                'efficiency_score': self._calculate_efficiency_score(),
                'bottlenecks': self._identify_bottlenecks(),
                'optimization_opportunities': self._identify_optimization_opportunities(),
                'resource_usage': self._analyze_resource_usage()
            }

            return analysis

        except Exception as e:
            self._log_error(f"Error generating performance analysis: {e}")
            return {}

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations for improvement"""
        try:
            recommendations = []

            # Tool usage recommendations
            tool_usage = self.session_metrics.get('tool_usage', {})
            if tool_usage.get('failed_tools', 0) > 0:
                recommendations.append("Consider reviewing failed tool executions for improvement opportunities")

            # Context usage recommendations
            context_usage = self.session_metrics.get('context_usage', {})
            if context_usage.get('context_warnings', 0) > 0:
                recommendations.append("Optimize context usage to reduce warnings and improve efficiency")

            # Agent performance recommendations
            agent_performance = self.session_metrics.get('agent_performance', {})
            if agent_performance.get('active_agents'):
                recommendations.append("Monitor agent performance and consider optimization")

            # Workflow recommendations
            workflow_metrics = self.session_metrics.get('workflow_metrics', {})
            if workflow_metrics.get('enforcement_actions', 0) > 0:
                recommendations.append("Review workflow enforcement actions for potential improvements")

            return recommendations

        except Exception as e:
            self._log_error(f"Error generating recommendations: {e}")
            return []

    def _generate_insights(self) -> List[str]:
        """Generate insights from session data"""
        try:
            insights = []

            # Tool usage insights
            tool_usage = self.session_metrics.get('tool_usage', {})
            most_used_tools = tool_usage.get('most_used_tools', [])
            if most_used_tools:
                top_tool = most_used_tools[0]
                insights.append(f"Most frequently used tool: {top_tool[0]} ({top_tool[1]} times)")

            # Context usage insights
            context_usage = self.session_metrics.get('context_usage', {})
            if context_usage.get('compaction_events', 0) > 0:
                insights.append(f"Context compaction occurred {context_usage['compaction_events']} times during session")

            # Performance insights
            performance = self.session_metrics.get('performance_metrics', {})
            if performance.get('operations_per_minute', 0) > 0:
                insights.append(f"Average operations per minute: {performance['operations_per_minute']:.2f}")

            return insights

        except Exception as e:
            self._log_error(f"Error generating insights: {e}")
            return []

    def _calculate_success_rate(self) -> float:
        """Calculate overall success rate"""
        try:
            tool_usage = self.session_metrics.get('tool_usage', {})
            successful = tool_usage.get('successful_tools', 0)
            total = tool_usage.get('total_tools_used', 0)

            if total > 0:
                return (successful / total) * 100
            return 0.0

        except Exception as e:
            self._log_error(f"Error calculating success rate: {e}")
            return 0.0

    def _calculate_efficiency_score(self) -> float:
        """Calculate overall efficiency score"""
        try:
            # Simple efficiency calculation based on success rate and context usage
            success_rate = self._calculate_success_rate()
            context_usage = self.session_metrics.get('context_usage', {})
            context_efficiency = context_usage.get('context_efficiency', 100)

            # Weighted average
            efficiency_score = (success_rate * 0.6) + (context_efficiency * 0.4)
            return min(100, max(0, efficiency_score))

        except Exception as e:
            self._log_error(f"Error calculating efficiency score: {e}")
            return 0.0

    def _identify_bottlenecks(self) -> List[str]:
        """Identify performance bottlenecks"""
        try:
            bottlenecks = []

            # Tool execution bottlenecks
            tool_usage = self.session_metrics.get('tool_usage', {})
            execution_times = tool_usage.get('tool_execution_times', {})

            for tool_name, times in execution_times.items():
                if times:
                    avg_time = sum(times) / len(times)
                    if avg_time > 5.0:  # More than 5 seconds average
                        bottlenecks.append(f"Slow tool execution: {tool_name} (avg: {avg_time:.2f}s)")

            # Context usage bottlenecks
            context_usage = self.session_metrics.get('context_usage', {})
            if context_usage.get('context_warnings', 0) > 3:
                bottlenecks.append("Frequent context warnings indicate inefficient context usage")

            return bottlenecks

        except Exception as e:
            self._log_error(f"Error identifying bottlenecks: {e}")
            return []

    def _identify_optimization_opportunities(self) -> List[str]:
        """Identify optimization opportunities"""
        try:
            opportunities = []

            # Tool usage optimization
            tool_usage = self.session_metrics.get('tool_usage', {})
            if tool_usage.get('blocked_tools', 0) > 0:
                opportunities.append("Review blocked tools for potential optimization")

            # Context optimization
            context_usage = self.session_metrics.get('context_usage', {})
            if context_usage.get('context_efficiency', 100) < 80:
                opportunities.append("Improve context efficiency through better filtering")

            # Agent optimization
            agent_performance = self.session_metrics.get('agent_performance', {})
            if agent_performance.get('active_agents'):
                opportunities.append("Optimize agent execution and coordination")

            return opportunities

        except Exception as e:
            self._log_error(f"Error identifying optimization opportunities: {e}")
            return []

    def _analyze_resource_usage(self) -> Dict[str, Any]:
        """Analyze resource usage patterns"""
        try:
            resource_analysis = {
                'context_usage_pattern': 'efficient',
                'tool_usage_pattern': 'balanced',
                'agent_utilization': 'moderate'
            }

            # Analyze context usage
            context_usage = self.session_metrics.get('context_usage', {})
            if context_usage.get('context_efficiency', 100) > 90:
                resource_analysis['context_usage_pattern'] = 'efficient'
            elif context_usage.get('context_efficiency', 100) > 70:
                resource_analysis['context_usage_pattern'] = 'moderate'
            else:
                resource_analysis['context_usage_pattern'] = 'inefficient'

            # Analyze tool usage
            tool_usage = self.session_metrics.get('tool_usage', {})
            success_rate = self._calculate_success_rate()
            if success_rate > 90:
                resource_analysis['tool_usage_pattern'] = 'efficient'
            elif success_rate > 70:
                resource_analysis['tool_usage_pattern'] = 'balanced'
            else:
                resource_analysis['tool_usage_pattern'] = 'needs_improvement'

            return resource_analysis

        except Exception as e:
            self._log_error(f"Error analyzing resource usage: {e}")
            return {}

    def _save_session_metrics(self) -> None:
        """Save session metrics to persistent storage"""
        try:
            # Save detailed metrics
            metrics_file = self.analytics_dir / f'session_metrics_{self._get_timestamp()}.json'
            with open(metrics_file, 'w') as f:
                json.dump(self.session_metrics, f, indent=2)

            # Save session report
            report = self._generate_session_report()
            report_file = self.analytics_dir / f'session_report_{self._get_timestamp()}.json'
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)

            # Update aggregate metrics
            self._update_aggregate_metrics()

            self._log_info(f"Session metrics saved to {self.analytics_dir}")

        except Exception as e:
            self._log_error(f"Error saving session metrics: {e}")

    def _update_aggregate_metrics(self) -> None:
        """Update aggregate metrics across all sessions"""
        try:
            aggregate_file = self.analytics_dir / 'aggregate_metrics.json'

            # Load existing aggregate metrics
            if aggregate_file.exists():
                with open(aggregate_file, 'r') as f:
                    aggregate = json.load(f)
            else:
                aggregate = {
                    'total_sessions': 0,
                    'total_tools_used': 0,
                    'average_success_rate': 0,
                    'average_efficiency_score': 0
                }

            # Update with current session data
            aggregate['total_sessions'] += 1

            tool_usage = self.session_metrics.get('tool_usage', {})
            aggregate['total_tools_used'] += tool_usage.get('total_tools_used', 0)

            # Update averages
            current_success_rate = self._calculate_success_rate()
            current_efficiency = self._calculate_efficiency_score()

            total_sessions = aggregate['total_sessions']
            aggregate['average_success_rate'] = (
                (aggregate['average_success_rate'] * (total_sessions - 1) + current_success_rate) / total_sessions
            )
            aggregate['average_efficiency_score'] = (
                (aggregate['average_efficiency_score'] * (total_sessions - 1) + current_efficiency) / total_sessions
            )

            # Save updated aggregate metrics
            with open(aggregate_file, 'w') as f:
                json.dump(aggregate, f, indent=2)

        except Exception as e:
            self._log_error(f"Error updating aggregate metrics: {e}")

    def _cleanup_agent_contexts(self) -> None:
        """Enhanced agent context cleanup with better memory management"""
        agent_context_dir = Path('.claude/state/agent_context')

        if not agent_context_dir.exists():
            return

        try:
            for agent_dir in agent_context_dir.iterdir():
                if not agent_dir.is_dir():
                    continue
                self._cleanup_agent_directory(agent_dir)

            self._log_info("Agent context cleanup completed")
        except Exception as exc:
            self._log_error(f"Error cleaning up agent contexts: {exc}")

    def _cleanup_agent_directory(self, agent_dir: Path) -> None:
        """Remove transient files for a single agent directory."""
        try:
            self._remove_temp_files(agent_dir)
            self._prune_agent_chunks(agent_dir)
            self._cleanup_old_session_data(agent_dir)
        except Exception as exc:
            self._log_warning(f"Agent cleanup failed for {agent_dir}: {exc}")

    def _remove_temp_files(self, agent_dir: Path) -> None:
        for temp_file in agent_dir.glob('temp_*'):
            try:
                temp_file.unlink()
            except Exception as exc:
                self._log_warning(f"Failed to remove temp file {temp_file}: {exc}")

    def _prune_agent_chunks(self, agent_dir: Path) -> None:
        chunk_files = sorted(
            agent_dir.glob('chunk_*.json'),
            key=lambda file_path: file_path.stat().st_mtime,
            reverse=True,
        )

        for old_chunk in chunk_files[10:]:  # Keep last 10
            try:
                old_chunk.unlink()
            except Exception as exc:
                self._log_warning(f"Failed to remove agent chunk {old_chunk}: {exc}")

    def _cleanup_old_session_data(self, agent_dir: Path) -> None:
        """Clean up agent data older than 7 days"""
        try:
            import time
            cutoff_time = time.time() - (7 * 24 * 60 * 60)  # 7 days ago
            for file_path in agent_dir.glob('*'):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                    except Exception as exc:
                        self._log_warning(f"Failed to remove old agent file {file_path}: {exc}")
        except Exception as exc:
            self._log_warning(f"_cleanup_old_session_data failed for {agent_dir}: {exc}")

    def _trigger_memory_cleanup(self) -> None:
        """Trigger memory cleanup and garbage collection"""
        try:
            # Log memory usage before cleanup
            memory_before = self._safe_get_memory_usage()
            if memory_before:
                self._log_info(f"Memory before cleanup: {memory_before.get('rss_mb', 0):.1f}MB")

            # Trigger garbage collection
            gc_stats = self._safe_trigger_gc()
            if gc_stats:
                self._log_info(f"Garbage collection: {gc_stats.get('collected_objects', 0)} objects collected")

            # Log memory usage after cleanup
            memory_after = self._safe_get_memory_usage()
            if memory_after:
                self._log_info(f"Memory after cleanup: {memory_after.get('rss_mb', 0):.1f}MB")

            # Log memory usage for monitoring
            self._safe_log_memory_usage()

        except Exception as e:
            self._log_error(f"Error in memory cleanup: {e}")

    def _safe_get_memory_usage(self) -> Optional[Dict[str, Any]]:
        try:
            return self.shared_state.get_memory_usage()
        except Exception as exc:
            self._log_warning(f"get_memory_usage failed: {exc}")
            return None

    def _safe_trigger_gc(self) -> Optional[Dict[str, Any]]:
        try:
            return self.shared_state.trigger_garbage_collection()
        except Exception as exc:
            self._log_warning(f"trigger_garbage_collection failed: {exc}")
            return None

    def _safe_log_memory_usage(self) -> None:
        try:
            self.shared_state.log_memory_usage()
        except Exception as exc:
            self._log_warning(f"log_memory_usage failed: {exc}")

    def _safe_get_current_task(self) -> Dict[str, Any]:
        try:
            return self.shared_state.get_current_task()
        except Exception as exc:
            self._log_warning(f"get_current_task failed: {exc}")
            return {}

    def _safe_get_daic_mode(self) -> str:
        try:
            return self.shared_state.get_daic_mode()
        except Exception as exc:
            self._log_warning(f"get_daic_mode failed: {exc}")
            return "unknown"

    def _safe_get_enforcement_state(self) -> Dict[str, Any]:
        try:
            return self.shared_state.get_enforcement_state()
        except Exception as exc:
            self._log_warning(f"get_enforcement_state failed: {exc}")
            return {}

    def _safe_update_current_task(self, task: Dict[str, Any]) -> None:
        try:
            self.shared_state.update_current_task(task)
        except Exception as exc:
            self._log_warning(f"update_current_task failed: {exc}")

    def _persist_final_state(self) -> None:
        """Persist final state to ensure no data loss"""
        try:
            # Get current state
            current_task = self._safe_get_current_task()
            daic_mode = self._safe_get_daic_mode()
            enforcement_state = self._safe_get_enforcement_state()

            # Create final state snapshot
            final_state = {
                'session_end_time': self._get_timestamp(),
                'current_task': current_task,
                'daic_mode': daic_mode,
                'enforcement_state': enforcement_state,
                'session_completed': True,
                'final_cleanup_performed': True
            }

            # Save final state
            final_state_file = self.state_dir / 'final_state.json'
            with open(final_state_file, 'w') as f:
                json.dump(final_state, f, indent=2)

            # Update current task with completion status
            if current_task:
                current_task['session_completed'] = True
                current_task['completion_time'] = self._get_timestamp()
                self._safe_update_current_task(current_task)

            self._log_info("Final state persisted successfully")

        except Exception as e:
            self._log_error(f"Error persisting final state: {e}")

    def _update_project_metrics(self) -> None:
        """Update project-level metrics"""
        try:
            # Load existing project metrics
            if self.project_metrics_file.exists():
                with open(self.project_metrics_file, 'r') as f:
                    project_metrics = json.load(f)
            else:
                project_metrics = {
                    'total_sessions': 0,
                    'total_tools_used': 0,
                    'average_session_duration': 0,
                    'average_success_rate': 0,
                    'average_context_efficiency': 0,
                    'last_updated': None
                }

            # Load current session metrics
            tool_usage = self.session_metrics.get('tool_usage', {})
            context_usage = self.session_metrics.get('context_usage', {})
            session_info = self.session_metrics.get('session_info', {})

            # Update project metrics
            project_metrics['total_sessions'] += 1
            project_metrics['total_tools_used'] += tool_usage.get('total_tools_used', 0)
            project_metrics['last_updated'] = self._get_timestamp()

            # Update averages
            current_duration = session_info.get('duration_seconds', 0) / 60  # Convert to minutes
            current_success_rate = self._calculate_success_rate()
            current_context_efficiency = context_usage.get('context_efficiency', 0)

            total_sessions = project_metrics['total_sessions']
            project_metrics['average_session_duration'] = (
                (project_metrics['average_session_duration'] * (total_sessions - 1) + current_duration) / total_sessions
            )
            project_metrics['average_success_rate'] = (
                (project_metrics['average_success_rate'] * (total_sessions - 1) + current_success_rate) / total_sessions
            )
            project_metrics['average_context_efficiency'] = (
                (project_metrics['average_context_efficiency'] * (total_sessions - 1) + current_context_efficiency) / total_sessions
            )

            # Save updated project metrics
            with open(self.project_metrics_file, 'w') as f:
                json.dump(project_metrics, f, indent=2)

            self._log_info("Project metrics updated successfully")

        except Exception as e:
            self._log_error(f"Error updating project metrics: {e}")

    def _cleanup_temp_files(self) -> None:
        """Clean up temporary files"""
        try:
            # Clean up temp directory
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                self.temp_dir.mkdir(parents=True, exist_ok=True)

            # Clean up old analytics files (keep only last 30 days)
            cutoff_date = datetime.now() - timedelta(days=30)
            for file_path in self.analytics_dir.glob('*'):
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_date:
                        file_path.unlink()

            self._log_info("Temporary files cleaned up")

        except Exception as e:
            self._log_error(f"Error cleaning up temp files: {e}")

    def _archive_session_data(self) -> None:
        """Archive session data for long-term storage"""
        try:
            # Create archive directory
            archive_dir = Path('.claude/archive')
            archive_dir.mkdir(parents=True, exist_ok=True)

            # Create session archive
            session_id = self._generate_session_id()
            session_archive_dir = archive_dir / f'session_{session_id}'
            session_archive_dir.mkdir(exist_ok=True)

            # Archive important files
            important_files = [
                'current_task.json',
                'daic-mode.json',
                'final_state.json'
            ]

            for file_name in important_files:
                source_file = self.state_dir / file_name
                if source_file.exists():
                    shutil.copy2(source_file, session_archive_dir / file_name)

            # Archive analytics
            analytics_archive_dir = session_archive_dir / 'analytics'
            analytics_archive_dir.mkdir(exist_ok=True)

            for analytics_file in self.analytics_dir.glob('*'):
                if analytics_file.is_file():
                    shutil.copy2(analytics_file, analytics_archive_dir / analytics_file.name)

            self._log_info(f"Session data archived to {session_archive_dir}")

        except Exception as e:
            self._log_error(f"Error archiving session data: {e}")

    def _final_cleanup(self) -> None:
        """Perform final cleanup tasks"""
        try:
            # Update final state
            final_state = {
                'session_ended': True,
                'cleanup_completed': True,
                'end_time': self._get_timestamp(),
                'next_session_ready': True
            }

            final_state_file = self.state_dir / 'session_end_state.json'
            with open(final_state_file, 'w') as f:
                json.dump(final_state, f, indent=2)

            # Log final cleanup
            self._log_info("Final cleanup completed - session ready for next use")

        except Exception as e:
            self._log_error(f"Error in final cleanup: {e}")

    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        import uuid
        return str(uuid.uuid4())[:8]

    def _get_session_start_time(self) -> Optional[str]:
        """Get session start time from shared state"""
        try:
            return self.shared_state.get_session_start_time()
        except Exception as exc:
            self._log_warning(f"get_session_start_time failed: {exc}")
            return None

    def _calculate_session_duration(self) -> float:
        """Calculate session duration in seconds"""
        try:
            start_time = self._get_session_start_time()
            if start_time:
                start_dt = datetime.fromisoformat(start_time)
                duration = (datetime.now() - start_dt).total_seconds()
                return duration
            return 0.0
        except Exception as exc:
            self._log_warning(f"calculate_session_duration failed: {exc}")
            return 0.0

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
    """Main entry point for Session Lifecycle hook"""
    try:
        # Read input from stdin (if any)
        try:
            input_data = json.loads(sys.stdin.read())
        except:
            input_data = {}

        # Determine if this is session end or session stop based on hook event
        hook_event_name = input_data.get('hookEventName', '')
        is_session_end = (hook_event_name == 'SessionEnd' or input_data.get('session_end', False))

        # Initialize session lifecycle manager
        lifecycle_manager = SessionLifecycleManager()

        # Handle session lifecycle
        success = lifecycle_manager.handle_session_lifecycle(is_session_end)

        if success:
            result = {
                'status': 'success',
                'message': 'Session lifecycle processing completed successfully',
                'session_type': 'end' if is_session_end else 'stop',
                'timestamp': lifecycle_manager._get_timestamp()
            }
            print(json.dumps(result))
            sys.exit(0)
        else:
            result = {
                'status': 'error',
                'message': 'Session lifecycle processing failed',
                'timestamp': lifecycle_manager._get_timestamp()
            }
            print(json.dumps(result), file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        result = {
            'status': 'error',
            'message': f'Unexpected error: {e}',
            'timestamp': lifecycle_manager._get_timestamp() if 'lifecycle_manager' in locals() else 'unknown'
        }
        print(json.dumps(result), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
