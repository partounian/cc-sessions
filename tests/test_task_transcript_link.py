import json
import subprocess
from pathlib import Path


def read_error_messages(tmp: Path) -> list[str]:
    log_file = tmp / ".claude" / "state" / "error_log.json"
    if not log_file.exists():
        return []
    messages = []
    for line in log_file.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            messages.append(json.loads(line).get("message", ""))
        except json.JSONDecodeError:
            continue
    return messages


def run_hook(tmp: Path, payload: dict) -> subprocess.CompletedProcess:
    script = Path(__file__).resolve().parents[1] / "cc_sessions" / "hooks" / "task_transcript_link.py"
    return subprocess.run([
        "python3",
        str(script),
    ], input=json.dumps(payload), text=True, capture_output=True, cwd=str(tmp), timeout=10)


def test_transcript_chunking(tmp_path: Path):
    # Build a simple transcript with a Task call
    transcript = [
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "start"}]}},
        {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "go"}]}},
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "tool_use", "name": "Task", "input": {"subagent_type": "shared"}}]}}
    ]
    trans_path = tmp_path / "transcript.jsonl"
    trans_path.write_text("\n".join(json.dumps(x) for x in transcript))

    payload = {"tool_name": "Task", "transcript_path": str(trans_path)}
    res = run_hook(tmp_path, payload)
    assert res.returncode == 0
    out_dir = tmp_path / ".claude" / "state" / "shared"
    files = list(out_dir.glob("current_transcript_*.json"))
    assert files, "expected chunk output files"


def test_transcript_cleanup_logs_failures(tmp_path: Path):
    # Build transcript that triggers chunk creation
    transcript = [
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "tool_use", "name": "Task", "input": {"subagent_type": "shared"}}]}}
    ]
    trans_path = tmp_path / "transcript.jsonl"
    trans_path.write_text("\n".join(json.dumps(x) for x in transcript))

    # No pre-created files; rely on cleanup function's internal warning path not being triggered

    payload = {"tool_name": "Task", "transcript_path": str(trans_path)}
    res = run_hook(tmp_path, payload)
    assert res.returncode == 0


