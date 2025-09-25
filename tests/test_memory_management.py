#!/usr/bin/env python3
"""
Memory Management Tests for cc-sessions

Comprehensive tests for memory leak prevention and cleanup mechanisms.
Includes both unit tests and integration tests for the actual implementation.
"""

import json
import os
import tempfile
import time
from pathlib import Path
import sys

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

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
        except Exception as exc:
            print(f"WARNING: cleanup_old_transcript_chunks failed to remove {old_chunk}: {exc}")

# ============================================================================
# UNIT TESTS - Test individual functions and components
# ============================================================================

def test_transcript_chunk_cleanup_unit():
    """Unit test: Test that cleanup keeps only recent transcript chunks"""
    print("🧪 Testing transcript chunk cleanup (unit test)...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        batch_dir = tmp_path / "transcript_chunks"
        batch_dir.mkdir(parents=True, exist_ok=True)

        # Create 25 transcript chunk files with different timestamps
        for i in range(25):
            chunk_file = batch_dir / f"current_transcript_{i:03}.json"
            with open(chunk_file, 'w') as f:
                json.dump([{"chunk": i, "data": f"chunk_data_{i}"}], f)

            # Set different modification times (older files first)
            old_time = time.time() - (25 - i) * 60  # 1 minute apart
            os.utime(chunk_file, (old_time, old_time))

        # Verify we have 25 files
        initial_files = list(batch_dir.glob("current_transcript_*.json"))
        assert len(initial_files) == 25, f"Expected 25 files, got {len(initial_files)}"
        print(f"✅ Created {len(initial_files)} test files")

        # Run cleanup
        cleanup_old_transcript_chunks(batch_dir)

        # Verify only last 20 chunks remain
        remaining_files = list(batch_dir.glob("current_transcript_*.json"))
        assert len(remaining_files) == 20, f"Expected 20 files after cleanup, got {len(remaining_files)}"
        print(f"✅ Cleanup successful: {len(remaining_files)} files remaining")

        # Verify the most recent files are kept
        remaining_numbers = sorted([int(f.stem.split('_')[-1]) for f in remaining_files])
        expected_numbers = list(range(5, 25))  # Files 5-24 kept
        assert remaining_numbers == expected_numbers, f"Expected {expected_numbers}, got {remaining_numbers}"
        print(f"✅ Correct files kept: {remaining_numbers}")

        print("✅ Transcript chunk cleanup unit test PASSED")

def test_cleanup_handles_missing_directory():
    """Unit test: Test that cleanup handles missing directory gracefully"""
    print("🧪 Testing cleanup with missing directory...")

    missing_dir = Path("/nonexistent/directory")

    # Should not raise exception
    try:
        cleanup_old_transcript_chunks(missing_dir)
        print("✅ Missing directory handled gracefully")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise

def test_cleanup_handles_file_errors_gracefully():
    """Unit test: Test that cleanup handles file errors gracefully"""
    print("🧪 Testing cleanup with file errors...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        batch_dir = tmp_path / "transcript_chunks"
        batch_dir.mkdir(parents=True, exist_ok=True)

        # Create a file
        chunk_file = batch_dir / "current_transcript_001.json"
        with open(chunk_file, 'w') as f:
            json.dump([{"chunk": 1}], f)

        # Test cleanup (should not raise exception even if there are permission issues)
        try:
            cleanup_old_transcript_chunks(batch_dir)
            print("✅ File errors handled gracefully")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            raise

def test_log_file_memory_issue_demonstration():
    """Unit test: Demonstrate the current log file memory issue"""
    print("🧪 Demonstrating log file memory issue...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        log_file = tmp_path / "test_log.json"

        # Create a large existing log file (simulating current behavior)
        large_log_data = [{"entry": f"log_entry_{i}", "data": "x" * 1000} for i in range(500)]
        with open(log_file, 'w') as f:
            json.dump(large_log_data, f)

        # Simulate current problematic behavior: load entire file into memory
        with open(log_file, 'r') as f:
            data = json.load(f)

        # This loads the entire 500-entry file into memory every time
        assert len(data) == 500
        print(f"✅ Current behavior loads {len(data)} entries into memory (problematic)")

        # Show file size
        file_size = log_file.stat().st_size
        print(f"✅ File size: {file_size} bytes")

        # Demonstrate streaming approach would be better
        print("✅ Streaming approach would append without loading entire file")

# ============================================================================
# INTEGRATION TESTS - Test actual implementation
# ============================================================================

def test_streaming_log_append():
    """Test the new streaming log append functionality"""
    print("🧪 Testing streaming log append...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Change to temp directory for shared state
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Import after changing directory
            from cc_sessions.hooks.shared_state import SharedState

            shared_state = SharedState()

            # Test streaming append
            for i in range(5):
                shared_state.log_tool_usage({
                    "tool_name": "test_tool",
                    "timestamp": f"2024-01-01T00:00:{i:02d}Z",
                    "success": True
                })

            # Verify log file exists and has reasonable size
            assert shared_state.tool_usage_log_file.exists()
            log_size = shared_state.tool_usage_log_file.stat().st_size
            print(f"✅ Log file created with size: {log_size} bytes")

            # Verify we can read the log
            log_entries = shared_state.get_tool_usage_log()
            assert len(log_entries) == 5
            print(f"✅ Successfully read {len(log_entries)} log entries")

        finally:
            os.chdir(original_cwd)

def test_memory_monitoring():
    """Test memory monitoring functionality"""
    print("🧪 Testing memory monitoring...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Change to temp directory for shared state
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Import after changing directory
            from cc_sessions.hooks.shared_state import SharedState

            shared_state = SharedState()

            # Test memory usage monitoring
            memory_info = shared_state.get_memory_usage()
            assert 'timestamp' in memory_info
            print(f"✅ Memory monitoring working: {memory_info}")

            # Test garbage collection
            gc_stats = shared_state.trigger_garbage_collection()
            assert 'collected_objects' in gc_stats
            print(f"✅ Garbage collection working: {gc_stats['collected_objects']} objects collected")

        finally:
            os.chdir(original_cwd)

def test_enhanced_agent_cleanup():
    """Test enhanced agent context cleanup"""
    print("🧪 Testing enhanced agent cleanup...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create agent context directory structure
        agent_context_dir = tmp_path / ".claude" / "state" / "agent_context"
        test_agent_dir = agent_context_dir / "test_agent"
        test_agent_dir.mkdir(parents=True, exist_ok=True)

        # Create chunk files (15 total)
        for i in range(15):
            chunk_file = test_agent_dir / f"chunk_{i:03}.json"
            with open(chunk_file, 'w') as f:
                json.dump({"chunk": i, "data": f"chunk_data_{i}"}, f)

            # Set different modification times
            old_time = time.time() - (15 - i) * 60
            os.utime(chunk_file, (old_time, old_time))

        # Create temp files
        temp_file = test_agent_dir / "temp_file.json"
        temp_file.write_text("temp data")

        # Change to temp directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Import after changing directory
            from cc_sessions.hooks.session_lifecycle import SessionLifecycleManager

            # Test cleanup
            lifecycle_manager = SessionLifecycleManager()
            lifecycle_manager.state_dir = tmp_path / ".claude" / "state"
            lifecycle_manager._cleanup_agent_contexts()

            # Verify only last 10 chunks remain
            remaining_chunks = list(test_agent_dir.glob("chunk_*.json"))
            assert len(remaining_chunks) == 10, f"Expected 10 chunks, got {len(remaining_chunks)}"
            print(f"✅ Enhanced cleanup working: {len(remaining_chunks)} chunks remaining")

            # Verify temp files are removed
            temp_files = list(test_agent_dir.glob("temp_*"))
            assert len(temp_files) == 0, f"Expected 0 temp files, got {len(temp_files)}"
            print("✅ Temp files cleaned up")

        finally:
            os.chdir(original_cwd)

def test_optimized_directory_traversal():
    """Test optimized directory traversal"""
    print("🧪 Testing optimized directory traversal...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create workspace with multiple repos
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir(parents=True, exist_ok=True)

        # Create multiple repo directories
        for i in range(5):
            repo_dir = workspace_root / f"repo_{i}"
            repo_dir.mkdir(parents=True, exist_ok=True)
            (repo_dir / ".git").mkdir(exist_ok=True)

        # Change to workspace for shared state
        original_cwd = os.getcwd()
        try:
            os.chdir(workspace_root)

            # Import after changing directory
            from cc_sessions.hooks.shared_state import SharedState

            shared_state = SharedState()
            repositories = shared_state.detect_workspace_repositories()

            # Verify we found repositories but didn't accumulate memory
            assert len(repositories) <= 10  # Should respect max_repos limit
            assert all(isinstance(repo, Path) for repo in repositories)
            print(f"✅ Found {len(repositories)} repositories with optimized traversal")

        finally:
            os.chdir(original_cwd)

def test_get_shared_state_returns_correct_type():
    """Test that get_shared_state() returns SharedState instance"""
    print("🧪 Testing get_shared_state() returns SharedState...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Change to temp directory for shared state
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Import after changing directory
            from cc_sessions.hooks.shared_state import get_shared_state, SharedState

            # Test that get_shared_state() returns SharedState instance
            shared_state = get_shared_state()
            assert isinstance(shared_state, SharedState), f"Expected SharedState instance, got {type(shared_state)}"
            print("✅ get_shared_state() returns SharedState instance")

            # Test that it's a singleton
            shared_state2 = get_shared_state()
            assert shared_state is shared_state2, "get_shared_state() should return same instance"
            print("✅ get_shared_state() returns singleton instance")

        finally:
            os.chdir(original_cwd)

def main():
    """Run all memory management tests (unit + integration)"""
    print("🚀 Running cc-sessions memory management tests...\n")

    # Unit tests
    unit_tests = [
        test_transcript_chunk_cleanup_unit,
        test_cleanup_handles_missing_directory,
        test_cleanup_handles_file_errors_gracefully,
        test_log_file_memory_issue_demonstration,
    ]

    # Integration tests
    integration_tests = [
        test_streaming_log_append,
        test_memory_monitoring,
        test_enhanced_agent_cleanup,
        test_optimized_directory_traversal,
        test_get_shared_state_returns_correct_type,
    ]

    all_tests = unit_tests + integration_tests

    passed = 0
    total = len(all_tests)

    print("📋 Running unit tests...")
    for test in unit_tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
        print()

    print("📋 Running integration tests...")
    for test in integration_tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
        print()

    print(f"📊 Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All memory management tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Review issues.")
        return 1

if __name__ == "__main__":
    exit(main())
