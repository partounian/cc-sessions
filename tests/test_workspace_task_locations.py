import os
import json
import subprocess
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_session_start(tmp: Path, env=None) -> subprocess.CompletedProcess:
    script = repo_root() / "cc_sessions" / "python" / "hooks" / "session_start.py"
    return subprocess.run(["python3", str(script)], text=True, capture_output=True, cwd=str(tmp), timeout=10, env=env)


def test_workspace_root_detection_env_override(tmp_path: Path):
    # Layout: /tmp/ws/{project}/
    ws = tmp_path / "ws"
    proj = ws / "proj"
    (proj / ".claude").mkdir(parents=True, exist_ok=True)
    (proj / "sessions" / "tasks").mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["CLAUDE_WORKSPACE_ROOT"] = str(ws)

    # Running session_start shouldn't error; it will use ws as workspace
    res = run_session_start(proj, env=env)
    assert res.returncode in (0, 2)


def test_tasks_dir_is_under_workspace_root(tmp_path: Path):
    # Create workspace indicators to detect ws
    ws = tmp_path / "ws"
    proj = ws / "proj"
    (proj / ".claude").mkdir(parents=True, exist_ok=True)
    (proj / "sessions").mkdir(parents=True, exist_ok=True)
    (ws / ".vscode").mkdir(parents=True, exist_ok=True)

    # Import shared_state in a subprocess to read constants
    script = repo_root() / "cc_sessions" / "python" / "hooks" / "shared_state.py"
    code = (
        "import json, os; from pathlib import Path; "
        "import sys; sys.path.insert(0, str(Path('cc_sessions/python/hooks').resolve().parents[2] / 'cc_sessions' / 'python' / 'hooks')); "
        "from shared_state import PROJECT_ROOT, WORKSPACE_ROOT, TASKS_DIR; "
        "print(json.dumps({'project': str(PROJECT_ROOT), 'workspace': str(WORKSPACE_ROOT), 'tasks': str(TASKS_DIR)}))"
    )

    res = subprocess.run(["python3", "-c", code], capture_output=True, text=True, cwd=str(tmp_path), timeout=10)
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    # Ensure tasks dir points under workspace root, not project root
    assert data["tasks"].startswith(str(ws)), data


