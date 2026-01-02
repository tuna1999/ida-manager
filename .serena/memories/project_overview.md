# IDA Plugin Manager - Project Overview

## Project Purpose

IDA Plugin Manager is a **standalone Windows desktop application** for managing IDA Pro plugins. It helps users discover, install, update, and manage plugins for the IDA Pro disassembler.

**Key Features:**
- Plugin discovery from GitHub
- Installation via git clone or release downloads
- Version tracking and update checking
- Compatibility validation with IDA versions
- Support for both legacy (IDA < 9.0) and modern (IDA >= 9.0) plugin formats
- Native Windows UI built with Dear PyGui

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Language** | Python 3.10+ |
| **UI Framework** | Dear PyGui (>=1.1.0) |
| **Database** | SQLite via SQLAlchemy 2.0+ |
| **Data Validation** | Pydantic 2.0+ |
| **HTTP Client** | Requests (>=2.31.0) |
| **Git Operations** | GitPython (>=3.1.0) |
| **Packaging** | Python packaging (>=23.0) |
| **Package Manager** | uv (recommended) |

## Architecture

The project follows a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│                     UI Layer (Dear PyGui)               │
│  MainWindow │ PluginBrowser │ StatusPanel │ Dialogs    │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────┐
│                  Core Business Logic Layer              │
│  PluginManager │ IDADetector │ PluginInstaller │        │
│  VersionManager                                         │
└───────────────────────────┬─────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────┴────────┐  ┌────────┴────────┐  ┌─────┴──────────┐
│  Database Layer │  │ GitHub Layer   │  │ Models Layer   │
│  SQLAlchemy 2.0 │  │ GitHubClient   │  │  Pydantic 2.0  │
└────────────────┘  └─────────────────┘  └────────────────┘
```

## Layer Descriptions

### 1. **Config Layer** (`src/config/`)
- **constants.py**: Application-wide constants
- **settings.py**: Configuration management with dataclasses
- Config stored in: `%APPDATA%\IDA-Plugin-Manager\config.json`

### 2. **Models Layer** (`src/models/`)
- **plugin.py**: Pydantic models for plugins (Plugin, PluginMetadata, ValidationResult, etc.)
- **github_info.py**: GitHub-related models (GitHubRepo, GitHubRelease, GitHubAsset)
- Uses Pydantic 2.0+ with `model_config` (NOT `Config` class from v1)

### 3. **Database Layer** (`src/database/`)
- **models.py**: SQLAlchemy 2.0 models with `Mapped[]` type hints
- **db_manager.py**: CRUD operations
- **migrations.py**: Database schema migrations
- JSON columns stored as TEXT, require manual serialization/deserialization

### 4. **Core Layer** (`src/core/`)
- **plugin_manager.py**: Central orchestrator for all plugin operations
- **ida_detector.py**: Discovers IDA installations via registry/PATH
- **installer.py**: Executes plugin installation/uninstallation
- **version_manager.py**: Version parsing and compatibility validation

### 5. **GitHub Layer** (`src/github/`)
- **client.py**: GitHub API client with rate limiting and caching
- **repo_parser.py**: Extracts plugin metadata from README/plugins.json
- **release_fetcher.py**: Filters releases by IDA version compatibility

### 6. **UI Layer** (`src/ui/`)
- **main_window.py**: Main application window with Dear PyGui
- **plugin_browser.py**: Plugin list display and filtering
- **status_panel.py**: Operation feedback display
- **themes.py**: Dark/Light color schemes
- **dialogs/**: Modal dialogs (confirm, install_url, progress, settings, about, plugin_details)

### 7. **Utils Layer** (`src/utils/`)
- **file_ops.py**: File operations with backup support
- **logger.py**: Logging configuration
- **validators.py**: Input validation utilities

## Plugin Types

1. **Legacy Plugins**: Single `.py` files with IDA entry points (`PLUGIN_ENTRY`, `IDP_init`)
2. **Modern Plugins**: Directory with `plugins.json` manifest containing:
   - name, version, entry_point, dependencies, ida_version constraints

## Data Flow Example (Plugin Installation)

```
User clicks "Install" 
    → UI callback in MainWindow
    → calls PluginManager.install_plugin()
    → uses IDADetector to find IDA path
    → uses PluginInstaller to install files
    → uses GitHubClient to download if needed
    → updates database via DatabaseManager
    → UI updates via StatusPanel
```

## Key Design Patterns

1. **Dependency Injection**: Core components accept dependencies in `__init__` for testability
2. **Result Objects**: Operations return typed result objects (InstallationResult, ValidationResult) instead of raising exceptions
3. **Model Conversion**: Database models (SQLAlchemy) → Pydantic models via `_db_to_model()` pattern
4. **Dataclass Config**: Configuration uses Python dataclasses with type hints
5. **Enum Usage**: Plugin types and statuses use Python enums
6. **UUID Tags**: Dialogs use UUID-based tags to avoid Dear PyGui alias conflicts

## Current Implementation Status

**Completed:**
- ✅ Config Layer (with tests)
- ✅ Models Layer (Pydantic models)
- ✅ Database Layer (SQLAlchemy 2.0, with tests)
- ✅ Utils Layer (validators complete)
- ✅ UI Layer (MainWindow, PluginBrowser, StatusPanel, themes)
- ✅ All Dialogs (Confirm, InstallURL, Progress, Settings, About, PluginDetails)
- ✅ File dialog for IDA path browsing
- ✅ Progress dialog integration
- ✅ Update checking with results display
- ✅ 56 tests covering config, models, database
- ✅ Dialog tag conflict fixes with UUID

**In Progress:**
- ⚠️ Core Layer (PluginManager scaffolded, needs IDADetector/PluginInstaller/VersionManager)
- ⚠️ GitHub Layer (GitHubClient scaffolded, needs RepoParser/ReleaseFetcher)

**Todo List:**
1. Complete GitHub Integration Layer (RepoParser, ReleaseFetcher)
2. Complete Core Business Logic Layer (IDADetector, PluginInstaller, VersionManager)
3. Add integration tests
4. Create user documentation

## Important: Dear PyGui Tag Management

**Critical Pattern**: All dialogs MUST use unique UUID-based tags to avoid "Alias already exists" errors when opening dialogs multiple times.

```python
import uuid

class MyDialog:
    def __init__(self, dpg):
        self.dpg = dpg
        self._instance_id = str(uuid.uuid4())[:8]
        self._dialog_tag = f"my_dialog_{self._instance_id}"
```

This pattern is used in:
- [SettingsDialog](src/ui/dialogs/settings_dialog.py)
- [AboutDialog](src/ui/dialogs/about_dialog.py)
- [PluginDetailsDialog](src/ui/dialogs/plugin_details_dialog.py)

## Recent Bug Fixes (2026-01-02)

1. **Settings Dialog Tag Conflicts**: Fixed by adding UUID-based instance IDs to all widget tags
2. **About Dialog Tag Conflicts**: Fixed by adding UUID-based instance IDs
3. **Plugin Details Dialog Tag Conflicts**: Fixed by adding UUID-based instance IDs
4. **MainWindow _refresh_ui Context Issues**: Fixed by specifying `parent="main_window"` for child_window
