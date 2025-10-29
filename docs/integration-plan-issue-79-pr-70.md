# Integration Plan: Issue #79 & PR #70

## Overview

This plan integrates fixes from two external sources:
- **Issue #79**: Fix kickstart session-start hook blocking every session ([link](https://github.com/GWUDCAP/cc-sessions/issues/79))
- **PR #70**: Add Development Setup documentation to CLAUDE.md

## Issue #79: Kickstart Hook Blocks Every Session

### Problem Summary
The `kickstart_session_start.js` and `kickstart_session_start.py` hooks output onboarding instructions on **every** session start, even when:
- Kickstart is already in progress (`current_index > 0`)
- User has completed multiple modules
- User wants to work normally while kickstart metadata exists

This blocks normal Claude Code interaction until users manually remove the hook or clear metadata.

### Root Cause
Both hooks always output instructions without checking:
1. Whether kickstart is complete (check for `onboarding_complete` flag or `current_index >= sequence.length`)
2. Whether instructions were shown recently (within last hour)
3. Whether user explicitly wants to continue kickstart vs. work normally

### Implementation Plan

#### Task 1: Add Kickstart Completion Detection
**Files**: `cc_sessions/python/hooks/kickstart_session_start.py`, `cc_sessions/javascript/hooks/kickstart_session_start.js`

**Changes**:
- Check if kickstart has `onboarding_complete: true` metadata flag (set by `kickstart complete` command)
- If complete, silently exit (no output, allow normal session to proceed)
- Exit code: `process.exit(0)` / `sys.exit(0)`

**Code Pattern**:
```javascript
// Check if kickstart is already complete
if (kickstartMeta.onboarding_complete) {
    process.exit(0);  // Silent exit, let normal session proceed
}
```

#### Task 2: Add Recent Instructions Cooldown
**Files**: Same as above

**Changes**:
- Add `last_shown` timestamp to kickstart metadata when instructions are displayed
- Check if `last_shown` exists and is within last hour (configurable, default 1 hour)
- If shown recently, skip output but update `last_active` timestamp
- Only show instructions if:
  - First time (no `last_shown`)
  - More than 1 hour since `last_shown`
  - User explicitly requests kickstart (via trigger phrase or API command)

**Code Pattern**:
```javascript
const lastShown = kickstartMeta.last_shown;
const now = Date.now();
const oneHourMs = 60 * 60 * 1000;

if (lastShown && (now - new Date(lastShown).getTime() < oneHourMs)) {
    // Update last_active but don't show instructions
    editState(s => {
        s.metadata.kickstart.last_active = new Date().toISOString();
        return s;
    });
    process.exit(0);
}
```

#### Task 3: Add Progress-Aware Logic
**Files**: Same as above

**Changes**:
- If `current_index > 0` (in progress), only show instructions if:
  - User hasn't seen them in last hour (from Task 2)
  - OR user explicitly triggers kickstart continuation
- For first-time (current_index === 0), always show instructions on first session start
- Track instruction display: set `last_shown` timestamp when instructions are output

**Code Pattern**:
```javascript
// Only show instructions if kickstart just started (index 0)
// or if user explicitly wants to continue (handled separately)
if (kickstartMeta.current_index > 0) {
    // In progress - use cooldown logic from Task 2
    // Don't auto-show instructions every session
}
```

#### Task 4: Update Kickstart Complete Command
**Files**: `cc_sessions/python/api/kickstart_commands.py`, `cc_sessions/javascript/api/kickstart_commands.js`

**Changes**:
- When `kickstart complete` runs, set `onboarding_complete: true` in metadata
- Ensure cleanup still removes kickstart files but preserves completion flag temporarily
- Hook will then silently exit on subsequent session starts

**Code Pattern**:
```javascript
editState(s => {
    s.metadata.kickstart.onboarding_complete = true;
    s.metadata.kickstart.completed_at = new Date().toISOString();
    return s;
});
```

#### Task 5: Add Optional Disable Flag (Future Enhancement)
**Files**: Configuration system (`SessionsConfig`)

**Future Consideration**:
- Add `kickstart_auto_prompt: boolean` config option (default: `true`)
- When `false`, hook only runs if explicitly triggered (not on every session start)
- Useful for users who want kickstart available but not intrusive

### Testing Plan
1. **Fresh Install Test**: Start new session with kickstart metadata → should show instructions
2. **In Progress Test**: Continue session when `current_index > 0` → should NOT show instructions if within cooldown
3. **Complete Test**: After `kickstart complete` → should silently exit, no blocking
4. **Cooldown Test**: Show instructions, wait 2 hours, start new session → should show again
5. **Explicit Continuation Test**: User types "kickstart" or runs `sessions kickstart next` → should show current protocol

---

## PR #70: Development Setup Documentation

### Problem Summary
`CLAUDE.md` lacks a dedicated "Development Setup" section with:
- Local installation instructions
- Build commands (Python `python -m build`, JavaScript `npm pack`)
- Testing workflow documentation
- Manual testing guidelines

This increases onboarding friction for contributors.

### Implementation Plan

#### Task 1: Add Development Setup Section
**File**: `CLAUDE.md`

**Location**: After "Installation Methods" section (around line 89)

**New Section Content**:
```markdown
## Development Setup

### Local Installation

To develop cc-sessions locally without publishing:

**Python Variant:**
1. Clone repository: `git clone https://github.com/GWUDCAP/cc-sessions.git`
2. Install in development mode: `pip install -e .` (from repo root)
3. Verify hooks accessible: `python -m cc_sessions.scripts.api --help`

