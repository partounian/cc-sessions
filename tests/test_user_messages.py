import json
import subprocess
from pathlib import Path


def run_hook(tmp: Path, payload: dict) -> subprocess.CompletedProcess:
    script = Path(__file__).resolve().parents[1] / "cc_sessions" / "hooks" / "user_messages.py"
    return subprocess.run([
        "python3",
        str(script),
    ], input=json.dumps(payload), text=True, capture_output=True, cwd=str(tmp), timeout=10)


def setup_project(tmp: Path) -> None:
    (tmp / ".claude" / "state").mkdir(parents=True, exist_ok=True)
    (tmp / "sessions").mkdir(parents=True, exist_ok=True)


def test_daic_trigger_to_implementation(tmp_path: Path):
    setup_project(tmp_path)
    payload = {"prompt": "okay, make it so", "transcript_path": ""}
    res = run_hook(tmp_path, payload)
    assert res.returncode == 0
    assert "Implementation Mode Activated" in (res.stdout or "")


def test_emergency_stop(tmp_path: Path):
    setup_project(tmp_path)
    payload = {"prompt": "STOP", "transcript_path": ""}
    res = run_hook(tmp_path, payload)
    assert res.returncode == 0
    assert "EMERGENCY STOP" in (res.stdout or "")


