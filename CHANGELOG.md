# Changelog

## [Unreleased - v0.4.0]

### Changed - BREAKING
- **Icon Style System**: Replaced `use_nerd_fonts` boolean with `icon_style` string offering three modes:
  - `"nerd-fonts"` - Full Nerd Fonts icon support (default)
  - `"unicode"` - Standard Unicode emoji icons (📊 💬 🔨 🌿 📋 📁)
  - `"ascii"` - Plain text, no icons
  - Automatic migration: `use_nerd_fonts=true` → `icon_style="nerd-fonts"`, `false` → `"ascii"`
  - Configuration: `sessions config features set icon_style <nerd-fonts|ascii|unicode>`

### Added
- **Workspace Mode Feature**: Optional `workspace_mode` feature flag for super-repo/multi-project scenarios
  - Default: `false` (PROJECT_ROOT only, aligned with upstream/main)
  - Enable via: `sessions config features toggle workspace_mode`
  - Allows tasks in WORKSPACE_ROOT when enabled
- **Enhanced DAIC Test Coverage**: Comprehensive test suite expansion with 50+ new tests
  - Complete DAIC enforcement matrix (sed, awk, find, xargs write detection)
  - Icon style migration and statusline output validation
  - Sessions command surface integration tests
  - Workspace mode feature toggle tests
- **Updated Service Documentation Agent**: Adopted expanded upstream guidance for super-repo, mono-repo, and module patterns

### Deprecated
- `use_nerd_fonts` configuration field (use `icon_style` instead)
- Config command `sessions config features toggle use_nerd_fonts` no longer available

## [Unreleased - v0.3.0]

### Added
- **CI Environment Detection**: All hooks now automatically detect CI environments (GitHub Actions, etc.) and bypass DAIC enforcement to enable automated Claude Code agents
  - Thanks to @oppianmatt (matt@oppian.com) for the implementation guidance (#14)
- **Nerd Fonts Icons and Git Branch Display**: Enhanced statusline with Nerd Fonts icons and git branch information
  - Nerd Fonts icons for context, task, mode, open tasks, and git branch
  - Git branch display at end of line 2
  - Configurable toggle with ASCII fallback for users without Nerd Fonts
  - Thanks to @dnviti (dnviti@gmail.com) for the ideas (#21)
- **Safe Uninstaller**: Interactive uninstaller with automatic backups, dry-run mode, and user data preservation
  - Thanks to @gabelul for the uninstaller concept (#45)

## [0.2.8] - 2025-09-04

### Changed
- **No More Sudo Required**: The `daic` command no longer requires sudo for installation
- **Package Manager Integration**: `daic` is now installed as a package command:
  - Python: Automatically available when installed via pip/pipx
  - Node.js: Automatically available when installed via npm  
- **Fallback Location**: Local fallback moved from `.claude/bin` to `sessions/bin`
- **Cleaner Directory Structure**: cc-sessions specific files moved out of `.claude/` to keep it clean for Claude Code

### Added
- `cc_sessions/daic.py` - Python entry point for pip installations
- `daic.js` - Node.js entry point for npm installations
- Console scripts entry in `pyproject.toml`
- Bin entry in `package.json`

### Removed
- Sudo fallback logic from all installers
- Global `/usr/local/bin` installation attempt

## [0.2.7] - Previous Release
- Initial public release