**JavaScript Variant:**
1. Clone repository: `git clone https://github.com/GWUDCAP/cc-sessions.git`
2. Install dependencies: `npm install` (from repo root)
3. Verify hooks accessible: `node cc_sessions/javascript/hooks/shared_state.js`

**Symlinked Development:**
For real-time testing without reinstalling:
1. Set `CLAUDE_PROJECT_DIR` environment variable to repo root
2. Configure `.claude/settings.json` hooks to reference `sessions/hooks/*`
3. Changes to hooks/API files immediately available in test projects

### Building Packages

**Python Package:**
```bash
# Build wheel and source distribution
python -m build

# Outputs to: dist/cc_sessions-X.Y.Z-py3-none-any.whl
#              dist/cc-sessions-X.Y.Z.tar.gz
```

**JavaScript Package:**
```bash
# Validate package structure (dry-run)
npm pack --dry-run

# Create package tarball
npm pack

# Outputs to: cc-sessions-X.Y.Z.tgz
```

### Testing

**Automated Tests:**
```bash
# Python tests
python -m pytest tests/

# Run specific test suite
python -m pytest tests/test_daic_enforcement.py
```

**Manual Testing Workflow:**
1. Make changes to hooks or API files
2. Test in isolated project directory:
   ```bash
   mkdir /tmp/test-cc-sessions
   cd /tmp/test-cc-sessions
   git init
   # Install from local clone (pip install -e /path/to/cc-sessions)
   # OR use symlinked setup via CLAUDE_PROJECT_DIR
   ```
3. Verify hook execution via SessionStart/PreToolUse logs
4. Test both Python and JavaScript variants independently

**Testing Both Language Variants:**
- Python hook tests: `tests/test_daic_enforcement.py`
- JavaScript parity: Manually verify equivalent behavior
- Cross-validation: Run same scenarios through both hook implementations
```

#### Task 2: Update Release Script References (if needed)
**File**: `CLAUDE.md`

**Check**: Ensure references to `scripts/prepare-release.py` and `scripts/publish-release.py` are accurate (PR #70 mentions removing obsolete release script references)

**Verification**:
- Confirm `scripts/prepare-release.py` exists (line 60)
- Confirm `scripts/publish-release.py` exists (line 61)
- If PR #70 removed these, update CLAUDE.md to match current state

---

## Integration Priority

### High Priority (Blocking Issue)
1. **Issue #79 - Kickstart Completion Detection** (Task 1, 4)
   - Severity: High - blocks normal usage
   - Impact: All users with kickstart metadata
   - Effort: Low (simple metadata check)

2. **Issue #79 - Cooldown Logic** (Task 2)
   - Severity: Medium - reduces annoyance
   - Impact: Improves UX for in-progress kickstart
   - Effort: Medium (timestamp tracking)

### Medium Priority (UX Improvement)
3. **PR #70 - Development Setup Section** (Task 1)
   - Severity: Low - documentation only
   - Impact: Helps contributors get started
   - Effort: Low (markdown documentation)

4. **Issue #79 - Progress-Aware Logic** (Task 3)
   - Severity: Medium - improves behavior
   - Impact: Better session management
   - Effort: Medium (logic refinement)

### Low Priority (Future Enhancement)
5. **Issue #79 - Disable Flag** (Task 5)
   - Severity: Low - optional feature
   - Impact: Power user convenience
   - Effort: High (config system changes)

---

## Implementation Order

1. **Phase 1 (Quick Fix)**: Add completion detection (Issue #79, Tasks 1 & 4)
   - 30 minutes
   - Immediately unblocks affected users
   - Both Python and JavaScript hooks

2. **Phase 2 (UX Polish)**: Add cooldown and progress-aware logic (Issue #79, Tasks 2 & 3)
   - 1-2 hours
   - Improves experience for in-progress kickstart
   - Both Python and JavaScript hooks

3. **Phase 3 (Documentation)**: Add Development Setup section (PR #70, Task 1)
   - 30 minutes
   - Helps contributors
   - Single file update

4. **Phase 4 (Testing)**: Add regression tests for kickstart hook behavior
   - 1 hour
   - Prevents regression
   - Test both completion and cooldown scenarios

---

## File Checklist

### Issue #79 Fixes
- [ ] `cc_sessions/javascript/hooks/kickstart_session_start.js` - Add completion check, cooldown, progress logic
- [ ] `cc_sessions/python/hooks/kickstart_session_start.py` - Add completion check, cooldown, progress logic
- [ ] `cc_sessions/javascript/api/kickstart_commands.js` - Set `onboarding_complete` flag on complete
- [ ] `cc_sessions/python/api/kickstart_commands.py` - Set `onboarding_complete` flag on complete
- [ ] `tests/test_kickstart_hooks.py` (new) - Add tests for completion, cooldown, progress scenarios

### PR #70 Documentation
- [ ] `CLAUDE.md` - Add Development Setup section after Installation Methods
- [ ] Verify `scripts/prepare-release.py` and `scripts/publish-release.py` references are accurate

---

## References
- Issue #79: https://github.com/GWUDCAP/cc-sessions/issues/79
- PR #70: https://github.com/GWUDCAP/cc-sessions/pull/70
- Current kickstart hooks: `cc_sessions/{python,javascript}/hooks/kickstart_session_start.{py,js}`
- Current kickstart commands: `cc_sessions/{python,javascript}/api/kickstart_commands.{py,js}`

