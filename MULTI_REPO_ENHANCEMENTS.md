# Multi-Repository Enhancements for cc-sessions

This document describes the enhancements made to cc-sessions to support multi-repository workspaces, making it more effective for developers working with connected projects.

## 🎯 Overview

The enhanced cc-sessions now provides:

- **Workspace Awareness**: Automatically detects and manages multiple connected repositories
- **Cross-Repository Task Management**: Create and coordinate tasks that span multiple projects
- **Intelligent Context Sharing**: Share relevant context between related repositories
- **Multi-Repo Agent System**: Specialized agents for cross-repository analysis and coordination
- **Workspace-Safe Operations**: Hooks that respect workspace boundaries while enabling collaboration

## 🏗️ Architecture

### Core Components

1. **Multi-Repo Configuration** (`multi_repo_config.py`)

   - Manages workspace-wide settings
   - Tracks repository relationships
   - Handles cross-repo context sharing

2. **Workspace Task Manager** (`workspace_task_manager.py`)

   - Creates and manages tasks across repositories
   - Coordinates subtasks between projects
   - Tracks dependencies and relationships

3. **Workspace Initialization** (`workspace_init.py`)

   - Auto-detects repositories in workspace
   - Sets up cross-repo awareness
   - Creates workspace-specific agent configurations

4. **Enhanced Hooks**
   - Updated to be workspace-aware
   - Respect workspace boundaries
   - Enable cross-repo operations when appropriate

## 🚀 Features

### 1. Automatic Repository Detection

The system automatically detects repositories in your workspace:

```bash
# Run workspace initialization
python3 cc_sessions/hooks/workspace_init.py
```

**Output:**

```
Initializing workspace awareness for cc-sessions...
Project root: /path/to/current/project
Workspace root: /path/to/workspace
Detected 3 repositories:
  - frontend-app (/path/to/workspace/frontend-app)
  - backend-api (/path/to/workspace/backend-api)
  - shared-lib (/path/to/workspace/shared-lib)
```

### 2. Cross-Repository Task Management

Create tasks that span multiple repositories:

```python
# Example: Create a cross-repo task
task_manager = WorkspaceTaskManager(workspace_root, project_root)
task = task_manager.create_cross_repo_task(
    task_name="Implement user authentication",
    description="Add JWT authentication across frontend and backend",
    affected_repos=["frontend-app", "backend-api", "shared-lib"],
    priority="high"
)
```

### 3. Workspace-Aware Context Preservation

Context preservation now considers the entire workspace:

- **Shared Context**: Common patterns and configurations across repos
- **Repository Relationships**: Dependencies and connections between projects
- **Cross-Repo Impact**: Understanding how changes affect other repositories

### 4. Multi-Repository Agent System

Specialized agents for workspace management:

#### Cross-Repository Analyzer

- Analyzes relationships between repositories
- Identifies shared dependencies and patterns
- Assesses impact of changes across repositories

#### Workspace Coordinator

- Coordinates tasks across multiple repositories
- Manages dependencies between projects
- Orchestrates complex multi-repo workflows

### 5. Enhanced Security and Boundaries

The hooks now respect workspace boundaries:

- **File Operations**: Allow operations within workspace, block outside
- **Context Sharing**: Share context between related repositories
- **Task Coordination**: Coordinate tasks without interfering with unrelated projects

## 📁 File Structure

```
workspace/
├── .claude/
│   ├── workspace_context.json      # Workspace-wide context
│   ├── multi_repo_config.json      # Multi-repo configuration
│   ├── workspace_tasks/            # Cross-repo tasks
│   └── agents/                     # Workspace-specific agents
├── project-1/
│   ├── .claude/
│   │   └── state/                  # Project-specific state
│   └── ...
├── project-2/
│   ├── .claude/
│   │   └── state/                  # Project-specific state
│   └── ...
└── shared-lib/
    ├── .claude/
    │   └── state/                  # Project-specific state
    └── ...
```

## 🔧 Configuration

### Workspace Configuration

The system creates a workspace configuration file at `.claude/multi_repo_config.json`:

```json
{
  "workspace_name": "Multi-Repo Workspace",
  "repositories": {
    "/path/to/project-1": {
      "name": "project-1",
      "type": "git",
      "description": "Main application",
      "active": true
    },
    "/path/to/project-2": {
      "name": "project-2",
      "type": "git",
      "description": "Supporting service",
      "active": true
    }
  },
  "shared_agents": ["cross_repo_analyzer", "workspace_coordinator"],
  "cross_repo_tasks": true,
  "context_sharing": true
}
```

