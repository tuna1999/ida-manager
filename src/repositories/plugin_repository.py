"""
Plugin Repository - Data access layer.

Provides abstraction over database operations for plugins.
Follows Repository Pattern for clean separation of concerns.
"""

from logging import getLogger
from typing import List, Optional

from src.database.db_manager import DatabaseManager
from src.database.models import Plugin as DBPlugin
from src.models.plugin import InstallationMethod, Plugin, PluginStatus, PluginType
from src.utils.version_utils import IDAVersion, is_version_compatible

logger = getLogger(__name__)


class PluginRepository:
    """
    Repository for Plugin data access.

    Abstracts database operations and provides a clean interface
    for the service layer.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize plugin repository.

        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager

    def find_by_id(self, plugin_id: str) -> Optional[Plugin]:
        """
        Find a plugin by ID.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Plugin object or None if not found
        """
        db_plugin = self.db.get_plugin(plugin_id)
        if db_plugin:
            return self._db_to_model(db_plugin)
        return None

    def find_by_name(self, name: str) -> Optional[Plugin]:
        """
        Find a plugin by name.

        Args:
            name: Plugin name

        Returns:
            Plugin object or None if not found
        """
        db_plugin = self.db.get_plugin_by_name(name)
        if db_plugin:
            return self._db_to_model(db_plugin)
        return None

    def find_all(self) -> List[Plugin]:
        """
        Find all plugins.

        Returns:
            List of all plugins
        """
        db_plugins = self.db.get_all_plugins()
        return [self._db_to_model(p) for p in db_plugins]

    def find_installed(self) -> List[Plugin]:
        """
        Find all installed plugins.

        Returns:
            List of installed plugins
        """
        db_plugins = self.db.get_installed_plugins()
        return [self._db_to_model(p) for p in db_plugins]

    def find_by_type(self, plugin_type: PluginType) -> List[Plugin]:
        """
        Find plugins by type.

        Args:
            plugin_type: Plugin type (modern or legacy)

        Returns:
            List of plugins of the specified type
        """
        db_plugins = self.db.get_plugins_by_type(plugin_type.value)
        return [self._db_to_model(p) for p in db_plugins]

    def find_compatible(self, ida_version: str) -> List[Plugin]:
        """
        Find plugins compatible with IDA version.

        Uses proper version comparison via IDAVersion utility.

        Args:
            ida_version: IDA Pro version string

        Returns:
            List of compatible plugins
        """
        db_plugins = self.db.get_plugins_by_compatibility(ida_version)
        return [self._db_to_model(p) for p in db_plugins]

    def search(self, query: str) -> List[Plugin]:
        """
        Search plugins by name or description.

        Args:
            query: Search query string

        Returns:
            List of matching plugins
        """
        db_plugins = self.db.search_plugins(query)
        return [self._db_to_model(p) for p in db_plugins]

    def save(self, plugin: Plugin) -> bool:
        """
        Save a plugin (create or update).

        Args:
            plugin: Plugin to save

        Returns:
            True if successful, False otherwise
        """
        # Check if plugin exists
        existing = self.find_by_id(plugin.id)

        if existing:
            # Update
            return self.db.update_plugin(self._model_to_db(plugin))
        else:
            # Create new
            db_plugin = self._model_to_db(plugin)
            return self.db.add_plugin(db_plugin)

    def delete(self, plugin_id: str) -> bool:
        """
        Delete a plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if successful, False otherwise
        """
        return self.db.delete_plugin(plugin_id)

    def update_status(
        self,
        plugin_id: str,
        status: PluginStatus,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Update plugin status.

        Args:
            plugin_id: Plugin identifier
            status: New status
            error_message: Optional error message

        Returns:
            True if successful, False otherwise
        """
        return self.db.update_plugin_status(plugin_id, status.value, error_message)

    def is_compatible(
        self,
        plugin_id: str,
        ida_version: str,
    ) -> bool:
        """
        Check if plugin is compatible with IDA version.

        Args:
            plugin_id: Plugin identifier
            ida_version: IDA Pro version string

        Returns:
            True if compatible, False otherwise
        """
        plugin = self.find_by_id(plugin_id)
        if not plugin:
            return False

        return is_version_compatible(
            plugin.ida_version_min,
            plugin.ida_version_max,
            ida_version,
        )

    def _db_to_model(self, db_plugin: DBPlugin) -> Plugin:
        """
        Convert database model to Pydantic model.

        Args:
            db_plugin: SQLAlchemy model

        Returns:
            Pydantic Plugin model
        """
        # Parse JSON fields
        metadata_json = {}
        if db_plugin.metadata_json:
            try:
                import json
                metadata_json = json.loads(db_plugin.metadata_json)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse metadata_json for {db_plugin.id}")

        # Parse status enum
        try:
            status = PluginStatus(db_plugin.status) if db_plugin.status else PluginStatus.NOT_INSTALLED
        except ValueError:
            status = PluginStatus.NOT_INSTALLED

        # Parse installation method enum
        try:
            installation_method = InstallationMethod(db_plugin.installation_method) if db_plugin.installation_method else InstallationMethod.UNKNOWN
        except ValueError:
            installation_method = InstallationMethod.UNKNOWN

        # Parse tags (stored as JSON dict, convert to list)
        tags = []
        if db_plugin.tags:
            if isinstance(db_plugin.tags, list):
                tags = db_plugin.tags
            elif isinstance(db_plugin.tags, dict):
                tags = list(db_plugin.tags.keys())

        return Plugin(
            id=db_plugin.id,
            name=db_plugin.name,
            description=db_plugin.description,
            author=db_plugin.author,
            repository_url=db_plugin.repository_url,
            installed_version=db_plugin.installed_version,
            latest_version=db_plugin.latest_version,
            install_date=db_plugin.install_date,
            last_updated=db_plugin.last_updated,
            plugin_type=db_plugin.plugin_type,
            ida_version_min=db_plugin.ida_version_min,
            ida_version_max=db_plugin.ida_version_max,
            is_active=db_plugin.is_active,
            install_path=db_plugin.install_path,
            metadata=metadata_json,
            status=status,
            installation_method=installation_method,
            error_message=db_plugin.error_message,
            added_at=db_plugin.added_at,
            last_updated_at=db_plugin.last_updated_at,
            tags=tags,
        )

    def _model_to_db(self, plugin: Plugin) -> DBPlugin:
        """
        Convert Pydantic model to database model.

        Args:
            plugin: Pydantic Plugin model

        Returns:
            SQLAlchemy model
        """
        # Serialize metadata to JSON
        metadata_json = None
        if plugin.metadata:
            import json
            metadata_json = json.dumps(plugin.metadata.model_dump())

        return DBPlugin(
            id=plugin.id,
            name=plugin.name,
            description=plugin.description,
            author=plugin.author,
            repository_url=plugin.repository_url,
            installed_version=plugin.installed_version,
            latest_version=plugin.latest_version,
            install_date=plugin.install_date,
            last_updated=plugin.last_updated,
            plugin_type=plugin.plugin_type.value if plugin.plugin_type else None,
            ida_version_min=plugin.ida_version_min,
            ida_version_max=plugin.ida_version_max,
            is_active=plugin.is_active,
            install_path=plugin.install_path,
            metadata_json=metadata_json,
        )
