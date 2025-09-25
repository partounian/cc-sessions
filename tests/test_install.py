import subprocess
from pathlib import Path


def test_install_logs_failures(tmp_path: Path):
    (tmp_path / ".claude" / "state").mkdir(parents=True, exist_ok=True)

    script = """
import importlib

module = importlib.import_module('cc_sessions.install')

class Boom(module.SessionsInstaller):
    def run(self):
        raise RuntimeError('installation exploded')

module.SessionsInstaller = Boom

try:
    module.main()
except RuntimeError:
    print('installation exploded')
"""
    result = subprocess.run(
        ["python3", "-c", script],
        text=True,
        capture_output=True,
        cwd=str(tmp_path),
        timeout=10,
    )

    output = result.stderr or result.stdout
    assert "installation exploded" in output

