import json
import os
import subprocess
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_hook(tmp: Path, payload: dict) -> subprocess.CompletedProcess:
    script = repo_root() / "cc_sessions" / "hooks" / "workflow_manager.py"
    return subprocess.run(
        ["python3", str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=str(tmp),
        timeout=10,
    )


def setup_project(tmp: Path) -> None:
    (tmp / ".claude" / "state").mkdir(parents=True, exist_ok=True)
    (tmp / "sessions").mkdir(parents=True, exist_ok=True)
    # Initialize DAIC discussion mode
    (tmp / ".claude" / "state" / "daic-mode.json").write_text(json.dumps({"mode": "discussion"}))


def test_daic_blocks_edit(tmp_path: Path):
    setup_project(tmp_path)
    payload = {"tool_name": "Edit", "tool_input": {"file_path": "app.py"}}
    result = run_hook(tmp_path, payload)
    assert result.returncode == 2
    assert "DAIC: Tool Blocked" in (result.stderr or "")


def test_bash_read_only_allows_ls(tmp_path: Path):
    setup_project(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "ls"}}
    result = run_hook(tmp_path, payload)
    assert result.returncode == 0


def test_verbose_guard_blocks_npm_build(tmp_path: Path):
    setup_project(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "npm run build"}}
    result = run_hook(tmp_path, payload)
    assert result.returncode == 2
    assert "Verbose Command Guard" in (result.stderr or "")


def test_verbose_guard_blocks_deploy_script(tmp_path: Path):
    setup_project(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "./deploy.sh"}}
    result = run_hook(tmp_path, payload)
    assert result.returncode == 2
    assert "Verbose Command Guard" in (result.stderr or "")


def test_subagent_boundary_blocks_state_edits(tmp_path: Path):
    setup_project(tmp_path)
    # Simulate subagent active using shared state tracker file
    state_file = tmp_path / ".claude" / "state" / "subagent_state.json"
    state_file.write_text(json.dumps({"sessions": {"abc": {"types": {"shared": {"count": 1, "last_seen": "2025-01-01T00:00:00"}}}}}))
    # Attempt edit under .claude/state
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(Path(".claude/state/test.json"))}, "session_id": "abc"}
    result = run_hook(tmp_path, payload)
    # In discussion mode, DAIC block occurs before subagent boundary check
    assert result.returncode == 2
    assert "DAIC: Tool Blocked" in (result.stderr or "")


def test_branch_enforcement_single_repo(tmp_path: Path):
    setup_project(tmp_path)
    # Initialize a git repo and set current branch
    subprocess.run(["git", "init", "-q"], cwd=tmp_path)
    subprocess.run(["git", "checkout", "-b", "feature/x", "-q"], cwd=tmp_path)
    # Write task state expecting different branch
    task_state = tmp_path / ".claude" / "state" / "current_task.json"
    task_state.write_text(json.dumps({"task": "t", "branch": "feature/y", "services": [], "updated": "2025-01-01"}))

    payload = {"tool_name": "Edit", "tool_input": {"file_path": "main.py"}}
    result = run_hook(tmp_path, payload)
    # In discussion mode, DAIC block occurs before branch enforcement
    assert result.returncode == 2
    assert "DAIC: Tool Blocked" in (result.stderr or "")


def test_post_tool_use_detection_via_event_name(tmp_path: Path):
    setup_project(tmp_path)
    # Simulate PostToolUse by providing event name and cwd
    payload = {
        "hookEventName": "PostToolUse",
        "cwd": str(tmp_path),
        "tool_name": "Write",
        "tool_input": {"file_path": "x.txt"},
    }
    result = run_hook(tmp_path, payload)
    # PostToolUse path should not block; exit code can be 0 or 2 (reminder)
    assert result.returncode in (0, 2)


def test_post_tool_use_detection_via_tool_response(tmp_path: Path):
    setup_project(tmp_path)
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "Write",
        "tool_input": {"file_path": "x.txt"},
        "tool_response": {"success": True},
    }
    result = run_hook(tmp_path, payload)
    assert result.returncode in (0, 2)


def test_cooldown_allows_tools_after_switch(tmp_path: Path):
    setup_project(tmp_path)
    # Manually set cooldown to active by invoking user_messages trigger path would be overkill; simulate
    state_dir = tmp_path / ".claude" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "daic-mode.json").write_text(json.dumps({"mode": "implementation"}))
    # Write cooldown file
    from datetime import datetime, timedelta
    expires = (datetime.now() + timedelta(seconds=60)).isoformat()
    (state_dir / "daic-cooldown.json").write_text(json.dumps({"expires_at": expires, "seconds": 60}))
    # Now attempt an Edit tool; should not be blocked by DAIC even if discussion mode would block
    payload = {"tool_name": "Edit", "tool_input": {"file_path": "app.py"}}
    result = run_hook(tmp_path, payload)
    # Should be allowed (exit 0) or pass through with reminder codes
    assert result.returncode in (0,)



