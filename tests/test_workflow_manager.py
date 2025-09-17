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


def test_subagent_boundary_blocks_state_edits(tmp_path: Path):
    setup_project(tmp_path)
    # Create subagent flag
    (tmp_path / ".claude" / "state" / "in_subagent_context.flag").touch()
    # Attempt edit under .claude/state
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(Path(".claude/state/test.json"))}}
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



