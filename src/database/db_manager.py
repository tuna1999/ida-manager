"""
Database manager for IDA Plugin Manager.

Handles all database operations including initialization, CRUD operations,
and queries for plugins, history, and settings.

REFACTORED: Uses context managers for all session operations to prevent resource leaks.
"""

import json
from datetime import datetime, timezone
from logging import getLogger
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.config.constants import DATABASE_FILE
from src.database.models import Base, Plugin, GitHubRepo, InstallationHistory, Settings

logger = getLogger(__name__)


class DatabaseManager:
    """
    Database operations manager.

    Provides methods for all database operations including initialization,
    CRUD operations, and queries.

    All session operations now use context managers to prevent resource leaks.
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

        # Create session factory with expire_on_commit=False to avoid detached instance errors
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)

    def init_database(self) -> bool:
        """
        Initialize database schema.

        Creates all tables if they don't exist.

        Returns:
            True if successful, False otherwise.
        """
        try:
            Base.metadata.create_all(self.engine)
            logger.info(f"Database initialized at {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False

    def get_session(self) -> Session:
        """
        Get a new database session.

        Returns:
            SQLAlchemy session object.

        Note: For most operations, use the context manager methods instead.
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
            with self.Session() as session:
                session.add(plugin)
                session.commit()
                logger.debug(f"Added plugin: {plugin.id}")
                return True
        except Exception as e:
            logger.error(f"Failed to add plugin {plugin.id}: {e}")
            return False

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """
        Get a plugin by ID.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Plugin object or None if not found.
        """
        with self.Session() as session:
            return session.query(Plugin).filter_by(id=plugin_id).first()

    def get_plugin_by_name(self, name: str) -> Optional[Plugin]:
        """
        Get a plugin by name.

        Args:
            name: Plugin name

        Returns:
            Plugin object or None if not found.
        """
        with self.Session() as session:
            return session.query(Plugin).filter_by(name=name).first()

    def get_all_plugins(self) -> List[Plugin]:
        """
        Get all plugins from database.

        Returns:
            List of all plugins.
        """
        with self.Session() as session:
            return session.query(Plugin).all()

    def get_installed_plugins(self) -> List[Plugin]:
        """
        Get all installed plugins.

        Returns:
            List of installed plugins.
        """
        with self.Session() as session:
            return session.query(Plugin).filter(Plugin.installed_version.isnot(None)).all()

    def update_plugin(self, plugin: Plugin) -> bool:
        """
        Update an existing plugin.

        Args:
            plugin: Plugin object with updated data

        Returns:
            True if successful, False otherwise.
        """
        try:
            with self.Session() as session:
                existing = session.query(Plugin).filter_by(id=plugin.id).first()
                if existing:
                    # Update specific fields only
                    existing.name = plugin.name
                    existing.description = plugin.description
                    existing.author = plugin.author
                    existing.repository_url = plugin.repository_url
                    existing.installed_version = plugin.installed_version
                    existing.latest_version = plugin.latest_version
                    existing.install_date = plugin.install_date
                    existing.last_updated = plugin.last_updated
                    existing.plugin_type = plugin.plugin_type
                    existing.ida_version_min = plugin.ida_version_min
                    existing.ida_version_max = plugin.ida_version_max
                    existing.is_active = plugin.is_active
                    existing.install_path = plugin.install_path
                    existing.metadata_json = plugin.metadata_json
                    existing.updated_at = datetime.now(timezone.utc)

                    session.commit()
                    logger.debug(f"Updated plugin: {plugin.id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to update plugin {plugin.id}: {e}")
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
            with self.Session() as session:
                plugin = session.query(Plugin).filter_by(id=plugin_id).first()
                if plugin:
                    session.delete(plugin)
                    session.commit()
                    logger.debug(f"Deleted plugin: {plugin_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to delete plugin {plugin_id}: {e}")
            return False

    def update_plugin_status(
        self, plugin_id: str, status: str, error_message: Optional[str] = None
    ) -> bool:
        """
        Update plugin installation status.

        Args:
            plugin_id: Plugin identifier
            status: New status ('not_installed', 'installed', 'failed')
            error_message: Optional error message for failed status

        Returns:
            True if successful, False otherwise.
        """
        try:
            with self.Session() as session:
                plugin = session.query(Plugin).filter_by(id=plugin_id).first()
                if plugin:
                    plugin.status = status
                    plugin.error_message = error_message
                    if status == "installed":
                        from datetime import datetime, timezone

                        plugin.install_date = datetime.now(timezone.utc)
                    session.commit()
                    logger.debug(f"Updated plugin status: {plugin_id} -> {status}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to update plugin status {plugin_id}: {e}")
            return False

    def search_plugins(self, query: str) -> List[Plugin]:
        """
        Search plugins by name or description.

        Args:
            query: Search query string

        Returns:
            List of matching plugins.
        """
        with self.Session() as session:
            return (
                session.query(Plugin)
                .filter(
                    (Plugin.name.ilike(f"%{query}%")) | (Plugin.description.ilike(f"%{query}%"))
                )
                .all()
            )

    def get_plugins_by_type(self, plugin_type: str) -> List[Plugin]:
        """
        Get plugins by type.

        Args:
            plugin_type: Plugin type ('legacy' or 'modern')

        Returns:
            List of plugins of the specified type.
        """
        with self.Session() as session:
            return session.query(Plugin).filter_by(plugin_type=plugin_type).all()

    def get_plugins_by_compatibility(self, ida_version: str) -> List[Plugin]:
        """
        Get plugins compatible with given IDA version.

        Uses proper version comparison via IDAVersion utility.

        Args:
            ida_version: IDA Pro version string

        Returns:
            List of compatible plugins.
        """
        from src.utils.version_utils import is_version_compatible

        with self.Session() as session:
            # Get all plugins and filter in Python (more reliable than SQL comparison)
            all_plugins = session.query(Plugin).all()

            compatible_plugins = []
            for plugin in all_plugins:
                if is_version_compatible(
                    plugin.ida_version_min,
                    plugin.ida_version_max,
                    ida_version
                ):
                    compatible_plugins.append(plugin)

            return compatible_plugins

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
            with self.Session() as session:
                existing = session.query(GitHubRepo).filter_by(id=repo.id).first()
                if existing:
                    # Update fields manually
                    existing.plugin_id = repo.plugin_id
                    existing.repo_owner = repo.repo_owner
                    existing.repo_name = repo.repo_name
                    existing.stars = repo.stars
                    existing.last_fetched = repo.last_fetched
                    existing.topics = repo.topics
                    existing.releases = repo.releases
                else:
                    session.add(repo)
                session.commit()
                logger.debug(f"Saved GitHub repo: {repo.id}")
                return True
        except Exception as e:
            logger.error(f"Failed to save GitHub repo {repo.id}: {e}")
            return False

    def get_github_repo(self, repo_id: str) -> Optional[GitHubRepo]:
        """
        Get GitHub repository by ID.

        Args:
            repo_id: Repository ID

        Returns:
            GitHubRepo object or None.
        """
        with self.Session() as session:
            return session.query(GitHubRepo).filter_by(id=repo_id).first()

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
            with self.Session() as session:
                history = InstallationHistory(
                    plugin_id=plugin_id,
                    action=action,
                    version=version,
                    success=success,
                    error_message=error_message,
                )
                session.add(history)
                session.commit()
                logger.debug(f"Logged installation: {plugin_id} - {action}")
                return True
        except Exception as e:
            logger.error(f"Failed to log installation {plugin_id}: {e}")
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
        with self.Session() as session:
            return (
                session.query(InstallationHistory)
                .filter_by(plugin_id=plugin_id)
                .order_by(InstallationHistory.timestamp.desc())
                .limit(limit)
                .all()
            )

    def get_recent_history(self, limit: int = 50) -> List[InstallationHistory]:
        """
        Get recent installation history across all plugins.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of recent installation history records.
        """
        with self.Session() as session:
            return (
                session.query(InstallationHistory)
                .order_by(InstallationHistory.timestamp.desc())
                .limit(limit)
                .all()
            )

    def clear_history(self, plugin_id: Optional[str] = None) -> bool:
        """
        Clear installation history.

        Args:
            plugin_id: Plugin ID to clear history for, or None for all history

        Returns:
            True if successful, False otherwise.
        """
        try:
            with self.Session() as session:
                if plugin_id:
                    session.query(InstallationHistory).filter_by(plugin_id=plugin_id).delete()
                else:
                    session.query(InstallationHistory).delete()
                session.commit()
                logger.debug(f"Cleared history for: {plugin_id or 'all'}")
                return True
        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
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
        with self.Session() as session:
            try:
                setting = session.query(Settings).filter_by(key=key).first()
                if setting and setting.value:
                    try:
                        return json.loads(setting.value)
                    except json.JSONDecodeError:
                        return setting.value
                return default
            except Exception as e:
                logger.error(f"Failed to get setting {key}: {e}")
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
            with self.Session() as session:
                setting = session.query(Settings).filter_by(key=key).first()
                if setting:
                    setting.value = json.dumps(value)
                    setting.updated_at = datetime.now(timezone.utc)
                else:
                    setting = Settings(key=key, value=json.dumps(value))
                    session.add(setting)
                session.commit()
                logger.debug(f"Set setting: {key}")
                return True
        except Exception as e:
            logger.error(f"Failed to set setting {key}: {e}")
            return False

    def get_all_settings(self) -> Dict[str, Any]:
        """
        Get all settings as a dictionary.

        Returns:
            Dictionary of all settings.
        """
        with self.Session() as session:
            settings = session.query(Settings).all()

        result = {}
        for setting in settings:
            if setting.value:
                try:
                    result[setting.key] = json.loads(setting.value)
                except json.JSONDecodeError:
                    result[setting.key] = setting.value
        return result

    def close(self) -> None:
        """
        Close the database engine and dispose of connections.

        Call this when shutting down the application.
        """
        try:
            self.engine.dispose()
            logger.info("Database engine disposed")
        except Exception as e:
            logger.error(f"Failed to dispose database engine: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures database is properly closed."""
        self.close()
