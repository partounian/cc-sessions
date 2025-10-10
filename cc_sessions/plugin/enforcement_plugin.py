#!/usr/bin/env python3
"""
Claude Code Enforcement Plugin MVP (shim)

Purpose:
- Provide a lightweight adapter that maps Claude Code plugin events to the
  existing cc-sessions Python hooks without duplicating logic.

Notes:
- This MVP shells out to the current hook entrypoints to preserve behavior.
- It is intentionally best-effort and non-blocking: failures are surfaced in
  return payloads rather than raising hard exceptions.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def _repo_root() -> Path:
    # Resolve cc_sessions/ root from this file location
    return Path(__file__).resolve().parents[1]


def _hook_path(rel: str) -> Path:
    return _repo_root() / "python" / "hooks" / rel


def _run_hook(script_rel: str, payload: Optional[Dict[str, Any]] = None, timeout: int = 10) -> Dict[str, Any]:
    script = _hook_path(script_rel)
    if not script.exists():
        sys.stderr.write(f"[enforcement_plugin] missing hook: {script}\n")
        return {
            "ok": False,
            "exit_code": None,
            "stderr": f"hook not found: {script}",
            "stdout": "",
        }

    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            input=(json.dumps(payload) if payload is not None else None),
            text=True,
            capture_output=True,
            cwd=str(_repo_root().parent),  # project root (contains .claude)
            timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stderr": proc.stderr or "",
            "stdout": proc.stdout or "",
        }
    except Exception as exc:
        # Log and return structured error rather than silencing; include type info
        err_type = type(exc).__name__
        try:
            sys.stderr.write(f"[enforcement_plugin] hook_exec_error({err_type}): {exc}\n")
        except Exception as log_exc:
            # Last-resort: include error in return; avoid silent swallow
            return {
                "ok": False,
                "exit_code": None,
                "stderr": f"stderr_write_error({type(log_exc).__name__}): {log_exc}",
                "stdout": "",
            }
        return {
            "ok": False,
            "exit_code": None,
            "stderr": f"hook_exec_error({err_type}): {exc}",
            "stdout": "",
        }


class EnforcementPlugin:
    """Event adapters for Claude Code plugin runtime.

    Methods return a normalized dict with keys: ok, exit_code, stdout, stderr,
    and optionally additional parsed fields where applicable.
    """

    def on_session_start(self) -> Dict[str, Any]:
        # Maps to SessionStart hook
        return _run_hook("session_start.py", payload={})

    def on_user_message(self, prompt: str, transcript_path: str = "") -> Dict[str, Any]:
        # Maps to UserPromptSubmit hook
        payload = {"prompt": prompt, "transcript_path": transcript_path}
        result = _run_hook("user_messages.py", payload=payload)
        # Try to parse structured additionalContext if present
        try:
            if result.get("stdout"):
                data = json.loads(result["stdout"])  # { hookSpecificOutput: { additionalContext } }
                result["additionalContext"] = (
                    (data.get("hookSpecificOutput") or {}).get("additionalContext")
                )
        except Exception as parse_exc:
            # Surface parse error in stderr field to avoid silent swallow
            result["stderr"] = (result.get("stderr") or "") + f"\nplugin_parse_error({type(parse_exc).__name__}): {parse_exc}"
        return result

    def on_tool_use(self, tool_name: str, tool_input: Dict[str, Any], cwd: str = "") -> Dict[str, Any]:
        # Maps to PreToolUse enforcement
        payload = {"tool_name": tool_name, "tool_input": tool_input, "cwd": cwd}
        return _run_hook("sessions_enforce.py", payload=payload)

    def on_post_tool_use(self, tool_name: str, tool_input: Dict[str, Any], cwd: str = "") -> Dict[str, Any]:
        # Maps to PostToolUse
        payload = {"tool_name": tool_name, "tool_input": tool_input, "cwd": cwd}
        return _run_hook("post_tool_use.py", payload=payload)

    def on_session_end(self) -> Dict[str, Any]:
        # No dedicated session_end hook yet; return success to avoid blocking
        return {"ok": True, "exit_code": 0, "stdout": "", "stderr": ""}


__all__ = ["EnforcementPlugin"]


