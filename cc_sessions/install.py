#!/usr/bin/env python3

# ===== IMPORTS ===== #

## ===== STDLIB ===== ##
import shutil, json, sys, os
from pathlib import Path
##-##

## ===== 3RD-PARTY ===== ##
from inquirer import themes
import platform
import inquirer
##-##

## ===== LOCAL ===== ##
##-##

#-#

"""
╔═════════════════════════════════════════════════════════════════════╗
║ ██████╗██╗  ██╗██████╗██████╗ █████╗ ██╗     ██╗     ██████╗█████╗  ║
║ ╚═██╔═╝███╗ ██║██╔═══╝╚═██╔═╝██╔══██╗██║     ██║     ██╔═══╝██╔═██╗ ║
║   ██║  ████╗██║██████╗  ██║  ███████║██║     ██║     █████╗ █████╔╝ ║
║   ██║  ██╔████║╚═══██║  ██║  ██╔══██║██║     ██║     ██╔══╝ ██╔═██╗ ║
║ ██████╗██║╚███║██████║  ██║  ██║  ██║███████╗███████╗██████╗██║ ██║ ║
║ ╚═════╝╚═╝ ╚══╝╚═════╝  ╚═╝  ╚═╝  ╚═╝╚══════╝╚══════╝╚═════╝╚═╝ ╚═╝ ║
╚═════════════════════════════════════════════════════════════════════╝
cc-sessions installer module for pip/pipx installation.
This module is imported and executed when running `cc-sessions` command.
"""

