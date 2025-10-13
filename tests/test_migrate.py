import json
import os
import subprocess
from pathlib import Path


def run_migrate(tmp: Path, args=None):
    exe = Path(__file__).resolve().parents[1] / "cc_sessions" / "python" / "migrate.py"
    cmd = ["python3", str(exe)]
    if args:
        cmd.extend(args)
    return subprocess.run(cmd, cwd=str(tmp), capture_output=True, text=True, timeout=20)


def write_legacy(tmp: Path):
    (tmp / ".claude").mkdir(parents=True, exist_ok=True)
    (tmp / "sessions").mkdir(parents=True, exist_ok=True)
    # legacy settings pointing to .claude/hooks
    settings = {
        "hooks": {
            "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/user_messages.py"}]}]
        }
    }
    (tmp / ".claude" / "settings.json").write_text(json.dumps(settings))
    # legacy flat config
    cfg = {
        "developer_name": "Dev",
        "trigger_phrases": ["go ahead"],
        "blocked_tools": ["Edit", "Write"],
        "branch_enforcement": {"enabled": True},
        "task_detection": {"enabled": False},
        "workspace": {"include_repositories": ["foo"], "exclude_patterns": []},
    }
    (tmp / "sessions" / "sessions-config.json").write_text(json.dumps(cfg))


def test_migrate_dry_run(tmp_path: Path):
    write_legacy(tmp_path)
    res = run_migrate(tmp_path, ["--dry-run"])
    assert res.returncode == 0
    out = json.loads(res.stdout)
    assert out["legacy_detected"] is True
    assert out.get("would_migrate_config") is True
    assert out.get("would_migrate_settings") is True


def test_migrate_exec(tmp_path: Path):
    write_legacy(tmp_path)
    res = run_migrate(tmp_path, [])
    assert res.returncode == 0
    # settings migrated
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    assert settings.get("hooks")
    assert ".claude/hooks/" not in json.dumps(settings.get("hooks"))
    # config migrated
    cfg = json.loads((tmp_path / "sessions" / "sessions-config.json").read_text())
    assert "git_preferences" in cfg and "environment" in cfg and "blocked_actions" in cfg and "features" in cfg
    # report exists
    reports = list((tmp_path / ".claude").glob("migration-report-*.json"))
    assert reports


