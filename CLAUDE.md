# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Running the Application
```bash
uv run python -m src.main
```

### Testing
```bash
# Run all tests
uv run pytest

# Run single test file
uv run pytest tests/test_plugin_manager.py

# Run with coverage
uv run pytest --cov=src
```

### Code Quality
```bash
# Format code
uv run black src/

# Lint code
uv run ruff check src/

# Type checking
uv run mypy src/
```

### Installing Dependencies
```bash
# Using uv (recommended)
uv sync

# Using pip
pip install -e .
```

## Architecture Overview

This is a Windows desktop application for managing IDA Pro plugins. The architecture follows a layered design with clear separation of concerns.

### Core Layer (`src/core/`)
The business logic layer that orchestrates all plugin operations:

- **PluginManager**: Central orchestrator that coordinates IDA detection, installation, updates, and database operations. All plugin operations flow through this class.
- **IDADetector**: Discovers IDA Pro installations via Windows registry, common paths, and PATH environment variable. Handles version extraction.
- **PluginInstaller**: Executes actual plugin installation/uninstallation. Supports two installation methods: git clone (development version) and release download (stable version).
- **VersionManager**: Handles version parsing, comparison, and compatibility validation between plugins and IDA versions.

### Database Layer (`src/database/`)
SQLite-based persistence using SQLAlchemy:

- **DBPlugin, GitHubRepo, InstallationHistory, Settings**: SQLAlchemy models defining the schema
- **DatabaseManager**: Provides CRUD operations for all entities
- JSON columns are stored as TEXT and require manual serialization/deserialization

### GitHub Integration (`src/github/`)
Handles GitHub API interaction for plugin discovery and installation:

- **GitHubClient**: Manages API requests with rate limit tracking and caching. Can clone repos, fetch releases, download assets.
- **RepoParser**: Extracts plugin metadata from README and `plugins.json` files. Detects whether a repo contains a valid IDA plugin (legacy vs modern).
- **ReleaseFetcher**: Filters and selects appropriate releases based on IDA version compatibility.

### UI Layer (`src/ui/`)
Dear PyGui-based native Windows interface:

- **MainWindow**: Creates the viewport, menu bar, toolbar, and manages application lifecycle
- **PluginBrowser**: Displays filtered/sorted plugin list, handles selection
- **StatusPanel**: Shows operation feedback with color-coded messages
- **themes.py**: Defines Dark and Light color schemes
- **Dialogs** (`src/ui/dialogs/`):
  - **AboutDialog**: Application information and version display
  - **PluginDetailsDialog**: Comprehensive plugin information with scrollable content
  - **ConfirmDialog**: User confirmation prompts for destructive actions
  - **InstallURLDialog**: GitHub URL input for plugin installation
  - **ProgressDialog**: Progress feedback for long-running operations
  - **SettingsDialog**: Configuration with tabbed interface and file browser

### Data Flow

1. User action (e.g., "install plugin") triggers UI callback
2. UI calls PluginManager method
3. PluginManager uses IDADetector to find IDA installation
4. PluginManager uses PluginInstaller to install (via GitHubClient for downloads)
5. PluginManager updates database via DatabaseManager
6. UI updates via StatusPanel feedback

### Plugin Types

- **Legacy**: Single `.py` files or directories with IDA entry points (`PLUGIN_ENTRY`, `IDP_init`)
- **Modern**: Directory with `plugins.json` manifest containing name, version, entry_point, dependencies

### Configuration Location
`%APPDATA%\IDA-Plugin-Manager\config.json` - contains IDA paths, GitHub token, UI preferences, update settings.

### Key Patterns

- **Dependency Injection**: Core components accept dependencies in `__init__` for testability
- **Result Objects**: Operations return typed result objects (InstallationResult, ValidationResult) rather than raising exceptions
- **Model Conversion**: Database models (SQLAlchemy) are converted to Pydantic models when moving between layers (`_db_to_model()` in PluginManager)
- **Backup/Restore**: File operations in `src/utils/file_ops.py` provide backup before destructive operations

### Dear PyGui Patterns

Critical patterns when working with Dear PyGui 2.x:

- **UUID-Based Widget Tags**: All widget tags must be unique to avoid "Alias already exists" errors when reopening dialogs
  ```python
  import uuid
  self._instance_id = str(uuid.uuid4())[:8]
  dialog_tag = f"settings_dialog_{self._instance_id}"
  ```

- **Parent Parameter for child_window**: When creating child_window outside initialization context, explicitly specify parent
  ```python
  # Use this pattern to avoid "Parent could not be deduced" errors
  dpg.child_window(tag="plugins_child_window", parent="main_window")
  ```

- **Modal Dialog Lifecycle**: Always check if dialog exists before showing, and delete properly on close
  ```python
  if self._dialog_id and dpg.does_item_exist(self._dialog_id):
      dpg.delete_item(self._dialog_id)
      self._dialog_id = None
  ```

### Utilities

- **src/utils/validators.py**: GitHub URL validation and parsing (`validate_github_url()`, `parse_github_url()`)
- **src/utils/logger.py**: Logging configuration
- **src/utils/file_ops.py**: Safe file operations with backup/restore
- **.serena/memories/**: Additional context and patterns for Serena agent (project overview, known issues, GUI task checklist)
