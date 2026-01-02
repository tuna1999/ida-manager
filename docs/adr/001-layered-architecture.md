# ADR 001: Layered Architecture Design

## Status

Accepted

## Context

IDA Pro Plugin Manager has multiple concerns:
- User interface (Dear PyGui)
- Business logic (plugin management)
- External API integration (GitHub)
- Data persistence (SQLite)
- Data validation (Pydantic models)

### Challenges

- How to organize code for maintainability?
- How to enable parallel development?
- How to test components in isolation?
- How to swap implementations (e.g., change UI framework)?

## Decision

Adopt **strict layered architecture** with clear separation of concerns.

```
┌─────────────────────────────────────┐
│         UI Layer (Dear PyGui)       │  ← User Interaction
├─────────────────────────────────────┤
│        Core Business Logic          │  ← Orchestration
├─────────────────────────────────────┤
│    GitHub Integration Layer         │  ← External APIs
├─────────────────────────────────────┤
│       Database Layer (SQLite)       │  ← Persistence
├─────────────────────────────────────┤
│     Models & Config Layer           │  ← Data Structures
└─────────────────────────────────────┘
```

**Rule**: Dependencies only flow **downward**. Upper layers can call lower layers, but never the reverse.

### Rationale

**Benefits:**

1. **Clear Separation**: Each layer has a single responsibility
2. **Testability**: Mock lower layers to test upper layers in isolation
3. **Parallel Development**: Teams can work on different layers simultaneously
4. **Flexibility**: Can swap implementations (e.g., Dear PyGui → Qt)
5. **Maintainability**: Easy to locate and fix bugs
6. **Code Reuse**: Lower layers can be reused in different contexts

**Example: Testing**

```python
# Can test Core layer without UI
def test_plugin_manager():
    mock_github = MockGitHubClient()
    mock_db = MockDatabaseManager()
    pm = PluginManager(github=mock_github, db=mock_db)
    assert pm.install_plugin("test-id").success == True
```

### Dependency Rules

| From | To | Allowed |
|------|-----|---------|
| UI → Core | ✅ Yes |
| UI → Database | ❌ No |
| UI → GitHub | ❌ No |
| Core → GitHub | ✅ Yes |
| Core → Database | ✅ Yes |
| GitHub → Database | ❌ No |
| All → Models | ✅ Yes |

## Layer Responsibilities

### 1. Models & Config Layer

**Location**: `src/models/`, `src/config/`

**Responsibilities**:
- Define data structures (Pydantic models)
- Validate data inputs
- Manage application configuration
- No business logic, no external dependencies

**Public Interface**:
```python
class Plugin(BaseModel):
    id: str
    name: str
    plugin_type: PluginType
    # ... validation rules

class SettingsManager:
    def get(key: str) -> Any
    def set(key: str, value: Any)
```

### 2. Database Layer

**Location**: `src/database/`

**Responsibilities**:
- Persist and retrieve data
- Execute SQL queries
- Manage transactions
- Return Pydantic models, not SQLAlchemy objects

**Public Interface**:
```python
class DatabaseManager:
    def add_plugin(plugin: Plugin) -> bool
    def get_plugin(plugin_id: str) -> Optional[Plugin]
    def update_plugin(plugin: Plugin) -> bool
    def delete_plugin(plugin_id: str) -> bool
    def search_plugins(query: str) -> List[Plugin]
```

### 3. GitHub Integration Layer

**Location**: `src/github/`

**Responsibilities**:
- GitHub API communication
- Git repository operations
- Metadata parsing
- Release asset downloads
- Return Pydantic models

**Public Interface**:
```python
class GitHubClient:
    def search_repositories(query: str) -> List[GitHubRepo]
    def get_repository(owner: str, name: str) -> GitHubRepo
    def clone_repository(url: str, path: Path) -> bool
    def download_asset(url: str, path: Path) -> bool

class RepoParser:
    def parse_readme(content: str) -> PluginMetadata
    def detect_plugin_type(repo: GitHubRepo) -> PluginType
```

### 4. Core Business Logic Layer

**Location**: `src/core/`

**Responsibilities**:
- Orchestrate operations across layers
- Implement business rules
- Coordinate GitHub and Database layers
- Never talk to UI layer directly

**Public Interface**:
```python
class PluginManager:
    def discover_plugins(query: str) -> List[Plugin]
    def install_plugin(plugin_id: str) -> InstallationResult
    def uninstall_plugin(plugin_id: str) -> InstallationResult
    def check_for_updates(plugin_id: str) -> UpdateInfo
```

### 5. UI Layer

**Location**: `src/ui/`

**Responsibilities**:
- Render user interface
- Handle user input
- Display status and errors
- Only calls Core layer

**Public Interface**:
```python
class MainWindow:
    def __init__(self, plugin_manager: PluginManager):
        self.pm = plugin_manager
```

## Consequences

### Positive

- **Easy to Test**: Each layer can be tested in isolation
- **Parallel Development**: UI team and Core team work independently
- **Swappable Implementations**: Can replace Dear PyGui with Qt if needed
- **Clear Code Organization**: New developers understand structure quickly

### Negative

- **More Boilerplate**: Need to pass data through layers
- **Performance Overhead**: Extra function calls (negligible for desktop app)
- **Rigidity**: Cannot easily bypass layers (feature, not bug)

## Anti-Patterns to Avoid

### ❌ Violating Dependency Rules

```python
# BAD: UI directly accessing database
class MainWindow:
    def install_plugin(self):
        db = DatabaseManager()  # Should not happen!
        db.add_plugin(plugin)
```

```python
# GOOD: UI going through Core
class MainWindow:
    def install_plugin(self):
        result = self.plugin_manager.install_plugin(plugin_id)
```

### ❌ Business Logic in Wrong Layer

```python
# BAD: Validation in database layer
class DatabaseManager:
    def add_plugin(self, plugin):
        if not plugin.name:  # Validation logic belongs in Models!
            return False
```

```python
# GOOD: Validation in Pydantic models
class Plugin(BaseModel):
    name: str = Field(..., min_length=1)
```

## Related Decisions

- [ADR 000: Use SQLite](./000-use-sqlite.md) - Database as separate layer
- [ADR 003: Pydantic for Validation](./003-pydantic-for-validation.md) - Model layer

## References

- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Layered Architecture Pattern](https://en.wikipedia.org/wiki/Multilayered_architecture)
- [Python Architecture Patterns](https://www.youtube.com/watch?v=7K7qCVZx5jM)

---

**Metadata:**
- **Date**: 2026-01-02
- **Author**: IDA Plugin Manager Team
- **Status**: Accepted
- **Supersedes**: None
