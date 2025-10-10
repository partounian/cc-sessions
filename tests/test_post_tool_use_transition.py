import json
import subprocess
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_post_tool(tmp: Path, payload: dict) -> subprocess.CompletedProcess:
    script = repo_root() / "cc_sessions" / "python" / "hooks" / "post_tool_use.py"
    return subprocess.run(["python3", str(script)], input=json.dumps(payload), text=True, capture_output=True, cwd=str(tmp), timeout=10)


def setup_impl_with_todos(tmp: Path) -> None:
    (tmp / ".claude").mkdir(parents=True, exist_ok=True)
    (tmp / "sessions").mkdir(parents=True, exist_ok=True)
    state = {
        "mode": "implementation",
        "current_task": {"name": "t", "branch": "feature/x", "file": None, "submodules": []},
        "todos": {"active": [{"content": "do a"}]},
        "flags": {"bypass_mode": False},
    }
    (tmp / "sessions" / "sessions-state.json").write_text(json.dumps(state))


def test_daic_transition_on_todos_complete(tmp_path: Path):
    setup_impl_with_todos(tmp_path)
    payload = {"tool_name": "TodoWrite", "tool_input": {}, "cwd": str(tmp_path)}

    # Simulate all todos complete by marking state then running post tool
    state_path = tmp_path / "sessions" / "sessions-state.json"
    st = json.loads(state_path.read_text())
    st["todos"]["active"] = []
    state_path.write_text(json.dumps(st))

    res = run_post_tool(tmp_path, payload)
    assert res.returncode in (0, 2)
    events = (tmp_path / "sessions" / "sessions-events.jsonl")
    # Post tool use writes a DAIC transition event on todos complete
    assert events.exists()
    content = events.read_text()
    assert "daic_transition" in content


