"""
Tests for Models and Config layers.

Validates that all Pydantic models work correctly and config management functions properly.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.config.constants import (
    CONFIG_DIR,
    CONFIG_FILE,
    GITHUB_API_BASE,
    PLUGIN_TYPE_LEGACY,
    PLUGIN_TYPE_MODERN,
)
from src.config.settings import (
    AdvancedConfig,
    AppConfig,
    GitHubConfig,
    IDAConfig,
    SettingsManager,
    UIConfig,
    UpdatesConfig,
)
from src.models.github_info import (
    GitHubAsset,
    GitHubPluginInfo,
    GitHubRelease,
    GitHubRepo,
)
from src.models.plugin import (
    CompatibilityStatus,
    InstallationResult,
    Plugin,
    PluginMetadata,
    PluginType,
    UpdateInfo,
    ValidationResult,
)


class TestPluginModels:
    """Test plugin-related Pydantic models."""

    def test_plugin_type_enum(self):
        """Test PluginType enum values."""
        assert PluginType.LEGACY == "legacy"
        assert PluginType.MODERN == "modern"

    def test_plugin_model_basic(self):
        """Test basic Plugin model creation."""
        plugin = Plugin(
            id="test-plugin",
            name="Test Plugin",
            description="A test plugin",
            author="Test Author",
            repository_url="https://github.com/test/plugin",
            plugin_type=PluginType.MODERN,
            ida_version_min="8.0",
            ida_version_max="9.0",
        )

        assert plugin.id == "test-plugin"
        assert plugin.name == "Test Plugin"
        assert plugin.plugin_type == PluginType.MODERN
        assert plugin.is_active is True
        assert plugin.metadata == {}

    def test_plugin_model_with_all_fields(self):
        """Test Plugin model with all fields populated."""
        now = datetime.now()
        plugin = Plugin(
            id="complete-plugin",
            name="Complete Plugin",
            description="Full featured plugin",
            author="Full Author",
            repository_url="https://github.com/full/plugin",
            installed_version="1.0.0",
            latest_version="2.0.0",
            install_date=now,
            last_updated=now,
            plugin_type=PluginType.LEGACY,
            ida_version_min="7.0",
            ida_version_max="9.5",
            is_active=False,
            install_path="C:/IDA/plugins/complete",
            metadata={"custom_field": "value"},
        )

        assert plugin.installed_version == "1.0.0"
        assert plugin.latest_version == "2.0.0"
        assert plugin.plugin_type == PluginType.LEGACY
        assert plugin.is_active is False
        assert plugin.metadata["custom_field"] == "value"

    def test_plugin_serialization(self):
        """Test Plugin model JSON serialization."""
        plugin = Plugin(
            id="serial-test",
            name="Serialization Test",
            plugin_type=PluginType.MODERN,
        )

        # Should serialize without errors
        data = plugin.model_dump()
        assert data["id"] == "serial-test"
        assert data["name"] == "Serialization Test"

    def test_plugin_metadata_model(self):
        """Test PluginMetadata model."""
        metadata = PluginMetadata(
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            ida_version_min="8.0",
            ida_version_max="9.0",
            dependencies=["dependency1", "dependency2"],
            entry_point="main.py",
        )

        assert metadata.name == "Test Plugin"
        assert metadata.version == "1.0.0"
        assert len(metadata.dependencies) == 2
        assert metadata.entry_point == "main.py"

    def test_validation_result_model(self):
        """Test ValidationResult model."""
        result_valid = ValidationResult(
            valid=True,
            plugin_type=PluginType.MODERN,
            warnings=["Minor warning"],
        )

        assert result_valid.valid is True
        assert result_valid.plugin_type == PluginType.MODERN
        assert len(result_valid.warnings) == 1

        result_invalid = ValidationResult(
            valid=False,
            error="Invalid plugin structure",
        )

        assert result_invalid.valid is False
        assert result_invalid.error == "Invalid plugin structure"

    def test_installation_result_model(self):
        """Test InstallationResult model."""
        result = InstallationResult(
            success=True,
            plugin_id="test-plugin",
            message="Plugin installed successfully",
            previous_version="1.0.0",
            new_version="2.0.0",
        )

        assert result.success is True
        assert result.previous_version == "1.0.0"
        assert result.new_version == "2.0.0"

    def test_update_info_model(self):
        """Test UpdateInfo model."""
        update = UpdateInfo(
            has_update=True,
            current_version="1.0.0",
            latest_version="2.0.0",
            changelog="New features added",
            release_url="https://github.com/test/releases/2.0.0",
        )

        assert update.has_update is True
        assert update.current_version == "1.0.0"
        assert update.latest_version == "2.0.0"


class TestGitHubModels:
    """Test GitHub-related Pydantic models."""

    def test_github_asset_model(self):
        """Test GitHubAsset model."""
        asset = GitHubAsset(
            name="plugin.zip",
            size=1024000,
            download_url="https://github.com/test/releases/download/v1.0/plugin.zip",
            content_type="application/zip",
        )

        assert asset.name == "plugin.zip"
        assert asset.size == 1024000
        assert "download" in asset.download_url

    def test_github_release_model(self):
        """Test GitHubRelease model."""
        release = GitHubRelease(
            id=12345,
            tag_name="v1.0.0",
            name="First Release",
            body="Release notes here",
            published_at=datetime.now(),
            prerelease=False,
            html_url="https://github.com/test/releases/v1.0.0",
        )

        assert release.id == 12345
        assert release.tag_name == "v1.0.0"
        assert release.prerelease is False

    def test_github_repo_model(self):
        """Test GitHubRepo model."""
        repo = GitHubRepo(
            id=67890,
            name="test-plugin",
            full_name="testuser/test-plugin",
            owner="testuser",
            description="Test plugin repo",
            stars=100,
            topics=["ida-pro", "plugin"],
            language="Python",
            clone_url="https://github.com/testuser/test-plugin.git",
            html_url="https://github.com/testuser/test-plugin",
            default_branch="main",
        )

        assert repo.full_name == "testuser/test-plugin"
        assert repo.stars == 100
        assert "ida-pro" in repo.topics

    def test_github_plugin_info_aggregate(self):
        """Test GitHubPluginInfo aggregation."""
        repo = GitHubRepo(
            id=1,
            name="test",
            full_name="user/test",
            owner="user",
            clone_url="https://github.com/user/test.git",
            html_url="https://github.com/user/test",
        )

        release = GitHubRelease(
            id=1,
            tag_name="v1.0",
            html_url="https://github.com/user/test/releases/v1.0",
        )

        plugin_info = GitHubPluginInfo(
            repository=repo,
            releases=[release],
            latest_release=release,
            readme_content="# Test Plugin",
            plugin_metadata={"version": "1.0"},
            is_valid_plugin=True,
            detected_plugin_type="modern",
        )

        assert plugin_info.is_valid_plugin is True
        assert len(plugin_info.releases) == 1
        assert plugin_info.repository.name == "test"


class TestConfigLayer:
    """Test configuration management."""

    def test_ida_config_defaults(self):
        """Test IDAConfig default values."""
        config = IDAConfig()
        assert config.install_path == ""
        assert config.version == ""
        assert config.plugin_dir == ""
        assert config.auto_detect is True

    def test_github_config_defaults(self):
        """Test GitHubConfig default values."""
        config = GitHubConfig()
        assert config.token == ""
        assert config.api_base == GITHUB_API_BASE
        assert "remaining" in config.rate_limit

    def test_updates_config_defaults(self):
        """Test UpdatesConfig default values."""
        config = UpdatesConfig()
        assert config.auto_check is True
        assert config.check_interval_hours == 24
        assert config.include_pre_release is False

    def test_ui_config_defaults(self):
        """Test UIConfig default values."""
        config = UIConfig()
        assert config.theme == "Dark"
        assert config.window_width == 1200
        assert config.window_height == 800
        assert "name" in config.column_widths

    def test_advanced_config_defaults(self):
        """Test AdvancedConfig default values."""
        config = AdvancedConfig()
        assert config.log_level == "INFO"
        assert config.backup_on_uninstall is True
        assert config.concurrent_downloads == 3

    def test_app_config_aggregation(self):
        """Test AppConfig aggregation of all configs."""
        config = AppConfig()
        assert hasattr(config, "ida")
        assert hasattr(config, "github")
        assert hasattr(config, "updates")
        assert hasattr(config, "ui")
        assert hasattr(config, "advanced")
        assert config.version == "0.1.0"


class TestSettingsManager:
    """Test SettingsManager functionality."""

    def test_settings_manager_create_temp_config(self):
        """Test creating config file in temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.json"
            manager = SettingsManager(config_path=config_path)

            # Should create default config
            assert config_path.exists()
            assert manager.config.version == "0.1.0"

    def test_settings_manager_save_and_load(self):
        """Test saving and loading configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.json"
            manager = SettingsManager(config_path=config_path)

            # Modify settings
            manager.config.ida.install_path = "C:/IDA Pro 9.0"
            manager.config.ida.version = "9.0"
            manager.config.github.token = "test_token_123"

            # Save
            assert manager.save() is True

            # Load into new manager
            manager2 = SettingsManager(config_path=config_path)
            assert manager2.config.ida.install_path == "C:/IDA Pro 9.0"
            assert manager2.config.ida.version == "9.0"
            assert manager2.config.github.token == "test_token_123"

    def test_settings_manager_get_dot_notation(self):
        """Test getting values using dot notation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.json"
            manager = SettingsManager(config_path=config_path)

            manager.config.ida.install_path = "C:/Test"
            manager.config.ui.theme = "Light"

            assert manager.get("ida.install_path") == "C:/Test"
            assert manager.get("ui.theme") == "Light"
            assert manager.get("nonexistent.key", "default") == "default"

    def test_settings_manager_set_dot_notation(self):
        """Test setting values using dot notation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.json"
            manager = SettingsManager(config_path=config_path)

            # Set values
            assert manager.set("ida.version", "8.4") is True
            assert manager.set("ui.theme", "Light") is True

            # Verify
            assert manager.config.ida.version == "8.4"
            assert manager.config.ui.theme == "Light"

    def test_settings_manager_to_dict(self):
        """Test converting config to dictionary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.json"
            manager = SettingsManager(config_path=config_path)

            manager.config.ida.version = "9.0"
            data = manager._to_dict()

            assert isinstance(data, dict)
            assert "ida" in data
            assert "github" in data
            assert "updates" in data
            assert data["ida"]["version"] == "9.0"

    def test_settings_manager_export_import(self):
        """Test exporting and importing configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            export_path = Path(tmpdir) / "exported.json"

            # Create and modify config
            manager = SettingsManager(config_path=config_path)
            manager.config.ida.version = "9.0"
            manager.config.github.token = "ghp_test"

            # Export
            assert manager.export_config(export_path) is True
            assert export_path.exists()

            # Import into new manager
            import_path = Path(tmpdir) / "imported.json"
            manager2 = SettingsManager(config_path=import_path)
            assert manager2.import_config(export_path) is True

            assert manager2.config.ida.version == "9.0"
            assert manager2.config.github.token == "ghp_test"

    def test_settings_manager_reset_to_defaults(self):
        """Test resetting configuration to defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            manager = SettingsManager(config_path=config_path)

            # Modify values
            manager.config.ui.theme = "Light"
            manager.config.ida.version = "8.4"

            # Reset
            manager.reset_to_defaults()

            # Should be back to defaults
            assert manager.config.ui.theme == "Dark"
            assert manager.config.ida.version == ""


class TestConstants:
    """Test application constants."""

    def test_config_paths(self):
        """Test configuration path constants."""
        assert CONFIG_DIR.name == "IDA-Plugin-Manager"
        assert CONFIG_FILE.name == "config.json"
        assert CONFIG_FILE.parent == CONFIG_DIR

    def test_plugin_type_constants(self):
        """Test plugin type constants."""
        assert PLUGIN_TYPE_LEGACY == "legacy"
        assert PLUGIN_TYPE_MODERN == "modern"

    def test_github_api_constants(self):
        """Test GitHub API constants."""
        assert GITHUB_API_BASE == "https://api.github.com"
