"""
Tests for DatabaseManager refactored with context managers.

Tests verify that:
1. Context managers properly close sessions
2. No resource leaks occur
3. Error handling works correctly
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from src.database.db_manager import DatabaseManager
from src.database.models import Plugin, GitHubRepo, InstallationHistory, Settings
from datetime import datetime, timezone


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


class TestDatabaseManagerContextManagers:
    """Test that context managers work correctly and prevent resource leaks."""

    def test_add_plugin_with_context_manager(self, temp_db):
        """Test adding plugin uses context manager correctly."""
        plugin = Plugin(
            id="test/plugin",
            name="Test Plugin",
            description="Test Description",
            author="Test Author",
            repository_url="https://github.com/test/test",
            installed_version="1.0.0",
            latest_version="1.0.0",
            plugin_type="modern",
        )

        # Should work without manual session management
        result = temp_db.add_plugin(plugin)
        assert result is True

        # Verify plugin was added
        retrieved = temp_db.get_plugin("test/plugin")
        assert retrieved is not None
        assert retrieved.name == "Test Plugin"

    def test_get_plugin_with_context_manager(self, temp_db):
        """Test getting plugin uses context manager correctly."""
        # First add a plugin
        plugin = Plugin(
            id="test/plugin2",
            name="Test Plugin 2",
            description="Test",
            author="Test",
            repository_url="https://github.com/test/test2",
            plugin_type="modern",
        )
        temp_db.add_plugin(plugin)

        # Get plugin - should auto-close session
        retrieved = temp_db.get_plugin("test/plugin2")
        assert retrieved is not None
        assert retrieved.name == "Test Plugin 2"

    def test_get_all_plugins_with_context_manager(self, temp_db):
        """Test getting all plugins uses context manager correctly."""
        # Add multiple plugins
        for i in range(3):
            plugin = Plugin(
                id=f"test/plugin{i}",
                name=f"Plugin {i}",
                description=f"Description {i}",
                author="Test",
                repository_url=f"https://github.com/test/plugin{i}",
                plugin_type="modern",
            )
            temp_db.add_plugin(plugin)

        # Get all - should auto-close session
        plugins = temp_db.get_all_plugins()
        assert len(plugins) == 3

    def test_update_plugin_with_context_manager(self, temp_db):
        """Test updating plugin uses context manager correctly."""
        # Add plugin
        plugin = Plugin(
            id="test/update",
            name="Original Name",
            description="Original",
            author="Test",
            repository_url="https://github.com/test/update",
            installed_version="1.0.0",
            plugin_type="modern",
        )
        temp_db.add_plugin(plugin)

        # Update plugin
        plugin.name = "Updated Name"
        plugin.description = "Updated Description"
        result = temp_db.update_plugin(plugin)
        assert result is True

        # Verify update
        retrieved = temp_db.get_plugin("test/update")
        assert retrieved.name == "Updated Name"
        assert retrieved.description == "Updated Description"

    def test_delete_plugin_with_context_manager(self, temp_db):
        """Test deleting plugin uses context manager correctly."""
        # Add plugin
        plugin = Plugin(
            id="test/delete",
            name="To Delete",
            description="Will be deleted",
            author="Test",
            repository_url="https://github.com/test/delete",
            plugin_type="modern",
        )
        temp_db.add_plugin(plugin)

        # Delete plugin
        result = temp_db.delete_plugin("test/delete")
        assert result is True

        # Verify deletion
        retrieved = temp_db.get_plugin("test/delete")
        assert retrieved is None

    def test_error_handling_with_context_manager(self, temp_db):
        """Test that errors don't cause resource leaks."""
        # Try to add invalid plugin (missing required fields)
        invalid_plugin = Plugin(
            id=None,  # Invalid: ID is required
            name="Invalid Plugin",
            plugin_type="modern",
        )

        # Should handle error gracefully without leaking session
        result = temp_db.add_plugin(invalid_plugin)
        # Result will be False due to error, but no resource leak

        # Verify database still works (no leak)
        valid_plugin = Plugin(
            id="test/after_error",
            name="Valid Plugin",
            description="Test",
            author="Test",
            repository_url="https://github.com/test/after_error",
            plugin_type="modern",
        )
        result = temp_db.add_plugin(valid_plugin)
        assert result is True

    def test_context_manager_interface(self, temp_db):
        """Test DatabaseManager as context manager."""
        # Test using DatabaseManager as context manager
        with temp_db as db:
            # Add plugin
            plugin = Plugin(
                id="test/context",
                name="Context Manager Test",
                description="Test",
                author="Test",
                repository_url="https://github.com/test/context",
                plugin_type="modern",
            )
            db.add_plugin(plugin)

        # Database should still be usable after context exit
        retrieved = temp_db.get_plugin("test/context")
        assert retrieved is not None
        assert retrieved.name == "Context Manager Test"

    def test_settings_with_context_manager(self, temp_db):
        """Test settings operations use context manager correctly."""
        # Set setting
        result = temp_db.set_setting("test_key", "test_value")
        assert result is True

        # Get setting
        value = temp_db.get_setting("test_key")
        assert value == "test_value"

        # Get all settings
        settings = temp_db.get_all_settings()
        assert "test_key" in settings
        assert settings["test_key"] == "test_value"

    def test_installation_history_with_context_manager(self, temp_db):
        """Test history logging uses context manager correctly."""
        # Log installation
        result = temp_db.log_installation(
            plugin_id="test/history",
            action="install",
            version="1.0.0",
            success=True,
        )
        assert result is True

        # Get history
        history = temp_db.get_installation_history("test/history")
        assert len(history) == 1
        assert history[0].action == "install"
        assert history[0].version == "1.0.0"

    def test_github_repo_with_context_manager(self, temp_db):
        """Test GitHub repo operations use context manager correctly."""
        repo = GitHubRepo(
            id="test/repo",
            plugin_id="test/plugin",
            repo_owner="test",
            repo_name="repo",
            stars=100,
        )

        # Save repo
        result = temp_db.save_github_repo(repo)
        assert result is True

        # Get repo
        retrieved = temp_db.get_github_repo("test/repo")
        assert retrieved is not None
        assert retrieved.stars == 100


