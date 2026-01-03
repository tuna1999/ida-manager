# IDA Plugin Manager - Project Overview

## Project Purpose

IDA Plugin Manager is a **standalone Windows desktop application** for managing IDA Pro plugins. It helps users discover, install, update, and manage plugins for the IDA Pro disassembler.

**Key Features:**
- **Plugin Catalog Management**: Add plugins to catalog without immediate installation
- **Individual Plugin Actions**: Install, Update, Uninstall, Remove from catalog
- **Version Display**: Show commit hash for Clone method, version tag for Release method
- **Auto-tagging**: Automatic tag extraction from GitHub topics, description, README
- **Last Update Tracking**: Relative time display (2h ago, 1d ago, etc.)
- Plugin discovery from GitHub
- Installation via git clone or release downloads
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
| **Git Operations** | GitPython (>=3.1.40) |
| **Packaging** | Python packaging (>=23.0) |
| **Package Manager** | uv (recommended) |

## Architecture

The project follows a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│                     UI Layer (Dear PyGui)               │
│  MainWindow │ PluginBrowser │ StatusPanel │ Dialogs    │
│  [NEW: Status-based filtering, Version/Method/Tags columns] │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────┐
│              Service Layer (Business Logic)              │
│  PluginService │ PluginTagger │ DIContainer              │
│  [NEW: add_plugin_to_catalog, tag extraction]            │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────┐
│         Repository Pattern (Data Access)                │
│  PluginRepository │ update_status │ find_by_status       │
└───────────────────────────┬─────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────┴────────┐  ┌────────┴────────┐  ┌─────┴──────────┐
│  Database Layer │  │ GitHub Layer   │  │ Models Layer   │
│  SQLAlchemy 2.0 │  │ GitPython       │  │  Pydantic 2.0  │
│  [NEW: status,  │  │ [get_commit_hash│  │ [NEW:          │
│   installation_ │  │  pull_repository]│  │  PluginStatus, │
│   method, tags] │  │                 │  │  Installation  │
└────────────────┘  └─────────────────┘  │  Method enums] │
                                          └────────────────┘
```

## New Features (Plugin Catalog Management System - 2026-01-03)

### 1. Plugin Status Management
**Plugin Status Enum** ([src/models/plugin.py](src/models/plugin.py#L27-L32)):
```python
class PluginStatus(str, Enum):
    NOT_INSTALLED = "not_installed"  # Added to catalog but not installed
    INSTALLED = "installed"          # Successfully installed
    FAILED = "failed"                # Installation failed
```

**Database Schema Changes**:
- Added `status` column with enum values
- Added `installation_method` column (clone/release)
- Added `error_message` column for failed installations
- Added `added_at` column for catalog tracking
- Added `last_updated_at` column for GitHub update tracking
- Added `tags` column (JSON) for automatic tag storage

### 2. Installation Method Tracking
**Installation Method Enum** ([src/models/plugin.py](src/models/plugin.py#L35-L40)):
```python
class InstallationMethod(str, Enum):
    CLONE = "clone"      # Development version (commit hash shown as a1b2c3d)
    RELEASE = "release"  # Stable release (version tag shown as v1.2.3)
    UNKNOWN = "unknown"
