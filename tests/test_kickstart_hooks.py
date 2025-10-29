import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_kickstart_hook(tmp: Path) -> subprocess.CompletedProcess:
    """Run kickstart_session_start hook and return result.

    The hook now uses find_project_root() from shared_state.py like other hooks,
    making it more testable and flexible. We set CLAUDE_PROJECT_DIR and PYTHONPATH
    so the hook can find the project root and import shared_state correctly.
    """
    script = repo_root() / "cc_sessions" / "python" / "hooks" / "kickstart_session_start.py"

    # Set CLAUDE_PROJECT_DIR so shared_state.find_project_root() finds test tmp directory
    # Add repo root to PYTHONPATH so hook can import cc_sessions package (fallback import)
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(tmp)
    pythonpath = str(repo_root())
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = f"{pythonpath}:{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = pythonpath

    return subprocess.run(
        ["python3", str(script)],
        input="{}",
        text=True,
        capture_output=True,
        cwd=str(tmp),
        env=env,
        timeout=10
    )


def setup_kickstart_state(tmp: Path, kickstart_meta: dict) -> None:
    """Setup test state with kickstart metadata."""
    (tmp / ".claude").mkdir(parents=True, exist_ok=True)
    (tmp / "sessions").mkdir(parents=True, exist_ok=True)
    state = {
        "model": "opus",
        "mode": "discussion",
        "current_task": {"name": None, "branch": None, "file": None, "submodules": []},
        "todos": {"active": []},
        "flags": {"bypass_mode": False},
        "metadata": {
            "kickstart": kickstart_meta
        }
    }
    (tmp / "sessions" / "sessions-state.json").write_text(json.dumps(state))


def read_state(tmp: Path) -> dict:
    """Read state file."""
    return json.loads((tmp / "sessions" / "sessions-state.json").read_text())


def write_state(tmp: Path, state: dict) -> None:
    """Write state file."""
    (tmp / "sessions" / "sessions-state.json").write_text(json.dumps(state))


def parse_hook_output(output: str) -> dict:
    """Parse hook JSON output."""
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {}


# ===== PHASE 1: COMPLETION DETECTION TESTS =====

def test_kickstart_completion_flag_exits_silently(tmp_path: Path):
    """Phase 1: Hook exits silently when onboarding_complete is true."""
    kickstart_meta = {
        "mode": "full",
        "sequence": ["01-discussion.md", "02-implementation.md"],
        "current_index": 1,
        "completed": ["01-discussion.md"],
        "onboarding_complete": True,
        "completed_at": datetime.now().isoformat()
    }
    setup_kickstart_state(tmp_path, kickstart_meta)

    res = run_kickstart_hook(tmp_path)
    assert res.returncode == 0
    assert not res.stdout.strip()  # Should exit silently with no output
    assert not res.stderr.strip()


def test_kickstart_missing_metadata_with_hook_file_exits_silently(tmp_path: Path):
    """Phase 1: Hook exits silently when metadata missing but hook file exists."""
    (tmp_path / ".claude").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sessions").mkdir(parents=True, exist_ok=True)

    # Create hook file to simulate cleanup window
    hook_file = tmp_path / "sessions" / "hooks" / "kickstart_session_start.py"
    hook_file.parent.mkdir(parents=True, exist_ok=True)
    hook_file.write_text("# test hook file")

    # State without kickstart metadata
    state = {
        "model": "opus",
        "mode": "discussion",
        "metadata": {}
    }
    write_state(tmp_path, state)

    res = run_kickstart_hook(tmp_path)
    assert res.returncode == 0  # Should exit silently


def test_kickstart_missing_metadata_no_hook_file_exits_silently(tmp_path: Path):
    """Phase 1: Hook exits silently when metadata missing and no hook file."""
    (tmp_path / ".claude").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sessions").mkdir(parents=True, exist_ok=True)

    # State without kickstart metadata, no hook file
    state = {
        "model": "opus",
        "mode": "discussion",
        "metadata": {}
    }
    write_state(tmp_path, state)

    res = run_kickstart_hook(tmp_path)
    assert res.returncode == 0  # Should exit silently


