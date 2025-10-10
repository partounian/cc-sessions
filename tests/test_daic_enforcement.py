import json
import subprocess
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_enforce(tmp: Path, payload: dict) -> subprocess.CompletedProcess:
    script = repo_root() / "cc_sessions" / "python" / "hooks" / "sessions_enforce.py"
    return subprocess.run(["python3", str(script)], input=json.dumps(payload), text=True, capture_output=True, cwd=str(tmp), timeout=10)


def setup_discussion(tmp: Path) -> None:
    (tmp / ".claude").mkdir(parents=True, exist_ok=True)
    (tmp / "sessions").mkdir(parents=True, exist_ok=True)
    state = {
        "mode": "discussion",
        "current_task": {"name": "t", "branch": "feature/x", "file": None, "submodules": []},
        "todos": {"active": []},
        "flags": {"bypass_mode": False},
    }
    (tmp / "sessions" / "sessions-state.json").write_text(json.dumps(state))


def test_block_write_tool_in_discussion(tmp_path: Path):
    setup_discussion(tmp_path)
    payload = {"tool_name": "Write", "tool_input": {"file_path": "x.py"}}
    res = run_enforce(tmp_path, payload)
    assert res.returncode == 2
    assert "DAIC: Tool Blocked" in (res.stderr or "")


def test_allow_readonly_bash_in_discussion(tmp_path: Path):
    setup_discussion(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "ls"}}
    res = run_enforce(tmp_path, payload)
    assert res.returncode == 0


