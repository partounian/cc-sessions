import json
import subprocess
from pathlib import Path


def run_hook(tmp: Path, payload: dict) -> subprocess.CompletedProcess:
    script = Path(__file__).resolve().parents[1] / "cc_sessions" / "hooks" / "context_manager.py"
    return subprocess.run([
        "python3",
        str(script),
    ], input=json.dumps(payload), text=True, capture_output=True, cwd=str(tmp), timeout=10)


def setup_project(tmp: Path) -> None:
    (tmp / ".claude" / "state" / "compaction").mkdir(parents=True, exist_ok=True)


def test_precompact_creates_summaries(tmp_path: Path):
    setup_project(tmp_path)
    # Write a current task to ensure manifest gets proper names
    state_dir = tmp_path / ".claude" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "current_task.json").write_text(json.dumps({
        "task": "m-example",
        "branch": "feature/m-example",
        "services": ["app"],
        "updated": "2025-01-01"
    }))
    payload = {"hookEventName": "PreCompact"}
    res = run_hook(tmp_path, payload)
    assert res.returncode == 0
    comp_dir = tmp_path / ".claude" / "state" / "compaction"
    # files expected per implementation
    assert (comp_dir / "agent_context_summary.json").exists()
    assert (comp_dir / "workflow_state_summary.json").exists()
    assert (comp_dir / "task_context_summary.json").exists()
    assert (comp_dir / "context_manifest.json").exists()
    # verify manifest has non-unknown resume hints
    manifest = json.loads((comp_dir / "context_manifest.json").read_text())
    hints = manifest.get("recovery_instructions", [])
    assert any("Continue with task: m-example" in h for h in hints)
    # phase should be set to discussion/implementation, not 'unknown'
    phase = manifest.get("workflow_state", {}).get("current_phase")
    assert phase in ("discussion", "implementation")


def test_precompact_logs_context_usage_failure(monkeypatch):
    import cc_sessions.hooks.context_manager as cm

    captured: list[str] = []
    monkeypatch.setattr(cm.ContextManager, "_log_warning", lambda self, msg: captured.append(msg))

    manager = cm.ContextManager()

    def boom(*_args, **_kwargs):
        raise RuntimeError("log_context_usage broken")

    manager.shared_state = type("Stub", (), {"log_context_usage": staticmethod(boom)})()

    manager._log_context_usage({})

    assert any("Failed to log context usage" in msg for msg in captured)


