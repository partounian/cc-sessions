"""Test unified /sessions command surface."""
import json
import subprocess
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_sessions_cmd(tmp: Path, *args) -> subprocess.CompletedProcess:
    """Run sessions API command"""
    script = repo_root() / "cc_sessions" / "python" / "api" / "__main__.py"
    return subprocess.run(
        ["python3", str(script)] + list(args),
        capture_output=True,
        text=True,
        cwd=str(tmp),
        timeout=10
    )


def setup_test_env(tmp: Path):
    """Set up minimal test environment"""
    (tmp / ".claude").mkdir(parents=True, exist_ok=True)
    (tmp / "sessions" / "tasks").mkdir(parents=True, exist_ok=True)

    config = {
        "environment": {"developer_name": "developer", "os": "linux", "shell": "bash"},
        "features": {},
        "trigger_phrases": {
            "implementation_mode": ["yert", "make it so"],
            "discussion_mode": ["stop"],
            "task_creation": ["mek:"],
            "task_startup": ["start^"],
            "task_completion": ["finito"],
            "context_compaction": ["squish"]
        },
        "blocked_actions": {
            "implementation_only_tools": ["Edit", "Write"],
            "bash_read_patterns": [],
            "bash_write_patterns": []
        },
        "git_preferences": {
            "add_pattern": "ask",
            "default_branch": "main",
            "commit_style": "conventional",
            "auto_merge": False,
            "auto_push": False,
            "has_submodules": False
        }
    }
    (tmp / "sessions" / "sessions-config.json").write_text(json.dumps(config))

    state = {
        "model": "opus",
        "mode": "discussion",
        "current_task": None,
        "active_protocol": None,
        "api": {"startup_load": False, "completion": False},
        "todos": {"active": []},
        "flags": {},
        "metadata": {}
    }
    (tmp / "sessions" / "sessions-state.json").write_text(json.dumps(state))


def test_config_phrases_list(tmp_path: Path):
    """sessions config phrases list → JSON output"""
    setup_test_env(tmp_path)

    result = run_sessions_cmd(tmp_path, "config", "phrases", "list")
    assert result.returncode == 0
    assert "implementation_mode" in result.stdout
    assert "yert" in result.stdout or "make it so" in result.stdout


def test_config_phrases_add(tmp_path: Path):
    """sessions config phrases add implementation_mode "gotime" """
    setup_test_env(tmp_path)

    result = run_sessions_cmd(tmp_path, "config", "phrases", "add", "implementation_mode", "gotime")
    assert result.returncode == 0

    # Verify it was added
    config = json.loads((tmp_path / "sessions" / "sessions-config.json").read_text())
    assert "gotime" in config["trigger_phrases"]["implementation_mode"]


def test_config_features_show(tmp_path: Path):
    """sessions config features show → lists all features"""
    setup_test_env(tmp_path)

    result = run_sessions_cmd(tmp_path, "config", "features", "show")
    assert result.returncode == 0
    # Output should show features
    assert "task_detection" in result.stdout or "branch_enforcement" in result.stdout


def test_config_features_toggle_non_boolean_error(tmp_path: Path):
    """sessions config features toggle icon_style → error (not boolean)"""
    setup_test_env(tmp_path)

    result = run_sessions_cmd(tmp_path, "config", "features", "toggle", "icon_style")
    # Should fail because icon_style is not a boolean
    assert result.returncode != 0


def test_config_tools_block(tmp_path: Path):
    """sessions config tools block Write → success"""
    setup_test_env(tmp_path)

    result = run_sessions_cmd(tmp_path, "config", "tools", "block", "MultiEdit")
    assert result.returncode == 0


def test_config_tools_list(tmp_path: Path):
    """sessions config tools list → includes blocked tools"""
    setup_test_env(tmp_path)

    result = run_sessions_cmd(tmp_path, "config", "tools", "list")
    assert result.returncode == 0
    assert "Write" in result.stdout or "Edit" in result.stdout


def test_config_read_add(tmp_path: Path):
    """sessions config read add jq → success"""
    setup_test_env(tmp_path)

    result = run_sessions_cmd(tmp_path, "config", "read", "add", "jq")
    assert result.returncode == 0

    # Verify it was added
    config = json.loads((tmp_path / "sessions" / "sessions-config.json").read_text())
    assert "jq" in config["blocked_actions"]["bash_read_patterns"]


def test_state_show(tmp_path: Path):
    """sessions state show → includes mode, task, todos"""
    setup_test_env(tmp_path)

    result = run_sessions_cmd(tmp_path, "state", "show")
    assert result.returncode == 0
    assert "mode" in result.stdout.lower()
    assert "discussion" in result.stdout.lower()


def test_tasks_list(tmp_path: Path):
    """sessions tasks list → task listing"""
    setup_test_env(tmp_path)

    # Create a test task
    (tmp_path / "sessions" / "tasks" / "h-test-task.md").write_text(
        "---\ntitle: Test Task\nstatus: pending\n---\n\n# Test Task\n"
    )

    result = run_sessions_cmd(tmp_path, "tasks", "list")
    assert result.returncode == 0


def test_state_mode_discussion(tmp_path: Path):
    """sessions state mode discussion → switches mode"""
    setup_test_env(tmp_path)

    # Set to implementation first
    state = json.loads((tmp_path / "sessions" / "sessions-state.json").read_text())
    state["mode"] = "implementation"
    (tmp_path / "sessions" / "sessions-state.json").write_text(json.dumps(state))

    # Switch to discussion
    result = run_sessions_cmd(tmp_path, "state", "mode", "discussion")
    assert result.returncode == 0

    # Verify mode changed
    state = json.loads((tmp_path / "sessions" / "sessions-state.json").read_text())
    assert state["mode"] == "discussion"


def test_config_write_add(tmp_path: Path):
    """sessions config write add <pattern> → adds write pattern"""
    setup_test_env(tmp_path)

    result = run_sessions_cmd(tmp_path, "config", "write", "add", "dangerous_cmd")
    assert result.returncode == 0

    # Verify it was added
    config = json.loads((tmp_path / "sessions" / "sessions-config.json").read_text())
    assert "dangerous_cmd" in config["blocked_actions"]["bash_write_patterns"]

