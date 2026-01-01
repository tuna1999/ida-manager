"""
SQLAlchemy database models for IDA Plugin Manager.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Plugin(Base):
    """
    Plugin database model.

    Stores plugin information including metadata, versions, and installation status.
    """

    __tablename__ = "plugins"

    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    author = Column(String, nullable=True)
    repository_url = Column(String, nullable=True)
    installed_version = Column(String, nullable=True)
    latest_version = Column(String, nullable=True)
    install_date = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, nullable=True)
    plugin_type = Column(Enum("legacy", "modern", name="plugin_type_enum"), nullable=False)
    ida_version_min = Column(String, nullable=True)
    ida_version_max = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    install_path = Column(String, nullable=True)
    metadata_json = Column(Text, nullable=True)  # JSON stored as text
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    installation_history = relationship("InstallationHistory", back_populates="plugin", cascade="all, delete-orphan")


class GitHubRepo(Base):
    """
    GitHub repository cache model.

    Caches GitHub repository information to reduce API calls.
    """

    __tablename__ = "github_repos"

    id = Column(String, primary_key=True)
    plugin_id = Column(String, ForeignKey("plugins.id", ondelete="CASCADE"), nullable=True)
    repo_owner = Column(String, nullable=False)
    repo_name = Column(String, nullable=False)
    stars = Column(Integer, default=0)
    last_fetched = Column(DateTime, nullable=True)
    topics = Column(Text, nullable=True)  # JSON array stored as text
    releases = Column(Text, nullable=True)  # JSON array stored as text


class InstallationHistory(Base):
    """
    Installation history model.

    Tracks all installation, uninstallation, and update operations.
    """

    __tablename__ = "installation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plugin_id = Column(String, ForeignKey("plugins.id", ondelete="CASCADE"), nullable=False)
    action = Column(Enum("install", "uninstall", "update", "failed", name="action_enum"), nullable=False)
    version = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    error_message = Column(Text, nullable=True)
    success = Column(Boolean, default=True)

    # Relationships
    plugin = relationship("Plugin", back_populates="installation_history")


class Settings(Base):
    """
    Application settings model.

    Stores application-wide settings and preferences.
    """

    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)  # JSON stored as text
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