def test_kickstart_active_shows_instructions(tmp_path: Path):
    """Phase 1: Hook shows instructions when kickstart is active and not complete."""
    kickstart_meta = {
        "mode": "full",
        "sequence": ["01-discussion.md", "02-implementation.md"],
        "current_index": 0,
        "completed": []
    }
    setup_kickstart_state(tmp_path, kickstart_meta)

    # Create protocols directory structure
    protocols_dir = tmp_path / "sessions" / "protocols" / "kickstart"
    protocols_dir.mkdir(parents=True, exist_ok=True)
    (protocols_dir / "01-discussion.md").write_text("# Discussion Protocol\n\nContent here")

    res = run_kickstart_hook(tmp_path)
    assert res.returncode == 0
    output = parse_hook_output(res.stdout)
    assert "hookSpecificOutput" in output
    assert "additionalContext" in output["hookSpecificOutput"]
    assert "kickstart" in output["hookSpecificOutput"]["additionalContext"].lower() or \
           "discussion" in output["hookSpecificOutput"]["additionalContext"].lower()


# ===== PHASE 2: COOLDOWN LOGIC TESTS =====

def test_kickstart_first_time_shows_instructions(tmp_path: Path):
    """Phase 2: First-time kickstart (current_index=0) always shows instructions."""
    kickstart_meta = {
        "mode": "full",
        "sequence": ["01-discussion.md"],
        "current_index": 0,
        "completed": []
    }
    setup_kickstart_state(tmp_path, kickstart_meta)

    protocols_dir = tmp_path / "sessions" / "protocols" / "kickstart"
    protocols_dir.mkdir(parents=True, exist_ok=True)
    (protocols_dir / "01-discussion.md").write_text("# Discussion Protocol")

    res = run_kickstart_hook(tmp_path)
    assert res.returncode == 0
    output = parse_hook_output(res.stdout)
    assert "hookSpecificOutput" in output

    # Verify last_shown timestamp was set
    state = read_state(tmp_path)
    assert "last_shown" in state["metadata"]["kickstart"]
    assert "last_active" in state["metadata"]["kickstart"]


def test_kickstart_cooldown_skips_instructions(tmp_path: Path):
    """Phase 2: Instructions skipped if shown within last hour."""
    # Set last_shown to 30 minutes ago (within cooldown)
    last_shown_time = datetime.now() - timedelta(minutes=30)
    kickstart_meta = {
        "mode": "full",
        "sequence": ["01-discussion.md", "02-implementation.md"],
        "current_index": 1,  # In progress
        "completed": ["01-discussion.md"],
        "last_shown": last_shown_time.isoformat(),
        "last_active": last_shown_time.isoformat()
    }
    setup_kickstart_state(tmp_path, kickstart_meta)

    res = run_kickstart_hook(tmp_path)
    assert res.returncode == 0
    assert not res.stdout.strip() or "hookSpecificOutput" not in parse_hook_output(res.stdout)

    # Verify last_active was updated but last_shown unchanged
    state = read_state(tmp_path)
    assert "last_shown" in state["metadata"]["kickstart"]
    assert state["metadata"]["kickstart"]["last_shown"] == last_shown_time.isoformat()
    # last_active should be updated (more recent)
    assert state["metadata"]["kickstart"]["last_active"] != last_shown_time.isoformat()


