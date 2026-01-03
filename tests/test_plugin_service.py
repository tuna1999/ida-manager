"""
Integration tests for PluginService.

Tests verify that:
1. Service layer properly orchestrates components
2. Business logic is separated from data access
3. Dependency injection works correctly
4. Version compatibility checks use proper comparison
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock

from src.services.plugin_service import PluginService
from src.database.db_manager import DatabaseManager
from src.github.client import GitHubClient
from src.core.ida_detector import IDADetector
from src.core.installer import PluginInstaller
from src.core.version_manager import VersionManager
from src.database.models import Plugin
from src.models.plugin import PluginType, ValidationResult, InstallationResult


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.db"

    db = DatabaseManager(db_path)
    db.init_database()

    yield db

    # Cleanup
    db.close()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    client = Mock(spec=GitHubClient)
    return client


@pytest.fixture
def mock_ida_detector():
    """Create a mock IDA detector."""
    detector = Mock(spec=IDADetector)
    detector.detect_ida_installation.return_value = "C:/Program Files/IDA Pro 9.0"
    detector.get_ida_version.return_value = "9.0"
    return detector


@pytest.fixture
def mock_installer():
    """Create a mock plugin installer."""
    installer = Mock(spec=PluginInstaller)
    return installer


@pytest.fixture
def plugin_service(temp_db, mock_github_client, mock_ida_detector, mock_installer):
    """Create a PluginService with mocked dependencies."""
    return PluginService(
        db_manager=temp_db,
        github_client=mock_github_client,
        ida_detector=mock_ida_detector,
        installer=mock_installer,
    )


class TestPluginServiceInitialization:
    """Test PluginService initialization and dependency injection."""

    def test_service_with_all_dependencies(self, temp_db):
        """Test creating service with all dependencies injected."""
        github_client = GitHubClient(token=None)
        ida_detector = IDADetector()
        installer = PluginInstaller(github_client, ida_detector)
        version_manager = VersionManager()

        service = PluginService(
            db_manager=temp_db,
            github_client=github_client,
            ida_detector=ida_detector,
            installer=installer,
            version_manager=version_manager,
        )

        assert service.db == temp_db
        assert service.github_client == github_client
        assert service.ida_detector == ida_detector
        assert service.installer == installer
        assert service.version_manager == version_manager

    def test_service_with_default_dependencies(self, temp_db):
        """Test creating service with default (created) dependencies."""
        service = PluginService(db_manager=temp_db)

        assert service.db == temp_db
        assert service.github_client is not None
        assert service.ida_detector is not None
        assert service.installer is not None
        assert service.version_manager is not None

    def test_service_exposes_plugin_manager_interface(self, plugin_service):
        """Test that service exposes PluginManager interface."""
        assert plugin_service._plugin_manager is not None


class TestPluginServiceValidation:
    """Test plugin validation through service layer."""

    def test_validate_plugin_from_valid_url(self, plugin_service, mock_github_client):
        """Test validating a plugin from valid GitHub URL."""
        # Mock GitHub API responses
        mock_contents = [
            Mock(name="README.md", download_url="https://example.com/README.md"),
            Mock(name="plugin.py", download_url=None),
        ]
        mock_github_client.get_repository_contents.return_value = mock_contents
        mock_github_client.get_readme.return_value="# Test Plugin\n\nIDA Pro plugin."

        result = plugin_service.validate_plugin_from_url("https://github.com/test/test-plugin")

        assert result.valid is True
        assert result.plugin_type is not None
        mock_github_client.get_repository_contents.assert_called_once_with("test", "test-plugin")

    def test_validate_plugin_from_invalid_url(self, plugin_service):
        """Test validating from invalid URL."""
        result = plugin_service.validate_plugin_from_url("not-a-github-url")

        assert result.valid is False
        assert "Invalid GitHub URL format" in result.error

    def test_validate_plugin_from_private_repo(self, plugin_service, mock_github_client):
        """Test validating from private repository."""
        mock_github_client.get_repository_contents.return_value = None

        result = plugin_service.validate_plugin_from_url("https://github.com/test/private")

        assert result.valid is False
        assert "Could not access repository" in result.error


class TestPluginServiceInstallation:
    """Test plugin installation through service layer."""

    def test_install_plugin_success(self, plugin_service, mock_installer):
        """Test successful plugin installation."""
        # Mock successful installation
        mock_installer.install_plugin.return_value = InstallationResult(
            success=True,
            message="Plugin installed successfully",
            plugin_id="test/plugin",
        )

        result = plugin_service.install_plugin(
            url="https://github.com/test/test-plugin",
            method="clone",
            branch="main",
        )

        assert result.success is True
        assert result.plugin_id == "test/plugin"
        mock_installer.install_plugin.assert_called_once()

    def test_install_plugin_failure(self, plugin_service, mock_installer):
        """Test failed plugin installation."""
        mock_installer.install_plugin.return_value = InstallationResult(
            success=False,
            message="Installation failed",
            plugin_id=None,
        )

        result = plugin_service.install_plugin(
            url="https://github.com/test/test-plugin",
            method="clone",
        )

        assert result.success is False
        assert "Installation failed" in result.message

    def test_uninstall_plugin(self, plugin_service, mock_installer):
        """Test plugin uninstallation."""
        mock_installer.uninstall_plugin.return_value = InstallationResult(
            success=True,
            message="Plugin uninstalled",
            plugin_id="test/plugin",
        )

        result = plugin_service.uninstall_plugin("test/plugin")

        assert result.success is True
        mock_installer.uninstall_plugin.assert_called_once_with("test/plugin")

    def test_update_plugin(self, plugin_service, mock_installer):
        """Test plugin update."""
        mock_installer.update_plugin.return_value = InstallationResult(
            success=True,
            message="Plugin updated",
            plugin_id="test/plugin",
        )

        result = plugin_service.update_plugin("test/plugin")

        assert result.success is True
        mock_installer.update_plugin.assert_called_once_with("test/plugin")


class TestPluginServiceQueries:
    """Test plugin queries through service layer."""

    def test_get_all_plugins(self, plugin_service, temp_db):
        """Test getting all plugins."""
        # Add test plugins
        for i in range(3):
            plugin = Plugin(
                id=f"test/plugin{i}",
                name=f"Plugin {i}",
                description=f"Description {i}",
                author="Test",
                repository_url=f"https://github.com/test/plugin{i}",
            )
            temp_db.add_plugin(plugin)

        plugins = plugin_service.get_all_plugins()

        assert len(plugins) == 3

    def test_get_installed_plugins(self, plugin_service, temp_db):
        """Test getting installed plugins."""
        # Add installed plugin
        plugin = Plugin(
            id="test/installed",
            name="Installed Plugin",
            description="Test",
            author="Test",
            repository_url="https://github.com/test/installed",
            installed_version="1.0.0",
        )
        temp_db.add_plugin(plugin)

        # Add not installed plugin
        plugin2 = Plugin(
            id="test/not_installed",
            name="Not Installed",
            description="Test",
            author="Test",
            repository_url="https://github.com/test/not_installed",
            installed_version=None,
        )
        temp_db.add_plugin(plugin2)

        plugins = plugin_service.get_installed_plugins()

        assert len(plugins) == 1
        assert plugins[0].id == "test/installed"

    def test_get_plugin_by_id(self, plugin_service, temp_db):
        """Test getting plugin by ID."""
        plugin = Plugin(
            id="test/specific",
            name="Specific Plugin",
            description="Test",
            author="Test",
            repository_url="https://github.com/test/specific",
        )
        temp_db.add_plugin(plugin)

        retrieved = plugin_service.get_plugin("test/specific")

        assert retrieved is not None
        assert retrieved.name == "Specific Plugin"


class TestPluginServiceCompatibility:
    """Test version compatibility checks through service layer."""

    def test_get_compatible_plugins_uses_proper_comparison(self, plugin_service, temp_db):
        """Test that compatibility checks use proper version comparison."""
        from src.utils.version_utils import is_version_compatible

        # Add plugins with different version requirements
        plugins = [
            Plugin(
                id="test/v1",
                name="Plugin 8.x",
                description="For IDA 8.x",
                author="Test",
                repository_url="https://github.com/test/v1",
                ida_version_min="8.0",
                ida_version_max="8.9",
            ),
            Plugin(
                id="test/v2",
                name="Plugin 9.x",
                description="For IDA 9.x",
                author="Test",
                repository_url="https://github.com/test/v2",
                ida_version_min="9.0",
                ida_version_max="9.2",
            ),
        ]

        for plugin in plugins:
            temp_db.add_plugin(plugin)

        # Test with IDA 9.0
        compatible = plugin_service.get_compatible_plugins("9.0")

        plugin_ids = [p.id for p in compatible]
        assert "test/v1" not in plugin_ids  # 8.x plugin not compatible
        assert "test/v2" in plugin_ids  # 9.x plugin compatible

    def test_is_plugin_compatible_with_valid_version(self, plugin_service, temp_db):
        """Test checking plugin compatibility."""
        plugin = Plugin(
            id="test/compat",
            name="Compatible Plugin",
            description="Test",
            author="Test",
            repository_url="https://github.com/test/compat",
            ida_version_min="8.0",
            ida_version_max="9.0",
        )
        temp_db.add_plugin(plugin)

        # Compatible version
        assert plugin_service.is_plugin_compatible("test/compat", "8.5") is True

        # Not compatible (below min)
        assert plugin_service.is_plugin_compatible("test/compat", "7.9") is False

        # Not compatible (above max)
        assert plugin_service.is_plugin_compatible("test/compat", "9.1") is False

    def test_version_comparison_edge_cases(self, plugin_service, temp_db):
        """Test version comparison edge cases through service."""
        # Critical: "8.10" > "8.9" (would fail with string comparison)
        plugin = Plugin(
            id="test/edge",
            name="Edge Case Plugin",
            description="Test",
            author="Test",
            repository_url="https://github.com/test/edge",
            ida_version_min="8.0",
            ida_version_max="8.9",
        )
        temp_db.add_plugin(plugin)

        # 8.10 should NOT be compatible (above 8.9)
        assert plugin_service.is_plugin_compatible("test/edge", "8.10") is False

        # 8.9 should be compatible
        assert plugin_service.is_plugin_compatible("test/edge", "8.9") is True


class TestPluginServiceUpdateChecking:
    """Test update checking through service layer."""

    def test_check_updates(self, plugin_service):
        """Test checking for updates."""
        with patch.object(plugin_service._plugin_manager, 'check_updates') as mock_check:
            mock_check.return_value = []

            updates = plugin_service.check_updates()

            mock_check.assert_called_once()
            assert updates == []

    def test_check_plugin_update(self, plugin_service, temp_db):
        """Test checking for updates for a specific plugin."""
        plugin = Plugin(
            id="test/update",
            name="Updateable Plugin",
            description="Test",
            author="Test",
            repository_url="https://github.com/test/update",
            installed_version="1.0.0",
            latest_version="2.0.0",
        )
        temp_db.add_plugin(plugin)

        with patch.object(plugin_service._plugin_manager, '_check_single_plugin_update') as mock_check:
            mock_check.return_value = None

            result = plugin_service.check_plugin_update("test/update")

            mock_check.assert_called_once()
            assert result is None


class TestPluginServiceSearch:
    """Test plugin search through service layer."""

    def test_search_plugins(self, plugin_service, temp_db):
        """Test searching plugins."""
        # Add test plugins
        plugins = [
            Plugin(
                id="test/search1",
                name="Python Plugin",
                description="A plugin for Python analysis",
                author="Test",
                repository_url="https://github.com/test/search1",
            ),
            Plugin(
                id="test/search2",
                name="Java Plugin",
                description="A plugin for Java analysis",
                author="Test",
                repository_url="https://github.com/test/search2",
            ),
        ]

        for plugin in plugins:
            temp_db.add_plugin(plugin)

        # Search by name
        results = plugin_service.search_plugins("Python")
        assert len(results) == 1
        assert results[0].id == "test/search1"

        # Search by description
        results = plugin_service.search_plugins("analysis")
        assert len(results) == 2


class TestPluginServiceLifecycle:
    """Test service lifecycle management."""

    def test_service_close(self, plugin_service, mock_github_client):
        """Test that service closes resources properly."""
        mock_github_client.close = Mock()

        plugin_service.close()

        mock_github_client.close.assert_called_once()

    def test_service_context_manager(self, temp_db):
        """Test using service as context manager."""
        with PluginService(db_manager=temp_db) as service:
            assert service is not None
            service.should_close = True

        # Service should be closed after context exit


class TestPluginServiceDependencyInjection:
    """Test dependency injection patterns."""

    def test_service_uses_injected_dependencies(self, temp_db):
        """Test that service uses injected dependencies, not creates new ones."""
        # Create specific instances
        github_client = GitHubClient(token=None)
        ida_detector = IDADetector()

        service = PluginService(
            db_manager=temp_db,
            github_client=github_client,
            ida_detector=ida_detector,
        )

        # Verify it uses injected instances
        assert service.github_client is github_client
        assert service.ida_detector is ida_detector

    def test_service_creates_dependencies_when_not_injected(self, temp_db):
        """Test that service creates dependencies when not provided."""
        service = PluginService(db_manager=temp_db)

        # Should create new instances
        assert service.github_client is not None
        assert service.ida_detector is not None
        assert service.installer is not None
        assert service.version_manager is not None

        # Installer should use the created github_client and ida_detector
        assert service.installer.github_client is service.github_client
        assert service.installer.ida_detector is service.ida_detector


class TestPluginServiceIntegration:
    """Integration tests for complete workflows."""

    def test_full_installation_workflow(self, plugin_service, mock_installer, mock_github_client):
        """Test complete installation workflow: validate -> install -> verify."""
        # Setup mocks
        mock_contents = [Mock(name="ida-plugin.json", download_url=None)]
        mock_github_client.get_repository_contents.return_value = mock_contents
        mock_github_client.get_readme.return_value="# Test Plugin"

        mock_installer.install_plugin.return_value = InstallationResult(
            success=True,
            message="Installed",
            plugin_id="test/full",
        )

        # Validate
        validation = plugin_service.validate_plugin_from_url("https://github.com/test/full")
        assert validation.valid is True

        # Install
        result = plugin_service.install_plugin(
            url="https://github.com/test/full",
            method="clone",
            plugin_type=validation.plugin_type,
        )
        assert result.success is True

        # Verify (would check database in real scenario)
        mock_installer.install_plugin.assert_called_once()

    def test_update_workflow(self, plugin_service, temp_db, mock_installer):
        """Test update workflow: check updates -> update specific plugin."""
        # Add plugin to database
        plugin = Plugin(
            id="test/update_workflow",
            name="Update Workflow Test",
            description="Test",
            author="Test",
            repository_url="https://github.com/test/update_workflow",
            installed_version="1.0.0",
        )
        temp_db.add_plugin(plugin)

        # Mock update
        mock_installer.update_plugin.return_value = InstallationResult(
            success=True,
            message="Updated",
            plugin_id="test/update_workflow",
        )

        # Check for updates
        updates = plugin_service.check_updates()

        # Update plugin
        result = plugin_service.update_plugin("test/update_workflow")

        assert result.success is True
        mock_installer.update_plugin.assert_called_once_with("test/update_workflow")
