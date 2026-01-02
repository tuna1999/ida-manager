# ADR 000: Use SQLite for Data Persistence

## Status

Accepted

## Context

IDA Pro Plugin Manager needs to persist:
- Plugin metadata and versions
- Installation history
- GitHub repository cache
- Application settings

### Constraints

- Desktop application running on Windows
- Single user, local machine
- No network access to shared database
- Must work offline after initial plugin discovery
- Simple deployment (no separate database server)

## Decision

Use **SQLite** as the embedded database.

### Rationale

**Pros:**
- ✅ Serverless - no separate database process to manage
- ✅ Single-file storage - easy backup and portability
- ✅ Built into Python standard library (`sqlite3` module)
- ✅ Excellent Windows support
- ✅ Zero configuration - works out of the box
- ✅ ACID transactions for data integrity
- ✅ Sufficient performance for desktop application scale
- ✅ Full-text search extension available if needed
- ✅ Easy to inspect with SQLite GUI tools

**Cons:**
- ❌ No concurrent write support (not needed for single-user desktop app)
- ❌ Limited scalability (not needed for <10,000 plugins)
- ❌ No network access (feature, not bug for offline use)

### Alternatives Considered

#### 1. JSON Files
```python
# Store data in JSON files
plugins.json
github_cache.json
settings.json
```

**Rejected because:**
- No query capabilities
- Slow for large datasets
- No transaction support
- Manual index management
- Race conditions on writes

#### 2. PostgreSQL / MySQL
```python
# Use full database server
connection = psycopg2.connect("postgresql://...")
```

**Rejected because:**
- Requires separate database server installation
- Complex deployment (Docker, services, ports)
- Overkill for single-user desktop app
- Network configuration required
- Heavier resource footprint

#### 3. TinyDB
```python
# Document-oriented database
from tinydb import TinyDB, Query
db = TinyDB('plugins.json')
```

**Rejected because:**
- Less mature than SQLite
- No built-in Python support (external dependency)
- Slower for large datasets
- Limited query capabilities
- No ACID guarantees

## Consequences

### Positive

- **Simple Deployment**: Single `.db` file alongside application
- **Easy Debugging**: Can open database with DB Browser for SQLite
- **Fast Performance**: In-process queries, no network overhead
- **Transaction Safety**: ACID guarantees prevent data corruption
- **Backup/Restore**: Single file copy for full backup

### Negative

- **Schema Migrations**: Requires custom migration system (implemented)
- **JSON Columns**: No native JSON type (workaround: TEXT with JSON parsing)
- **File Locking**: SQLite file locks on Windows (engine.dispose() required)

## Implementation

### Database Location

```python
# %APPDATA%\IDA-Plugin-Manager\plugins.db
DATABASE_FILE = CONFIG_DIR / "plugins.db"
```

### ORM: SQLAlchemy 2.0

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class DatabaseManager:
    def __init__(self):
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
```

### Migration System

Custom migration manager in `src/database/migrations.py`:

```python
class MigrationManager:
    def migrate(self, target_version: Optional[int] = None) -> bool
    def get_current_version(self) -> int
    def get_applied_migrations(self) -> List[int]
```

## Related Decisions

- [ADR 001: Layered Architecture](./001-layered-architecture.md) - Database as separate layer
- [ADR 003: Pydantic for Validation](./003-pydantic-for-validation.md) - Model separation

## References

- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [DB Browser for SQLite](https://sqlitebrowser.org/)

---

**Metadata:**
- **Date**: 2026-01-02
- **Author**: IDA Plugin Manager Team
- **Status**: Accepted
- **Supersedes**: None
