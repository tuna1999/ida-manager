"""
GitHub repository and release models.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class GitHubAsset(BaseModel):
    """
    GitHub release asset model.

    Represents a file attached to a GitHub release.
    """

    name: str = Field(..., description="Asset filename")
    size: int = Field(..., description="Asset size in bytes")
    download_url: str = Field(..., description="Download URL")
    content_type: str = Field(..., description="Content type")


class GitHubRelease(BaseModel):
    """
    GitHub release model.

    Represents a GitHub release with its assets and metadata.
    """

    id: int = Field(..., description="Release ID")
    tag_name: str = Field(..., description="Git tag name")
    name: Optional[str] = Field(None, description="Release name")
    body: Optional[str] = Field(None, description="Release notes/body")
    published_at: Optional[datetime] = Field(None, description="Publication date")
    prerelease: bool = Field(False, description="Whether this is a pre-release")
    assets: List[GitHubAsset] = Field(default_factory=list, description="Release assets")
    html_url: str = Field(..., description="Release page URL")


class GitHubRepo(BaseModel):
    """
    GitHub repository model.

    Represents a GitHub repository with metadata.
    """

    id: int = Field(..., description="Repository ID")
    name: str = Field(..., description="Repository name")
    full_name: str = Field(..., description="Full repository name (owner/repo)")
    owner: str = Field(..., description="Repository owner")
    description: Optional[str] = Field(None, description="Repository description")
    stars: int = Field(0, description="Star count")
    topics: List[str] = Field(default_factory=list, description="Repository topics")
    language: Optional[str] = Field(None, description="Primary language")
    clone_url: str = Field(..., description="Git clone URL")
    html_url: str = Field(..., description="Repository webpage URL")
    default_branch: str = Field("main", description="Default branch name")
    last_fetched: Optional[datetime] = Field(None, description="Last fetch timestamp")


class GitHubContentItem(BaseModel):
    """
    GitHub repository content item model.

    Represents a file or directory in a GitHub repository.
    """

    name: str = Field(..., description="Item name")
    path: str = Field(..., description="Item path")
    type: str = Field(..., description="Item type (file, dir, etc.)")
    size: Optional[int] = Field(None, description="File size in bytes")
    download_url: Optional[str] = Field(None, description="Download URL")


class GitHubPluginInfo(BaseModel):
    """
    Combined GitHub plugin information.

    Aggregates repository info, releases, and parsed metadata for a plugin.
    """

    repository: GitHubRepo = Field(..., description="Repository information")
    releases: List[GitHubRelease] = Field(default_factory=list, description="Available releases")
    latest_release: Optional[GitHubRelease] = Field(None, description="Latest release")
    readme_content: Optional[str] = Field(None, description="README content")
    plugin_metadata: Optional[Dict] = Field(None, description="Parsed plugin metadata")
    is_valid_plugin: bool = Field(False, description="Whether this is a valid IDA plugin")
    detected_plugin_type: Optional[str] = Field(None, description="Detected plugin type")