```

**Version Display Logic** ([src/ui/plugin_browser.py](src/ui/plugin_browser.py#L241-L251)):
- Clone method: Show first 8 chars of commit hash `(a1b2c3d)`
- Release method: Show version tag `v1.2.3`
- Not installed: Show `-`

### 3. Auto-Tagging System
**PluginTagger Service** ([src/services/plugin_tagger.py](src/services/plugin_tagger.py)):
- 10 predefined tags: debugger, decompiler, hex-editor, network, analysis, scripting, yara, graph, patcher, unpacker
- Tag extraction from:
  - GitHub topics (highest priority)
  - Repository description (keyword analysis)
  - README content (keyword analysis)
  - Repository name (pattern matching)

**Tag Definitions**:
```python
TAG_DEFINITIONS = {
    "debugger": {"keywords": ["debug", "debugger", "breakpoint"], "topics": ["debugging"]},
    "decompiler": {"keywords": ["decompile", "decompiler"], "topics": ["decompiler"]},
    "hex-editor": {"keywords": ["hex", "binary", "byte"], "topics": ["hex-editor"]},
    # ... 7 more tags
}
```

### 4. GitPython Integration
**Replaced subprocess calls with GitPython** ([src/github/client.py](src/github/client.py#L371-L465)):
- `clone_repository()`: Uses `git.Repo.clone_from()` with shallow clone
- `get_commit_hash()`: Returns first 8 chars of current commit
- `pull_repository()`: Updates repository with `repo.remotes.origin.pull()`
- Better error handling with `git.GitCommandError`

### 5. UI/UX Enhancements
**New Table Columns** ([src/ui/main_window.py](src/ui/main_window.py#L307-L338)):
```
| Name | Version | Type | Method | Tags | Last Update | Status |
|------|---------|------|--------|------|-------------|--------|
| A    | v1.2.3  | M    |[Rel]  | [dbg][ana] | 2h ago |[Inst] |
| B    | a1b2c3d | L    |[Clon] | [hex]      | 1d ago |[Inst] |
| C    | -       | M    | -      | [net]      | Never |[Not]  |
```

**Status-Based Filtering**:
- Replaced "Installed/Available" checkboxes with "Installed/Not Installed/Failed"
- Statistics shown with colors:
  - Installed: Green (50, 200, 50)
  - Not Installed: Yellow (200, 200, 50)
  - Failed: Red (200, 50, 50)

**Action Buttons** ([src/ui/main_window.py](src/ui/main_window.py#L340-L365)):
- Install: Install selected plugin
- Update: Update installed plugin
- Uninstall: Remove plugin files (status → not_installed)
- Remove: Delete from catalog entirely

### 6. Add to Catalog Flow
**InstallURLDialog Changes** ([src/ui/dialogs/install_url_dialog.py](src/ui/dialogs/install_url_dialog.py)):
1. User enters GitHub URL
2. Click "Validate & Preview" → fetch metadata
3. Preview shows: Name, Description, Version, Author
4. Click "Add" → calls `plugin_service.add_plugin_to_catalog()`
5. Plugin saved with `status=not_installed`
6. Plugin appears in main window list

## Layer Descriptions

### 1. **Config Layer** (`src/config/`)
- **constants.py**: Application-wide constants
- **settings.py**: Configuration management
- Config: `%APPDATA%\IDA-Plugin-Manager\config.json`

### 2. **Models Layer** (`src/models/`)
- **plugin.py**: Pydantic models with new enums
  - `PluginStatus`: NOT_INSTALLED, INSTALLED, FAILED
  - `InstallationMethod`: CLONE, RELEASE, UNKNOWN
  - `Plugin`: Added status, installation_method, error_message, added_at, last_updated_at, tags fields
- **github_info.py**: GitHub models
- Uses Pydantic 2.0+ with `model_config` and `use_enum_values=True`

### 3. **Database Layer** (`src/database/`)
- **models.py**: SQLAlchemy 2.0 models
  - Added catalog fields to DBPlugin model
  - JSON columns for tags storage
- **db_manager.py**: CRUD operations
  - `update_plugin_status()`: Update plugin status and error_message
- **migrations.py**: Schema versioning
  - Version 2: Added catalog management fields
  - Migration system with up/down SQL

### 4. **Core Layer** (`src/core/`)
- **plugin_manager.py**: DEPRECATED - delegates to PluginService
- **ida_detector.py**: Discovers IDA installations
- **installer.py**: Uses GitPython for version tracking
- **version_manager.py**: Version validation

### 5. **Service Layer** (`src/services/`)
- **plugin_service.py**: Business logic
  - `add_plugin_to_catalog()`: Add plugin without installing
  - Updated install/uninstall to track status and installation_method
- **plugin_tagger.py**: NEW - Automatic tag extraction
  - 10 predefined tag definitions
  - Extracts tags from GitHub, description, README, repo name

### 6. **Repository Layer** (`src/repositories/`)
- **plugin_repository.py**: Data access
  - `update_status()`: Update plugin status
  - `_db_to_model()`: Handle new catalog fields
  - Proper metadata_json handling (defaults to {})

### 7. **GitHub Layer** (`src/github/`)
- **client.py**: GitPython integration
  - `clone_repository()`: Using git.Repo.clone_from()
  - `get_commit_hash()`: Get 8-char commit hash
  - `pull_repository()`: Update cloned repo
- **repo_parser.py**: Metadata extraction
- **release_fetcher.py**: Release filtering

### 8. **UI Layer** (`src/ui/`)
- **main_window.py**: Updated with catalog UI
  - New table columns (Version, Method, Tags, Last Update, Status)
  - Status-based filtering
  - Action buttons (Install, Update, Uninstall, Remove)
- **plugin_browser.py**: NEW - List component
  - Status filtering and display
  - Version display based on installation method
  - Tag badges display
  - Last update formatting
- **dialogs/install_url_dialog.py**: Changed to "Add" button
  - Calls `add_plugin_to_catalog()` instead of installing

### 9. **Utils Layer** (`src/utils/`)
- **version_utils.py**: Version comparison
- **validators.py**: URL parsing
- **file_ops.py**: File operations
- **logger.py**: Logging

## Plugin Types

### 1. **Modern Plugins** (IDA >= 9.0)
- **`ida-plugin.json`** manifest (singular, official format)
- Structure: `{"plugin": {name, version, entryPoint, ...}}`
- Auto-detected during catalog add

### 2. **Legacy Plugins** (IDA < 9.0)
- Single `.py` files or directories
- Entry points: `PLUGIN_ENTRY`, `IDP_init`
- Detected by file patterns and entry point search

## Installation Paths

**Priority Order:**
1. `$IDAUSR/plugins` (user plugins - highest priority)
2. `$IDADIR/plugins` (installation plugins)
3. Auto-create IDAUSR/plugins if needed

**IDAUSR Support:**
- Windows: `%APPDATA%\Hex-Rays\IDA Pro`
- Linux/Mac: `~/.idapro`
- Supports multiple paths (`;` on Windows, `:` on Unix)

## Key Design Patterns

1. **Service Layer Pattern**: Business logic separation
2. **Repository Pattern**: Data access abstraction
3. **Dependency Injection**: DIContainer for component management
4. **Result Objects**: Typed results instead of exceptions
5. **Model Conversion**: DB ↔ Pydantic via `_db_to_model()`
6. **Enum Usage**: Type-safe status and method tracking
7. **GitPython API**: Direct git operations (no subprocess)

## Current Implementation Status

**Completed (2026-01-03):**
- ✅ Database schema v2 with catalog fields
- ✅ Plugin Status and Installation Method enums
- ✅ Add to Catalog functionality
- ✅ Auto-tagging system (10 tags)
- ✅ GitPython integration
- ✅ Version display differentiation (clone vs release)
- ✅ Status-based filtering
- ✅ Method badges display
- ✅ Tags display (max 3)
- ✅ Last update relative time
- ✅ Action buttons (Install, Update, Uninstall, Remove)
- ✅ Migration system with main block

**Application Status:**
- Running successfully
- 1 plugin loaded from database
- All catalog features functional

## Database Migration

**Migration v2** ([src/database/migrations.py](src/database/migrations.py#L35-L78)):
```sql
-- New columns
ALTER TABLE plugins ADD COLUMN status VARCHAR(20) DEFAULT 'not_installed';
ALTER TABLE plugins ADD COLUMN installation_method VARCHAR(10);
ALTER TABLE plugins ADD COLUMN error_message TEXT;
ALTER TABLE plugins ADD COLUMN added_at DATETIME;
ALTER TABLE plugins ADD COLUMN last_updated_at DATETIME;
ALTER TABLE plugins ADD COLUMN tags JSON;

