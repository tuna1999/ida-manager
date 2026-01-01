"""
Plugin data models using Pydantic for validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PluginType(str, Enum):
    """Plugin type enumeration."""

    LEGACY = "legacy"
    MODERN = "modern"


class CompatibilityStatus(str, Enum):
    """Plugin compatibility status."""

    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"


class Plugin(BaseModel):
    """
    Plugin data model.

    Represents a plugin with all its metadata and installation information.
    """

    id: str = Field(..., description="Unique plugin identifier")
    name: str = Field(..., description="Plugin name")
    description: Optional[str] = Field(None, description="Plugin description")
    author: Optional[str] = Field(None, description="Plugin author")
    repository_url: Optional[str] = Field(None, description="GitHub repository URL")
    installed_version: Optional[str] = Field(None, description="Currently installed version")
    latest_version: Optional[str] = Field(None, description="Latest available version")
    install_date: Optional[datetime] = Field(None, description="Installation date")
    last_updated: Optional[datetime] = Field(None, description="Last update date")
    plugin_type: PluginType = Field(..., description="Plugin type (legacy or modern)")
    ida_version_min: Optional[str] = Field(None, description="Minimum IDA version required")
    ida_version_max: Optional[str] = Field(None, description="Maximum IDA version supported")
    is_active: bool = Field(True, description="Whether plugin is active")
    install_path: Optional[str] = Field(None, description="Installation path")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata")

    class Config:
        """Pydantic config."""

        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class PluginMetadata(BaseModel):
    """
    Plugin metadata extracted from repository or manifest.

    Contains information parsed from README, plugins.json, or other sources.
    """

    name: str = Field(..., description="Plugin name")
    version: Optional[str] = Field(None, description="Plugin version")
    description: Optional[str] = Field(None, description="Plugin description")
    author: Optional[str] = Field(None, description="Plugin author")
    ida_version_min: Optional[str] = Field(None, description="Minimum IDA version")
    ida_version_max: Optional[str] = Field(None, description="Maximum IDA version")
    dependencies: List[str] = Field(default_factory=list, description="Plugin dependencies")
    entry_point: Optional[str] = Field(None, description="Main entry point file")
    readme_content: Optional[str] = Field(None, description="README content")

    class Config:
        """Pydantic config."""

        use_enum_values = True


class ValidationResult(BaseModel):
    """
    Result of plugin validation.

    Indicates whether a plugin is valid and provides error details if not.
    """

    valid: bool = Field(..., description="Whether validation passed")
    plugin_type: Optional[PluginType] = Field(None, description="Detected plugin type")
    error: Optional[str] = Field(None, description="Error message if validation failed")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")


class InstallationResult(BaseModel):
    """
    Result of plugin installation/uninstallation operation.

    Provides success status and any errors or warnings.
    """

    success: bool = Field(..., description="Whether operation succeeded")
    plugin_id: str = Field(..., description="Plugin ID")
    message: str = Field(..., description="Human-readable result message")
    error: Optional[str] = Field(None, description="Error message if failed")
    previous_version: Optional[str] = Field(None, description="Previous version if updated")
    new_version: Optional[str] = Field(None, description="New version installed")


class UpdateInfo(BaseModel):
    """
    Information about available plugin updates.

    Contains details about available updates and versions.
    """

    has_update: bool = Field(..., description="Whether an update is available")
    current_version: Optional[str] = Field(None, description="Currently installed version")
    latest_version: Optional[str] = Field(None, description="Latest available version")
    changelog: Optional[str] = Field(None, description="Changelog for new version")
    release_url: Optional[str] = Field(None, description="URL to latest release")
