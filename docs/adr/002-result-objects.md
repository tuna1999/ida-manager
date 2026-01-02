# ADR 002: Result Objects Instead of Exceptions

## Status

Accepted

## Context

Plugin operations can fail for various reasons:
- Network errors (GitHub API unreachable)
- File system errors (permission denied, disk full)
- Validation errors (incompatible IDA version)
- Git errors (clone failed, invalid repository)

### Challenge

How should operations signal success or failure to callers?

## Decision

Use **result objects** with explicit success/failure status instead of raising exceptions.

### Pattern

```python
class InstallationResult(BaseModel):
    success: bool           # True if operation succeeded
    plugin_id: str          # Plugin identifier
    message: str            # Human-readable description
    error: Optional[str]    # Error details if failed
    previous_version: Optional[str]  # For updates
    new_version: Optional[str]       # For updates

# Usage
result: InstallationResult = plugin_manager.install_plugin(plugin_id)
if result.success:
    logger.info(f"Installed {result.new_version}")
else:
    logger.error(f"Failed: {result.error}")
```

### Rationale

**Benefits:**

1. **Explicit Error Handling**: Success/failure is clear in code
2. **No Hidden Control Flow**: Exceptions skip intermediate code
3. **Easy to Test**: Can assert on result object properties
4. **Better Error Messages**: Structured error data, not just exceptions
5. **Functional Style**: Works well with type hints and mypy

**Alternatives Considered:**

#### 1. Raise Exceptions

```python
def install_plugin(plugin_id: str) -> None:
    if error:
        raise InstallationError("Failed to install")

# Usage
try:
    install_plugin(plugin_id)
except InstallationError as e:
    logger.error(str=e)
```

**Rejected because:**
- Exceptions are for **exceptional** circumstances (not user errors)
- Hidden control flow - hard to see all failure paths
- Requires try/except blocks everywhere
- Cannot return both data AND error (needs separate error callback)

#### 2. Return Tuples

```python
def install_plugin(plugin_id: str) -> tuple[bool, str, Optional[Exception]]:
    # Returns (success, message, error)

# Usage
success, message, error = install_plugin(plugin_id)
if success:
    print(message)
```

**Rejected because:**
- No field names - hard to remember tuple positions
- Cannot extend with additional fields
- Unclear what each element represents
- Not self-documenting

#### 3. Callbacks

```python
def install_plugin(plugin_id: str,
                  on_success: Callable,
                  on_error: Callable):
    if success:
        on_success(data)
    else:
        on_error(error)
```

**Rejected because:**
- Callback hell for nested operations
- Hard to chain multiple operations
- Control flow split across functions
- Not composable

## Result Object Hierarchy

### Validation Result

```python
class ValidationResult(BaseModel):
    valid: bool
    plugin_type: Optional[PluginType]
    error: Optional[str]
    warnings: List[str]

# Usage
result = validator.validate_plugin(repo)
if not result.valid:
    show_error(result.error)
```

### Installation Result

```python
class InstallationResult(BaseModel):
    success: bool
    plugin_id: str
    message: str
    error: Optional[str]
    previous_version: Optional[str]
    new_version: Optional[str]

# Usage
result = installer.install(plugin)
if result.success:
    show_success(f"Installed {result.new_version}")
else:
    show_error(result.error)
```

### Update Info

```python
class UpdateInfo(BaseModel):
    has_update: bool
    current_version: Optional[str]
    latest_version: Optional[str]
    changelog: Optional[str]
    release_url: Optional[str]

# Usage
info = updater.check_update(plugin_id)
if info.has_update:
    prompt_update(info.latest_version, info.changelog)
```

## When to Use Exceptions

Result objects are for **expected** failures. Use exceptions for **unexpected** errors:

| Scenario | Approach | Example |
|-----------|----------|---------|
| Network timeout | Result Object | GitHub API unreachable |
| Invalid user input | Result Object | Bad plugin URL |
| File not found | Result Object | Plugin directory missing |
| Null pointer | Exception | `NoneType has no attribute` |
| Assertion failure | Exception | Invariant violated |
| Programming error | Exception | Type error in function call |

```python
# GOOD: Result object for expected failure
def download_plugin(url: str) -> DownloadResult:
    try:
        response = requests.get(url, timeout=30)
        return DownloadResult(success=True, data=response.content)
    except requests.Timeout:
        # Expected: network can timeout
        return DownloadResult(success=False, error="Request timed out")
    except Exception as e:
        # Unexpected: programming error
        raise RuntimeError(f"Unexpected error: {e}") from e
```

## Consequences

### Positive

- **Explicit Error Handling**: All error paths visible in code
- **Composable Results**: Can chain result-returning functions
- **Type Safety**: Result objects work with mypy
- **Easy Testing**: Assert on result object properties
- **Better UX**: Can show detailed error messages to users

### Negative

- **More Boilerplate**: Need to define result classes
- **Verbosity**: `result.success` check vs try/except
- **Forgetting to Check**: Easy to ignore `result.success`

## Implementation Examples

### Chaining Results

```python
def install_and_update(plugin_id: str) -> InstallationResult:
    # Step 1: Download
    download_result = github_client.download_plugin(plugin_id)
    if not download_result.success:
        return InstallationResult(
            success=False,
            plugin_id=plugin_id,
            error=f"Download failed: {download_result.error}"
        )

    # Step 2: Install
    install_result = installer.install_files(download_result.data)
    if not install_result.success:
        return InstallationResult(
            success=False,
            plugin_id=plugin_id,
            error=f"Install failed: {install_result.error}"
        )

    # Step 3: Update database
    db.update_plugin(plugin_id, version=install_result.version)

    return InstallationResult(
        success=True,
        plugin_id=plugin_id,
        message="Successfully installed",
        new_version=install_result.version
    )
```

### Error Aggregation

```python
def batch_install(plugin_ids: List[str]) -> BatchResult:
    results = []
    for plugin_id in plugin_ids:
        result = install_plugin(plugin_id)
        results.append(result)

    return BatchResult(
        total=len(results),
        successful=sum(r.success for r in results),
        failed=sum(not r.success for r in results),
        results=results
    )
```

## Related Decisions

- [ADR 001: Layered Architecture](./001-layered-architecture.md) - Result objects cross layers
- [ADR 003: Pydantic for Validation](./003-pydantic-for-validation.md) - Result objects as Pydantic models

## References

- [Result Pattern in Rust](https://doc.rust-lang.org/std/result/enum.Result.html)
- [Never Throw Exceptions in API Design](https://www.youtube.com/watch?v=6WbKLaIdJHA)
- [Result Pattern in Python](https://github.com/dry-python/returns)

---

**Metadata:**
- **Date**: 2026-01-02
- **Author**: IDA Plugin Manager Team
- **Status**: Accepted
- **Supersedes**: None
