# Code Style Conventions

## Project-Specific Conventions

### File Organization

**Layer Structure:**
```
src/
├── config/          # Configuration and constants
├── models/          # Pydantic data models
├── database/        # Database models and managers
├── core/            # Core business logic (installer, detector, etc.)
├── services/        # Service layer (orchestration)
├── repositories/    # Repository pattern (data access)
├── containers/      # Dependency injection
├── github/          # GitHub API integration
├── ui/              # Dear PyGui UI components
│   └── dialogs/     # Modal dialogs
└── utils/           # Utility functions
```

**Import Order:**
1. Standard library imports
2. Third-party imports (grouped by package)
3. Local imports (grouped by layer)
4. Type-only imports (TYPE_CHECKING)

```python
# Standard library
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# Third-party
import git
import requests
from pydantic import BaseModel, Field

# Local - models
from src.models.plugin import Plugin, PluginStatus

# Local - services
from src.services.plugin_service import PluginService
```

### Naming Conventions

**Classes:** PascalCase
```python
class PluginService:
class InstallationMethod:
class PluginRepository:
```

**Functions/Methods:** snake_case
```python
def add_plugin_to_catalog():
def get_commit_hash():
def update_plugin_status():
```

**Private Methods:** Leading underscore
```python
def _db_to_model():
def _model_to_db():
def _ensure_migration_table():
```

**Constants:** UPPER_SNAKE_CASE
```python
GITHUB_API_BASE = "https://api.github.com"
DEFAULT_BRANCH = "main"
```

**Instance Variables:** snake_case with optional underscore for "private"
```python
self.plugin_service = plugin_service
self._validated_url = None  # "private" internal state
self._dialog_id = None
```

### Pydantic Models

**Use Pydantic 2.0+ Style:**
```python
from pydantic import BaseModel, ConfigDict, Field

class Plugin(BaseModel):
    """Plugin data model."""
    
    id: str = Field(..., description="Unique plugin identifier")
    name: str = Field(..., description="Plugin name")
    status: PluginStatus = Field(default=PluginStatus.NOT_INSTALLED)
    tags: List[str] = Field(default_factory=list)
    
    model_config = ConfigDict(
        use_enum_values=True,  # Auto-convert enums to strings
    )
    
    @field_serializer("install_date")
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None
```

**Key Points:**
- Use `Field()` for all fields with descriptions
- Use `default_factory=list` for mutable defaults (NOT `default=[]`)
- Use `ConfigDict` NOT `Config` class (Pydantic 2.0)
- Add `model_config = ConfigDict(use_enum_values=True)` for enums
- Use `@field_serializer` for custom serialization

### SQLAlchemy Models

**Use SQLAlchemy 2.0+ Style:**
```python
from sqlalchemy import DateTime, Enum, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

class Plugin(Base):
    __tablename__ = "plugins"
    
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        Enum("not_installed", "installed", "failed", 
              name="plugin_status_enum", create_constraint=True),
        nullable=False,
        default="not_installed",
        index=True,
    )
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

**Key Points:**
- Use `Mapped[type]` for type hints
- Use `mapped_column()` for column definitions
- Use `Enum()` for enum columns with `create_constraint=True`
- Use `JSON` type for JSON columns (NOT String + manual serialization)
- Always add `index=True` for frequently queried columns

### Enum Classes

**String Enums for Status/Type:**
```python
from enum import Enum

class PluginStatus(str, Enum):
    """Plugin installation status."""
    NOT_INSTALLED = "not_installed"
    INSTALLED = "installed"
    FAILED = "failed"

class InstallationMethod(str, Enum):
    """How plugin was installed."""
    CLONE = "clone"
    RELEASE = "release"
    UNKNOWN = "unknown"
```

**Key Points:**
- Inherit from `str` and `Enum` for string enums
- Use UPPERCASE for enum values
- Add docstrings for clarity
- Use with `use_enum_values=True` in Pydantic models

### Service Layer Pattern

**Service Class Structure:**
```python
from logging import getLogger

logger = getLogger(__name__)

class PluginService:
    """
    Plugin service for business logic.
    
    Orchestrates operations between repositories, GitHub client,
    and other components.
    """
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        github_client: GitHubClient,
        installer: PluginInstaller,
    ):
        """Initialize service with dependencies."""
        self.db = db_manager
        self.github_client = github_client
        self.installer = installer
        self.repository = PluginRepository(db_manager)
    
    def add_plugin_to_catalog(
        self,
        url: str,
        metadata: Optional[PluginMetadata] = None,
    ) -> bool:
        """
        Add plugin to catalog without installing.
        
        Args:
            url: GitHub repository URL
            metadata: Parsed plugin metadata (optional)
        
        Returns:
            True if added successfully
        """
        logger.info(f"Adding plugin to catalog: {url}")
        
        # Implementation...
        
        return True
