#!/usr/bin/env python3
"""Pre-tool-use hook to chunk transcript for subagents when Task tool is called."""
from collections import deque
from pathlib import Path
try:
    import tiktoken
except Exception:
    tiktoken = None
import json
import sys
import os

# Load input from stdin
try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
    sys.exit(1)

# Check if this is a Task tool call
tool_name = input_data.get("tool_name", "")
if tool_name != "Task":
    sys.exit(0)

# Get the transcript path from the input data
transcript_path = input_data.get("transcript_path", "")
if not transcript_path:
    sys.exit(0)

# Get the transcript into memory
with open(transcript_path, 'r') as f:
    transcript = [json.loads(line) for line in f]

# Helpers to simplify nested conditions
def _is_pre_work_entry(entry: dict) -> bool:
    message = entry.get('message') or {}
    content = message.get('content')
    if not isinstance(content, list):
        return False
    return any(
        block.get('type') == 'tool_use' and block.get('name') in ['Edit', 'MultiEdit', 'Write']
        for block in content
    )


# Remove any pre-work transcript entries
start_index = next((i for i, e in enumerate(transcript) if _is_pre_work_entry(e)), -1)
if start_index != -1:
    transcript = transcript[start_index + 1:]

# Clean the transcript
clean_transcript = deque()
for entry in transcript:
    message = entry.get('message')
    message_type = entry.get('type')

    if message and message_type in ['user', 'assistant']:
        content = message.get('content')
        role = message.get('role')
        clean_entry = {
            'role': role,
            'content': content
        }
        clean_transcript.append(clean_entry)

def _extract_subagent_type(task_call: dict) -> str:
    content = task_call.get('content', [])
    return next(
        (
            (block.get('input') or {}).get('subagent_type', 'shared')
            for block in content
            if block.get('type') == 'tool_use' and block.get('name') == 'Task'
        ),
        'shared'
    )


# Route the transcript
if not clean_transcript:
    sys.exit(0)

task_call = clean_transcript[-1]
subagent_type = _extract_subagent_type(task_call)

# Get project root using shared_state
from shared_state import get_project_root, get_shared_state
PROJECT_ROOT = get_project_root()


def cleanup_old_transcript_chunks(batch_dir: Path) -> None:
    """Simple cleanup: keep only last 20 chunks per subagent type"""
    if not batch_dir.exists():
        return

    chunk_files = sorted(batch_dir.glob("current_transcript_*.json"),
                        key=lambda f: f.stat().st_mtime, reverse=True)

    # Keep only last 20 chunks, delete the rest
    for old_chunk in chunk_files[20:]:
        try:
            old_chunk.unlink()
        except Exception:
            pass  # Silent failure, don't break the workflow

# Clear the current transcript directory
BATCH_DIR = PROJECT_ROOT / '.claude' / 'state' / subagent_type
BATCH_DIR.mkdir(parents=True, exist_ok=True)

# Clean up old transcript chunks before creating new ones
cleanup_old_transcript_chunks(BATCH_DIR)

target_dir = BATCH_DIR
for item in target_dir.iterdir():
    if item.is_file():
        item.unlink()

# Record entering subagent context with session id for robust tracking
session_id = input_data.get('session_id') or 'default'
try:
    get_shared_state().enter_subagent(session_id, subagent_type)
except Exception:
    pass

# Set up token counting
if tiktoken is not None:
    enc = tiktoken.get_encoding('cl100k_base')
    def n_tokens(s: str) -> int:
        return len(enc.encode(s))
else:
    def n_tokens(s: str) -> int:
        # Fallback approximation: ~4 chars per token
        return max(1, len(s) // 4)

# Save the transcript in chunks
MAX_TOKENS_PER_BATCH = 18_000
transcript_batch, batch_tokens, file_index = [], 0, 1

while clean_transcript:
    entry = clean_transcript.popleft()
    entry_tokens = n_tokens(json.dumps(entry, ensure_ascii=False))

    if batch_tokens + entry_tokens > MAX_TOKENS_PER_BATCH and transcript_batch:
        file_path = BATCH_DIR / f"current_transcript_{file_index:03}.json"
        with file_path.open('w') as f:
            json.dump(transcript_batch, f, indent=2, ensure_ascii=False)
        file_index += 1
        transcript_batch, batch_tokens = [], 0

    transcript_batch.append(entry)
    batch_tokens += entry_tokens

if transcript_batch:
    file_path = BATCH_DIR / f'current_transcript_{file_index:03}.json'
    with file_path.open('w') as f:
        json.dump(transcript_batch, f, indent=2, ensure_ascii=False)

# Clean up old chunks again after creating new ones
cleanup_old_transcript_chunks(BATCH_DIR)

# Allow the tool call to proceed
sys.exit(0)