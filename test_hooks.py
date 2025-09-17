#!/usr/bin/env python3
"""
Basic integration tests for cc-sessions consolidated hooks
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def _make_temp_transcript(tmpdir: Path, include_prework: bool = True) -> Path:
    transcript = []
    if include_prework:
        # Pre-work entries before first edit
        transcript.append({
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "discussion"}
                ]
            }
        })
        transcript.append({
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "name": "Edit"}
                ]
            }
        })
    # Post-work entries including Task call
    transcript.append({
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {"type": "text", "text": "please run task"}
            ]
        }
    })
    transcript.append({
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "name": "Task", "input": {"subagent_type": "shared"}}
            ]
        }
    })

    path = tmpdir / "transcript.jsonl"
    with path.open("w") as f:
        for item in transcript:
            f.write(json.dumps(item) + "\n")
    return path


def test_task_transcript_link():
    """Test task_transcript_link.py with a temp transcript"""
    print("Testing task_transcript_link.py...")

    tmpdir = Path(tempfile.mkdtemp())
    transcript_path = _make_temp_transcript(tmpdir)

    test_input = {
        "tool_name": "Task",
        "transcript_path": str(transcript_path)
    }

    try:
        result = subprocess.run(
            [sys.executable, "cc_sessions/hooks/task_transcript_link.py"],
            input=json.dumps(test_input),
            text=True,
            capture_output=True,
            timeout=15
        )

        if result.returncode != 0:
            print(f"❌ task_transcript_link.py: FAIL (exit code {result.returncode})")
            print(f"stderr: {result.stderr}")
            return False

        # Verify chunk files created under project .claude/state/shared
        # Determine project root similar to hook's behavior
        from cc_sessions.hooks.shared_state import get_project_root
        project_root = get_project_root()
        batch_dir = project_root / ".claude" / "state" / "shared"
        files = list(batch_dir.glob("current_transcript_*.json"))
        if files:
            print("✅ task_transcript_link.py: PASS")
            return True
        else:
            print("❌ task_transcript_link.py: FAIL (no transcript chunks found)")
            return False

    except Exception as e:
        print(f"❌ task_transcript_link.py: ERROR - {e}")
        return False

def test_workflow_manager():
    """Test workflow manager hook with safe input"""
    print("Testing workflow_manager.py...")

    # Test with safe bash command
    test_input = {
        "tool_name": "Bash",
        "tool_input": {"command": "echo 'test'"}
    }

    try:
        result = subprocess.run(
            [sys.executable, "cc_sessions/hooks/workflow_manager.py"],
            input=json.dumps(test_input),
            text=True,
            capture_output=True,
            timeout=10
        )

        if result.returncode == 0:
            print("✅ workflow_manager.py: PASS")
            return True
        else:
            print(f"❌ workflow_manager.py: FAIL (exit code {result.returncode})")
            print(f"stderr: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ workflow_manager.py: ERROR - {e}")
        return False


def test_session_start():
    """Test session start hook"""
    print("Testing session_start.py...")

    try:
        result = subprocess.run(
            [sys.executable, "cc_sessions/hooks/session_start.py"],
            text=True,
            capture_output=True,
            timeout=15
        )

        if result.returncode == 0:
            print("✅ session_start.py: PASS")
            return True
        else:
            print(f"❌ session_start.py: FAIL (exit code {result.returncode})")
            print(f"stderr: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ session_start.py: ERROR - {e}")
        return False


def test_context_manager():
    """Test context manager hook"""
    print("Testing context_manager.py...")

    test_input = {
        "hookEventName": "PreCompact"
    }

    try:
        result = subprocess.run(
            [sys.executable, "cc_sessions/hooks/context_manager.py"],
            input=json.dumps(test_input),
            text=True,
            capture_output=True,
            timeout=10
        )

        if result.returncode == 0:
            print("✅ context_manager.py: PASS")
            return True
        else:
            print(f"❌ context_manager.py: FAIL (exit code {result.returncode})")
            print(f"stderr: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ context_manager.py: ERROR - {e}")
        return False


def test_session_lifecycle():
    """Test session lifecycle hook"""
    print("Testing session_lifecycle.py...")

    test_input = {
        "hookEventName": "Stop"
    }

    try:
        result = subprocess.run(
            [sys.executable, "cc_sessions/hooks/session_lifecycle.py"],
            input=json.dumps(test_input),
            text=True,
            capture_output=True,
            timeout=10
        )

        if result.returncode == 0:
            print("✅ session_lifecycle.py: PASS")
            return True
        else:
            print(f"❌ session_lifecycle.py: FAIL (exit code {result.returncode})")
            print(f"stderr: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ session_lifecycle.py: ERROR - {e}")
        return False


def main():
    """Run all hook tests"""
    print("🧪 Running cc-sessions hook integration tests...\n")

    tests = [
        test_workflow_manager,
        test_session_start,
        test_context_manager,
        test_session_lifecycle,
        test_task_transcript_link
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print(f"📊 Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All tests passed! cc-sessions is ready for deployment.")
        return 0
    else:
        print("⚠️  Some tests failed. Review issues before deployment.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