-- Indexes
CREATE INDEX idx_plugin_status ON plugins(status);
CREATE INDEX idx_last_updated ON plugins(last_updated_at);

-- Migrate existing data
UPDATE plugins SET status='installed' WHERE installed_version IS NOT NULL;
```

**Run migrations:**
```bash
uv run python -m src.database.migrations
uv run python -m src.database.migrations status
```

## Recent Bug Fixes (2026-01-03)

1. **Migration system**: Added `if __name__ == "__main__"` block
2. **Metadata validation**: Changed `metadata_json` default from `None` to `{}`
3. **Plugin type display**: Fixed `.value` access (use_enum_values makes it a string)
4. **Application startup**: Successfully loads plugins with new schema

## Important Notes

**Pydantic use_enum_values:**
- Plugin model has `use_enum_values=True`
- Enum fields are automatically converted to strings
- Access as `plugin.plugin_type[0].upper()` NOT `plugin.plugin_type.value[0].upper()`

**Git vs GitPython:**
- OLD: `subprocess.run(["git", "clone", ...])`
- NEW: `git.Repo.clone_from(...)`
- Better error handling and performance

**Status Flow:**
```
Add to catalog → NOT_INSTALLED
Install → INSTALLED
Uninstall → NOT_INSTALLED
Install failed → FAILED
Remove from catalog → deleted from DB
```

---

**Last Updated:** 2026-01-03
**Database Version:** 2
**Application Status:** Running successfully