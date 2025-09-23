import json
from pathlib import Path
import subprocess


def run_hook(path: Path, script_rel: str, payload: dict | None = None) -> subprocess.CompletedProcess:
    args = ["python3", str(Path(__file__).resolve().parents[1] / script_rel)]
    return subprocess.run(args, input=(json.dumps(payload) if payload else None), text=True, capture_output=True, cwd=str(path), timeout=10)


def setup_project(tmp: Path) -> None:
    (tmp / ".claude" / "state" / "compaction").mkdir(parents=True, exist_ok=True)
    (tmp / "sessions").mkdir(parents=True, exist_ok=True)
    # Seed a current task state
    state_dir = tmp / ".claude" / "state"
    (state_dir / "daic-mode.json").write_text(json.dumps({"mode": "discussion"}))
    (state_dir / "current_task.json").write_text(json.dumps({
        "task": "m-example",
        "branch": "feature/m-example",
        "services": ["app"],
        "updated": "2025-01-01"
    }))


def test_precompact_writes_manifest_and_metadata(tmp_path: Path):
    setup_project(tmp_path)
    res = run_hook(tmp_path, "cc_sessions/hooks/context_manager.py", {"hookEventName": "PreCompact"})
    assert res.returncode == 0
    comp_dir = tmp_path / ".claude" / "state" / "compaction"
    assert (comp_dir / "context_manifest.json").exists()
    # metadata.json removed by design; rely on task-file checkpoints only


def test_session_start_surfaces_resume_plan(tmp_path: Path):
    setup_project(tmp_path)
    # PreCompact to create manifest and metadata
    res_pre = run_hook(tmp_path, "cc_sessions/hooks/context_manager.py", {"hookEventName": "PreCompact"})
    assert res_pre.returncode == 0
    # Simulate /clear by just running SessionStart
    res_start = run_hook(tmp_path, "cc_sessions/hooks/session_start.py")
    assert res_start.returncode == 0
    out = res_start.stdout or ""
    # Expect the session-start text to include resume hints
    assert "Continue from where you left off" in out or "Resume" in out
    # If manifest exists, instructions should be mentioned
    assert "Continue with task" in out or "Next steps" in out or "recovery" in out


