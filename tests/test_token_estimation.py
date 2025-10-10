from pathlib import Path
import json


def write_transcript(tmp: Path, entries: list[dict]) -> Path:
    p = tmp / "transcript.jsonl"
    with p.open("w", encoding="utf-8", errors="backslashreplace") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    return p


def test_transcript_usage_parsing(monkeypatch, tmp_path: Path):
    # Import function under test
    from cc_sessions.python.hooks.user_messages import get_context_length_from_transcript

    entries = [
        {"timestamp": "2025-01-01T00:00:00", "isSidechain": False, "message": {"usage": {"input_tokens": 100, "cache_read_input_tokens": 50, "cache_creation_input_tokens": 0}}},
        {"timestamp": "2025-01-01T00:00:01", "isSidechain": False, "message": {"usage": {"input_tokens": 200, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}},
    ]
    p = write_transcript(tmp_path, entries)
    assert get_context_length_from_transcript(str(p)) == 200


def test_heuristic_estimation(monkeypatch, tmp_path: Path):
    # Use internal fallback helpers by importing module and calling private function
    import cc_sessions.python.hooks.user_messages as um

    est = um._estimate_tokens_from_text("a" * 400)
    assert 90 <= est <= 110  # ~100 tokens


