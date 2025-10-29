# Codebase Inconsistencies Review

## Summary

Found inconsistencies in import patterns and PROJECT_ROOT handling between hooks, particularly in the JavaScript `kickstart_session_start.js` hook.

## Issues Found

### 1. JavaScript kickstart_session_start.js Uses Hardcoded Path Calculation

**Location**: `cc_sessions/javascript/hooks/kickstart_session_start.js` (lines 15-17)

**Current Code**:
```javascript
const PROJECT_ROOT = path.resolve(__dirname, '../../../../..');
const sharedStatePath = path.join(PROJECT_ROOT, 'sessions', 'hooks', 'shared_state.js');
const { loadState } = require(sharedStatePath);
```

**Problem**: 
- Uses hardcoded path calculation (`../../../../..`) instead of relative import
- Inconsistent with other JavaScript hooks which use `require('./shared_state.js')`
- Just refactored the Python version to use `find_project_root()` for consistency

**Expected Pattern** (matches other hooks):
```javascript
const { loadState, PROJECT_ROOT, editState } = require('./shared_state.js');
```

**Impact**: 
- Less testable
- Breaks if hook file structure changes
- Inconsistent with Python version after refactoring

### 2. Python Hooks Have Mixed Import Patterns

**Pattern A** (with try/except fallback): `user_messages.py`, `kickstart_session_start.py`
```python
try:
    from shared_state import ...
except ImportError:
    from cc_sessions.hooks.shared_state import ...
```

**Pattern B** (direct import): `session_start.py`, `sessions_enforce.py`, `post_tool_use.py`, `subagent_hooks.py`
```python
from shared_state import ...
```

**Analysis**:
- Pattern A is more robust for symlinked development setups
- Pattern B works when hooks are installed or in package structure
- Pattern A is preferred for consistency and flexibility

**Recommendation**: 
- Consider standardizing on Pattern A (try/except) for all hooks
- OR document when Pattern B is acceptable (e.g., hooks that are always run from package context)

### 3. Plugin File Uses Different Path Calculation

**Location**: `cc_sessions/plugin/enforcement_plugin.py` (line 26)

**Code**:
```python
def _repo_root() -> Path:
    # Resolve cc_sessions/ root from this file location
    return Path(__file__).resolve().parents[1]
```

**Analysis**: 
- This appears intentional - plugin needs to find `cc_sessions/` package root, not project root
- Uses `parents[1]` (one level up) vs hooks which used `parents[5]` (five levels up)
- Different use case: plugin runs within package context, hooks run in project context
- **Not an inconsistency** - this is correct for its context

## Recommendations

### High Priority

1. **Refactor JavaScript kickstart_session_start.js** to match Python version:
   - Use relative import: `require('./shared_state.js')`
   - Import `PROJECT_ROOT` from shared_state instead of calculating it
   - This will match the pattern used by all other JavaScript hooks

### Medium Priority

2. **Consider standardizing Python hook imports**:
   - Document which pattern (try/except vs direct) should be used
   - OR refactor all hooks to use try/except pattern for consistency
   - Benefit: Better support for symlinked development setups

### Low Priority

3. **Review plugin path calculation**:
   - Current implementation is correct for its use case
   - No changes needed, but could benefit from a comment explaining why it differs from hooks

## Files to Update

1. `cc_sessions/javascript/hooks/kickstart_session_start.js` - Refactor import pattern
2. Consider: `cc_sessions/python/hooks/subagent_hooks.py` - Add try/except pattern?
3. Consider: `cc_sessions/python/hooks/sessions_enforce.py` - Add try/except pattern?
4. Consider: `cc_sessions/python/hooks/post_tool_use.py` - Add try/except pattern?
5. Consider: `cc_sessions/python/hooks/session_start.py` - Add try/except pattern?

## Consistency Matrix

| File | Language | Import Pattern | PROJECT_ROOT Source |
|------|----------|----------------|---------------------|
| kickstart_session_start.js | JS | **Hardcoded path** ❌ | Calculated ❌ |
| kickstart_session_start.py | Python | try/except ✅ | `shared_state.find_project_root()` ✅ |
| user_messages.js | JS | `require('./shared_state.js')` ✅ | From shared_state ✅ |
| user_messages.py | Python | try/except ✅ | From shared_state ✅ |
| session_start.js | JS | `require('./shared_state.js')` ✅ | From shared_state ✅ |
| session_start.py | Python | Direct import ⚠️ | From shared_state ✅ |
| sessions_enforce.js | JS | `require('./shared_state.js')` ✅ | From shared_state ✅ |
| sessions_enforce.py | Python | Direct import ⚠️ | From shared_state ✅ |
| post_tool_use.js | JS | `require('./shared_state.js')` ✅ | From shared_state ✅ |
| post_tool_use.py | Python | Direct import ⚠️ | From shared_state ✅ |
| subagent_hooks.js | JS | `require('./shared_state.js')` ✅ | From shared_state ✅ |
| subagent_hooks.py | Python | Direct import ⚠️ | From shared_state ✅ |

**Legend**: ✅ Consistent | ⚠️ Works but could be more robust | ❌ Inconsistent

