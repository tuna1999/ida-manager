"""
Database manager for IDA Plugin Manager.

Handles all database operations including initialization, CRUD operations,
and queries for plugins, history, and settings.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session

from src.config.constants import DATABASE_FILE
from src.database.models import Base, Plugin, GitHubRepo, InstallationHistory, Settings


class DatabaseManager:
    """
    Database operations manager.

    Provides methods for all database operations including initialization,
    CRUD operations, and queries.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database manager.

        Args:
            db_path: Path to database file. Defaults to DATABASE_FILE.
        """
        self.db_path = db_path or DATABASE_FILE
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create engine
        self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)

        # Create session factory
        self.Session = sessionmaker(bind=self.engine)

    def init_database(self) -> bool:
        """
        Initialize database schema.

        Creates all tables if they don't exist.

        Returns:
            True if successful, False otherwise.
        """
        try:
            Base.metadata.create_all(self.engine)
            return True
        except Exception as e:
            print(f"Failed to initialize database: {e}")
            return False

    def get_session(self) -> Session:
        """
        Get a new database session.

        Returns:
            SQLAlchemy session object.
        """
        return self.Session()

    # ============ Plugin Operations ============

    def add_plugin(self, plugin: Plugin) -> bool:
        """
        Add a plugin to the database.

        Args:
            plugin: Plugin object to add

        Returns:
            True if successful, False otherwise.
        """
        try:
            session = self.get_session()
            session.add(plugin)
            session.commit()
            session.close()
            return True
        except Exception as e:
            print(f"Failed to add plugin: {e}")
            return False

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """
        Get a plugin by ID.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Plugin object or None if not found.
        """
        session = self.get_session()
        plugin = session.query(Plugin).filter_by(id=plugin_id).first()
        session.close()
        return plugin

    def get_plugin_by_name(self, name: str) -> Optional[Plugin]:
        """
        Get a plugin by name.

        Args:
            name: Plugin name

        Returns:
            Plugin object or None if not found.
        """
        session = self.get_session()
        plugin = session.query(Plugin).filter_by(name=name).first()
        session.close()
        return plugin

    def get_all_plugins(self) -> List[Plugin]:
        """
        Get all plugins from database.

        Returns:
            List of all plugins.
        """
        session = self.get_session()
        plugins = session.query(Plugin).all()
        session.close()
        return plugins

    def get_installed_plugins(self) -> List[Plugin]:
        """
        Get all installed plugins.

        Returns:
            List of installed plugins.
        """
        session = self.get_session()
        plugins = session.query(Plugin).filter(Plugin.installed_version.isnot(None)).all()
        session.close()
        return plugins

    def update_plugin(self, plugin: Plugin) -> bool:
        """
        Update an existing plugin.

        Args:
            plugin: Plugin object with updated data

        Returns:
            True if successful, False otherwise.
        """
        try:
            session = self.get_session()
            existing = session.query(Plugin).filter_by(id=plugin.id).first()
            if existing:
                for key, value in plugin.__dict__.items():
                    if not key.startswith("_"):
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                session.commit()
                session.close()
                return True
            session.close()
            return False
        except Exception as e:
            print(f"Failed to update plugin: {e}")
            return False

    def delete_plugin(self, plugin_id: str) -> bool:
        """
        Delete a plugin from database.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if successful, False otherwise.
        """
        try:
            session = self.get_session()
            plugin = session.query(Plugin).filter_by(id=plugin_id).first()
            if plugin:
                session.delete(plugin)
                session.commit()
                session.close()
                return True
            session.close()
            return False
        except Exception as e:
            print(f"Failed to delete plugin: {e}")
            return False

    def search_plugins(self, query: str) -> List[Plugin]:
        """
        Search plugins by name or description.

        Args:
            query: Search query string

        Returns:
            List of matching plugins.
        """
        session = self.get_session()
        plugins = (
            session.query(Plugin)
            .filter(
                (Plugin.name.ilike(f"%{query}%")) | (Plugin.description.ilike(f"%{query}%"))
            )
            .all()
        )
        session.close()
        return plugins

    def get_plugins_by_type(self, plugin_type: str) -> List[Plugin]:
        """
        Get plugins by type.

        Args:
            plugin_type: Plugin type ('legacy' or 'modern')

        Returns:
            List of plugins of the specified type.
        """
        session = self.get_session()
        plugins = session.query(Plugin).filter_by(plugin_type=plugin_type).all()
        session.close()
        return plugins

    def get_plugins_by_compatibility(self, ida_version: str) -> List[Plugin]:
        """
        Get plugins compatible with given IDA version.

        Args:
            ida_version: IDA Pro version string

        Returns:
            List of compatible plugins.
        """
        session = self.get_session()
        # Simple string comparison - should use proper version parsing
        plugins = (
            session.query(Plugin)
            .filter(
                (Plugin.ida_version_min.is_(None)) | (Plugin.ida_version_min <= ida_version),
                (Plugin.ida_version_max.is_(None)) | (Plugin.ida_version_max >= ida_version),
            )
            .all()
        )
        session.close()
        return plugins

    # ============ GitHub Repository Operations ============

    def save_github_repo(self, repo: GitHubRepo) -> bool:
        """
        Save or update GitHub repository information.

        Args:
            repo: GitHubRepo object

        Returns:
            True if successful, False otherwise.
        """
        try:
            session = self.get_session()
            existing = session.query(GitHubRepo).filter_by(id=repo.id).first()
            if existing:
                # Update existing
                existing.repo_owner = repo.repo_owner
                existing.repo_name = repo.repo_name
                existing.stars = repo.stars
                existing.last_fetched = repo.last_fetched
                existing.topics = repo.topics
                existing.releases = repo.releases
            else:
                session.add(repo)
            session.commit()
            session.close()
            return True
        except Exception as e:
            print(f"Failed to save GitHub repo: {e}")
            return False

    def get_github_repo(self, repo_id: str) -> Optional[GitHubRepo]:
        """
        Get GitHub repository by ID.

        Args:
            repo_id: Repository ID

        Returns:
            GitHubRepo object or None.
        """
        session = self.get_session()
        repo = session.query(GitHubRepo).filter_by(id=repo_id).first()
        session.close()
        return repo

    # ============ Installation History Operations ============

    def log_installation(
        self,
        plugin_id: str,
        action: str,
        version: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Log an installation action.

        Args:
            plugin_id: Plugin identifier
            action: Action type ('install', 'uninstall', 'update', 'failed')
            version: Plugin version
            success: Whether action succeeded
            error_message: Error message if failed

        Returns:
            True if successful, False otherwise.
        """
        try:
            session = self.get_session()
            history = InstallationHistory(
                plugin_id=plugin_id,
                action=action,
                version=version,
                success=success,
                error_message=error_message,
            )
            session.add(history)
            session.commit()
            session.close()
            return True
        except Exception as e:
            print(f"Failed to log installation: {e}")
            return False

    def get_installation_history(self, plugin_id: str, limit: int = 100) -> List[InstallationHistory]:
        """
        Get installation history for a plugin.

        Args:
            plugin_id: Plugin identifier
            limit: Maximum number of records to return

        Returns:
            List of installation history records.
        """
        session = self.get_session()
        history = (
            session.query(InstallationHistory)
            .filter_by(plugin_id=plugin_id)
            .order_by(InstallationHistory.timestamp.desc())
            .limit(limit)
            .all()
        )
        session.close()
        return history

    def get_recent_history(self, limit: int = 50) -> List[InstallationHistory]:
        """
        Get recent installation history across all plugins.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of recent installation history records.
        """
        session = self.get_session()
        history = (
            session.query(InstallationHistory)
            .order_by(InstallationHistory.timestamp.desc())
            .limit(limit)
            .all()
        )
        session.close()
        return history

    def clear_history(self, plugin_id: Optional[str] = None) -> bool:
        """
        Clear installation history.

        Args:
            plugin_id: Plugin ID to clear history for, or None for all history

        Returns:
            True if successful, False otherwise.
        """
        try:
            session = self.get_session()
            if plugin_id:
                session.query(InstallationHistory).filter_by(plugin_id=plugin_id).delete()
            else:
                session.query(InstallationHistory).delete()
            session.commit()
            session.close()
            return True
        except Exception as e:
            print(f"Failed to clear history: {e}")
            return False

    # ============ Settings Operations ============

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value.

        Args:
            key: Setting key
            default: Default value if key not found

        Returns:
            Setting value or default.
        """
        session = self.get_session()
        setting = session.query(Settings).filter_by(key=key).first()
        session.close()

        if setting and setting.value:
            try:
                return json.loads(setting.value)
            except json.JSONDecodeError:
                return setting.value
        return default

    def set_setting(self, key: str, value: Any) -> bool:
        """
        Set a setting value.

        Args:
            key: Setting key
            value: Setting value (will be JSON serialized)

        Returns:
            True if successful, False otherwise.
        """
        try:
            session = self.get_session()
            setting = session.query(Settings).filter_by(key=key).first()
            if setting:
                setting.value = json.dumps(value)
                setting.updated_at = datetime.utcnow()
            else:
                setting = Settings(key=key, value=json.dumps(value))
                session.add(setting)
            session.commit()
            session.close()
            return True
        except Exception as e:
            print(f"Failed to set setting: {e}")
            return False

    def get_all_settings(self) -> Dict[str, Any]:
        """
        Get all settings as a dictionary.

        Returns:
            Dictionary of all settings.
        """
        session = self.get_session()
        settings = session.query(Settings).all()
        session.close()

        result = {}
        for setting in settings:
            if setting.value:
                try:
                    result[setting.key] = json.loads(setting.value)
                except json.JSONDecodeError:
                    result[setting.key] = setting.value
        return result
