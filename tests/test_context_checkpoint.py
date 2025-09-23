from pathlib import Path
import json
import subprocess


def run_hook(tmp: Path, script_rel: str, payload: dict | None = None) -> subprocess.CompletedProcess:
    args = ["python3", str(Path(__file__).resolve().parents[1] / script_rel)]
    return subprocess.run(args, input=(json.dumps(payload) if payload else None), text=True, capture_output=True, cwd=str(tmp), timeout=10)


def setup_task(tmp: Path) -> Path:
    sessions = tmp / "sessions" / "tasks"
    sessions.mkdir(parents=True, exist_ok=True)
    task_file = sessions / "m-example.md"
    task_file.write_text(
        """---
task: m-example
branch: feature/m-example
status: in-progress
created: 2025-01-01
modules: [app]
---

# Example Task

## Work Log
- [2025-01-01] Started work
"""
    )

    state_dir = tmp / ".claude" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "current_task.json").write_text(json.dumps({
        "task": "m-example",
        "branch": "feature/m-example",
        "services": ["app"],
        "updated": "2025-01-01"
    }))
    (state_dir / "compaction").mkdir(parents=True, exist_ok=True)
    return task_file


def test_precompact_appends_checkpoint_to_task_file(tmp_path: Path):
    task_file = setup_task(tmp_path)
    # Run PreCompact
    res = run_hook(tmp_path, "cc_sessions/hooks/context_manager.py", {"hookEventName": "PreCompact"})
    assert res.returncode == 0
    content = task_file.read_text()
    assert "## Work Log" in content
    assert "[Checkpoint]" in content or "Checkpoint" in content




