import json
from pathlib import Path


def test_daic_mode_roundtrip(tmp_path: Path):
    # Create .claude/state
    state_dir = tmp_path / ".claude" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    # Minimal import path shim: run shared_state in tmp cwd
    from cc_sessions.hooks.shared_state import set_daic_mode, check_daic_mode_bool

    cwd = Path.cwd()
    try:
        # Switch to tmp to let project_root resolve
        import os
        os.chdir(tmp_path)
        assert check_daic_mode_bool() is True
        set_daic_mode(False)
        assert check_daic_mode_bool() is False
        set_daic_mode(True)
        assert check_daic_mode_bool() is True
    finally:
        import os
        os.chdir(cwd)


def test_task_state_update(tmp_path: Path):
    state_dir = tmp_path / ".claude" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    from cc_sessions.hooks import shared_state as ss_mod
    ss_mod._shared_state_instance = None
    from cc_sessions.hooks.shared_state import get_shared_state
    from cc_sessions.hooks import shared_state as ss_mod
    ss_mod._shared_state_instance = None
    from cc_sessions.hooks.shared_state import get_shared_state

    cwd = Path.cwd()
    try:
        import os
        os.chdir(tmp_path)
        ss = get_shared_state()
        ss.update_current_task({"task": "t1", "branch": "feature/t1", "services": ["svc"]})
        data = json.loads((state_dir / "current_task.json").read_text())
        assert data["task"] == "t1"
        assert data["branch"] == "feature/t1"
        assert data["services"] == ["svc"]
    finally:
        import os
        os.chdir(cwd)


def test_subagent_context_tracker(tmp_path: Path):
    # Prepare state dir
    state_dir = tmp_path / ".claude" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    # Reset singleton
    from cc_sessions.hooks import shared_state as ss_mod
    ss_mod._shared_state_instance = None
    from cc_sessions.hooks.shared_state import get_shared_state

    cwd = Path.cwd()
    try:
        import os
        os.chdir(tmp_path)
        ss = get_shared_state()
        # Initially inactive
        assert ss.is_subagent_active("s1") is False
        # Enter twice
        ss.enter_subagent("s1", "shared")
        ss.enter_subagent("s1", "shared")
        assert ss.is_subagent_active("s1") is True
        # Exit twice
        ss.exit_subagent("s1", "shared")
        assert ss.is_subagent_active("s1") is True
        ss.exit_subagent("s1", "shared")
        # May still be active due to TTL, but clearing should force inactive
        ss.clear_subagent_state("s1")
        assert ss.is_subagent_active("s1") is False
    finally:
        import os
        os.chdir(cwd)


