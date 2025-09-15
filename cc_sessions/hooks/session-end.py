#!/usr/bin/env python3
"""
Session End Hook for cc-sessions

Handles final session cleanup, state persistence, and project metrics updates.
This hook runs when a Claude Code session ends to ensure complete cleanup
and proper state management.

This hook adds unique value by:
- Performing final state persistence and cleanup
- Generating comprehensive session reports
- Updating project-level metrics and analytics
- Cleaning up temporary files and agent contexts
- Ensuring proper session closure
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


class SessionEndManager:
    """Manages final session cleanup and state persistence"""

    def __init__(self):
        self.shared_state = SharedState()
        self.state_dir = Path('.claude/state')
        self.temp_dir = Path('.claude/temp')
        self.analytics_dir = Path('.claude/state/analytics')
        self.project_metrics_file = Path('.claude/state/project_metrics.json')

        # Ensure directories exist
        self.analytics_dir.mkdir(parents=True, exist_ok=True)

    def handle_session_end(self) -> bool:
        """Handle complete session end processing"""
        try:
            # Final state persistence
            self._persist_final_state()

            # Generate comprehensive session report
            self._generate_comprehensive_report()

            # Update project metrics
            self._update_project_metrics()

            # Clean up temporary files
            self._cleanup_temp_files()

            # Clean up agent contexts
            self._cleanup_agent_contexts()

            # Archive session data
            self._archive_session_data()

            # Final cleanup
            self._final_cleanup()

            return True

        except Exception as e:
            self._log_error(f"Error handling session end: {e}")
            return False

    def _persist_final_state(self) -> None:
        """Persist final state to ensure no data loss"""
        try:
            # Get current state
            current_task = self.shared_state.get_current_task()
            daic_mode = self.shared_state.get_daic_mode()
            enforcement_state = self.shared_state.get_enforcement_state()

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
                self.shared_state.update_current_task(current_task)

            self._log_info("Final state persisted successfully")

        except Exception as e:
            self._log_error(f"Error persisting final state: {e}")

    def _generate_comprehensive_report(self) -> None:
        """Generate comprehensive session report"""
        try:
            # Collect all session data
            session_data = self._collect_comprehensive_session_data()

            # Generate report
            report = {
                'session_info': self._generate_session_info(session_data),
                'performance_summary': self._generate_performance_summary(session_data),
                'workflow_analysis': self._generate_workflow_analysis(session_data),
                'agent_analysis': self._generate_agent_analysis(session_data),
                'context_analysis': self._generate_context_analysis(session_data),
                'recommendations': self._generate_final_recommendations(session_data),
                'insights': self._generate_final_insights(session_data),
                'timestamp': self._get_timestamp()
            }

            # Save comprehensive report
            report_file = self.analytics_dir / f'comprehensive_report_{self._get_timestamp()}.json'
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)

            # Generate human-readable summary
            self._generate_human_readable_summary(report)

            self._log_info(f"Comprehensive report generated: {report_file}")

        except Exception as e:
            self._log_error(f"Error generating comprehensive report: {e}")

    def _collect_comprehensive_session_data(self) -> Dict[str, Any]:
        """Collect comprehensive session data"""
        try:
            session_data = {
                'session_metrics': self._load_latest_session_metrics(),
                'tool_usage_log': self.shared_state.get_tool_usage_log(),
                'context_usage_log': self.shared_state.get_context_usage_log(),
                'error_log': self.shared_state.get_error_log(),
                'workflow_events': self.shared_state.get_workflow_events(),
                'agent_contexts': self._collect_agent_contexts_data(),
                'current_state': self._collect_current_state()
            }

            return session_data

        except Exception as e:
            self._log_error(f"Error collecting comprehensive session data: {e}")
            return {}

    def _load_latest_session_metrics(self) -> Dict[str, Any]:
        """Load the latest session metrics"""
        try:
            # Find the most recent session metrics file
            metrics_files = list(self.analytics_dir.glob('session_metrics_*.json'))
            if metrics_files:
                latest_file = max(metrics_files, key=lambda f: f.stat().st_mtime)
                with open(latest_file, 'r') as f:
                    return json.load(f)
            return {}

        except Exception as e:
            self._log_error(f"Error loading latest session metrics: {e}")
            return {}

    def _collect_agent_contexts_data(self) -> Dict[str, Any]:
        """Collect data from all agent contexts"""
        try:
            agent_data = {}
            agent_context_dir = Path('.claude/state/agent_context')

            if agent_context_dir.exists():
                for agent_type_dir in agent_context_dir.iterdir():
                    if agent_type_dir.is_dir():
                        agent_type = agent_type_dir.name
                        agent_data[agent_type] = {
                            'files': list(agent_type_dir.glob('*')),
                            'last_modified': agent_type_dir.stat().st_mtime,
                            'size': sum(f.stat().st_size for f in agent_type_dir.glob('*') if f.is_file())
                        }

            return agent_data

        except Exception as e:
            self._log_error(f"Error collecting agent contexts data: {e}")
            return {}

    def _collect_current_state(self) -> Dict[str, Any]:
        """Collect current system state"""
        try:
            return {
                'current_task': self.shared_state.get_current_task(),
                'daic_mode': self.shared_state.get_daic_mode(),
                'enforcement_state': self.shared_state.get_enforcement_state(),
                'session_start_time': self.shared_state.get_session_start_time(),
                'compaction_metadata': self.shared_state.get_compaction_metadata()
            }

        except Exception as e:
            self._log_error(f"Error collecting current state: {e}")
            return {}

    def _generate_session_info(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate session information summary"""
        try:
            current_state = session_data.get('current_state', {})
            session_metrics = session_data.get('session_metrics', {})

            session_info = {
                'session_id': self._generate_session_id(),
                'start_time': current_state.get('session_start_time'),
                'end_time': self._get_timestamp(),
                'duration_minutes': self._calculate_session_duration_minutes(),
                'daic_mode': current_state.get('daic_mode', 'unknown'),
                'current_task': current_state.get('current_task', {}).get('title', 'No active task'),
                'session_status': 'completed'
            }

            return session_info

        except Exception as e:
            self._log_error(f"Error generating session info: {e}")
            return {}

    def _generate_performance_summary(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance summary"""
        try:
            session_metrics = session_data.get('session_metrics', {})
            tool_usage = session_metrics.get('tool_usage', {})
            context_usage = session_metrics.get('context_usage', {})

            performance_summary = {
                'total_tools_used': tool_usage.get('total_tools_used', 0),
                'success_rate': self._calculate_success_rate(tool_usage),
                'context_efficiency': context_usage.get('context_efficiency', 0),
                'average_execution_time': self._calculate_average_execution_time(tool_usage),
                'operations_per_minute': self._calculate_operations_per_minute(session_data),
                'error_rate': self._calculate_error_rate(session_data)
            }

            return performance_summary

        except Exception as e:
            self._log_error(f"Error generating performance summary: {e}")
            return {}

    def _generate_workflow_analysis(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate workflow analysis"""
        try:
            workflow_events = session_data.get('workflow_events', [])
            current_state = session_data.get('current_state', {})

            workflow_analysis = {
                'daic_transitions': len([e for e in workflow_events if e.get('type') == 'daic_transition']),
                'task_completions': len([e for e in workflow_events if e.get('type') == 'task_completion']),
                'enforcement_actions': len([e for e in workflow_events if e.get('type') == 'enforcement_action']),
                'workflow_phase': current_state.get('current_task', {}).get('phase', 'unknown'),
                'workflow_efficiency': self._calculate_workflow_efficiency(workflow_events)
            }

            return workflow_analysis

        except Exception as e:
            self._log_error(f"Error generating workflow analysis: {e}")
            return {}

    def _generate_agent_analysis(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate agent analysis"""
        try:
            agent_contexts = session_data.get('agent_contexts', {})
            session_metrics = session_data.get('session_metrics', {})
            agent_performance = session_metrics.get('agent_performance', {})

            agent_analysis = {
                'active_agents': list(agent_contexts.keys()),
                'total_agent_executions': sum(
                    len(agent_performance.get('agent_execution_times', {}).get(agent_type, []))
                    for agent_type in agent_contexts.keys()
                ),
                'agent_success_rates': agent_performance.get('agent_success_rates', {}),
                'agent_context_usage': agent_performance.get('agent_context_usage', {}),
                'agent_output_quality': agent_performance.get('agent_output_quality', {})
            }

            return agent_analysis

        except Exception as e:
            self._log_error(f"Error generating agent analysis: {e}")
            return {}

    def _generate_context_analysis(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate context analysis"""
        try:
            context_usage_log = session_data.get('context_usage_log', [])
            session_metrics = session_data.get('session_metrics', {})
            context_usage = session_metrics.get('context_usage', {})

            context_analysis = {
                'total_tokens_used': context_usage.get('total_tokens_used', 0),
                'context_warnings': context_usage.get('context_warnings', 0),
                'compaction_events': context_usage.get('compaction_events', 0),
                'peak_context_usage': context_usage.get('peak_context_usage', 0),
                'context_efficiency': context_usage.get('context_efficiency', 0),
                'context_optimization_opportunities': self._identify_context_optimization_opportunities(context_usage_log)
            }

            return context_analysis

        except Exception as e:
            self._log_error(f"Error generating context analysis: {e}")
            return {}

    def _generate_final_recommendations(self, session_data: Dict[str, Any]) -> List[str]:
        """Generate final recommendations"""
        try:
            recommendations = []

            # Performance recommendations
            performance_summary = self._generate_performance_summary(session_data)
            if performance_summary.get('success_rate', 100) < 90:
                recommendations.append("Improve tool execution success rate through better parameter validation")

            if performance_summary.get('context_efficiency', 100) < 80:
                recommendations.append("Optimize context usage through better filtering and relevance scoring")

            # Workflow recommendations
            workflow_analysis = self._generate_workflow_analysis(session_data)
            if workflow_analysis.get('enforcement_actions', 0) > 0:
                recommendations.append("Review workflow enforcement actions for potential improvements")

            # Agent recommendations
            agent_analysis = self._generate_agent_analysis(session_data)
            if agent_analysis.get('active_agents'):
                recommendations.append("Monitor and optimize agent performance and coordination")

            # Context recommendations
            context_analysis = self._generate_context_analysis(session_data)
            if context_analysis.get('context_warnings', 0) > 0:
                recommendations.append("Implement better context management to reduce warnings")

            return recommendations

        except Exception as e:
            self._log_error(f"Error generating final recommendations: {e}")
            return []

    def _generate_final_insights(self, session_data: Dict[str, Any]) -> List[str]:
        """Generate final insights"""
        try:
            insights = []

            # Session duration insights
            session_info = self._generate_session_info(session_data)
            duration_minutes = session_info.get('duration_minutes', 0)
            if duration_minutes > 60:
                insights.append(f"Long session duration: {duration_minutes:.1f} minutes")
            elif duration_minutes < 10:
                insights.append(f"Short session duration: {duration_minutes:.1f} minutes")

            # Tool usage insights
            performance_summary = self._generate_performance_summary(session_data)
            total_tools = performance_summary.get('total_tools_used', 0)
            if total_tools > 50:
                insights.append(f"High tool usage: {total_tools} tools executed")
            elif total_tools < 5:
                insights.append(f"Low tool usage: {total_tools} tools executed")

            # Context usage insights
            context_analysis = self._generate_context_analysis(session_data)
            if context_analysis.get('compaction_events', 0) > 0:
                insights.append(f"Context compaction occurred {context_analysis['compaction_events']} times")

            # Agent insights
            agent_analysis = self._generate_agent_analysis(session_data)
            active_agents = agent_analysis.get('active_agents', [])
            if active_agents:
                insights.append(f"Active agents: {', '.join(active_agents)}")

            return insights

        except Exception as e:
            self._log_error(f"Error generating final insights: {e}")
            return []

    def _generate_human_readable_summary(self, report: Dict[str, Any]) -> None:
        """Generate human-readable summary report"""
        try:
            summary_file = self.analytics_dir / f'session_summary_{self._get_timestamp()}.md'

            with open(summary_file, 'w') as f:
                f.write("# Session Summary Report\n\n")

                # Session info
                session_info = report.get('session_info', {})
                f.write(f"**Session ID:** {session_info.get('session_id', 'Unknown')}\n")
                f.write(f"**Duration:** {session_info.get('duration_minutes', 0):.1f} minutes\n")
                f.write(f"**DAIC Mode:** {session_info.get('daic_mode', 'Unknown')}\n")
                f.write(f"**Current Task:** {session_info.get('current_task', 'No active task')}\n\n")

                # Performance summary
                performance = report.get('performance_summary', {})
                f.write("## Performance Summary\n\n")
                f.write(f"- **Tools Used:** {performance.get('total_tools_used', 0)}\n")
                f.write(f"- **Success Rate:** {performance.get('success_rate', 0):.1f}%\n")
                f.write(f"- **Context Efficiency:** {performance.get('context_efficiency', 0):.1f}%\n")
                f.write(f"- **Operations/Minute:** {performance.get('operations_per_minute', 0):.2f}\n\n")

                # Recommendations
                recommendations = report.get('recommendations', [])
                if recommendations:
                    f.write("## Recommendations\n\n")
                    for i, rec in enumerate(recommendations, 1):
                        f.write(f"{i}. {rec}\n")
                    f.write("\n")

                # Insights
                insights = report.get('insights', [])
                if insights:
                    f.write("## Key Insights\n\n")
                    for insight in insights:
                        f.write(f"- {insight}\n")
                    f.write("\n")

            self._log_info(f"Human-readable summary generated: {summary_file}")

        except Exception as e:
            self._log_error(f"Error generating human-readable summary: {e}")

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
            session_metrics = self._load_latest_session_metrics()
            tool_usage = session_metrics.get('tool_usage', {})
            context_usage = session_metrics.get('context_usage', {})
            session_info = session_metrics.get('session_info', {})

            # Update project metrics
            project_metrics['total_sessions'] += 1
            project_metrics['total_tools_used'] += tool_usage.get('total_tools_used', 0)
            project_metrics['last_updated'] = self._get_timestamp()

            # Update averages
            current_duration = session_info.get('duration_seconds', 0) / 60  # Convert to minutes
            current_success_rate = self._calculate_success_rate(tool_usage)
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

    def _cleanup_agent_contexts(self) -> None:
        """Clean up agent context files"""
        try:
            agent_context_dir = Path('.claude/state/agent_context')
            if agent_context_dir.exists():
                for agent_type_dir in agent_context_dir.iterdir():
                    if agent_type_dir.is_dir():
                        # Clean up temporary files
                        for temp_file in agent_type_dir.glob('temp_*'):
                            temp_file.unlink()

                        # Clean up old chunk files (keep only last 10)
                        chunk_files = sorted(agent_type_dir.glob('chunk_*.json'))
                        if len(chunk_files) > 10:
                            for old_chunk in chunk_files[:-10]:
                                old_chunk.unlink()

            self._log_info("Agent contexts cleaned up")

        except Exception as e:
            self._log_error(f"Error cleaning up agent contexts: {e}")

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

    def _calculate_success_rate(self, tool_usage: Dict[str, Any]) -> float:
        """Calculate success rate from tool usage data"""
        try:
            successful = tool_usage.get('successful_tools', 0)
            total = tool_usage.get('total_tools_used', 0)
            return (successful / total * 100) if total > 0 else 0.0
        except:
            return 0.0

    def _calculate_average_execution_time(self, tool_usage: Dict[str, Any]) -> float:
        """Calculate average execution time"""
        try:
            execution_times = tool_usage.get('tool_execution_times', {})
            all_times = []
            for times in execution_times.values():
                all_times.extend(times)
            return sum(all_times) / len(all_times) if all_times else 0.0
        except:
            return 0.0

    def _calculate_operations_per_minute(self, session_data: Dict[str, Any]) -> float:
        """Calculate operations per minute"""
        try:
            session_info = self._generate_session_info(session_data)
            duration_minutes = session_info.get('duration_minutes', 0)
            tool_usage = session_data.get('session_metrics', {}).get('tool_usage', {})
            total_tools = tool_usage.get('total_tools_used', 0)
            return total_tools / duration_minutes if duration_minutes > 0 else 0.0
        except:
            return 0.0

    def _calculate_error_rate(self, session_data: Dict[str, Any]) -> float:
        """Calculate error rate"""
        try:
            error_log = session_data.get('error_log', [])
            tool_usage = session_data.get('session_metrics', {}).get('tool_usage', {})
            total_tools = tool_usage.get('total_tools_used', 0)
            total_errors = len(error_log)
            return (total_errors / total_tools * 100) if total_tools > 0 else 0.0
        except:
            return 0.0

    def _calculate_workflow_efficiency(self, workflow_events: List[Dict[str, Any]]) -> float:
        """Calculate workflow efficiency"""
        try:
            # Simple efficiency calculation based on task completions vs transitions
            completions = len([e for e in workflow_events if e.get('type') == 'task_completion'])
            transitions = len([e for e in workflow_events if e.get('type') == 'daic_transition'])
            total_events = len(workflow_events)

            if total_events > 0:
                return ((completions + transitions) / total_events) * 100
            return 0.0
        except:
            return 0.0

    def _identify_context_optimization_opportunities(self, context_usage_log: List[Dict[str, Any]]) -> List[str]:
        """Identify context optimization opportunities"""
        try:
            opportunities = []

            # Check for frequent warnings
            warnings = len([entry for entry in context_usage_log if entry.get('warning_triggered', False)])
            if warnings > 3:
                opportunities.append("Frequent context warnings indicate need for better context management")

            # Check for frequent compactions
            compactions = len([entry for entry in context_usage_log if entry.get('compaction_triggered', False)])
            if compactions > 2:
                opportunities.append("Frequent context compactions suggest need for more efficient context usage")

            return opportunities
        except:
            return []

    def _calculate_session_duration_minutes(self) -> float:
        """Calculate session duration in minutes"""
        try:
            start_time = self.shared_state.get_session_start_time()
            if start_time:
                start_dt = datetime.fromisoformat(start_time)
                duration = (datetime.now() - start_dt).total_seconds()
                return duration / 60
            return 0.0
        except:
            return 0.0

    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
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
    """Main entry point for Session End hook"""
    try:
        # Read input from stdin (if any)
        try:
            input_data = json.loads(sys.stdin.read())
        except:
            input_data = {}

        # Initialize session end manager
        end_manager = SessionEndManager()

        # Handle session end
        success = end_manager.handle_session_end()

        if success:
            result = {
                'status': 'success',
                'message': 'Session end processing completed successfully',
                'timestamp': end_manager._get_timestamp()
            }
            print(json.dumps(result))
            sys.exit(0)
        else:
            result = {
                'status': 'error',
                'message': 'Session end processing failed',
                'timestamp': end_manager._get_timestamp()
            }
            print(json.dumps(result), file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        result = {
            'status': 'error',
            'message': f'Unexpected error: {e}',
            'timestamp': end_manager._get_timestamp() if 'end_manager' in locals() else 'unknown'
        }
        print(json.dumps(result), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
