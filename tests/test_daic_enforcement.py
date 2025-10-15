import json
import subprocess
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_enforce(tmp: Path, payload: dict) -> subprocess.CompletedProcess:
    script = repo_root() / "cc_sessions" / "python" / "hooks" / "sessions_enforce.py"
    return subprocess.run(["python3", str(script)], input=json.dumps(payload), text=True, capture_output=True, cwd=str(tmp), timeout=10)


def setup_discussion(tmp: Path) -> None:
    (tmp / ".claude").mkdir(parents=True, exist_ok=True)
    (tmp / "sessions").mkdir(parents=True, exist_ok=True)
    state = {
        "model": "opus",
        "mode": "discussion",
        "current_task": {"name": "t", "branch": "feature/x", "file": None, "submodules": []},
        "todos": {"active": []},
        "flags": {"bypass_mode": False},
    }
    (tmp / "sessions" / "sessions-state.json").write_text(json.dumps(state))


def test_block_write_tool_in_discussion(tmp_path: Path):
    setup_discussion(tmp_path)
    payload = {"tool_name": "Write", "tool_input": {"file_path": "x.py"}}
    res = run_enforce(tmp_path, payload)
    assert res.returncode == 2
    assert "DAIC: Tool Blocked" in (res.stderr or "")


def test_allow_readonly_bash_in_discussion(tmp_path: Path):
    setup_discussion(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "ls"}}
    res = run_enforce(tmp_path, payload)
    assert res.returncode == 0


# Comprehensive DAIC enforcement matrix tests
def test_allow_cat_in_discussion(tmp_path: Path):
    """cat README.md → allowed (exit 0)"""
    setup_discussion(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "cat README.md"}}
    res = run_enforce(tmp_path, payload)
    assert res.returncode == 0


def test_block_sed_inplace_in_discussion(tmp_path: Path):
    """sed -i 's/a/b/' file → blocked (exit 2)"""
    setup_discussion(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "sed -i 's/a/b/' file.txt"}}
    res = run_enforce(tmp_path, payload)
    assert res.returncode == 2
    assert "write-like" in (res.stderr or "").lower()


def test_block_awk_output_redirect_in_discussion(tmp_path: Path):
    """awk '{print > "out"}' file → blocked"""
    setup_discussion(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "awk '{print > \"out\"}' input.txt"}}
    res = run_enforce(tmp_path, payload)
    assert res.returncode == 2


def test_block_find_delete_in_discussion(tmp_path: Path):
    """find . -delete → blocked"""
    setup_discussion(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "find . -name '*.tmp' -delete"}}
    res = run_enforce(tmp_path, payload)
    assert res.returncode == 2


def test_block_find_exec_rm_in_discussion(tmp_path: Path):
    """find . -exec rm {} + → blocked"""
    setup_discussion(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "find . -name '*.tmp' -exec rm {} +"}}
    res = run_enforce(tmp_path, payload)
    assert res.returncode == 2


def test_block_xargs_rm_in_discussion(tmp_path: Path):
    """printf "a\n" | xargs rm → blocked"""
    setup_discussion(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "printf 'file1\\nfile2\\n' | xargs rm"}}
    res = run_enforce(tmp_path, payload)
    assert res.returncode == 2


def test_allow_readonly_compound_in_discussion(tmp_path: Path):
    """cat file | grep pattern | sort → allowed"""
    setup_discussion(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "cat file.txt | grep pattern | sort"}}
    res = run_enforce(tmp_path, payload)
    assert res.returncode == 0


def test_block_write_after_pipe_in_discussion(tmp_path: Path):
    """cat file | xargs rm → blocked"""
    setup_discussion(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "cat filelist.txt | xargs rm"}}
    res = run_enforce(tmp_path, payload)
    assert res.returncode == 2


def test_block_echo_redirect_in_discussion(tmp_path: Path):
    """echo "text" > file → blocked"""
    setup_discussion(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "echo 'hello' > output.txt"}}
    res = run_enforce(tmp_path, payload)
    assert res.returncode == 2


def test_allow_echo_stdout_in_discussion(tmp_path: Path):
    """echo "text" without redirect → allowed"""
    setup_discussion(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "echo 'hello world'"}}
    res = run_enforce(tmp_path, payload)
    assert res.returncode == 0


def test_block_cp_in_discussion(tmp_path: Path):
    """cp source dest → blocked"""
    setup_discussion(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "cp file1.txt file2.txt"}}
    res = run_enforce(tmp_path, payload)
    assert res.returncode == 2


def test_block_mv_in_discussion(tmp_path: Path):
    """mv source dest → blocked"""
    setup_discussion(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "mv file1.txt file2.txt"}}
    res = run_enforce(tmp_path, payload)
    assert res.returncode == 2