# ===== DECLARATIONS ===== #
# Colors for terminal output
class Colors:
    RESET = '\033[0m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    CYAN = '\033[36m'
    BOLD = '\033[1m'
#-#

# ===== FUNCTIONS ===== #

## ===== HELPERS ===== ##
def color(text, color_code):
    return f"{color_code}{text}{Colors.RESET}"

def get_package_root():
    """Get the root directory of the installed cc_sessions package."""
    return Path(__file__).parent

def get_project_root():
    """Get the root directory where cc-sessions should be installed."""
    return Path.cwd()
##-##

def main():
    SCRIPT_DIR = get_package_root()
    PROJECT_ROOT = get_project_root()

    print(color('\n╔════════════════════════════════════════════════════════════════╗', Colors.CYAN))
    print(color('║           CC-SESSIONS INSTALLER (Python Edition)              ║', Colors.CYAN))
    print(color('╚════════════════════════════════════════════════════════════════╝\n', Colors.CYAN))

    # Check if already installed and backup if needed
    sessions_dir = PROJECT_ROOT / 'sessions'
    backup_dir = None

    if sessions_dir.exists():
        # Check if there's actual content to preserve
        tasks_dir = sessions_dir / 'tasks'
        has_content = tasks_dir.exists() and any(tasks_dir.rglob('*.md'))

        if not has_content:
            print(color('🆕 Detected empty sessions directory, treating as fresh install', Colors.CYAN))
        else:
            print(color('🔍 Detected existing cc-sessions installation', Colors.CYAN))
            backup_dir = create_backup(PROJECT_ROOT)

    print(color(f'\n⚙️  Installing cc-sessions to: {PROJECT_ROOT}', Colors.CYAN))
    print()

    try:
        # Create directory structure
        create_directory_structure(PROJECT_ROOT)

        # Copy shared files
        copy_shared_files(SCRIPT_DIR, PROJECT_ROOT)

        # Copy Python-specific files
        copy_python_files(SCRIPT_DIR, PROJECT_ROOT)

        # Configure .claude/settings.json
        configure_settings(PROJECT_ROOT)

        # Add reference to CLAUDE.md
        configure_claude_md(PROJECT_ROOT)

        # Configure .gitignore
        configure_gitignore(PROJECT_ROOT)

        # Initialize state and config files
        initialize_state_files(PROJECT_ROOT)

        # Run installer decision flow (first-time detection, config, kickstart)
        kickstart_mode = installer_decision_flow(PROJECT_ROOT)

        # Restore tasks if this was an update
        if backup_dir:
            restore_tasks(PROJECT_ROOT, backup_dir)
            print(color(f'\n📁 Backup saved at: {backup_dir.relative_to(PROJECT_ROOT)}/', Colors.CYAN))
            print(color('   (Agents backed up for manual restoration if needed)', Colors.CYAN))

        print(color('\n✅ cc-sessions installed successfully!\n', Colors.GREEN))
        print(color('Next steps:', Colors.BOLD))
        print('  1. Restart your Claude Code session (or run /clear)')

        if kickstart_mode == 'full':
            print('  2. The kickstart onboarding will guide you through setup\n')
        elif kickstart_mode == 'subagents':
            print('  2. Kickstart will guide you through subagent customization\n')
        else:  # skip
            print('  2. You can start using cc-sessions right away!')
            print('     - Try "mek: my first task" to create a task')
            print('     - Type "help" to see available commands\n')

        if backup_dir:
            print(color('Note: Check backup/ for any custom agents you want to restore\n', Colors.CYAN))

    except Exception as error:
        print(color(f'\n❌ Installation failed: {error}', Colors.RED), file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

def create_directory_structure(project_root):
    print(color('Creating directory structure...', Colors.CYAN))

    dirs = [
        '.claude',
        '.claude/agents',
        '.claude/commands',
        'sessions',
        'sessions/tasks',
        'sessions/tasks/done',
        'sessions/tasks/indexes',
        'sessions/hooks',
        'sessions/api',
        'sessions/protocols',
        'sessions/knowledge'
    ]

    for dir_name in dirs:
        full_path = project_root / dir_name
        full_path.mkdir(parents=True, exist_ok=True)

def copy_shared_files(script_dir, project_root):
    print(color('Installing shared files...', Colors.CYAN))

    # Copy agents
    agents_source = script_dir / 'agents'
    agents_dest = project_root / '.claude' / 'agents'
    if agents_source.exists():
        copy_directory(agents_source, agents_dest)

    # Copy knowledge base
    knowledge_source = script_dir / 'knowledge'
    knowledge_dest = project_root / 'sessions' / 'knowledge'
    if knowledge_source.exists():
        copy_directory(knowledge_source, knowledge_dest)

def copy_python_files(script_dir, project_root):
    print(color('Installing Python-specific files...', Colors.CYAN))

    py_root = script_dir / 'python'

    # Copy statusline
    copy_file(
        py_root / 'statusline.py',
        project_root / 'sessions' / 'statusline.py'
    )

    # Copy API
    copy_directory(
        py_root / 'api',
        project_root / 'sessions' / 'api'
    )

    # Copy hooks
    copy_directory(
        py_root / 'hooks',
        project_root / 'sessions' / 'hooks'
    )

    # Copy protocols
    copy_directory(
        py_root / 'protocols',
        project_root / 'sessions' / 'protocols'
    )

    # Copy commands
    copy_directory(
        py_root / 'commands',
        project_root / '.claude' / 'commands'
    )

    # Copy templates to their respective destinations
    templates_dir = py_root / 'templates'

    copy_file(
        templates_dir / 'CLAUDE.sessions.md',
        project_root / 'sessions' / 'CLAUDE.sessions.md'
    )

    copy_file(
        templates_dir / 'TEMPLATE.md',
        project_root / 'sessions' / 'tasks' / 'TEMPLATE.md'
    )

    copy_file(
        templates_dir / 'h-kickstart-setup.md',
        project_root / 'sessions' / 'tasks' / 'h-kickstart-setup.md'
    )

    copy_file(
        templates_dir / 'INDEX_TEMPLATE.md',
        project_root / 'sessions' / 'tasks' / 'indexes' / 'INDEX_TEMPLATE.md'
    )

def configure_settings(project_root):
    print(color('Configuring Claude Code hooks...', Colors.CYAN))

    settings_path = project_root / '.claude' / 'settings.json'
    settings = {}

    # Load existing settings if they exist
    if settings_path.exists():
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        except json.JSONDecodeError:
            print(color('⚠️  Could not parse existing settings.json, will create new one', Colors.YELLOW))

    # Define sessions hooks
    is_windows = sys.platform == 'win32'
    sessions_hooks = {
        'UserPromptSubmit': [
            {
                'hooks': [
                    {
                        'type': 'command',
                        'command': 'python "%CLAUDE_PROJECT_DIR%\\sessions\\hooks\\user_messages.py"' if is_windows
                                 else 'python $CLAUDE_PROJECT_DIR/sessions/hooks/user_messages.py'
                    }
                ]
            }
        ],
        'PreToolUse': [
            {
                'matcher': 'Write|Edit|MultiEdit|Task|Bash',
                'hooks': [
                    {
                        'type': 'command',
                        'command': 'python "%CLAUDE_PROJECT_DIR%\\sessions\\hooks\\sessions_enforce.py"' if is_windows
                                 else 'python $CLAUDE_PROJECT_DIR/sessions/hooks/sessions_enforce.py'
                    }
                ]
            },
            {
                'matcher': 'Task',
                'hooks': [
                    {
                        'type': 'command',
                        'command': 'python "%CLAUDE_PROJECT_DIR%\\sessions\\hooks\\subagent_hooks.py"' if is_windows
                                 else 'python $CLAUDE_PROJECT_DIR/sessions/hooks/subagent_hooks.py'
                    }
                ]
            }
        ],
        'PostToolUse': [
            {
                'hooks': [
                    {
                        'type': 'command',
                        'command': 'python "%CLAUDE_PROJECT_DIR%\\sessions\\hooks\\post_tool_use.py"' if is_windows
                                 else 'python $CLAUDE_PROJECT_DIR/sessions/hooks/post_tool_use.py'
                    }
                ]
            }
        ],
        'SessionStart': [
            {
                'matcher': 'startup|clear',
                'hooks': [
                    {
                        'type': 'command',
                        'command': 'python "%CLAUDE_PROJECT_DIR%\\sessions\\hooks\\session_start.py"' if is_windows
                                 else 'python $CLAUDE_PROJECT_DIR/sessions/hooks/session_start.py'
                    }
                ]
            }
        ]
    }

    # Initialize hooks object if it doesn't exist
    if 'hooks' not in settings:
        settings['hooks'] = {}

    # Merge each hook type (sessions hooks take precedence)
    for hook_type, hook_config in sessions_hooks.items():
        if hook_type not in settings['hooks']:
            settings['hooks'][hook_type] = []

        # Add sessions hooks (prepend so they run first)
        settings['hooks'][hook_type] = hook_config + settings['hooks'][hook_type]

    # Write updated settings
    with open(settings_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2)

def configure_claude_md(project_root):
    print(color('Configuring CLAUDE.md...', Colors.CYAN))

    claude_path = project_root / 'CLAUDE.md'
    reference = '@sessions/CLAUDE.sessions.md'

    if claude_path.exists():
        content = claude_path.read_text(encoding='utf-8')

        # Only add if not already present
        if reference not in content:
            # Add at the beginning after any frontmatter
            lines = content.split('\n')
            insert_index = 0

            # Skip frontmatter if it exists
            if lines[0] == '---':
                for i in range(1, len(lines)):
                    if lines[i] == '---':
                        insert_index = i + 1
                        break

            lines.insert(insert_index, '')
            lines.insert(insert_index + 1, reference)
            lines.insert(insert_index + 2, '')
            content = '\n'.join(lines)
            claude_path.write_text(content, encoding='utf-8')
    else:
        # Create minimal CLAUDE.md with reference
        minimal_claude = f"""# CLAUDE.md

{reference}

This file provides instructions for Claude Code when working with this codebase.
"""
        claude_path.write_text(minimal_claude, encoding='utf-8')

def configure_gitignore(project_root):
    print(color('Configuring .gitignore...', Colors.CYAN))

    gitignore_path = project_root / '.gitignore'
    gitignore_entries = [
        '',
        '# cc-sessions runtime files',
        'sessions/sessions-state.json',
        'sessions/transcripts/',
        ''
    ]

    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding='utf-8')

        # Only add if not already present
        if 'sessions/sessions-state.json' not in content:
            # Append to end of file
            content += '\n'.join(gitignore_entries)
            gitignore_path.write_text(content, encoding='utf-8')
    else:
        # Create new .gitignore with our entries
        gitignore_path.write_text('\n'.join(gitignore_entries), encoding='utf-8')

def get_readonly_commands_list():
    """Get the list of read-only commands from sessions_enforce.py for display."""
    # This is a subset for display purposes - the full list is in sessions_enforce.py
    return [
        'cat', 'ls', 'pwd', 'cd', 'echo', 'grep', 'find', 'git status', 'git log',
        'git diff', 'docker ps', 'kubectl get', 'npm list', 'pip show', 'head', 'tail',
        'less', 'more', 'file', 'stat', 'du', 'df', 'ps', 'top', 'htop', 'who', 'w',
        '...(70+ commands total)'
    ]

def get_write_commands_list():
    """Get the list of write-like commands from sessions_enforce.py for display."""
    return [
        'rm', 'mv', 'cp', 'chmod', 'chown', 'mkdir', 'rmdir', 'systemctl', 'service',
        'apt', 'yum', 'npm install', 'pip install', 'make', 'cmake', 'sudo', 'kill',
        '...(and more)'
    ]

def interactive_configuration(project_root):
    """
    Interactive configuration wizard for cc-sessions.
    Returns a dict with all user configuration choices.
    """
    print(color('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', Colors.CYAN))
    print(color('  Configuration Setup', Colors.BOLD))
    print(color('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', Colors.CYAN))

    config = {
        'git_preferences': {},
        'environment': {},
        'blocked_actions': {
            'implementation_only_tools': [],
            'bash_read_patterns': [],
            'bash_write_patterns': []
        },
        'trigger_phrases': {},
        'features': {}
    }

    # Git Preferences Section
    print(color('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', Colors.CYAN))
    print(color('  Git Preferences', Colors.BOLD))
    print(color('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', Colors.CYAN))

    # Default branch
    print("Default branch name (e.g. 'main', 'master', 'develop', etc.):")
    print(color("*This is the branch you will merge to when completing tasks*", Colors.YELLOW))
    default_branch = input(color("[main] ", Colors.CYAN)) or 'main'
    config['git_preferences']['default_branch'] = default_branch

    # Submodules
    has_submodules = inquirer.list_input(
        message="Does this repository use git submodules?",
        choices=['Yes', 'No'],
        default='Yes'
    )
    config['git_preferences']['has_submodules'] = (has_submodules == 'Yes')

    # Staging pattern
    add_pattern = inquirer.list_input(
        message="When committing, how should files be staged?",
        choices=[
            'Ask me each time',
            'Stage all modified files automatically'
        ]
    )
    config['git_preferences']['add_pattern'] = 'ask' if 'Ask' in add_pattern else 'all'

    # Commit style
    commit_style = inquirer.list_input(
        message="Commit message style:",
        choices=[
            'Detailed (multi-line with description)',
            'Conventional (type: subject format)',
            'Simple (single line)'
        ]
    )
    if 'Detailed' in commit_style:
        config['git_preferences']['commit_style'] = 'detailed'
    elif 'Conventional' in commit_style:
        config['git_preferences']['commit_style'] = 'conventional'
    else:
        config['git_preferences']['commit_style'] = 'simple'

    # Auto-merge
    auto_merge = inquirer.list_input(
        message="After task completion:",
        choices=[
            'Ask me first',
            f'Auto-merge to {default_branch}'
        ]
    )
    config['git_preferences']['auto_merge'] = ('Auto-merge' in auto_merge)

    # Auto-push
    auto_push = inquirer.list_input(
        message="After committing/merging:",
        choices=[
            'Ask me first',
            'Auto-push to remote'
        ]
    )
    config['git_preferences']['auto_push'] = ('Auto-push' in auto_push)

    # Environment Section
    print(color('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', Colors.CYAN))
    print(color('  Environment Settings', Colors.BOLD))
    print(color('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', Colors.CYAN))

    developer_name = input(color("What should Claude call you? [developer] ", Colors.CYAN)) or 'developer'
    config['environment']['developer_name'] = developer_name

    # Detect OS
    os_name = platform.system()
    os_map = {'Windows': 'windows', 'Linux': 'linux', 'Darwin': 'macos'}
    detected_os = os_map.get(os_name, 'linux')

    os_choice = inquirer.list_input(
        message=f"Detected OS: {detected_os.capitalize()}",
        choices=[
            f'{detected_os.capitalize()} is correct',
            'Switch to Windows' if detected_os != 'windows' else None,
            'Switch to macOS' if detected_os != 'macos' else None,
            'Switch to Linux' if detected_os != 'linux' else None
        ],
        default=f'{detected_os.capitalize()} is correct'
    )
    if 'Windows' in os_choice:
        config['environment']['os'] = 'windows'
    elif 'macOS' in os_choice:
        config['environment']['os'] = 'macos'
    elif 'Linux' in os_choice:
        config['environment']['os'] = 'linux'
    else:
        config['environment']['os'] = detected_os

    # Detect shell
    detected_shell = os.environ.get('SHELL', 'bash').split('/')[-1]

    shell_choice = inquirer.list_input(
        message=f"Detected shell: {detected_shell}",
        choices=[
            f'{detected_shell} is correct',
            'Switch to bash' if detected_shell != 'bash' else None,
            'Switch to zsh' if detected_shell != 'zsh' else None,
            'Switch to fish' if detected_shell != 'fish' else None,
            'Switch to powershell' if detected_shell != 'powershell' else None,
            'Switch to cmd' if detected_shell != 'cmd' else None
        ],
        default=f'{detected_shell} is correct'
    )

    if 'bash' in shell_choice:
        config['environment']['shell'] = 'bash'
    elif 'zsh' in shell_choice:
        config['environment']['shell'] = 'zsh'
    elif 'fish' in shell_choice:
        config['environment']['shell'] = 'fish'
    elif 'powershell' in shell_choice:
        config['environment']['shell'] = 'powershell'
    elif 'cmd' in shell_choice:
        config['environment']['shell'] = 'cmd'
    else:
        config['environment']['shell'] = detected_shell

    # Blocked Actions Section
    print(color('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', Colors.CYAN))
    print(color('  Tool Blocking Configuration', Colors.BOLD))
    print(color('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', Colors.CYAN))

    print("Which tools should be blocked in discussion mode?")
    print(color("*Use Space to toggle, Enter to submit*\n", Colors.YELLOW))

    # Default blocked tools
    default_blocked = ['Edit', 'Write', 'MultiEdit', 'NotebookEdit']
    all_tools = ['Edit', 'Write', 'MultiEdit', 'NotebookEdit', 'Bash', 'Read', 'Glob', 'Grep', 'Task', 'TodoWrite']

    blocked_tools = inquirer.checkbox(
        message="Select tools to BLOCK in discussion mode",
        choices=all_tools,
        default=default_blocked
    )
    config['blocked_actions']['implementation_only_tools'] = blocked_tools

    # Bash patterns
    print(color('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', Colors.CYAN))
    print(color('  Read-Only Bash Commands', Colors.BOLD))
    print(color('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', Colors.CYAN))

    print("In Discussion mode, Claude can only use read-like tools (including commands in")
    print("the Bash tool).\n")
    print("To do this, we parse Claude's Bash tool input in Discussion mode to check for")
    print("write-like and read-only bash commands from a known list.\n")
    print("You might have some CLI commands that you want to mark as \"safe\" to use in")
    print("Discussion mode. For reference, here are the commands we already auto-approve")
    print("in Discussion mode:\n")
    print(color(f"  {', '.join(get_readonly_commands_list())}\n", Colors.YELLOW))
    print("Type any additional command you would like to auto-allow in Discussion mode and")
    print("hit \"enter\" to add it. You may add as many as you like. When you're done, hit")
    print("enter again to move to the next configuration option:\n")

    custom_read = []
    while True:
        cmd = input(color("> ", Colors.CYAN)).strip()
        if not cmd:
            break
        custom_read.append(cmd)
        print(color(f"✓ Added '{cmd}' to read-only commands", Colors.GREEN))

    config['blocked_actions']['bash_read_patterns'] = custom_read

    # Write patterns
    print(color('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', Colors.CYAN))
    print(color('  Write-Like Bash Commands', Colors.BOLD))
    print(color('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', Colors.CYAN))

    print("Similar to the read-only bash commands, we also check for write-like bash")
    print("commands during Discussion mode and block them.\n")
    print("You might have some CLI commands that you want to mark as \"blocked\" in")
    print("Discussion mode. For reference, here are the commands we already block in")
    print("Discussion mode:\n")
    print(color(f"  {', '.join(get_write_commands_list())}\n", Colors.YELLOW))
    print("Type any additional command you would like blocked in Discussion mode and hit")
    print("\"enter\" to add it. You may add as many as you like. When you're done, hit")
    print("\"enter\" again to move to the next configuration option:\n")

    custom_write = []
    while True:
        cmd = input(color("> ", Colors.CYAN)).strip()
        if not cmd:
            break
        custom_write.append(cmd)
        print(color(f"✓ Added '{cmd}' to write-like commands", Colors.GREEN))

    config['blocked_actions']['bash_write_patterns'] = custom_write

    # Extrasafe mode
    print(color('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', Colors.CYAN))
    print(color('  Extrasafe Mode', Colors.BOLD))
    print(color('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', Colors.CYAN))

    extrasafe = inquirer.list_input(
        message="What if Claude uses a bash command in discussion mode that's not in our\nread-only *or* our write-like list?",
        choices=[
            'Extrasafe OFF (allows unrecognized commands)',
            'Extrasafe ON (blocks unrecognized commands)'
        ]
    )
    config['blocked_actions']['extrasafe'] = ('ON' in extrasafe)

    # Trigger Phrases Section
    print(color('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', Colors.CYAN))
    print(color('  Trigger Phrases', Colors.BOLD))
    print(color('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', Colors.CYAN))

    print("While you can drive cc-sessions using our slash command API, the preferred way")
    print("is with (somewhat) natural language. To achieve this, we use unique trigger")
    print("phrases that automatically activate the 4 protocols and 2 driving modes in")
    print("cc-sessions:\n")
    print("  • Switch to implementation mode (default: \"yert\")")
    print("  • Switch to discussion mode (default: \"SILENCE\")")
    print("  • Create a new task/task file (default: \"mek:\")")
    print("  • Start a task/task file (default: \"start^:\")")
    print("  • Complete/archive the current task (default: \"finito\")")
    print("  • Compact context with active task (default: \"squish\")\n")

    customize_triggers = inquirer.list_input(
        message="Would you like to add any of your own custom trigger phrases?",
        choices=['Use defaults', 'Customize']
    )

    # Set defaults first
    config['trigger_phrases'] = {
        'implementation_mode': ['yert'],
        'discussion_mode': ['SILENCE'],
        'task_creation': ['mek:'],
        'task_startup': ['start^:'],
        'task_completion': ['finito'],
        'context_compaction': ['squish']
    }

    if customize_triggers == 'Customize':
        # Implementation mode
        print(color('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', Colors.CYAN))
        print(color('  Implementation Mode Trigger', Colors.BOLD))
        print(color('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', Colors.CYAN))
        print("The implementation mode trigger is used when Claude proposes todos for")
        print("implementation that you agree with. Once used, the user_messages hook will")
        print("automatically switch the mode to Implementation, notify Claude, and lock in the")
        print("proposed todo list to ensure Claude doesn't go rogue.\n")
        print("To add your own custom trigger phrase, think of something that is:")
        print("  • Easy to remember and type")
        print("  • Won't ever come up in regular operation\n")
        print("We recommend using symbols or uppercase for trigger phrases that may otherwise")
        print("be used naturally in conversation (ex. instead of \"stop\", you might use \"STOP\"")
        print("or \"st0p\" or \"--stop\").\n")
        print(f"Current phrase: \"yert\"\n")
        print("Type a trigger phrase to add and press \"enter\". When you're done, press \"enter\"")
        print("again to move on to the next step:\n")

        while True:
            phrase = input(color("> ", Colors.CYAN)).strip()
            if not phrase:
                break
            config['trigger_phrases']['implementation_mode'].append(phrase)
            print(color(f"✓ Added '{phrase}'", Colors.GREEN))

        # Discussion mode
        print(color('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', Colors.CYAN))
        print(color('  Discussion Mode Trigger', Colors.BOLD))
        print(color('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', Colors.CYAN))
        print("The discussion mode trigger is an emergency stop that immediately switches")
        print("Claude back to discussion mode. Once used, the user_messages hook will set the")
        print("mode to discussion and inform Claude that they need to re-align.\n")
        print(f"Current phrase: \"SILENCE\"\n")

        while True:
            phrase = input(color("> ", Colors.CYAN)).strip()
            if not phrase:
                break
            config['trigger_phrases']['discussion_mode'].append(phrase)
            print(color(f"✓ Added '{phrase}'", Colors.GREEN))

        # Task creation
        print(color('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', Colors.CYAN))
        print(color('  Task Creation Trigger', Colors.BOLD))
        print(color('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', Colors.CYAN))
        print("The task creation trigger activates the task creation protocol. Once used, the")
        print("user_messages hook will load the task creation protocol which guides Claude")
        print("through creating a properly structured task file with priority, success")
        print("criteria, and context manifest.\n")
        print(f"Current phrase: \"mek:\"\n")

        while True:
            phrase = input(color("> ", Colors.CYAN)).strip()
            if not phrase:
                break
            config['trigger_phrases']['task_creation'].append(phrase)
            print(color(f"✓ Added '{phrase}'", Colors.GREEN))

        # Task startup
        print(color('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', Colors.CYAN))
        print(color('  Task Startup Trigger', Colors.BOLD))
        print(color('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', Colors.CYAN))
        print("The task startup trigger activates the task startup protocol. Once used, the")
        print("user_messages hook will load the task startup protocol which guides Claude")
        print("through checking git status, creating branches, gathering context, and")
        print("proposing implementation todos.\n")
        print(f"Current phrase: \"start^:\"\n")

        while True:
            phrase = input(color("> ", Colors.CYAN)).strip()
            if not phrase:
                break
            config['trigger_phrases']['task_startup'].append(phrase)
            print(color(f"✓ Added '{phrase}'", Colors.GREEN))

        # Task completion
        print(color('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', Colors.CYAN))
        print(color('  Task Completion Trigger', Colors.BOLD))
        print(color('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', Colors.CYAN))
        print("The task completion trigger activates the task completion protocol. Once used,")
        print("the user_messages hook will load the task completion protocol which guides")
        print("Claude through running pre-completion checks, committing changes, merging to")
        print("main, and archiving the completed task.\n")
        print(f"Current phrase: \"finito\"\n")

        while True:
            phrase = input(color("> ", Colors.CYAN)).strip()
            if not phrase:
                break
            config['trigger_phrases']['task_completion'].append(phrase)
            print(color(f"✓ Added '{phrase}'", Colors.GREEN))

        # Context compaction
        print(color('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', Colors.CYAN))
        print(color('  Context Compaction Trigger', Colors.BOLD))
        print(color('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', Colors.CYAN))
        print("The context compaction trigger activates the context compaction protocol. Once")
        print("used, the user_messages hook will load the context compaction protocol which")
        print("guides Claude through running logging and context-refinement agents to preserve")
        print("task state before the context window fills up.\n")
        print(f"Current phrase: \"squish\"\n")

        while True:
            phrase = input(color("> ", Colors.CYAN)).strip()
            if not phrase:
                break
            config['trigger_phrases']['context_compaction'].append(phrase)
            print(color(f"✓ Added '{phrase}'", Colors.GREEN))

    # Feature Toggles Section
    print(color('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', Colors.CYAN))
    print(color('  Feature Toggles', Colors.BOLD))
    print(color('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', Colors.CYAN))

    print("Configure optional features and behaviors:\n")

    # Branch enforcement
    print("When working on a task, branch enforcement blocks edits to files unless they")
    print("are in a repo that is on the task branch. If in a submodule, the submodule")
    print("also has to be listed in the task file under the \"submodules\" field.\n")
    print("This prevents Claude from doing silly things with files outside the scope of")
    print("what you're working on, which can happen frighteningly often. But, it may not")
    print("be as flexible as you want. *It also doesn't work well with non-Git VCS*.\n")

    branch_enforcement = inquirer.list_input(
        message="Branch enforcement:",
        choices=[
            'Enabled (recommended for git workflows)',
            'Disabled (for alternative VCS like Jujutsu)'
        ]
    )
    config['features']['branch_enforcement'] = ('Enabled' in branch_enforcement)

    # Auto-ultrathink
    print("\nAuto-ultrathink adds \"[[ ultrathink ]]\" to *every message* you submit to")
    print("Claude Code. This is the most robust way to force maximum thinking for every")
    print("message.\n")
    print("If you are not a Claude Max x20 subscriber and/or you are budget-conscious,")
    print("it's recommended that you disable auto-ultrathink and manually trigger thinking")
    print("as needed.\n")

    auto_ultrathink = inquirer.list_input(
        message="Auto-ultrathink:",
        choices=[
            'Enabled',
            'Disabled (recommended for budget-conscious users)'
        ]
    )
    config['features']['auto_ultrathink'] = ('Enabled' == auto_ultrathink)

    # Nerd Fonts
    nerd_fonts = inquirer.list_input(
        message="Nerd Fonts display icons in the statusline for a visual interface:",
        choices=[
            'Enabled',
            'Disabled (ASCII fallback)'
        ]
    )
    config['features']['use_nerd_fonts'] = ('Enabled' == nerd_fonts)

    # Context warnings
    context_warnings = inquirer.list_input(
        message="Context warnings notify you when approaching token limits (85% and 90%):",
        choices=[
            'Both warnings enabled',
            'Only 90% warning',
            'Disabled'
        ]
    )
    if 'Both' in context_warnings:
        config['features']['context_warnings'] = {'warn_85': True, 'warn_90': True}
    elif 'Only' in context_warnings:
        config['features']['context_warnings'] = {'warn_85': False, 'warn_90': True}
    else:
        config['features']['context_warnings'] = {'warn_85': False, 'warn_90': False}

    # Statusline configuration
    print(color('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', Colors.CYAN))
    print(color('  Statusline Configuration', Colors.BOLD))
    print(color('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', Colors.CYAN))

    statusline_choice = inquirer.list_input(
        message="cc-sessions includes a statusline that shows context usage, current task, mode, and git branch. Would you like to use it?",
        choices=[
            'Yes, use cc-sessions statusline',
            'No, I have my own statusline'
        ]
    )

    if 'Yes' in statusline_choice:
        # Configure statusline in .claude/settings.json
        settings_file = project_root / '.claude' / 'settings.json'

        if settings_file.exists():
            with open(settings_file, 'r') as f:
                settings = json.load(f)
        else:
            settings = {}

        # Set statusline command
        settings['statusLine'] = {
            'type': 'command',
            'command': f'python $CLAUDE_PROJECT_DIR/sessions/statusline.py'
        }

        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)

        print(color('✓ Statusline configured in .claude/settings.json', Colors.GREEN))
    else:
        print(color('\nYou can add the cc-sessions statusline later by adding this to .claude/settings.json:', Colors.YELLOW))
        print(color('{\n  "statusLine": {\n    "type": "command",\n    "command": "python $CLAUDE_PROJECT_DIR/sessions/statusline.py"\n  }\n}', Colors.YELLOW))

    print(color('\n✓ Configuration complete!\n', Colors.GREEN))
    return config

