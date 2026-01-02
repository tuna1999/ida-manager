# IDA Plugin Manager - Code Style & Conventions

## File Naming

- **Python modules**: `snake_case.py` (e.g., `plugin_manager.py`, `ida_detector.py`)
- **Test files**: `test_<module>.py` (e.g., `test_database.py`, `test_config_and_models.py`)
- **Class names**: `PascalCase` (e.g., `PluginManager`, `GitHubClient`)

## Code Style (per pyproject.toml)

| Tool | Setting | Value |
|------|---------|-------|
| **Black** | line-length | 100 characters |
| **Black** | target-version | py310 |
| **Ruff** | line-length | 100 characters |
| **Ruff** | select | E, F, W, I, N |

## Type Hints

**Required throughout the codebase:**

```python
from typing import Optional, List, Dict, Any

def install_plugin(
    self,
    plugin_id: str,
    version: Optional[str] = None
) -> InstallationResult:
    """Install a plugin."""
    pass
```

**Use Python 3.10+ style:**
- `Optional[str]` instead of `str | None`
- `List[str]` instead of `list[str]`
- `Dict[str, int]` instead of `dict[str, int]`

**For SQLAlchemy 2.0 models:**
```python
from sqlalchemy.orm import Mapped, mapped_column

id: Mapped[str] = mapped_column(String(255), primary_key=True)
name: Mapped[str] = mapped_column(String(255), nullable=False)
```

## Docstrings

**Google-style docstrings:**

```python
def install_plugin(
    self,
    plugin_id: str,
    version: Optional[str] = None
) -> InstallationResult:
    """
    Install a plugin from GitHub.

    Args:
        plugin_id: Unique identifier for the plugin
        version: Specific version to install (defaults to latest)

    Returns:
        InstallationResult with success status and details

    Raises:
        ValueError: If plugin_id is invalid
    """
    pass
```

**Module docstrings:**
```python
"""
Plugin management core business logic.

Orchestrates IDA detection, plugin installation, updates, and database operations.
"""
```

## Import Order

```python
# 1. Standard library
import json
from pathlib import Path
from typing import Optional

# 2. Third-party imports
from pydantic import BaseModel, Field
from sqlalchemy.orm import Mapped, mapped_column

# 3. Local imports
from src.config.constants import CONFIG_DIR
from src.models.plugin import Plugin
```

## Pydantic Models (v2.0+)

**Use `model_config` (NOT `Config` class):**

```python
from pydantic import BaseModel, ConfigDict, Field

class Plugin(BaseModel):
    """Plugin data model."""
    
    id: str = Field(..., description="Unique plugin identifier")
    name: str = Field(..., description="Plugin name")
    
    # Pydantic v2 style
    model_config = ConfigDict(
        use_enum_values=True,
    )
```

**Field serializers:**
```python
from pydantic import field_serializer

class Plugin(BaseModel):
    install_date: Optional[datetime] = Field(None)
    
    @field_serializer("install_date")
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO format string."""
        return value.isoformat() if value else None
```

## Enum Classes

```python
from enum import Enum

class PluginType(str, Enum):
    """Plugin type enumeration."""
    
    LEGACY = "legacy"
    MODERN = "modern"
```

## Dataclasses (for Config)

```python
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class IDAConfig:
    """IDA Pro configuration."""
    
    install_path: str = ""
    version: str = ""
    auto_detect: bool = True
    rate_limit: Dict[str, int] = field(default_factory=lambda: {"remaining": 60, "reset": 0})
```

## Constants

**Use UPPER_CASE for constants:**
```python
GITHUB_API_BASE = "https://api.github.com"
DEFAULT_AUTO_CHECK_UPDATES = True
PLUGIN_TYPE_LEGACY = "legacy"
```

## Method Naming

- **Public methods**: `snake_case` (e.g., `install_plugin()`, `get_repository_info()`)
- **Private methods**: `_leading_underscore` (e.g., `_check_rate_limit()`, `_db_to_model()`)
- **Boolean returners**: `is_`, `has_`, `can_` (e.g., `is_active`, `has_update`)

## Result Objects Pattern

**Instead of raising exceptions, return result objects:**

```python
# Don't do this:
def install_plugin(self, plugin_id: str) -> None:
    if not self._validate_plugin(plugin_id):
        raise ValueError("Invalid plugin")

# Do this:
from src.models.plugin import InstallationResult

def install_plugin(self, plugin_id: str) -> InstallationResult:
    """Install a plugin and return result object."""
    if not self._validate_plugin(plugin_id):
        return InstallationResult(
            success=False,
            plugin_id=plugin_id,
            message="Installation failed",
            error="Invalid plugin ID"
        )
    return InstallationResult(
        success=True,
        plugin_id=plugin_id,
        message="Plugin installed successfully"
    )
```

## Database JSON Columns

**JSON stored as TEXT requires manual serialization:**

```python
import json

# Reading
plugin.metadata = json.loads(db_plugin.metadata_json) if db_plugin.metadata_json else {}

# Writing
db_plugin.metadata_json = json.dumps(plugin.metadata) if plugin.metadata else None
```

## Logging

```python
import logging

logger = logging.getLogger(__name__)

logger.info("Plugin installation started")
logger.warning("Rate limit approaching")
logger.error("Failed to download plugin", exc_info=True)
```

## Error Handling

```python
try:
    result = self.github_client.get_repository_info(repo_url)
except requests.RequestException as e:
    logger.error(f"Network error: {e}")
    return InstallationResult(
        success=False,
        plugin_id=plugin_id,
        message="Network error",
        error=str(e)
    )
```

## Class Structure Example

```python
"""Module docstring."""

import logging
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Main plugin management orchestrator.
    
    Coordinates IDA detection, installation, updates, and database operations.
    """
    
    def __init__(self, db_manager: DatabaseManager, github_client: GitHubClient):
        """
        Initialize PluginManager.
        
        Args:
            db_manager: Database manager instance
            github_client: GitHub API client instance
        """
        self.db_manager = db_manager
        self.github_client = github_client
    
    def install_plugin(
        self,
        plugin_id: str,
        version: Optional[str] = None
    ) -> InstallationResult:
        """
        Install a plugin.
        
        Args:
            plugin_id: Plugin identifier
            version: Optional version specification
            
        Returns:
            Installation result with success status
        """
        pass
    
    def _private_method(self) -> None:
        """Private helper method."""
        pass
```

## Testing Conventions

```python
class TestPluginModels:
    """Test plugin-related Pydantic models."""
    
    def test_plugin_creation(self):
        """Test creating a plugin instance."""
        pass
    
    def test_plugin_validation_fails_with_invalid_data(self):
        """Test that validation fails with invalid data."""
        pass
```

## Windows-Specific Paths

```python
from pathlib import Path

# Use Path for cross-platform compatibility
config_path = Path("%APPDATA%/IDA-Plugin-Manager/config.json")
ida_path = Path("C:/Program Files/IDA Pro 9.0/plugins")
```
