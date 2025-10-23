"""Test icon_style configuration migration and statusline output."""
import json
import subprocess
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_config_migration_nerd_fonts_true(tmp_path: Path):
    """Test migration: use_nerd_fonts=True → icon_style='nerd-fonts'"""
    (tmp_path / "sessions").mkdir(parents=True, exist_ok=True)
    old_config = {
        "environment": {"developer_name": "developer", "os": "linux", "shell": "bash"},
        "features": {"use_nerd_fonts": True},
        "trigger_phrases": {},
        "blocked_actions": {},
        "git_preferences": {}
    }
    (tmp_path / "sessions" / "sessions-config.json").write_text(json.dumps(old_config))

    # Import and load config
    import sys
    sys.path.insert(0, str(repo_root() / "cc_sessions" / "python" / "hooks"))
    from shared_state import load_config

    config = load_config(project_root=tmp_path)
    assert config.features.icon_style == "nerd-fonts"


def test_config_migration_nerd_fonts_false(tmp_path: Path):
    """Test migration: use_nerd_fonts=False → icon_style='ascii'"""
    (tmp_path / "sessions").mkdir(parents=True, exist_ok=True)
    old_config = {
        "environment": {"developer_name": "developer", "os": "linux", "shell": "bash"},
        "features": {"use_nerd_fonts": False},
        "trigger_phrases": {},
        "blocked_actions": {},
        "git_preferences": {}
    }
    (tmp_path / "sessions" / "sessions-config.json").write_text(json.dumps(old_config))

    # Import and load config
    import sys
    sys.path.insert(0, str(repo_root() / "cc_sessions" / "python" / "hooks"))
    from shared_state import load_config

    config = load_config(project_root=tmp_path)
    assert config.features.icon_style == "ascii"


def test_config_new_icon_style_field(tmp_path: Path):
    """Test new icon_style field works correctly"""
    (tmp_path / "sessions").mkdir(parents=True, exist_ok=True)
    new_config = {
        "environment": {"developer_name": "developer", "os": "linux", "shell": "bash"},
        "features": {"icon_style": "unicode"},
        "trigger_phrases": {},
        "blocked_actions": {},
        "git_preferences": {}
    }
    (tmp_path / "sessions" / "sessions-config.json").write_text(json.dumps(new_config))

    # Import and load config
    import sys
    sys.path.insert(0, str(repo_root() / "cc_sessions" / "python" / "hooks"))
    from shared_state import load_config

    config = load_config(project_root=tmp_path)
    assert config.features.icon_style == "unicode"


def test_statusline_nerd_fonts_icons(tmp_path: Path):
    """Test statusline output with nerd-fonts icon_style"""
    (tmp_path / ".claude").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sessions").mkdir(parents=True, exist_ok=True)

    config = {
        "environment": {"developer_name": "developer", "os": "linux", "shell": "bash"},
        "features": {"icon_style": "nerd-fonts"},
        "trigger_phrases": {},
        "blocked_actions": {},
        "git_preferences": {}
    }
    (tmp_path / "sessions" / "sessions-config.json").write_text(json.dumps(config))

    state = {
        "model": "opus",
        "mode": "discussion",
        "current_task": None,
        "todos": {"active": []},
        "flags": {}
    }
    (tmp_path / "sessions" / "sessions-state.json").write_text(json.dumps(state))

    script = repo_root() / "cc_sessions" / "python" / "statusline.py"
    result = subprocess.run(
        ["python3", str(script)],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=10
    )

    assert result.returncode == 0
    output = result.stdout
    # Should contain nerd font icons
    assert "󱃖" in output or "󰭹" in output  # Context or discussion mode icon


def test_statusline_ascii_no_icons(tmp_path: Path):
    """Test statusline output with ascii icon_style"""
    (tmp_path / ".claude").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sessions").mkdir(parents=True, exist_ok=True)

    config = {
        "environment": {"developer_name": "developer", "os": "linux", "shell": "bash"},
        "features": {"icon_style": "ascii"},
        "trigger_phrases": {},
        "blocked_actions": {},
        "git_preferences": {}
    }
    (tmp_path / "sessions" / "sessions-config.json").write_text(json.dumps(config))

    state = {
        "model": "opus",
        "mode": "discussion",
        "current_task": None,
        "todos": {"active": []},
        "flags": {}
    }
    (tmp_path / "sessions" / "sessions-state.json").write_text(json.dumps(state))

    script = repo_root() / "cc_sessions" / "python" / "statusline.py"
    result = subprocess.run(
        ["python3", str(script)],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=10
    )

    assert result.returncode == 0
    output = result.stdout
    # Should NOT contain nerd font icons
    assert "󱃖" not in output
    assert "󰭹" not in output
    assert "󰷫" not in output


def test_statusline_unicode_icons(tmp_path: Path):
    """Test statusline output with unicode icon_style"""
    (tmp_path / ".claude").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sessions").mkdir(parents=True, exist_ok=True)

    config = {
        "environment": {"developer_name": "developer", "os": "linux", "shell": "bash"},
        "features": {"icon_style": "unicode"},
        "trigger_phrases": {},
        "blocked_actions": {},
        "git_preferences": {}
    }
    (tmp_path / "sessions" / "sessions-config.json").write_text(json.dumps(config))

    state = {
        "model": "opus",
        "mode": "discussion",
        "current_task": None,
        "todos": {"active": []},
        "flags": {}
    }
    (tmp_path / "sessions" / "sessions-state.json").write_text(json.dumps(state))

    script = repo_root() / "cc_sessions" / "python" / "statusline.py"
    result = subprocess.run(
        ["python3", str(script)],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=10
    )

    assert result.returncode == 0
    output = result.stdout
    # Should contain unicode emoji icons
    assert "📊" in output or "💬" in output or "🔨" in output