def initialize_state_files(project_root):
    print(color('Initializing state files...', Colors.CYAN))

    # Set environment variable so shared_state can find project root
    os.environ['CLAUDE_PROJECT_DIR'] = str(project_root)

    # Add sessions/hooks to path so we can import shared_state
    sys.path.insert(0, str(project_root / 'sessions' / 'hooks'))

    # Import and call load_state/load_config from shared_state
    try:
        from shared_state import load_state, load_config
    except ImportError as e:
        print(color('⚠️  Could not import shared_state module. File copying may have failed.', Colors.YELLOW))
        print(color(f'Error: {e}', Colors.YELLOW))
        sys.exit(1)

    # These functions create the files if they don't exist
    load_state()
    config = load_config()

    # Detect and set OS in configuration
    os_name = platform.system()  # Returns 'Windows', 'Linux', or 'Darwin'
    os_map = {'Windows': 'windows', 'Linux': 'linux', 'Darwin': 'macos'}
    detected_os = os_map.get(os_name, 'linux')  # Default to linux if unknown

    # Update config with detected OS
    config.environment.os = detected_os
    save_config(config)

    # Verify files were created
    state_file = project_root / 'sessions' / 'sessions-state.json'
    config_file = project_root / 'sessions' / 'sessions-config.json'

    if not state_file.exists() or not config_file.exists():
        print(color('⚠️  State files were not created properly', Colors.YELLOW))
        print(color('You may need to initialize them manually on first run', Colors.YELLOW))

