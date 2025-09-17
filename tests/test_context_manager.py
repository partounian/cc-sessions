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
    payload = {"hookEventName": "PreCompact"}
    res = run_hook(tmp_path, payload)
    assert res.returncode == 0
    comp_dir = tmp_path / ".claude" / "state" / "compaction"
    # files expected per implementation
    assert (comp_dir / "agent_context_summary.json").exists()
    assert (comp_dir / "workflow_state_summary.json").exists()
    assert (comp_dir / "task_context_summary.json").exists()
    assert (comp_dir / "context_manifest.json").exists()


