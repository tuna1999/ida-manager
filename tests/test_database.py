"""
Tests for Database layer.

Validates SQLAlchemy models, DatabaseManager CRUD operations, and migrations.
"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.database.db_manager import DatabaseManager
from src.database.models import Base, GitHubRepo, InstallationHistory, Plugin, Settings
from src.database.migrations import Migration, MigrationManager, MIGRATIONS
from src.models.plugin import PluginType


class TestDatabaseModels:
    """Test SQLAlchemy database models."""

    def test_plugin_model_creation(self):
        """Test creating Plugin model instance."""
        now = datetime.now(timezone.utc)
        plugin = Plugin(
            id="test-plugin-1",
            name="Test Plugin",
            description="Test description",
            author="Test Author",
            repository_url="https://github.com/test/plugin",
            plugin_type="modern",
            ida_version_min="8.0",
            ida_version_max="9.0",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        assert plugin.id == "test-plugin-1"
        assert plugin.name == "Test Plugin"
        assert plugin.plugin_type == "modern"
        assert plugin.is_active is True

    def test_github_repo_model_creation(self):
        """Test creating GitHubRepo model instance."""
        repo = GitHubRepo(
            id="github-test-1",
            plugin_id="test-plugin-1",
            repo_owner="testuser",
            repo_name="test-plugin",
            stars=100,
        )

        assert repo.id == "github-test-1"
        assert repo.repo_owner == "testuser"
        assert repo.stars == 100

    def test_installation_history_model_creation(self):
        """Test creating InstallationHistory model instance."""
        history = InstallationHistory(
            plugin_id="test-plugin-1",
            action="install",
            version="1.0.0",
            success=True,
        )

        assert history.plugin_id == "test-plugin-1"
        assert history.action == "install"
        assert history.success is True

    def test_settings_model_creation(self):
        """Test creating Settings model instance."""
        setting = Settings(
            key="test_key",
            value='{"test": "value"}',
        )

        assert setting.key == "test_key"
        assert setting.value == '{"test": "value"}'


class TestDatabaseManager:
    """Test DatabaseManager CRUD operations."""

    @pytest.fixture
    def db_manager(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            manager = DatabaseManager(db_path=db_path)
            manager.init_database()
            yield manager
            # Cleanup: dispose engine to release file lock
            manager.engine.dispose()

    def test_database_initialization(self, db_manager):
        """Test database initialization creates tables."""
        # Check if tables exist by querying them
        session = db_manager.get_session()
        assert session.query(Plugin).count() == 0
        assert session.query(GitHubRepo).count() == 0
        assert session.query(InstallationHistory).count() == 0
        assert session.query(Settings).count() == 0
        session.close()

    def test_add_and_get_plugin(self, db_manager):
        """Test adding and retrieving a plugin."""
        # Add plugin
        plugin = Plugin(
            id="test-plugin",
            name="Test Plugin",
            plugin_type="modern",
        )
        assert db_manager.add_plugin(plugin) is True

        # Get plugin
        retrieved = db_manager.get_plugin("test-plugin")
        assert retrieved is not None
        assert retrieved.id == "test-plugin"
        assert retrieved.name == "Test Plugin"

    def test_get_plugin_by_name(self, db_manager):
        """Test getting plugin by name."""
        plugin = Plugin(id="test-1", name="Unique Name", plugin_type="modern")
        db_manager.add_plugin(plugin)

        retrieved = db_manager.get_plugin_by_name("Unique Name")
        assert retrieved is not None
        assert retrieved.id == "test-1"

    def test_get_all_plugins(self, db_manager):
        """Test getting all plugins."""
        # Add multiple plugins
        for i in range(3):
            plugin = Plugin(id=f"plugin-{i}", name=f"Plugin {i}", plugin_type="modern")
            db_manager.add_plugin(plugin)

        plugins = db_manager.get_all_plugins()
        assert len(plugins) == 3

    def test_get_installed_plugins(self, db_manager):
        """Test getting only installed plugins."""
        # Add installed plugin
        plugin1 = Plugin(
            id="plugin-1",
            name="Installed Plugin",
            plugin_type="modern",
            installed_version="1.0.0",
        )
        db_manager.add_plugin(plugin1)

        # Add not installed plugin
        plugin2 = Plugin(id="plugin-2", name="Available Plugin", plugin_type="modern")
        db_manager.add_plugin(plugin2)

        installed = db_manager.get_installed_plugins()
        assert len(installed) == 1
        assert installed[0].id == "plugin-1"

    def test_update_plugin(self, db_manager):
        """Test updating a plugin."""
        # Add plugin
        plugin = Plugin(id="test-plugin", name="Original Name", plugin_type="modern")
        db_manager.add_plugin(plugin)

        # Update plugin
        plugin.name = "Updated Name"
        plugin.installed_version = "2.0.0"
        assert db_manager.update_plugin(plugin) is True

        # Verify update
        retrieved = db_manager.get_plugin("test-plugin")
        assert retrieved.name == "Updated Name"
        assert retrieved.installed_version == "2.0.0"

    def test_delete_plugin(self, db_manager):
        """Test deleting a plugin."""
        plugin = Plugin(id="test-plugin", name="To Delete", plugin_type="modern")
        db_manager.add_plugin(plugin)

        assert db_manager.delete_plugin("test-plugin") is True

        # Verify deletion
        retrieved = db_manager.get_plugin("test-plugin")
        assert retrieved is None

    def test_search_plugins(self, db_manager):
        """Test searching plugins."""
        # Add plugins
        plugin1 = Plugin(id="p1", name="Python Analyzer", description="Analyzes Python code", plugin_type="modern")
        plugin2 = Plugin(id="p2", name="X86 Decoder", description="Decodes x86 instructions", plugin_type="modern")
        plugin3 = Plugin(id="p3", name="ARM Helper", description="ARM architecture helper", plugin_type="modern")

        db_manager.add_plugin(plugin1)
        db_manager.add_plugin(plugin2)
        db_manager.add_plugin(plugin3)

        # Search by name
        results = db_manager.search_plugins("Python")
        assert len(results) == 1
        assert results[0].id == "p1"

        # Search by description
        results = db_manager.search_plugins("architecture")
        assert len(results) == 1
        assert results[0].id == "p3"

    def test_get_plugins_by_type(self, db_manager):
        """Test filtering plugins by type."""
        plugin1 = Plugin(id="p1", name="Modern Plugin", plugin_type="modern")
        plugin2 = Plugin(id="p2", name="Legacy Plugin", plugin_type="legacy")
        plugin3 = Plugin(id="p3", name="Another Modern", plugin_type="modern")

        db_manager.add_plugin(plugin1)
        db_manager.add_plugin(plugin2)
        db_manager.add_plugin(plugin3)

        modern_plugins = db_manager.get_plugins_by_type("modern")
        assert len(modern_plugins) == 2

        legacy_plugins = db_manager.get_plugins_by_type("legacy")
        assert len(legacy_plugins) == 1

    def test_save_and_get_github_repo(self, db_manager):
        """Test saving and retrieving GitHub repo info."""
        repo = GitHubRepo(
            id="gh-1",
            plugin_id="plugin-1",
            repo_owner="testuser",
            repo_name="test-repo",
            stars=150,
            topics='["ida", "plugin"]',
        )

        assert db_manager.save_github_repo(repo) is True

        retrieved = db_manager.get_github_repo("gh-1")
        assert retrieved is not None
        assert retrieved.repo_owner == "testuser"
        assert retrieved.stars == 150

    def test_update_github_repo(self, db_manager):
        """Test updating existing GitHub repo."""
        repo = GitHubRepo(
            id="gh-1",
            repo_owner="user",
            repo_name="repo",
            stars=100,
        )
        db_manager.save_github_repo(repo)

        # Update
        repo.stars = 200
        db_manager.save_github_repo(repo)

        retrieved = db_manager.get_github_repo("gh-1")
        assert retrieved.stars == 200

    def test_log_installation(self, db_manager):
        """Test logging installation actions."""
        assert db_manager.log_installation(
            plugin_id="plugin-1",
            action="install",
            version="1.0.0",
            success=True,
        ) is True

        history = db_manager.get_installation_history("plugin-1")
        assert len(history) == 1
        assert history[0].action == "install"
        assert history[0].version == "1.0.0"

    def test_get_installation_history(self, db_manager):
        """Test getting installation history."""
        # Log multiple actions
        db_manager.log_installation("plugin-1", "install", "1.0.0", True)
        db_manager.log_installation("plugin-1", "update", "2.0.0", True)
        db_manager.log_installation("plugin-1", "uninstall", None, True)

        history = db_manager.get_installation_history("plugin-1", limit=10)
        assert len(history) == 3
        # Should be in reverse chronological order
        assert history[0].action == "uninstall"
        assert history[2].action == "install"

    def test_get_recent_history(self, db_manager):
        """Test getting recent history across all plugins."""
        db_manager.log_installation("plugin-1", "install", "1.0.0")
        db_manager.log_installation("plugin-2", "install", "1.0.0")
        db_manager.log_installation("plugin-3", "install", "1.0.0")

        history = db_manager.get_recent_history(limit=2)
        assert len(history) == 2

    def test_clear_history(self, db_manager):
        """Test clearing installation history."""
        db_manager.log_installation("plugin-1", "install", "1.0.0")
        db_manager.log_installation("plugin-2", "install", "1.0.0")

        # Clear specific plugin
        assert db_manager.clear_history("plugin-1") is True
        assert len(db_manager.get_installation_history("plugin-1")) == 0
        assert len(db_manager.get_installation_history("plugin-2")) == 1

        # Clear all
        assert db_manager.clear_history() is True
        assert len(db_manager.get_recent_history()) == 0

    def test_set_and_get_setting(self, db_manager):
        """Test setting and getting settings."""
        # Set setting
        assert db_manager.set_setting("test_key", {"nested": "value"}) is True

        # Get setting
        value = db_manager.get_setting("test_key")
        assert value == {"nested": "value"}

        # Get with default
        value = db_manager.get_setting("nonexistent", "default")
        assert value == "default"

    def test_get_all_settings(self, db_manager):
        """Test getting all settings."""
        db_manager.set_setting("key1", "value1")
        db_manager.set_setting("key2", {"nested": "value2"})

        settings = db_manager.get_all_settings()
        assert len(settings) == 2
        assert settings["key1"] == "value1"
        assert settings["key2"] == {"nested": "value2"}

    def test_plugin_relationships(self, db_manager):
        """Test plugin-installation history relationship."""
        # Add plugin
        plugin = Plugin(id="test-plugin", name="Test", plugin_type="modern")
        db_manager.add_plugin(plugin)

        # Log installation
        db_manager.log_installation("test-plugin", "install", "1.0.0")

        # Get plugin with relationship
        session = db_manager.get_session()
        plugin_with_history = session.query(Plugin).filter_by(id="test-plugin").first()
        assert len(plugin_with_history.installation_history) == 1
        assert plugin_with_history.installation_history[0].action == "install"
        session.close()


class TestMigrations:
    """Test database migration system."""

    @pytest.fixture
    def migration_manager(self):
        """Create a temporary database for migration testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_migrations.db"
            manager = MigrationManager(db_path=db_path)
            yield manager

    def test_migration_table_creation(self, migration_manager):
        """Test that migration table is created."""
        migration_manager._ensure_migration_table()

        import sqlite3

        conn = sqlite3.connect(migration_manager.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None

    def test_get_current_version(self, migration_manager):
        """Test getting current database version."""
        version = migration_manager.get_current_version()
        assert version == 0  # No migrations applied yet

    def test_get_applied_migrations(self, migration_manager):
        """Test getting list of applied migrations."""
        applied = migration_manager.get_applied_migrations()
        assert applied == []  # No migrations applied

    def test_migration_status(self, migration_manager, capsys):
        """Test migration status output."""
        migration_manager.status()
        captured = capsys.readouterr()

        assert "Current schema version: 0" in captured.out
        assert "Applied migrations: []" in captured.out


class TestDatabaseIntegration:
    """Integration tests for database operations."""

    @pytest.fixture
    def db_manager(self):
        """Create a temporary database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_integration.db"
            manager = DatabaseManager(db_path=db_path)
            manager.init_database()
            yield manager
            # Cleanup: dispose engine to release file lock
            manager.engine.dispose()

    def test_complete_plugin_workflow(self, db_manager):
        """Test complete plugin lifecycle."""
        # 1. Discover and add plugin
        plugin = Plugin(
            id="complete-test",
            name="Complete Test Plugin",
            description="A plugin for testing complete workflow",
            author="Test Author",
            repository_url="https://github.com/test/complete",
            plugin_type="modern",
            ida_version_min="8.0",
            ida_version_max="9.0",
        )
        db_manager.add_plugin(plugin)

        # 2. Save GitHub info
        repo = GitHubRepo(
            id="gh-complete-test",
            plugin_id="complete-test",
            repo_owner="test",
            repo_name="complete-test",
            stars=50,
        )
        db_manager.save_github_repo(repo)

        # 3. Log installation
        db_manager.log_installation("complete-test", "install", "1.0.0", success=True)

        # 4. Update to installed version
        plugin.installed_version = "1.0.0"
        plugin.install_date = datetime.now(timezone.utc)
        db_manager.update_plugin(plugin)

        # 5. Verify all data
        retrieved_plugin = db_manager.get_plugin("complete-test")
        assert retrieved_plugin.installed_version == "1.0.0"
        assert retrieved_plugin.install_date is not None

        history = db_manager.get_installation_history("complete-test")
        assert len(history) == 1
        assert history[0].action == "install"

        gh_repo = db_manager.get_github_repo("gh-complete-test")
        assert gh_repo is not None
        assert gh_repo.stars == 50

    def test_search_and_filter_workflow(self, db_manager):
        """Test searching and filtering plugins."""
        # Add diverse set of plugins
        plugins = [
            Plugin(
                id="p1",
                name="X86 Analyzer",
                description="Analyzes x86 code",
                plugin_type="legacy",
                ida_version_min="7.0",
                ida_version_max="8.4",
            ),
            Plugin(
                id="p2",
                name="ARM Analyzer",
                description="Analyzes ARM code",
                plugin_type="modern",
                ida_version_min="9.0",
                ida_version_max="9.0",
            ),
            Plugin(
                id="p3",
                name="X86 Emulator",
                description="Emulates x86 instructions",
                plugin_type="modern",
                ida_version_min="8.0",
                ida_version_max="9.0",
            ),
        ]

        for plugin in plugins:
            db_manager.add_plugin(plugin)

        # Search for "x86"
        results = db_manager.search_plugins("x86")
        assert len(results) == 2

        # Filter by type
        modern_plugins = db_manager.get_plugins_by_type("modern")
        assert len(modern_plugins) == 2

        # Filter by compatibility
        compatible = db_manager.get_plugins_by_compatibility("8.5")
        # p1 (max 8.4) should NOT be compatible
        # p2 (min 9.0) should NOT be compatible with 8.5
        # p3 (8.0-9.0) should be compatible
        assert len(compatible) >= 1
        plugin_ids = [p.id for p in compatible]
        assert "p3" in plugin_ids  # Only p3 has range 8.0-9.0 which includes 8.5