def kickstart_cleanup(project_root):
    """
    Delete kickstart files when user skips onboarding.
    Returns manual cleanup instructions for router/settings that require careful editing.
    """
    print(color('\n🧹 Removing kickstart files...', Colors.CYAN))

    sessions_dir = project_root / 'sessions'

    # 1. Delete kickstart hook (check both language variants)
    py_hook = sessions_dir / 'hooks' / 'kickstart_session_start.py'
    js_hook = sessions_dir / 'hooks' / 'kickstart_session_start.js'

    if py_hook.exists():
        py_hook.unlink()
        is_python = True
        print(color('   ✓ Deleted kickstart_session_start.py', Colors.GREEN))
    elif js_hook.exists():
        js_hook.unlink()
        is_python = False
        print(color('   ✓ Deleted kickstart_session_start.js', Colors.GREEN))
    else:
        is_python = True  # default fallback

    # 2. Delete kickstart protocols directory
    protocols_dir = sessions_dir / 'protocols' / 'kickstart'
    if protocols_dir.exists():
        shutil.rmtree(protocols_dir)
        print(color('   ✓ Deleted protocols/kickstart/', Colors.GREEN))

    # 3. Delete kickstart setup task
    task_file = sessions_dir / 'tasks' / 'h-kickstart-setup.md'
    if task_file.exists():
        task_file.unlink()
        print(color('   ✓ Deleted h-kickstart-setup.md', Colors.GREEN))

    # Generate language-specific cleanup instructions
    if is_python:
        instructions = """
Manual cleanup required (edit these files carefully):

1. sessions/api/router.py
   - Remove: from .kickstart_commands import handle_kickstart_command
   - Remove: 'kickstart': handle_kickstart_command from COMMAND_HANDLERS

2. .claude/settings.json
   - Remove the kickstart SessionStart hook entry

3. sessions/api/kickstart_commands.py
   - Delete this entire file
"""
    else:  # JavaScript
        instructions = """
Manual cleanup required (edit these files carefully):

1. sessions/api/router.js
   - Remove: const { handleKickstartCommand } = require('./kickstart_commands');
   - Remove: 'kickstart': handleKickstartCommand from COMMAND_HANDLERS

2. .claude/settings.json
   - Remove the kickstart SessionStart hook entry

3. sessions/api/kickstart_commands.js
   - Delete this entire file
"""

    print(color(instructions, Colors.YELLOW))
    return instructions

