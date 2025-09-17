import subprocess
from pathlib import Path


def run_hook(tmp: Path) -> subprocess.CompletedProcess:
    script = Path(__file__).resolve().parents[1] / "cc_sessions" / "hooks" / "session_start.py"
    return subprocess.run(["python3", str(script)], text=True, capture_output=True, cwd=str(tmp), timeout=10)


def test_session_start_sets_flags_and_state(tmp_path: Path):
    (tmp_path / "sessions").mkdir(parents=True, exist_ok=True)
    res = run_hook(tmp_path)
    assert res.returncode == 0
    # state files created
    state_dir = tmp_path / ".claude" / "state"
    assert (state_dir / "daic-mode.json").exists()
    # warning flags cleared if present
    (state_dir / "context-warning-75.flag").touch()
    (state_dir / "context-warning-90.flag").touch()
    res2 = run_hook(tmp_path)
    assert res2.returncode == 0
    assert not (state_dir / "context-warning-75.flag").exists()
    assert not (state_dir / "context-warning-90.flag").exists()