```

**Key Points:**
- Inject dependencies via `__init__`
- Use docstrings with Args/Returns sections
- Use logger for important operations
- Return result objects (not raise exceptions for business logic)
- Keep methods focused on single responsibility

### Repository Pattern

**Repository Class Structure:**
```python
class PluginRepository:
    """Repository for Plugin data access."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize repository."""
        self.db = db_manager
    
    def find_by_id(self, plugin_id: str) -> Optional[Plugin]:
        """Find plugin by ID."""
        db_plugin = self.db.get_plugin(plugin_id)
        if db_plugin:
            return self._db_to_model(db_plugin)
        return None
    
    def save(self, plugin: Plugin) -> bool:
        """Save plugin (create or update)."""
        existing = self.find_by_id(plugin.id)
        if existing:
            return self.db.update_plugin(self._model_to_db(plugin))
        else:
            return self.db.add_plugin(self._model_to_db(plugin))
    
    def _db_to_model(self, db_plugin: DBPlugin) -> Plugin:
        """Convert database model to Pydantic model."""
        # Parse enums, JSON fields, etc.
        return Plugin(...)
    
    def _model_to_db(self, plugin: Plugin) -> DBPlugin:
        """Convert Pydantic model to database model."""
        # Serialize to JSON, etc.
        return DBPlugin(...)
```

**Key Points:**
- Abstract data access behind clean interface
- Use `find_by_*`, `save`, `delete` naming
- Handle model conversions in private methods
- Return Pydantic models (NOT database models)
- Default dict fields to `{}` instead of `None`

### Git Operations

**Use GitPython (NOT subprocess):**
```python
import git
from pathlib import Path

class GitHubClient:
    
    def clone_repository(
        self, 
        repo_url: str, 
        destination: Path, 
        branch: str = "main"
    ) -> bool:
        """Clone repository using GitPython."""
        try:
            git.Repo.clone_from(
                repo_url,
                destination,
                branch=branch,
                depth=1,  # Shallow clone for speed
            )
            logger.info(f"Cloned to {destination}")
            return True
        except git.GitCommandError as e:
            logger.error(f"Clone failed: {e.stderr}")
            return False
    
    def get_commit_hash(self, repo_path: Path) -> Optional[str]:
        """Get current commit hash (first 8 chars)."""
        try:
            repo = git.Repo(repo_path)
            return repo.head.commit.hexsha[:8]
        except Exception as e:
            logger.error(f"Failed to get commit hash: {e}")
            return None
```

**Key Points:**
- Use `git.Repo.clone_from()` for cloning
- Use `depth=1` for shallow clones (faster)
- Handle `git.GitCommandError` for git-specific errors
- Return first 8 chars of commit hash for display
- Use `repo.remotes.origin.pull()` for updates

### Dear PyGui UI Patterns

**UUID-Based Tags for Dialogs:**
```python
import uuid

class SettingsDialog:
    """Settings dialog with UUID-based tags."""
    
    def __init__(self, dpg):
        self.dpg = dpg
        # Generate unique instance ID
        self._instance_id = str(uuid.uuid4())[:8]
        # Create tags with instance ID
        self._dialog_tag = f"settings_dialog_{self._instance_id}"
        self._save_button_tag = f"settings_save_{self._instance_id}"
    
    def show(self):
        """Show dialog."""
        # Check if already open
        if self.dpg.does_item_exist(self._dialog_tag):
            self.dpg.focus_item(self._dialog_tag)
            return
        
        with self.dpg.window(
            label="Settings",
            tag=self._dialog_tag,
            modal=True,
        ):
            self.dpg.add_button(
                label="Save",
                tag=self._save_button_tag,
                callback=self._on_save,
            )
    
    def _close(self):
        """Close dialog."""
        if self.dpg.does_item_exist(self._dialog_tag):
            self.dpg.delete_item(self._dialog_tag)
```

**Key Points:**
- Always use UUID-based tags for dialogs
- Check if dialog exists before showing
- Use `focus_item()` if already open
- Delete dialog properly on close
- Use `does_item_exist()` before operations

**Specify Parent Explicitly:**
```python
# When creating child_window outside parent context
dpg.child_window(
    tag="plugins_child_window",
    parent="main_window",  # Always specify parent
    autosize_x=True,
    autosize_y=True,
)
```

### Error Handling

**Return Result Objects (Not Raise Exceptions):**
```python
from pydantic import BaseModel

class InstallationResult(BaseModel):
    """Result of installation operation."""
    success: bool
    plugin_id: str
    message: str
    error: Optional[str] = None
    new_version: Optional[str] = None

def install_plugin(self, url: str) -> InstallationResult:
    """Install plugin."""
    try:
        # Installation logic
        return InstallationResult(
            success=True,
            plugin_id=plugin_id,
            message=f"Installed {plugin_id}",
            new_version=version,
        )
    except Exception as e:
        logger.error(f"Installation failed: {e}")
        return InstallationResult(
            success=False,
            plugin_id=plugin_id,
            message="Installation failed",
            error=str(e),
        )