def installer_decision_flow(project_root):
    """
    Interactive decision flow for installer configuration and kickstart setup.
    Handles first-time detection, config import, interactive configuration, and kickstart choice.
    """
    print(color('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', Colors.CYAN))
    print(color('  Welcome to cc-sessions!', Colors.BOLD))
    print(color('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', Colors.CYAN))

    # First-time user detection
    first_time = inquirer.list_input(
        message="Is this your first time using cc-sessions?",
        choices=['Yes', 'No']
    )

    did_import = False

    if first_time == 'No':
        # Version detection for existing users
        version_check = inquirer.list_input(
            message="Have you used cc-sessions v0.3.0 or later (released October 2025)?",
            choices=['Yes', 'No']
        )

        if version_check == 'Yes':
            # Config/agent import workflow
            import_choice = inquirer.list_input(
                message="Would you like to import your configuration and agents?",
                choices=['Yes', 'No']
            )

            if import_choice == 'Yes':
                import_source = inquirer.list_input(
                    message="Where is your cc-sessions configuration?",
                    choices=['Local directory', 'Git repository URL', 'Skip import']
                )

                if import_source != 'Skip import':
                    source_path = input(color("Path or URL: ", Colors.CYAN)).strip()

                    # [PLACEHOLDER] Import config and agents, then present for interactive modification
                    # TODO: Implement config import with interactive modification feature
                    print(color('\n⚠️  Config import not yet implemented. Continuing with interactive configuration...', Colors.YELLOW))
                else:
                    print(color('\nSkipping import. Continuing with interactive configuration...', Colors.CYAN))
            else:
                print(color('\nContinuing with interactive configuration...', Colors.CYAN))
        else:
            # Treat as first-time user
            print(color('\nTreating as first-time user. Continuing with setup...', Colors.CYAN))

    # Run interactive configuration if we didn't import
    if not did_import:
        config = interactive_configuration(project_root)

    # Kickstart decision
    print(color('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', Colors.CYAN))
    print(color('  Learn cc-sessions with Kickstart', Colors.BOLD))
    print(color('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', Colors.CYAN))

    print("cc-sessions is an opinionated interactive workflow. You can learn how to use")
    print("it *with* Claude Code - we built a custom \"session\" called kickstart.\n")
    print("Kickstart will:")
    print("  • Teach you the features of cc-sessions")
    print("  • Help you set up your first task")
    print("  • Show you the 4 core protocols you can run")
    print("  • Help you customize cc-sessions subagents for your codebase\n")
    print("Time: 15-30 minutes\n")

    kickstart_choice = inquirer.list_input(
        message="Would you like to run kickstart on your first session?",
        choices=[
            'Yes (auto-start full kickstart tutorial)',
            'Just subagents (customize subagents but skip tutorial)',
            'No (skip tutorial, remove kickstart files)'
        ]
    )

    # Import edit_state from shared_state
    sys.path.insert(0, str(project_root / 'sessions' / 'hooks'))
    from shared_state import edit_state

    if 'Yes' in kickstart_choice:
        # Set metadata for full kickstart mode
        with edit_state() as s:
            s.metadata['kickstart'] = {'mode': 'full'}
        print(color('\n✓ Kickstart will auto-start on your first session', Colors.GREEN))

    elif 'Just subagents' in kickstart_choice:
        # Set metadata for subagents-only mode
        with edit_state() as s:
            s.metadata['kickstart'] = {'mode': 'subagents'}
        print(color('\n✓ Kickstart will guide you through subagent customization only', Colors.GREEN))

    else:  # No - skip kickstart
        # Don't set any metadata, run cleanup immediately
        print(color('\n⏭️  Skipping kickstart onboarding...', Colors.CYAN))
        kickstart_cleanup(project_root)
        print(color('\n✓ Kickstart files removed', Colors.GREEN))

    # Return kickstart choice for success message
    if 'Yes' in kickstart_choice:
        return 'full'
    elif 'Just subagents' in kickstart_choice:
        return 'subagents'
    else:
        return 'skip'

