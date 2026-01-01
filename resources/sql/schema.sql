-- IDA Plugin Manager Database Schema
-- SQLite database schema for plugin management

-- Plugins table
CREATE TABLE IF NOT EXISTS plugins (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    author TEXT,
    repository_url TEXT,
    installed_version TEXT,
    latest_version TEXT,
    install_date TIMESTAMP,
    last_updated TIMESTAMP,
    plugin_type TEXT CHECK(plugin_type IN ('legacy', 'modern')) NOT NULL,
    ida_version_min TEXT,
    ida_version_max TEXT,
    is_active BOOLEAN DEFAULT 1,
    install_path TEXT,
    metadata_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for plugins table
CREATE INDEX IF NOT EXISTS idx_plugins_name ON plugins(name);
CREATE INDEX IF NOT EXISTS idx_plugins_type ON plugins(plugin_type);
CREATE INDEX IF NOT EXISTS idx_plugins_active ON plugins(is_active);

-- GitHub repositories cache
CREATE TABLE IF NOT EXISTS github_repos (
    id TEXT PRIMARY KEY,
    plugin_id TEXT,
    repo_owner TEXT NOT NULL,
    repo_name TEXT NOT NULL,
    stars INTEGER DEFAULT 0,
    last_fetched TIMESTAMP,
    topics TEXT,
    releases TEXT,
    FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE
);

-- Installation history
CREATE TABLE IF NOT EXISTS installation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plugin_id TEXT NOT NULL,
    action TEXT CHECK(action IN ('install', 'uninstall', 'update', 'failed')),
    version TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    success BOOLEAN DEFAULT 1,
    FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE
);

-- Indexes for installation history
CREATE INDEX IF NOT EXISTS idx_history_plugin ON installation_history(plugin_id);
CREATE INDEX IF NOT EXISTS idx_history_date ON installation_history(timestamp);

-- Application settings
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Default settings
INSERT OR IGNORE INTO settings (key, value) VALUES
    ('ida_install_path', '""'),
    ('ida_version', '""'),
    ('github_token', '""'),
    ('auto_check_updates', '1'),
    ('check_updates_interval', '86400'),
    ('plugin_sources', '["https://github.com/topics/ida-pro-plugin"]'),
    ('theme', '"Dark"'),
    ('log_level', '"INFO"'),
    ('backup_on_uninstall', '1'),
    ('keep_install_history', '1');
