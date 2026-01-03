"""
Database migration utilities.

Handles database schema migrations and version management.
"""

import sqlite3
from pathlib import Path
from typing import List, Optional

from src.config.constants import DATABASE_FILE


class Migration:
    """Database migration definition."""

    def __init__(self, version: int, name: str, up_sql: str, down_sql: Optional[str] = None):
        """
        Initialize migration.

        Args:
            version: Migration version number
            name: Migration name/description
            up_sql: SQL to apply migration
            down_sql: SQL to rollback migration (optional)
        """
        self.version = version
        self.name = name
        self.up_sql = up_sql
        self.down_sql = down_sql


# Define migrations
MIGRATIONS: List[Migration] = [
    Migration(
        version=2,
        name="Add plugin catalog management fields",
        up_sql="""
            -- Add status column
            ALTER TABLE plugins ADD COLUMN status VARCHAR(20) DEFAULT 'not_installed' NOT NULL;

            -- Add installation_method column
            ALTER TABLE plugins ADD COLUMN installation_method VARCHAR(10);

            -- Add error_message column
            ALTER TABLE plugins ADD COLUMN error_message TEXT;

            -- Add added_at column
            ALTER TABLE plugins ADD COLUMN added_at DATETIME;

            -- Add last_updated_at column
            ALTER TABLE plugins ADD COLUMN last_updated_at DATETIME;

            -- Add tags column (JSON array)
            ALTER TABLE plugins ADD COLUMN tags JSON;

            -- Create indexes for performance
            CREATE INDEX IF NOT EXISTS idx_plugin_status ON plugins(status);
            CREATE INDEX IF NOT EXISTS idx_last_updated ON plugins(last_updated_at);

            -- Update existing installed plugins to have status='installed'
            UPDATE plugins SET status='installed' WHERE installed_version IS NOT NULL;
        """,
        down_sql="""
            -- Drop indexes
            DROP INDEX IF EXISTS idx_last_updated;
            DROP INDEX IF NOT EXISTS idx_plugin_status;

            -- Drop columns (SQLite doesn't support DROP COLUMN in older versions,
            -- but we'll include it for completeness)
            ALTER TABLE plugins DROP COLUMN tags;
            ALTER TABLE plugins DROP COLUMN last_updated_at;
            ALTER TABLE plugins DROP COLUMN added_at;
            ALTER TABLE plugins DROP COLUMN error_message;
            ALTER TABLE plugins DROP COLUMN installation_method;
            ALTER TABLE plugins DROP COLUMN status;
        """
    ),
]


class MigrationManager:
    """
    Database migration manager.

    Handles applying and rolling back database migrations.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize migration manager.

        Args:
            db_path: Path to database file. Defaults to DATABASE_FILE.
        """
        self.db_path = db_path or DATABASE_FILE

    def _ensure_migration_table(self) -> None:
        """Ensure migrations table exists."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        conn.commit()
        conn.close()

    def get_current_version(self) -> int:
        """
        Get current database schema version.

        Returns:
            Current schema version (0 if no migrations applied).
        """
        self._ensure_migration_table()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(version) FROM schema_migrations")
        result = cursor.fetchone()
        conn.close()

        return result[0] if result and result[0] else 0

    def get_applied_migrations(self) -> List[int]:
        """
        Get list of applied migration versions.

        Returns:
            List of applied migration version numbers.
        """
        self._ensure_migration_table()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
        result = [row[0] for row in cursor.fetchall()]
        conn.close()

        return result

    def migrate(self, target_version: Optional[int] = None) -> bool:
        """
        Apply migrations to bring database to target version.

        Args:
            target_version: Target version to migrate to.
                          If None, migrates to latest version.

        Returns:
            True if successful, False otherwise.
        """
        if target_version is None:
            target_version = max(m.version for m in MIGRATIONS) if MIGRATIONS else 0

        current_version = self.get_current_version()

        if current_version == target_version:
            print(f"Database already at version {current_version}")
            return True

        # Determine migrations to apply
        if target_version > current_version:
            # Apply forward migrations
            migrations_to_apply = [m for m in MIGRATIONS if current_version < m.version <= target_version]
        else:
            # Rollback migrations
            migrations_to_apply = [
                m for m in reversed(MIGRATIONS) if target_version <= m.version < current_version
            ]

        if not migrations_to_apply:
            print("No migrations to apply")
            return True

        # Apply migrations
        conn = sqlite3.connect(self.db_path)
        try:
            for migration in migrations_to_apply:
                if target_version > current_version:
                    print(f"Applying migration {migration.version}: {migration.name}")
                    sql = migration.up_sql
                else:
                    print(f"Rolling back migration {migration.version}: {migration.name}")
                    sql = migration.down_sql

                if not sql:
                    print(f"  No SQL defined for this operation, skipping")
                    continue

                cursor = conn.cursor()
                cursor.executescript(sql)
                conn.commit()

                if target_version > current_version:
                    cursor.execute(
                        "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                        (migration.version, migration.name),
                    )
                else:
                    cursor.execute("DELETE FROM schema_migrations WHERE version = ?", (migration.version,))

                conn.commit()
                print(f"  Done")

            conn.close()
            return True

        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"Migration failed: {e}")
            return False

    def status(self) -> None:
        """Print current migration status."""
        current_version = self.get_current_version()
        applied = self.get_applied_migrations()

        print(f"Current schema version: {current_version}")
        print(f"Applied migrations: {applied}")

        pending = [m for m in MIGRATIONS if m.version > current_version]
        if pending:
            print(f"Pending migrations: {[m.version for m in pending]}")
        else:
            print("Database is up to date")


if __name__ == "__main__":
    import sys

    manager = MigrationManager()

    # Check command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "status":
            manager.status()
        elif command == "migrate":
            target = int(sys.argv[2]) if len(sys.argv) > 2 else None
            success = manager.migrate(target)
            if not success:
                sys.exit(1)
        else:
            print(f"Unknown command: {command}")
            print("Usage: python -m src.database.migrations [status|migrate [version]]")
            sys.exit(1)
    else:
        # Default: run migrations
        print("Running database migrations...")
        success = manager.migrate()
        if success:
            print("\nMigration status:")
            manager.status()
        else:
            print("Migration failed!")
            sys.exit(1)
