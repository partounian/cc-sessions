from pathlib import Path
import json
import ast


def _load_function_from_user_messages(func_name: str):
    """Safely load a single function object from user_messages.py without importing module-level side effects."""
    hooks_dir = Path(__file__).resolve().parents[1] / "cc_sessions" / "python" / "hooks"
    src_path = hooks_dir / "user_messages.py"
    source = src_path.read_text(encoding="utf-8", errors="backslashreplace")
    module = ast.parse(source)
    func_node = None
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            func_node = node
            break
    assert func_node is not None, f"Function {func_name} not found"
    # Build a new module containing only the function
    new_mod = ast.Module(body=[func_node], type_ignores=[])
    code = compile(new_mod, filename=str(src_path), mode="exec")
    ns = {"json": json}
    exec(code, ns)
    return ns[func_name]


def write_transcript(tmp: Path, entries: list[dict]) -> Path:
    p = tmp / "transcript.jsonl"
    with p.open("w", encoding="utf-8", errors="backslashreplace") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    return p


def test_transcript_usage_parsing(monkeypatch, tmp_path: Path):
    # Import function under test
    get_context_length_from_transcript = _load_function_from_user_messages("get_context_length_from_transcript")

    entries = [
        {"timestamp": "2025-01-01T00:00:00", "isSidechain": False, "message": {"usage": {"input_tokens": 100, "cache_read_input_tokens": 50, "cache_creation_input_tokens": 0}}},
        {"timestamp": "2025-01-01T00:00:01", "isSidechain": False, "message": {"usage": {"input_tokens": 200, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}},
    ]
    p = write_transcript(tmp_path, entries)
    assert get_context_length_from_transcript(str(p)) == 200


def test_heuristic_estimation(monkeypatch, tmp_path: Path):
    # Use internal fallback helpers by importing module and calling private function
    _estimate_tokens_from_text = _load_function_from_user_messages("_estimate_tokens_from_text")

    est = _estimate_tokens_from_text("a" * 400)
    assert 90 <= est <= 110  # ~100 tokens


