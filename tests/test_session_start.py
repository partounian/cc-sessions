import json
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


def test_session_start_logs_warning_on_bad_config(tmp_path: Path):
    state_dir = tmp_path / ".claude" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    config_file = tmp_path / "sessions" / "sessions-config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    # Write invalid JSON to trigger warning path
    config_file.write_text("{ not: valid json }")

    res = run_hook(tmp_path)
    assert res.returncode == 0

    log_file = state_dir / "error_log.json"
    assert log_file.exists()

    messages = [
        json.loads(line).get("message", "")
        for line in log_file.read_text().splitlines()
        if line.strip()
    ]

    assert any("Failed to load developer name" in message for message in messages)


def test_session_start_updates_task_and_outputs_resume_info(tmp_path: Path):
    state_dir = tmp_path / ".claude" / "state"
    tasks_dir = tmp_path / "sessions" / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "compaction").mkdir(parents=True, exist_ok=True)

    task_file = tasks_dir / "m-sample.md"
    task_file.write_text("""---
title: Sample Task
status: pending
---

Initial content
""")

    manifest = {
        "recovery_instructions": [
            "Continue pending work",
            "Review notes"
        ]
    }
    (state_dir / "compaction" / "context_manifest.json").write_text(json.dumps(manifest, indent=2))

    current_task = {
        "task": "m-sample",
        "branch": "feature/m-sample",
        "services": ["app"],
    }
    (state_dir / "current_task.json").write_text(json.dumps(current_task))

    res = run_hook(tmp_path)
    assert res.returncode == 0

    output = res.stdout
    assert "<session-start>" in output
    context = output.split("<session-start>\n", 1)[1].rsplit("\n</session-start>", 1)[0]

    updated_content = task_file.read_text()
    assert "status: in-progress" in updated_content

    assert "Resume plan from last compaction:" in context
    assert "- Continue pending work" in context
    assert "[Note: Task status updated from 'pending' to 'in-progress']" in context


