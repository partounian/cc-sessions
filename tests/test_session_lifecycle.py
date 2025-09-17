import json
import subprocess
from pathlib import Path


def run_hook(tmp: Path, payload: dict) -> subprocess.CompletedProcess:
    script = Path(__file__).resolve().parents[1] / "cc_sessions" / "hooks" / "session_lifecycle.py"
    return subprocess.run([
        "python3",
        str(script),
    ], input=json.dumps(payload), text=True, capture_output=True, cwd=str(tmp), timeout=10)


def test_session_stop_writes_metrics(tmp_path: Path):
    (tmp_path / ".claude" / "state" / "analytics").mkdir(parents=True, exist_ok=True)
    res = run_hook(tmp_path, {"hookEventName": "Stop"})
    assert res.returncode == 0
    analytics_dir = tmp_path / ".claude" / "state" / "analytics"
    # metrics and report should be created
    assert any(p.name.startswith("session_metrics_") for p in analytics_dir.glob("*.json"))
    assert any(p.name.startswith("session_report_") for p in analytics_dir.glob("*.json"))


