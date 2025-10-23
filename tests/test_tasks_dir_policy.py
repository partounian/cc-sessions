import json
import subprocess
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_task_commands_use_workspace_tasks_dir(tmp_path: Path):
    # Workspace ws with indicator; project under ws
    ws = tmp_path / "ws"
    proj = ws / "proj"
    (proj / ".claude").mkdir(parents=True, exist_ok=True)
    (proj / "sessions" / "protocols").mkdir(parents=True, exist_ok=True)
    (ws / ".vscode").mkdir(parents=True, exist_ok=True)

    # Create a task under workspace tasks dir
    tasks_dir = ws / "sessions" / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / "h-sample.md").write_text("""---
status: pending
---
Body
""")

    # Run a small snippet to import and list indexes dir path used
    code = (
        "from pathlib import Path; import json; import os; "
        "from hooks import shared_state as ss; "
        "from api import task_commands as tc; "
        "print(json.dumps({'tasks': str(ss.TASKS_DIR), 'idx': str((ss.TASKS_DIR / 'indexes'))}))"
    )

    res = subprocess.run(["python3", "-c", code], capture_output=True, text=True, cwd=str((repo_root() / "cc_sessions" / "python")) , timeout=10)
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["tasks"].startswith(str(ws))