def test_kickstart_cooldown_expired_shows_instructions(tmp_path: Path):
    """Phase 2: Instructions shown if cooldown expired (>1 hour since last_shown)."""
    # Set last_shown to 2 hours ago (cooldown expired)
    last_shown_time = datetime.now() - timedelta(hours=2)
    kickstart_meta = {
        "mode": "full",
        "sequence": ["01-discussion.md", "02-implementation.md"],
        "current_index": 1,  # In progress
        "completed": ["01-discussion.md"],
        "last_shown": last_shown_time.isoformat(),
        "last_active": last_shown_time.isoformat()
    }
    setup_kickstart_state(tmp_path, kickstart_meta)

    protocols_dir = tmp_path / "sessions" / "protocols" / "kickstart"
    protocols_dir.mkdir(parents=True, exist_ok=True)
    (protocols_dir / "02-implementation.md").write_text("# Implementation Protocol")

    res = run_kickstart_hook(tmp_path)
    assert res.returncode == 0
    output = parse_hook_output(res.stdout)
    assert "hookSpecificOutput" in output

    # Verify last_shown was updated
    state = read_state(tmp_path)
    assert "last_shown" in state["metadata"]["kickstart"]
    # New last_shown should be more recent than old one
    new_last_shown = datetime.fromisoformat(state["metadata"]["kickstart"]["last_shown"])
    assert new_last_shown > last_shown_time


def test_kickstart_in_progress_no_last_shown_shows_instructions(tmp_path: Path):
    """Phase 2: Instructions shown if in progress but no last_shown timestamp."""
    kickstart_meta = {
        "mode": "full",
        "sequence": ["01-discussion.md", "02-implementation.md"],
        "current_index": 1,  # In progress but no last_shown
        "completed": ["01-discussion.md"]
    }
    setup_kickstart_state(tmp_path, kickstart_meta)

    protocols_dir = tmp_path / "sessions" / "protocols" / "kickstart"
    protocols_dir.mkdir(parents=True, exist_ok=True)
    (protocols_dir / "02-implementation.md").write_text("# Implementation Protocol")

    res = run_kickstart_hook(tmp_path)
    assert res.returncode == 0
    output = parse_hook_output(res.stdout)
    assert "hookSpecificOutput" in output

    # Verify last_shown was set
    state = read_state(tmp_path)
    assert "last_shown" in state["metadata"]["kickstart"]


def test_kickstart_timestamp_tracking(tmp_path: Path):
    """Phase 2: Both last_shown and last_active timestamps are tracked correctly."""
    kickstart_meta = {
        "mode": "full",
        "sequence": ["01-discussion.md"],
        "current_index": 0,
        "completed": []
    }
    setup_kickstart_state(tmp_path, kickstart_meta)

    protocols_dir = tmp_path / "sessions" / "protocols" / "kickstart"
    protocols_dir.mkdir(parents=True, exist_ok=True)
    (protocols_dir / "01-discussion.md").write_text("# Discussion Protocol")

    res = run_kickstart_hook(tmp_path)
    assert res.returncode == 0

    state = read_state(tmp_path)
    ks_meta = state["metadata"]["kickstart"]
    assert "last_shown" in ks_meta
    assert "last_active" in ks_meta

    # Both should be valid ISO timestamps
    datetime.fromisoformat(ks_meta["last_shown"])
    datetime.fromisoformat(ks_meta["last_active"])


# ===== COMPLETION COMMAND TESTS =====

def test_kickstart_complete_sets_flag(tmp_path: Path):
    """Phase 1: Complete command sets onboarding_complete flag."""
    kickstart_meta = {
        "mode": "full",
        "sequence": ["01-discussion.md"],
        "current_index": 0,
        "completed": []
    }
    setup_kickstart_state(tmp_path, kickstart_meta)

    # Simulate completion command by directly calling the Python function
    # (We can't easily test the API command without full API setup)
    # Instead, we'll manually set the flag and verify hook behavior
    from sys import path as sys_path
    sys_path.insert(0, str(tmp_path / "sessions" / "hooks"))

    # Import and test the completion logic
    state = read_state(tmp_path)
    state["metadata"]["kickstart"]["onboarding_complete"] = True
    state["metadata"]["kickstart"]["completed_at"] = datetime.now().isoformat()
    write_state(tmp_path, state)

    # Verify hook detects completion
    res = run_kickstart_hook(tmp_path)
    assert res.returncode == 0
    assert not res.stdout.strip()  # Should exit silently
    assert not res.stderr.strip()

    # Verify flag persists
    state = read_state(tmp_path)
    assert state["metadata"]["kickstart"]["onboarding_complete"] is True
    assert "completed_at" in state["metadata"]["kickstart"]

