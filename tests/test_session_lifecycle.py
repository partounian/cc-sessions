import json
import subprocess
from pathlib import Path


def read_error_messages(tmp: Path) -> list[str]:
    log_file = tmp / ".claude" / "state" / "error_log.json"
    if not log_file.exists():
        return []
    messages: list[str] = []
    for line in log_file.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            messages.append(json.loads(line).get("message", ""))
        except json.JSONDecodeError:
            continue
    return messages


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


def test_session_lifecycle_logs_clear_subagent_failures(monkeypatch):
    import cc_sessions.hooks.session_lifecycle as lifecycle

    captured: list[str] = []

    class StubSharedState:
        def clear_subagent_state(self):
            raise RuntimeError("boom")

        def get_session_start_time(self):
            return None

    monkeypatch.setattr(lifecycle.SessionLifecycleManager, "_log_warning", lambda self, msg: captured.append(msg))

    manager = lifecycle.SessionLifecycleManager()
    manager.shared_state = StubSharedState()

    manager.handle_session_lifecycle()

    assert any("clear_subagent_state failed" in msg for msg in captured)


