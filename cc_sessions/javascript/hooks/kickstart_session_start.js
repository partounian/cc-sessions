#!/usr/bin/env node

// ===== IMPORTS ===== //

/// ===== STDLIB ===== ///
const fs = require('fs');
const path = require('path');
///-///

/// ===== 3RD-PARTY ===== ///
///-///

/// ===== LOCAL ===== ///
// Import from shared_state (same pattern as other hooks)
const {
    loadState,
    PROJECT_ROOT,
    editState
} = require('./shared_state.js');
///-///

//-//

// ===== GLOBALS ===== //

/// ===== CI DETECTION ===== ///
function isCIEnvironment() {
    // Check if running in a CI environment (GitHub Actions)
    const ciIndicators = [
        'GITHUB_ACTIONS',         // GitHub Actions
        'GITHUB_WORKFLOW',        // GitHub Actions workflow
        'CI',                     // Generic CI indicator (set by GitHub Actions)
        'CONTINUOUS_INTEGRATION', // Generic CI (alternative)
    ];
    return ciIndicators.some(indicator => process.env[indicator]);
}

// Skip kickstart session start hook in CI environments
if (isCIEnvironment()) {
    process.exit(0);
}
///-///

/// ===== MODULE SEQUENCES ===== ///
const FULL_MODE_SEQUENCE = [
    '01-discussion.md',
    '02-implementation.md',
    '03-tasks-overview.md',
    '04-task-creation.md',
    '05-task-startup.md',
    '06-task-completion.md',
    '07-compaction.md',
    '08-agents.md',
    '09-api.md',
    '10-advanced.md',
    '11-graduation.md'
];

const SUBAGENTS_MODE_SEQUENCE = [
    '01-agents-only.md'
];
///-///

//-//

// ===== FUNCTIONS ===== //

function loadProtocolFile(relativePath) {
    /**
     * Load protocol markdown from protocols directory.
     */
    const protocolPath = path.join(PROJECT_ROOT, 'sessions', 'protocols', relativePath);
    if (!fs.existsSync(protocolPath)) {
        return `Error: Protocol file not found: ${relativePath}`;
    }
    return fs.readFileSync(protocolPath, 'utf8');
}

//-//

/*
Kickstart SessionStart Hook

Handles onboarding flow for users who chose kickstart in installer:
- Checks for kickstart metadata (should ALWAYS exist if this hook is running)
- Loads first module on first run, resumes from current_index on subsequent runs
- Sequences determined by mode (full or subagents)
*/

// ===== EXECUTION ===== //

//!> 1. Load state and check kickstart metadata
const STATE = loadState();

// Get kickstart metadata (should ALWAYS exist if this hook is running)
const kickstartMeta = STATE.metadata?.kickstart;

// NEW: Handle missing metadata gracefully (cleanup window detection)
if (!kickstartMeta) {
    // Metadata missing - check if we're in cleanup window
    // If hook file still exists but metadata gone, likely completed + cleanup in progress
    const hookFiles = [
        path.join(PROJECT_ROOT, 'sessions', 'hooks', 'kickstart_session_start.js'),
        path.join(PROJECT_ROOT, 'sessions', 'hooks', 'kickstart_session_start.py')
    ];

    const hookExists = hookFiles.some(hookPath => fs.existsSync(hookPath));

    if (hookExists) {
        // Hook exists but metadata gone = cleanup in progress, exit silently
        process.exit(0);
    } else {
        // No hook, no metadata = shouldn't be here, but exit silently anyway
        process.exit(0);
    }
}

// NEW: Check if kickstart is marked complete
if (kickstartMeta.onboarding_complete === true) {
    // Kickstart completed - exit silently, allow normal session
    process.exit(0);
}

const mode = kickstartMeta.mode;  // 'full' or 'subagents'
if (!mode) {
    console.log(JSON.stringify({
        hookSpecificOutput: {
            hookEventName: 'SessionStart',
            additionalContext: 'ERROR: kickstart metadata exists but no mode specified. This is an installer bug.'
        }
    }));
    process.exit(1);
}
//!<

//!> 2. Initialize or load sequence
// Determine sequence based on mode
let sequence;
if (mode === 'full') {
    sequence = FULL_MODE_SEQUENCE;
} else if (mode === 'subagents') {
    sequence = SUBAGENTS_MODE_SEQUENCE;
} else {
    console.log(JSON.stringify({
        hookSpecificOutput: {
            hookEventName: 'SessionStart',
            additionalContext: `ERROR: Invalid kickstart mode '${mode}'. Expected 'full' or 'subagents'.`
        }
    }));
    process.exit(1);
}

// Initialize sequence on first run
let protocolContent;
let currentIndex = kickstartMeta.current_index ?? 0;

if (!('sequence' in kickstartMeta)) {
    editState((s) => {
        s.metadata.kickstart.sequence = sequence;
        s.metadata.kickstart.current_index = 0;
        s.metadata.kickstart.completed = [];
        return s;
    });
    currentIndex = 0;
    protocolContent = loadProtocolFile(`kickstart/${sequence[0]}`);
} else {
    // Load current protocol from sequence
    protocolContent = loadProtocolFile(`kickstart/${sequence[currentIndex]}`);
}
//!<

//!> 2.5. Check cooldown and progress-aware logic
const lastShown = kickstartMeta.last_shown;
const now = Date.now();
const oneHourMs = 60 * 60 * 1000; // 1 hour in milliseconds

// If kickstart is in progress (current_index > 0), check cooldown
if (currentIndex > 0 && lastShown) {
    const lastShownTime = new Date(lastShown).getTime();
    const hoursSinceShown = (now - lastShownTime) / oneHourMs;

    // If shown within last hour, skip instructions but update last_active
    if (hoursSinceShown < 1) {
        editState((s) => {
            s.metadata.kickstart.last_active = new Date().toISOString();
            return s;
        });
        process.exit(0); // Exit silently, allow normal session
    }
}

// If we reach here, we should show instructions
// Update last_shown timestamp when displaying instructions
editState((s) => {
    s.metadata.kickstart.last_shown = new Date().toISOString();
    s.metadata.kickstart.last_active = new Date().toISOString();
    return s;
});
//!<

//!> 3. Append user instructions and output
protocolContent += `

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USER INSTRUCTIONS:
Just say 'kickstart' and press enter to begin
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`;

console.log(JSON.stringify({
    hookSpecificOutput: {
        hookEventName: 'SessionStart',
        additionalContext: protocolContent
    }
}));
process.exit(0);
//!<
