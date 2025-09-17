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



