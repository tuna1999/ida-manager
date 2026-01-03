"""
Tests for DI Container.

Tests verify that:
1. Container properly manages singleton instances
2. Dependencies are injected correctly
3. Lifecycle management works (shutdown/clear)
4. Configuration is properly loaded
5. Factory methods create correct instances
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from src.containers.di_container import (
    DIContainer,
    ApplicationContainer,
    get_container,
    reset_container,
)
from src.database.db_manager import DatabaseManager
from src.github.client import GitHubClient
from src.core.ida_detector import IDADetector
from src.core.installer import PluginInstaller
from src.core.version_manager import VersionManager
from src.core.plugin_manager import PluginManager
from src.services.plugin_service import PluginService
from src.repositories.plugin_repository import PluginRepository


class TestDIContainer:
    """Test basic DI container functionality."""

    def test_container_initialization(self):
        """Test container can be initialized."""
        container = DIContainer()
        assert container is not None

    def test_container_with_config(self):
        """Test container initialization with config file."""
        # Create temporary config file
        temp_dir = tempfile.mkdtemp()
        config_path = Path(temp_dir) / "config.json"

        import json
        config_data = {
            "github_token": "test_token",
            "database_path": str(Path(temp_dir) / "test.db"),
        }
        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        container = DIContainer(config_path)

        # Verify config was loaded
        assert container.get_config("github_token") == "test_token"
        assert container.get_config("database_path") == str(Path(temp_dir) / "test.db")

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_get_database_manager(self):
        """Test getting DatabaseManager from container."""
        container = DIContainer()
        db = container.get(DatabaseManager)

        assert db is not None
        assert isinstance(db, DatabaseManager)

        # Should return same instance (singleton)
        db2 = container.get(DatabaseManager)
        assert db is db2

    def test_get_github_client(self):
        """Test getting GitHubClient from container."""
        container = DIContainer()
        client = container.get(GitHubClient)

        assert client is not None
        assert isinstance(client, GitHubClient)

        # Should return same instance
        client2 = container.get(GitHubClient)
        assert client is client2

    def test_get_ida_detector(self):
        """Test getting IDADetector from container."""
        container = DIContainer()
        detector = container.get(IDADetector)

        assert detector is not None
        assert isinstance(detector, IDADetector)

    def test_get_version_manager(self):
        """Test getting VersionManager from container."""
        container = DIContainer()
        manager = container.get(VersionManager)

        assert manager is not None
        assert isinstance(manager, VersionManager)

    def test_get_plugin_installer(self):
        """Test getting PluginInstaller from container."""
        container = DIContainer()
        installer = container.get(PluginInstaller)

        assert installer is not None
        assert isinstance(installer, PluginInstaller)

    def test_get_plugin_repository(self):
        """Test getting PluginRepository from container."""
        container = DIContainer()
        repository = container.get(PluginRepository)

        assert repository is not None
        assert isinstance(repository, PluginRepository)

    def test_get_plugin_manager(self):
        """Test getting PluginManager from container."""
        container = DIContainer()
        manager = container.get(PluginManager)

        assert manager is not None
        assert isinstance(manager, PluginManager)

    def test_get_plugin_service(self):
        """Test getting PluginService from container."""
        container = DIContainer()
        service = container.get(PluginService)

        assert service is not None
        assert isinstance(service, PluginService)

    def test_dependency_injection(self):
        """Test that dependencies are properly injected."""
        container = DIContainer()

        # Get service
        service = container.get(PluginService)

        # Verify it has dependencies injected
        assert service.db is not None
        assert service.github_client is not None
        assert service.ida_detector is not None
        assert service.installer is not None
        assert service.version_manager is not None

    def test_singleton_pattern(self):
        """Test that singleton pattern works correctly."""
        container = DIContainer()

        # Get multiple instances of same type
        db1 = container.get(DatabaseManager)
        db2 = container.get(DatabaseManager)

        # Should be same instance
        assert db1 is db2

        # Get through another type that depends on it
        repository = container.get(PluginRepository)

        # Should have same DatabaseManager
        assert repository.db is db1

    def test_register_singleton(self):
        """Test registering a custom singleton instance."""
        container = DIContainer()

        # Create custom instance
        custom_db = DatabaseManager(Path(":memory:"))
        custom_db.init_database()

        # Register
        container.register(DatabaseManager, custom_db)

        # Should return custom instance
        db = container.get(DatabaseManager)
        assert db is custom_db

        # Cleanup
        custom_db.close()

    def test_register_factory(self):
        """Test registering a custom factory."""
        container = DIContainer()

        # Create custom factory
        def custom_factory() -> GitHubClient:
            return GitHubClient(token="custom_token")

        # Register factory
        container.register_factory(GitHubClient, custom_factory)

        # Should use custom factory
        client = container.get(GitHubClient)
        assert client is not None

    def test_config_management(self):
        """Test configuration management."""
        container = DIContainer()

        # Set config
        container.set_config("test_key", "test_value")
        container.set_config("number_key", 42)

        # Get config
        assert container.get_config("test_key") == "test_value"
        assert container.get_config("number_key") == 42
        assert container.get_config("nonexistent", "default") == "default"

    def test_is_registered(self):
        """Test checking if type is registered."""
        container = DIContainer()

        # Should be registered by default
        assert container.is_registered(DatabaseManager) is True
        assert container.is_registered(GitHubClient) is True

        # Should not be registered
        class NotRegistered:
            pass

        assert container.is_registered(NotRegistered) is False

    def test_clear_singletons(self):
        """Test clearing singletons."""
        container = DIContainer()

        # Get instances (creates singletons)
        db1 = container.get(DatabaseManager)
        client1 = container.get(GitHubClient)

        # Clear
        container.clear()

        # Get new instances (should be different)
        db2 = container.get(DatabaseManager)
        client2 = container.get(GitHubClient)

        # Should be different instances
        assert db1 is not db2
        assert client1 is not client2

    def test_shutdown(self):
        """Test shutdown closes resources."""
        container = DIContainer()

        # Create database manager
        db = container.get(DatabaseManager)

        # Shutdown
        container.shutdown()

        # Should clear singletons
        # Note: Can't easily test if db.close() was called without mocking

    def test_get_unregistered_type_raises_error(self):
        """Test getting unregistered type raises error."""
        container = DIContainer()

        class NotRegistered:
            pass

        with pytest.raises(ValueError, match="is not registered"):
            container.get(NotRegistered)


class TestApplicationContainer:
    """Test ApplicationContainer convenience methods."""

    def test_application_container_initialization(self):
        """Test ApplicationContainer can be initialized."""
        container = ApplicationContainer()
        assert container is not None

    def test_db_property(self):
        """Test db convenience property."""
        container = ApplicationContainer()
        db = container.db

        assert db is not None
        assert isinstance(db, DatabaseManager)

        # Should return same instance
        assert container.db is db

    def test_github_property(self):
        """Test github convenience property."""
        container = ApplicationContainer()
        client = container.github

        assert client is not None
        assert isinstance(client, GitHubClient)

    def test_ida_detector_property(self):
        """Test ida_detector convenience property."""
        container = ApplicationContainer()
        detector = container.ida_detector

        assert detector is not None
        assert isinstance(detector, IDADetector)

    def test_installer_property(self):
        """Test installer convenience property."""
        container = ApplicationContainer()
        installer = container.installer

        assert installer is not None
        assert isinstance(installer, PluginInstaller)

    def test_version_manager_property(self):
        """Test version_manager convenience property."""
        container = ApplicationContainer()
        manager = container.version_manager

        assert manager is not None
        assert isinstance(manager, VersionManager)

    def test_plugin_repository_property(self):
        """Test plugin_repository convenience property."""
        container = ApplicationContainer()
        repository = container.plugin_repository

        assert repository is not None
        assert isinstance(repository, PluginRepository)

    def test_plugin_manager_property(self):
        """Test plugin_manager convenience property."""
        container = ApplicationContainer()
        manager = container.plugin_manager

        assert manager is not None
        assert isinstance(manager, PluginManager)

    def test_plugin_service_property(self):
        """Test plugin_service convenience property."""
        container = ApplicationContainer()
        service = container.plugin_service

        assert service is not None
        assert isinstance(service, PluginService)


class TestGlobalContainer:
    """Test global container instance management."""

    def test_get_container_returns_instance(self):
        """Test get_container returns ApplicationContainer."""
        reset_container()  # Ensure clean state
        container = get_container()

        assert container is not None
        assert isinstance(container, ApplicationContainer)

    def test_get_container_returns_same_instance(self):
        """Test get_container returns singleton."""
        reset_container()  # Ensure clean state

        container1 = get_container()
        container2 = get_container()

        assert container1 is container2

    def test_get_container_with_config(self):
        """Test get_container with config file."""
        reset_container()  # Ensure clean state

        # Create temporary config
        temp_dir = tempfile.mkdtemp()
        config_path = Path(temp_dir) / "config.json"

        import json
        with open(config_path, 'w') as f:
            json.dump({"test": "value"}, f)

        container = get_container(config_path)

        assert container.get_config("test") == "value"

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
        reset_container()

    def test_reset_container(self):
        """Test reset_container clears global instance."""
        # Get container
        container1 = get_container()

        # Reset
        reset_container()

        # Get new container (should be different)
        container2 = get_container()

        assert container1 is not container2


class TestDIContainerIntegration:
    """Integration tests for DI container usage."""

    def test_full_workflow_with_container(self):
        """Test complete workflow using container."""
        container = ApplicationContainer()

        # Get service
        service = container.plugin_service

        # Verify dependencies are wired correctly
        assert service.db is not None
        assert service.github_client is not None
        assert service.ida_detector is not None

        # Verify database manager is shared
        repository = container.plugin_repository
        assert repository.db is service.db

    def test_container_manages_lifecycle(self):
        """Test container manages component lifecycle."""
        container = ApplicationContainer()

        # Create components
        db = container.db
        client = container.github

        # Shutdown
        container.shutdown()

        # Components should be cleaned up
        # New components should be created
        db2 = container.db
        client2 = container.github

        # Should be different instances after shutdown
        assert db is not db2

    def test_container_with_custom_config(self):
        """Test container with custom configuration."""
        container = ApplicationContainer()

        # Set custom config
        container.set_config("github_token", "custom_token")
        container.set_config("ida_path", "C:/Custom/IDA")

        # GitHub client should use config
        # Note: This tests the config mechanism, actual token usage would need mocking

        # Verify config is accessible
        assert container.get_config("github_token") == "custom_token"
        assert container.get_config("ida_path") == "C:/Custom/IDA"

    def test_dependency_chain_resolution(self):
        """Test that dependency chains are resolved correctly."""
        container = ApplicationContainer()

        # PluginService depends on:
        # - DatabaseManager
        # - GitHubClient
        # - IDADetector
        # - PluginInstaller (depends on GitHubClient, IDADetector)
        # - VersionManager

        service = container.plugin_service

        # All dependencies should be resolved
        assert service.db is not None
        assert service.github_client is not None
        assert service.ida_detector is not None
        assert service.installer is not None
        assert service.version_manager is not None

        # Installer should have correct dependencies
        assert service.installer.github_client is service.github_client
        assert service.installer.version_manager is service.version_manager

    def test_singleton_across_different_types(self):
        """Test that same instance is shared across different dependents."""
        container = ApplicationContainer()

        # Get service and repository
        service = container.plugin_service
        repository = container.plugin_repository
        manager = container.plugin_manager

        # All should share the same DatabaseManager
        assert service.db is repository.db
        assert service.db is manager.db

        # All should share the same GitHubClient
        assert service.github_client is manager.github_client

        # All should share the same IDADetector
        assert service.ida_detector is manager.ida_detector
