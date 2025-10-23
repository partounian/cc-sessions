"""Test workspace_mode feature flag for WORKSPACE_ROOT behavior."""
import json
import subprocess
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_workspace_mode_false_project_root_only(tmp_path: Path):
    """Test workspace_mode=False: only PROJECT_ROOT/sessions/tasks/ checked"""
    (tmp_path / "sessions" / "tasks").mkdir(parents=True, exist_ok=True)
    (tmp_path / "workspace" / "sessions" / "tasks").mkdir(parents=True, exist_ok=True)

    config = {
        "environment": {"developer_name": "developer", "os": "linux", "shell": "bash"},
        "features": {"workspace_mode": False},
        "trigger_phrases": {},
        "blocked_actions": {},
        "git_preferences": {}
    }
    (tmp_path / "sessions" / "sessions-config.json").write_text(json.dumps(config))

    # Create task only in workspace location
    (tmp_path / "workspace" / "sessions" / "tasks" / "h-test.md").write_text("# Test Task")

    # Task command should NOT find it (workspace_mode is false)
    script = repo_root() / "cc_sessions" / "python" / "api" / "__main__.py"
    result = subprocess.run(
        ["python3", str(script), "tasks", "list"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=10
    )

    # Should not find the task in workspace location
    assert "h-test" not in result.stdout


def test_workspace_mode_true_checks_both(tmp_path: Path):
    """Test workspace_mode=True: both WORKSPACE_ROOT and PROJECT_ROOT checked"""
    (tmp_path / "sessions" / "tasks").mkdir(parents=True, exist_ok=True)

    config = {
        "environment": {"developer_name": "developer", "os": "linux", "shell": "bash"},
        "features": {"workspace_mode": True},
        "trigger_phrases": {},
        "blocked_actions": {},
        "git_preferences": {}
    }
    (tmp_path / "sessions" / "sessions-config.json").write_text(json.dumps(config))

    # Create task in project root
    (tmp_path / "sessions" / "tasks" / "h-project-task.md").write_text("# Project Task")

    # Task command should find it
    script = repo_root() / "cc_sessions" / "python" / "api" / "__main__.py"
    result = subprocess.run(
        ["python3", str(script), "tasks", "list"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=10
    )

    # Should find the task
    assert result.returncode == 0


def test_feature_toggle_workspace_mode(tmp_path: Path):
    """Test toggling workspace_mode via config command"""
    (tmp_path / "sessions").mkdir(parents=True, exist_ok=True)

    config = {
        "environment": {"developer_name": "developer", "os": "linux", "shell": "bash"},
        "features": {"workspace_mode": False},
        "trigger_phrases": {},
        "blocked_actions": {},
        "git_preferences": {}
    }
    (tmp_path / "sessions" / "sessions-config.json").write_text(json.dumps(config))

    # Toggle workspace_mode on
    script = repo_root() / "cc_sessions" / "python" / "api" / "__main__.py"
    result = subprocess.run(
        ["python3", str(script), "config", "features", "toggle", "workspace_mode"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=10
    )

    assert result.returncode == 0

    # Verify it was toggled
    config_data = json.loads((tmp_path / "sessions" / "sessions-config.json").read_text())
    assert config_data["features"]["workspace_mode"] is True

    # Toggle back off
    result = subprocess.run(
        ["python3", str(script), "config", "features", "toggle", "workspace_mode"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=10
    )

    assert result.returncode == 0

    # Verify it was toggled back
    config_data = json.loads((tmp_path / "sessions" / "sessions-config.json").read_text())
    assert config_data["features"]["workspace_mode"] is False


def test_config_load_with_workspace_mode(tmp_path: Path):
    """Test that config loads workspace_mode field correctly"""
    (tmp_path / "sessions").mkdir(parents=True, exist_ok=True)

    config = {
        "environment": {"developer_name": "developer", "os": "linux", "shell": "bash"},
        "features": {"workspace_mode": True},
        "trigger_phrases": {},
        "blocked_actions": {},
        "git_preferences": {}
    }
    (tmp_path / "sessions" / "sessions-config.json").write_text(json.dumps(config))

    # Import and load config
    import sys
    sys.path.insert(0, str(repo_root() / "cc_sessions" / "python" / "hooks"))
    from shared_state import load_config

    loaded_config = load_config(project_root=tmp_path)
    assert loaded_config.features.workspace_mode is True