```

**Key Points:**
- Use result objects for business logic
- Log errors with context
- Return success + message + error
- Don't raise exceptions for expected failures

### Logging

**Use Structured Logging:**
```python
from logging import getLogger

logger = getLogger(__name__)

class PluginService:
    
    def add_plugin_to_catalog(self, url: str) -> bool:
        """Add plugin to catalog."""
        logger.info(f"Adding plugin to catalog: {url}")
        
        try:
            # Do work
            logger.info(f"Successfully added {plugin_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add plugin: {e}", exc_info=True)
            return False
```

**Log Levels:**
- `DEBUG`: Detailed debugging info
- `INFO`: Important operations (add, install, update)
- `WARNING**: Unexpected but recoverable issues
- `ERROR`: Errors that don't crash application
- `CRITICAL`: Serious errors that may crash

**Key Points:**
- Get logger with `getLogger(__name__)`
- Use f-strings for log messages
- Include `exc_info=True` for exceptions
- Log important operations at INFO level

### Type Hints

**Use Type Hints Everywhere:**
```python
from typing import List, Optional, Dict, Callable
from pathlib import Path

def find_plugins(
    query: str,
    limit: Optional[int] = None,
) -> List[Plugin]:
    """Search for plugins."""
    pass

def install_plugin(
    self,
    url: str,
    method: str = "clone",
) -> InstallationResult:
    """Install plugin."""
    pass

def set_callback(
    self,
    callback: Optional[Callable[[Plugin], None]] = None,
) -> None:
    """Set callback function."""
    pass
```

**Key Points:**
- Use `Optional[T]` for nullable values
- Use `List[T]`, `Dict[K, V]` for collections
- Use `Callable[[Args], ReturnType]` for functions
- Use `Path` for file paths (not strings)

### Context Managers

**Use Context Managers for Resources:**
```python
class GitHubClient:
    
    def close(self):
        """Close session."""
        if self._session:
            self._session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

# Usage
with GitHubClient() as client:
    client.get_repository_info(owner, repo)
```

**Key Points:**
- Implement `__enter__` and `__exit__`
- Clean up resources in `__exit__`
- Use with statements for resource management

### Testing Conventions

**Test File Naming:**
```
tests/
├── test_plugin_service.py
├── test_plugin_repository.py
├── test_github_client.py
└── conftest.py  # Shared fixtures
```

**Test Structure:**
```python
import pytest
from unittest.mock import Mock

class TestPluginService:
    """Test PluginService."""
    
    def test_add_plugin_to_catalog_success(self):
        """Test successful add to catalog."""
        # Arrange
        service = PluginService(mock_db, mock_github, ...)
        url = "https://github.com/user/repo"
        
        # Act
        result = service.add_plugin_to_catalog(url)
        
        # Assert
        assert result is True
        mock_db.add_plugin.assert_called_once()
    
    def test_add_plugin_to_catalog_already_exists(self):
        """Test adding duplicate plugin."""
        # Arrange
        service = PluginService(...)
        mock_repository.find_by_id.return_value = Plugin(...)
        
        # Act
        result = service.add_plugin_to_catalog(url)
        
        # Assert
        assert result is False
```

**Key Points:**
- Use descriptive test names (test_what_expected_result)
- Use AAA pattern (Arrange, Act, Assert)
- Mock external dependencies
- Test both success and failure cases

### Documentation

**Docstring Format:**
```python
def add_plugin_to_catalog(
    self,
    url: str,
    metadata: Optional[PluginMetadata] = None,
) -> bool:
    """
    Add plugin to catalog without installing.
    
    This saves the plugin information to the database with
    status='not_installed' so it can be installed later.
    
    Args:
        url: GitHub repository URL
        metadata: Parsed plugin metadata (optional)
    
    Returns:
        True if added successfully, False if already exists
    
    Example:
        >>> service = PluginService(...)
        >>> result = service.add_plugin_to_catalog(
        ...     "https://github.com/user/repo"
        ... )
        >>> assert result is True
    """
```

**Key Points:**
- Use Google-style docstrings
- Include summary, detailed description, Args, Returns
- Add Examples for complex functions
- Document side effects

### Constants

**Define in constants.py:**
```python
# src/config/constants.py

GITHUB_API_BASE = "https://api.github.com"
DEFAULT_BRANCH = "main"
MAX_TAGS_DISPLAY = 3

# Tag definitions
TAG_DEFINITIONS = {
    "debugger": {
        "keywords": ["debug", "debugger"],
        "topics": ["debugging"],
    },
    # ...
}
```

**Key Points:**
- Use UPPER_SNAKE_CASE
- Group related constants
- Add comments for complex values
- Import with `from src.config.constants import CONSTANT`

---

**Last Updated:** 2026-01-03
**Status:** Current conventions ✅