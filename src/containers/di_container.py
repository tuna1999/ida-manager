"""
Dependency Injection Container.

Manages application dependencies and their lifecycle.
Follows Service Locator pattern for dependency resolution.
"""

from logging import getLogger
from typing import Optional, Dict, Any, TypeVar, Type, Callable
from pathlib import Path

from src.database.db_manager import DatabaseManager
from src.github.client import GitHubClient
from src.core.ida_detector import IDADetector
from src.core.installer import PluginInstaller
from src.core.version_manager import VersionManager
from src.core.plugin_manager import PluginManager
from src.services.plugin_service import PluginService
from src.repositories.plugin_repository import PluginRepository

logger = getLogger(__name__)

T = TypeVar('T')


class DIContainer:
    """
    Dependency Injection Container.

    Manages the creation and lifecycle of application components.
    Supports singleton pattern for shared instances.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize DI container.

        Args:
            config_path: Optional path to configuration file
        """
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._config: Dict[str, Any] = {}

        # Load configuration if provided
        if config_path:
            self._load_config(config_path)

        # Register default factories
        self._register_default_factories()

        logger.info("DIContainer initialized")

    def _load_config(self, config_path: Path):
        """Load configuration from file."""
        import json
        try:
            with open(config_path, 'r') as f:
                self._config = json.load(f)
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")

    def _register_default_factories(self):
        """Register default factory methods for common types."""
        self._factories[DatabaseManager] = self._create_database_manager
        self._factories[GitHubClient] = self._create_github_client
        self._factories[IDADetector] = self._create_ida_detector
        self._factories[VersionManager] = self._create_version_manager
        self._factories[PluginInstaller] = self._create_plugin_installer
        self._factories[PluginRepository] = self._create_plugin_repository
        self._factories[PluginManager] = self._create_plugin_manager
        self._factories[PluginService] = self._create_plugin_service

    # ============ Factory Methods ============

    def _create_database_manager(self) -> DatabaseManager:
        """Create DatabaseManager instance."""
        db_path = self._config.get('database_path')
        if not db_path:
            # Default to AppData
            from pathlib import Path
            appdata = Path.home() / "AppData" / "Roaming" / "IDA-Plugin-Manager"
            appdata.mkdir(parents=True, exist_ok=True)
            db_path = appdata / "plugins.db"

        db_manager = DatabaseManager(Path(db_path))
        db_manager.init_database()
        logger.info(f"Created DatabaseManager with path: {db_path}")
        return db_manager

    def _create_github_client(self) -> GitHubClient:
        """Create GitHubClient instance."""
        token = self._config.get('github_token')
        client = GitHubClient(token=token)
        logger.info("Created GitHubClient")
        return client

    def _create_ida_detector(self) -> IDADetector:
        """Create IDADetector instance."""
        detector = IDADetector()
        logger.info("Created IDADetector")
        return detector

    def _create_version_manager(self) -> VersionManager:
        """Create VersionManager instance."""
        manager = VersionManager()
        logger.info("Created VersionManager")
        return manager

    def _create_plugin_installer(
        self,
        github_client: Optional[GitHubClient] = None,
        version_manager: Optional[VersionManager] = None,
    ) -> PluginInstaller:
        """Create PluginInstaller instance."""
        if github_client is None:
            github_client = self.get(GitHubClient)
        if version_manager is None:
            version_manager = self.get(VersionManager)

        installer = PluginInstaller(github_client, version_manager)
        logger.info("Created PluginInstaller")
        return installer

    def _create_plugin_repository(
        self,
        db_manager: Optional[DatabaseManager] = None,
    ) -> PluginRepository:
        """Create PluginRepository instance."""
        if db_manager is None:
            db_manager = self.get(DatabaseManager)

        repository = PluginRepository(db_manager)
        logger.info("Created PluginRepository")
        return repository

    def _create_plugin_manager(
        self,
        db_manager: Optional[DatabaseManager] = None,
        github_client: Optional[GitHubClient] = None,
        ida_detector: Optional[IDADetector] = None,
        installer: Optional[PluginInstaller] = None,
        version_manager: Optional[VersionManager] = None,
    ) -> PluginManager:
        """Create PluginManager instance."""
        if db_manager is None:
            db_manager = self.get(DatabaseManager)
        if github_client is None:
            github_client = self.get(GitHubClient)
        if ida_detector is None:
            ida_detector = self.get(IDADetector)
        if installer is None:
            installer = self.get(PluginInstaller)
        if version_manager is None:
            version_manager = self.get(VersionManager)

        manager = PluginManager(
            db_manager=db_manager,
            github_client=github_client,
            ida_detector=ida_detector,
            installer=installer,
            version_manager=version_manager,
        )
        logger.info("Created PluginManager")
        return manager

    def _create_plugin_service(
        self,
        db_manager: Optional[DatabaseManager] = None,
        github_client: Optional[GitHubClient] = None,
        ida_detector: Optional[IDADetector] = None,
        installer: Optional[PluginInstaller] = None,
        version_manager: Optional[VersionManager] = None,
    ) -> PluginService:
        """Create PluginService instance."""
        if db_manager is None:
            db_manager = self.get(DatabaseManager)
        if github_client is None:
            github_client = self.get(GitHubClient)
        if ida_detector is None:
            ida_detector = self.get(IDADetector)
        if version_manager is None:
            version_manager = self.get(VersionManager)
        # PluginInstaller must be created AFTER github_client and version_manager are resolved
        if installer is None:
            installer = PluginInstaller(github_client, version_manager)

        service = PluginService(
            db_manager=db_manager,
            github_client=github_client,
            ida_detector=ida_detector,
            installer=installer,
            version_manager=version_manager,
        )
        logger.info("Created PluginService")
        return service

    # ============ Public API ============

    def get(self, type_: Type[T]) -> T:
        """
        Get instance of specified type.

        Args:
            type_: Type to retrieve

        Returns:
            Instance of requested type

        Raises:
            ValueError: If type is not registered
        """
        # Check if singleton exists
        if type_ in self._singletons:
            return self._singletons[type_]

        # Check if factory exists
        if type_ not in self._factories:
            raise ValueError(f"Type {type_.__name__} is not registered in container")

        # Create instance using factory
        instance = self._factories[type_]()

        # Store as singleton
        self._singletons[type_] = instance

        return instance

    def register(self, type_: Type[T], instance: T):
        """
        Register a singleton instance.

        Args:
            type_: Type to register
            instance: Instance to use
        """
        self._singletons[type_] = instance
        logger.info(f"Registered singleton: {type_.__name__}")

    def register_factory(self, type_: Type[T], factory: Callable[..., T]):
        """
        Register a factory method for a type.

        Args:
            type_: Type to register
            factory: Factory method
        """
        self._factories[type_] = factory
        logger.info(f"Registered factory: {type_.__name__}")

    def set_config(self, key: str, value: Any):
        """
        Set configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        self._config[key] = value
        logger.debug(f"Set config: {key}")

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)

    def is_registered(self, type_: Type) -> bool:
        """
        Check if type is registered.

        Args:
            type_: Type to check

        Returns:
            True if registered, False otherwise
        """
        return type_ in self._factories or type_ in self._singletons

    def clear(self):
        """Clear all singletons and reset container."""
        # Close any resources that need cleanup
        for instance in self._singletons.values():
            if hasattr(instance, 'close'):
                try:
                    instance.close()
                except Exception as e:
                    logger.error(f"Error closing {instance}: {e}")

        self._singletons.clear()
        logger.info("Container cleared")

    def shutdown(self):
        """Shutdown container and cleanup resources."""
        logger.info("Shutting down DIContainer")
        self.clear()


class ApplicationContainer(DIContainer):
    """
    Application-specific DI container.

    Provides convenience methods for common application dependencies.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize application container."""
        super().__init__(config_path)
        logger.info("ApplicationContainer initialized")

    @property
    def db(self) -> DatabaseManager:
        """Get database manager."""
        return self.get(DatabaseManager)

    @property
    def github(self) -> GitHubClient:
        """Get GitHub client."""
        return self.get(GitHubClient)

    @property
    def ida_detector(self) -> IDADetector:
        """Get IDA detector."""
        return self.get(IDADetector)

    @property
    def installer(self) -> PluginInstaller:
        """Get plugin installer."""
        return self.get(PluginInstaller)

    @property
    def version_manager(self) -> VersionManager:
        """Get version manager."""
        return self.get(VersionManager)

    @property
    def plugin_repository(self) -> PluginRepository:
        """Get plugin repository."""
        return self.get(PluginRepository)

    @property
    def plugin_manager(self) -> PluginManager:
        """Get plugin manager."""
        return self.get(PluginManager)

    @property
    def plugin_service(self) -> PluginService:
        """Get plugin service."""
        return self.get(PluginService)


# ============ Global Container Instance ============

_global_container: Optional[ApplicationContainer] = None


def get_container(config_path: Optional[Path] = None) -> ApplicationContainer:
    """
    Get global container instance.

    Args:
        config_path: Optional path to configuration file

    Returns:
        ApplicationContainer instance
    """
    global _global_container

    if _global_container is None:
        _global_container = ApplicationContainer(config_path)

    return _global_container


def reset_container():
    """Reset global container instance."""
    global _global_container

    if _global_container:
        _global_container.shutdown()
        _global_container = None