# Utility functions

def copy_file(src, dest):
    if src.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

        # Preserve executable permissions
        try:
            src_mode = src.stat().st_mode
            dest.chmod(src_mode)
        except Exception:
            # Ignore chmod errors
            pass

def copy_directory(src, dest):
    if not src.exists():
        return

    dest.mkdir(parents=True, exist_ok=True)

    for item in src.iterdir():
        src_path = src / item.name
        dest_path = dest / item.name

        if item.is_dir():
            copy_directory(src_path, dest_path)
        else:
            copy_file(src_path, dest_path)

def create_backup(project_root):
    """Create timestamped backup of tasks and agents before reinstall."""
    from datetime import datetime

    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    backup_dir = project_root / '.claude' / f'.backup-{timestamp}'

    print(color(f'\n💾 Creating backup at {backup_dir.relative_to(project_root)}/...', Colors.CYAN))

    backup_dir.mkdir(parents=True, exist_ok=True)

    # Backup all task files (includes done/, indexes/, and all task files)
    tasks_src = project_root / 'sessions' / 'tasks'
    task_count = 0
    if tasks_src.exists():
        tasks_dest = backup_dir / 'tasks'
        copy_directory(tasks_src, tasks_dest)

        # Count task files for user feedback and verification
        task_count = sum(1 for f in tasks_src.rglob('*.md'))
        backed_up_count = sum(1 for f in tasks_dest.rglob('*.md'))

        if task_count != backed_up_count:
            print(color(f'   ✗ Backup verification failed: {backed_up_count}/{task_count} files backed up', Colors.RED))
            raise Exception('Backup verification failed - aborting to prevent data loss')

        print(color(f'   ✓ Backed up {task_count} task files', Colors.GREEN))

    # Backup all agents
    agents_src = project_root / '.claude' / 'agents'
    agent_count = 0
    if agents_src.exists():
        agents_dest = backup_dir / 'agents'
        copy_directory(agents_src, agents_dest)

        agent_count = len(list(agents_src.glob('*.md')))
        backed_up_agents = len(list(agents_dest.glob('*.md')))

        if agent_count != backed_up_agents:
            print(color(f'   ✗ Backup verification failed: {backed_up_agents}/{agent_count} agents backed up', Colors.RED))
            raise Exception('Backup verification failed - aborting to prevent data loss')

        print(color(f'   ✓ Backed up {agent_count} agent files', Colors.GREEN))

    return backup_dir

def restore_tasks(project_root, backup_dir):
    """Restore tasks from backup after installation."""
    print(color('\n♻️  Restoring tasks...', Colors.CYAN))

    try:
        tasks_backup = backup_dir / 'tasks'
        if tasks_backup.exists():
            tasks_dest = project_root / 'sessions' / 'tasks'
            copy_directory(tasks_backup, tasks_dest)

            task_count = sum(1 for f in tasks_backup.rglob('*.md'))
            print(color(f'   ✓ Restored {task_count} task files', Colors.GREEN))
    except Exception as e:
        print(color(f'   ✗ Restore failed: {e}', Colors.RED))
        print(color(f'   Your backup is safe at: {backup_dir.relative_to(project_root)}/', Colors.YELLOW))
        print(color('   Manually copy files from backup/tasks/ to sessions/tasks/', Colors.YELLOW))
        # Don't raise - let user recover manually
#-#

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(color(f'\n❌ Fatal error: {error}', Colors.RED), file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
