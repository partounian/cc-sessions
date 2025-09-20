import json
import os
from pathlib import Path


def write_sessions_config(root: Path, include: list[str]) -> None:
    sessions_dir = root / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    cfg = {
        "developer_name": "Tester",
        "workspace": {
            "include_repositories": include,
            "exclude_patterns": []
        }
    }
    (sessions_dir / "sessions-config.json").write_text(json.dumps(cfg, indent=2))


def touch_git_repo(path: Path) -> None:
    (path / ".git").mkdir(parents=True, exist_ok=True)


def test_workspace_context_respects_include_and_prunes_multi_repo_config(tmp_path: Path):
    # Arrange: create workspace and repos
    (tmp_path / ".claude" / "state").mkdir(parents=True, exist_ok=True)
    repo_a = tmp_path / "repoA"
    repo_b = tmp_path / "repoB"
    repo_c = tmp_path / "repoC"  # should be ignored
    for p in (repo_a, repo_b, repo_c):
        p.mkdir(parents=True)
        touch_git_repo(p)

    # sessions-config includes only A and B by name
    write_sessions_config(tmp_path, ["repoA", "repoB"])

    # Pre-populate multi_repo_config with an extra repo to verify pruning
    workspace_state = tmp_path / ".claude" / "workspace_state"
    workspace_state.mkdir(parents=True, exist_ok=True)
    pre_cfg = {
        "workspace_name": "Test",
        "repositories": {
            str(repo_c): {
                "name": repo_c.name,
                "path": str(repo_c),
                "type": "git",
                "description": "pre-existing",
                "last_accessed": None,
                "active": True,
            }
        },
        "shared_agents": [],
        "cross_repo_tasks": True,
        "context_sharing": True,
        "git_integration": True,
        "excluded_directories": [".git"],
        "included_file_types": [".py"],
        "workspace_agents": {},
    }
    (workspace_state / "multi_repo_config.json").write_text(json.dumps(pre_cfg, indent=2))

    # Act: run setup
    cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        from cc_sessions.hooks import shared_state as ss_mod
        ss_mod._shared_state_instance = None
        from cc_sessions.hooks.shared_state import get_shared_state

        ss = get_shared_state()
        ss.setup_workspace_awareness()
    finally:
        os.chdir(cwd)

    # Assert: workspace_context.json is not persisted anymore
    wc_path = workspace_state / "workspace_context.json"
    assert not wc_path.exists()

    # Assert: in-memory workspace context aligns with included repos
    from cc_sessions.hooks.shared_state import get_shared_state
    ctx = get_shared_state().get_workspace_context()
    ctx_repo_keys = set(ctx.get("repositories", {}).keys())
    assert ctx_repo_keys == {str(repo_a), str(repo_b)}
    assert ctx.get("repository_count") == 2

    # Assert: multi_repo_config has only A and B entries after pruning
    mrc = json.loads((workspace_state / "multi_repo_config.json").read_text())
    saved_repos = set(mrc.get("repositories", {}).keys())
    assert saved_repos == {str(repo_a), str(repo_b)}