class TestDatabaseManagerVersionComparison:
    """Test version comparison with IDAVersion utility."""

    def test_get_plugins_by_compatibility(self, temp_db):
        """Test that version comparison works correctly."""
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
                plugin_type="modern",
            ),
            Plugin(
                id="test/v2",
                name="Plugin 9.x",
                description="For IDA 9.x",
                author="Test",
                repository_url="https://github.com/test/v2",
                ida_version_min="9.0",
                ida_version_max="9.2",
                plugin_type="modern",
            ),
            Plugin(
                id="test/v3",
                name="Plugin Any",
                description="No version restrictions",
                author="Test",
                repository_url="https://github.com/test/v3",
                ida_version_min=None,
                ida_version_max=None,
                plugin_type="modern",
            ),
        ]

        for plugin in plugins:
            temp_db.add_plugin(plugin)

        # Test compatibility with IDA 9.0
        compatible = temp_db.get_plugins_by_compatibility("9.0")

        # Should include Plugin 9.x and Plugin Any, but not Plugin 8.x
        plugin_ids = [p.id for p in compatible]
        assert "test/v1" not in plugin_ids  # 8.x plugin not compatible
        assert "test/v2" in plugin_ids  # 9.x plugin compatible
        assert "test/v3" in plugin_ids  # No restrictions compatible

    def test_version_comparison_edge_cases(self):
        """Test edge cases in version comparison."""
        from src.utils.version_utils import compare_versions, is_version_compatible

        # Test: "8.10" > "8.9" (would fail with string comparison)
        assert compare_versions("8.10", "8.9") == 1
        assert compare_versions("8.9", "8.10") == -1

        # Test: "9.0" > "8.9"
        assert compare_versions("9.0", "8.9") == 1

        # Test: equal versions
        assert compare_versions("9.0", "9.0") == 0

        # Test compatibility
        assert is_version_compatible("8.0", "9.0", "8.5") is True
        assert is_version_compatible("9.0", "9.2", "8.9") is False
        assert is_version_compatible(None, "9.0", "8.5") is True
        assert is_version_compatible("9.0", None, "9.5") is True


class TestDatabaseManagerResourceLeaks:
    """Test that no resource leaks occur."""

    def test_no_leak_on_multiple_operations(self, temp_db):
        """Test that multiple operations don't leak connections."""
        # Perform many operations
        for i in range(100):
            plugin = Plugin(
                id=f"test/leak{i}",
                name=f"Plugin {i}",
                description="Test",
                author="Test",
                repository_url=f"https://github.com/test/leak{i}",
                plugin_type="modern",
            )
            temp_db.add_plugin(plugin)

        # If there were leaks, this might fail or slow down
        # All plugins should be retrievable
        all_plugins = temp_db.get_all_plugins()
        assert len(all_plugins) == 100

    def test_no_leak_on_error(self, temp_db):
        """Test that errors don't cause leaks."""
        # Try to get non-existent plugin multiple times
        for i in range(50):
            result = temp_db.get_plugin(f"nonexistent/{i}")
            assert result is None

        # Database should still work
        plugin = Plugin(
            id="test/after_errors",
            name="After Errors",
            description="Test",
            author="Test",
            repository_url="https://github.com/test/after_errors",
            plugin_type="modern",
        )
        result = temp_db.add_plugin(plugin)
        assert result is True
