#!/usr/bin/env python3
"""
Basic integration tests for cc-sessions consolidated hooks
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def test_workflow_manager():
    """Test workflow manager hook with safe input"""
    print("Testing workflow-manager.py...")

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
            print("✅ workflow-manager.py: PASS")
            return True
        else:
            print(f"❌ workflow-manager.py: FAIL (exit code {result.returncode})")
            print(f"stderr: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ workflow-manager.py: ERROR - {e}")
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
    print("Testing context-manager.py...")

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
            print("✅ context-manager.py: PASS")
            return True
        else:
            print(f"❌ context-manager.py: FAIL (exit code {result.returncode})")
            print(f"stderr: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ context-manager.py: ERROR - {e}")
        return False


def test_session_lifecycle():
    """Test session lifecycle hook"""
    print("Testing session-lifecycle.py...")

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
            print("✅ session-lifecycle.py: PASS")
            return True
        else:
            print(f"❌ session-lifecycle.py: FAIL (exit code {result.returncode})")
            print(f"stderr: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ session-lifecycle.py: ERROR - {e}")
        return False


def main():
    """Run all hook tests"""
    print("🧪 Running cc-sessions hook integration tests...\n")

    tests = [
        test_workflow_manager,
        test_session_start,
        test_context_manager,
        test_session_lifecycle
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
