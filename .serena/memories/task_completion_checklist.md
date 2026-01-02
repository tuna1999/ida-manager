# IDA Plugin Manager - Task Completion Checklist

## When Completing a Task

After finishing any development task, follow this checklist:

### 1. Code Quality

```bash
# Format your code
uv run black src/

# Fix linting issues
uv run ruff check --fix src/

# Run type checker
uv run mypy src/
```

**Requirements:**
- [ ] Code is formatted with Black (100 char line length)
- [ ] No Ruff linting errors (E, F, W, I, N rules)
- [ ] No mypy type errors
- [ ] All type hints are correct

### 2. Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

**Requirements:**
- [ ] All existing tests pass
- [ ] New tests added for new functionality (if applicable)
- [ ] Test coverage is not decreased
- [ ] Tests follow naming convention: `test_<function_name>`

### 3. Documentation

**In-code documentation:**
- [ ] All public methods have docstrings
- [ ] Docstrings follow Google style
- [ ] Complex logic has inline comments
- [ ] Module-level docstring present

**Example docstring:**
```python
def install_plugin(
    self,
    plugin_id: str,
    version: Optional[str] = None
) -> InstallationResult:
    """
    Install a plugin from GitHub.

    Args:
        plugin_id: Unique identifier for the plugin
        version: Specific version to install (defaults to latest)

    Returns:
        InstallationResult with success status and details
    """
```

### 4. Code Review Checklist

**Architecture & Design:**
- [ ] Follows layered architecture (UI → Core → Database/GitHub/Models)
- [ ] Dependencies are injected via `__init__` (testability)
- [ ] Returns result objects instead of raising exceptions
- [ ] Uses Pydantic models for data passing between layers
- [ ] Database models properly converted to Pydantic models

**Specific Patterns:**
- [ ] Enum classes for constants (PluginType, CompatibilityStatus)
- [ ] `model_config` for Pydantic v2 (NOT `Config` class)
- [ ] `Mapped[]` type hints for SQLAlchemy 2.0
- [ ] JSON columns manually serialized/deserialized
- [ ] Private methods prefixed with `_`

**Error Handling:**
- [ ] Exceptions caught and logged
- [ ] User-friendly error messages in result objects
- [ ] No bare `except:` clauses
- [ ] Uses specific exception types

### 5. Platform-Specific Checks

**Windows Considerations:**
- [ ] Uses `pathlib.Path` for cross-platform compatibility
- [ ] Paths use forward slashes in code (`C:/Program Files/`)
- [ ] Config location: `%APPDATA%\IDA-Plugin-Manager\`
- [ ] No Unix-specific commands

### 6. Git Commit

```bash
# Check what changed
git status
git diff

# Stage changes
git add <files>

# Commit with conventional commit format
git commit -m "feat: implement plugin installer"
```

**Commit Message Format:**
```
<type>: <description>

[optional body]

[optional footer]
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `refactor:` Code refactoring
- `test:` Adding/updating tests
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `chore:` Maintenance tasks

**Examples:**
```
feat: implement plugin installer from GitHub releases

- Add GitHubClient.download_release_asset()
- Add PluginInstaller.install_from_release()
- Handle download progress and errors
```

```
fix: resolve database connection issue

The database manager was not properly closing connections,
leading to SQLite database locks.
```

### 7. Integration Verification

**If working on a specific layer:**

**Config/Models Layer:**
- [ ] Run `pytest tests/test_config_and_models.py`
- [ ] All Pydantic models validate correctly
- [ ] Settings load/save properly

**Database Layer:**
- [ ] Run `pytest tests/test_database.py`
- [ ] CRUD operations work
- [ ] JSON columns serialize/deserialize correctly
- [ ] Relationships work (cascade deletes, etc.)

**Core Layer:**
- [ ] PluginManager orchestrates correctly
- [ ] IDADetector finds installations
- [ ] VersionManager compares versions properly
- [ ] Result objects returned with correct data

**GitHub Layer:**
- [ ] API requests handle rate limiting
- [ ] Error responses handled gracefully
- [ ] Caching works to minimize API calls
- [ ] RepoParser extracts metadata correctly

**UI Layer:**
- [ ] Application starts without errors
- [ ] UI elements display correctly
- [ ] Callbacks trigger proper operations
- [ ] Status updates shown to user

### 8. Final Checks

- [ ] No commented-out debug code
- [ ] No TODO/FIXME comments left in production code
- [ ] No hardcoded credentials or paths
- [ ] Logging statements appropriate (not excessive)
- [ ] Configuration can be customized
- [ ] README.md updated if user-facing changes

## Common Issues to Watch For

### Pydantic Version Mismatch
```python
# WRONG (Pydantic v1)
class Plugin(BaseModel):
    class Config:
        use_enum_values = True

# CORRECT (Pydantic v2)
class Plugin(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
```

### SQLAlchemy Version Mismatch
```python
# WRONG (SQLAlchemy < 2.0)
id = Column(String(255), primary_key=True)

# CORRECT (SQLAlchemy 2.0+)
id: Mapped[str] = mapped_column(String(255), primary_key=True)
```

### Exception Handling
```python
# WRONG
def install_plugin(self, plugin_id: str):
    try:
        self._do_install(plugin_id)
    except:
        pass  # Silent failure

# CORRECT
def install_plugin(self, plugin_id: str) -> InstallationResult:
    try:
        self._do_install(plugin_id)
        return InstallationResult(success=True, ...)
    except NetworkError as e:
        logger.error(f"Network error: {e}")
        return InstallationResult(success=False, error=str(e), ...)
```

### Type Hints
```python
# WRONG
def install_plugin(self, plugin_id, version=None):
    pass

# CORRECT
def install_plugin(self, plugin_id: str, version: Optional[str] = None) -> InstallationResult:
    pass
```

## Before Marking Task as Done

1. **Run the full test suite**: `uv run pytest`
2. **Run the application**: `uv run python -m src.main`
3. **Verify the feature works** manually if UI-related
4. **Check for any console errors or warnings**
5. **Ensure git status is clean** (or changes are properly committed)
