"""
SQLAlchemy database models for IDA Plugin Manager.

Compatible with SQLAlchemy 2.0+
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text, func, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class Plugin(Base):
    """
    Plugin database model.

    Stores plugin information including metadata, versions, and installation status.
    """

    __tablename__ = "plugins"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    repository_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    installed_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    latest_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    install_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    plugin_type: Mapped[str] = mapped_column(
        Enum("legacy", "modern", name="plugin_type_enum", create_constraint=True),
        nullable=False,
    )
    ida_version_min: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ida_version_max: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1", index=True)
    install_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON stored as text

    # Plugin catalog fields
    status: Mapped[str] = mapped_column(
        Enum("not_installed", "installed", "failed", name="plugin_status_enum", create_constraint=True),
        nullable=False,
        default="not_installed",
        index=True,
    )
    installation_method: Mapped[Optional[str]] = mapped_column(
        Enum("clone", "release", name="install_method_enum", create_constraint=True),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    added_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Stored as JSON array
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    installation_history: Mapped[list["InstallationHistory"]] = relationship(
        "InstallationHistory",
        back_populates="plugin",
        cascade="all, delete-orphan",
    )


class GitHubRepo(Base):
    """
    GitHub repository cache model.

    Caches GitHub repository information to reduce API calls.
    """

    __tablename__ = "github_repos"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    plugin_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("plugins.id", ondelete="CASCADE"),
        nullable=True,
    )
    repo_owner: Mapped[str] = mapped_column(String(255), nullable=False)
    repo_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    last_fetched: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    topics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array stored as text
    releases: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array stored as text


class InstallationHistory(Base):
    """
    Installation history model.

    Tracks all installation, uninstallation, and update operations.
    """

    __tablename__ = "installation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plugin_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("plugins.id", ondelete="CASCADE"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        Enum("install", "uninstall", "update", "failed", name="action_enum", create_constraint=True),
        nullable=False,
    )
    version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    plugin: Mapped["Plugin"] = relationship("Plugin", back_populates="installation_history")


class Settings(Base):
    """
    Application settings model.

    Stores application-wide settings and preferences.
    """

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON stored as text
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