### Agent Configuration

Workspace-specific agents are configured in `.claude/agents/`:

- `cross_repo_analyzer.json` - Cross-repository analysis agent
- `workspace_coordinator.json` - Workspace coordination agent

## 🎮 Usage Examples

### 1. Create a Cross-Repository Task

```bash
# Tell Claude to create a cross-repo task
Create a cross-repository task for:
Implement user authentication system across frontend and backend

# Claude will:
# 1. Analyze the workspace to identify relevant repositories
# 2. Create a workspace-level task
# 3. Generate repository-specific subtasks
# 4. Set up context sharing between repositories
```

### 2. Analyze Workspace Relationships

```bash
# Ask Claude to analyze workspace relationships
Analyze the relationships between repositories in this workspace

# Claude will:
# 1. Use the cross-repo analyzer agent
# 2. Identify shared dependencies and patterns
# 3. Map relationships between repositories
# 4. Suggest coordination strategies
```

### 3. Coordinate Changes Across Repositories

```bash
# Ask Claude to coordinate changes
Coordinate the implementation of the new API endpoint across all repositories

# Claude will:
# 1. Use the workspace coordinator agent
# 2. Create a coordinated implementation plan
# 3. Manage dependencies between repositories
# 4. Ensure consistent changes across projects
```

## 🔍 Validation and Testing

The validation system now includes multi-repo awareness:

```bash
# Run validation with workspace awareness
python3 validate_implementation.py

# The validation will:
# 1. Detect multi-repo environment
# 2. Test workspace-aware hooks
# 3. Validate cross-repo task management
# 4. Ensure proper boundary respect
```

## 🚨 Important Considerations

### 1. Workspace Boundaries

- Hooks respect workspace boundaries and won't interfere with unrelated projects
- File operations are limited to the workspace scope
- Context sharing is controlled and intentional

### 2. Performance

- Multi-repo awareness adds minimal overhead
- Context sharing is optimized to avoid duplication
- Repository detection is cached for performance

### 3. Security

- File operations are validated against workspace boundaries
- Cross-repo operations require explicit configuration
- Sensitive information is not shared between repositories

## 🔄 Migration from Single-Repo

If you're upgrading from single-repository cc-sessions:

1. **No Breaking Changes**: Existing functionality remains unchanged
2. **Automatic Detection**: The system automatically detects if you're in a multi-repo environment
3. **Gradual Adoption**: You can use multi-repo features as needed
4. **Backward Compatibility**: Single-repo workflows continue to work

## 🎯 Benefits for Multi-Repo Development

### 1. **Better Context Management**

- Understand relationships between repositories
- Share relevant context across projects
- Avoid duplicate work and inconsistencies

### 2. **Coordinated Development**

- Create tasks that span multiple repositories
- Coordinate changes across related projects
- Manage dependencies effectively

### 3. **Improved Efficiency**

- Reduce context switching between repositories
- Share common patterns and configurations
- Streamline cross-repo workflows

### 4. **Enhanced Collaboration**

- Better understanding of project relationships
- Coordinated task management
- Improved team communication

## 🛠️ Troubleshooting

### Common Issues

1. **Repository Not Detected**

   - Ensure the repository has a `.git` directory
   - Check that the repository is within the workspace scope
   - Run workspace initialization again

2. **Context Sharing Issues**

   - Verify workspace configuration
   - Check repository relationships
   - Ensure proper permissions

3. **Task Coordination Problems**
   - Verify task dependencies
   - Check repository status
   - Review workspace configuration

### Debug Mode

Enable debug mode for detailed logging:

```bash
export CC_SESSIONS_DEBUG=1
python3 cc_sessions/hooks/workspace_init.py
```

## 📚 Further Reading

- [Architecture Analysis](ARCHITECTURE_ANALYSIS.md) - Detailed architectural analysis
- [Agent Interface Specification](AGENT_INTERFACE_SPECIFICATION.md) - Agent system design
- [Context Optimization Analysis](CONTEXT_OPTIMIZATION_ANALYSIS.md) - Context management strategies
- [Validation Guide](VALIDATION_README.md) - Testing and validation procedures

---

The multi-repository enhancements make cc-sessions more powerful and flexible for complex development environments while maintaining the simplicity and effectiveness of the original system.
