import json


def test_enforcement_plugin_smoke(monkeypatch):
    from cc_sessions.plugin import enforcement_plugin as ep

    def _ok(*_args, **_kwargs):
        return {"ok": True, "exit_code": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(ep, "_run_hook", _ok)

    plugin = ep.EnforcementPlugin()

    assert plugin.on_session_start()["ok"] is True
    assert plugin.on_user_message("hello world")["ok"] is True
    assert plugin.on_tool_use("Bash", {"command": "ls"})["ok"] is True
    assert plugin.on_post_tool_use("Write", {"file_path": "x.py"})["ok"] is True
    assert plugin.on_session_end()["ok"] is True


