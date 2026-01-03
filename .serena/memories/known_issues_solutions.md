# Known Issues and Solutions

## Database & Migration Issues

### Issue: Database schema not updated after code changes
**Symptom:** `sqlite3.OperationalError: no such column: plugins.status`
**Cause:** Database migration not run after adding new columns
**Solution:** Run migration command:
```bash
uv run python -m src.database.migrations
```
**File:** `src/database/migrations.py`
**Fixed:** 2026-01-03

### Issue: Migration command didn't work initially
**Symptom:** No output when running migrations
**Cause:** Missing `if __name__ == "__main__"` block
**Solution:** Added CLI interface to migrations.py:
```python
if __name__ == "__main__":
    manager = MigrationManager()
    success = manager.migrate()
```
**Commands:**
- `uv run python -m src.database.migrations` - Run all migrations
- `uv run python -m src.database.migrations status` - Show current version
- `uv run python -m src.database.migrations migrate 2` - Migrate to version 2
**File:** `src/database/migrations.py:236-265`
**Fixed:** 2026-01-03

## Model & Validation Issues

### Issue: Pydantic validation error for metadata field
**Symptom:** `Input should be a valid dictionary [type=dict_type, input_value=None]`
**Cause:** `metadata_json` was `None` for plugins without metadata, but Plugin model expects Dict
**Solution:** Changed default value in `_db_to_model()`:
```python
# OLD: metadata_json = None
# NEW: metadata_json = {}
```
**File:** `src/repositories/plugin_repository.py:215`
**Fixed:** 2026-01-03

### Issue: Plugin type display error
**Symptom:** `AttributeError: 'str' object has no attribute 'value'`
**Cause:** Plugin model has `use_enum_values=True`, so enums are auto-converted to strings
**Solution:** Removed `.value` access:
```python
# OLD: plugin.plugin_type.value[0].upper()
# NEW: plugin.plugin_type[0].upper()
```
**File:** `src/ui/main_window.py:321-322`
**Fixed:** 2026-01-03

### Issue: RepoParser receiving wrong arguments
**Symptom:** `parse_repository() takes 4 positional arguments but 5 were given`
**Cause:** Passing owner, repo separately instead of combined repo_name
**Solution:** Changed call:
```python
# OLD: parser.parse_repository(owner, repo, repo_info, None, client)
# NEW: parser.parse_repository(repo, contents, readme, plugins_json)
```
**File:** `src/ui/dialogs/install_url_dialog.py:218-222`
**Fixed:** 2026-01-03

## UI & Dialog Issues

### Issue: URL input returns 'None' string
**Symptom:** URL input shows 'None' instead of empty string after dialog close
**Cause:** Dear PyGui callback behavior with input_text widgets
**Solution:** Store validated URL in instance variable:
```python
self._validated_url = url  # Store before closing dialog
# Use stored URL in callback
url = self._validated_url
```
**File:** `src/ui/dialogs/install_url_dialog.py:37,299-300`
**Fixed:** 2026-01-03

### Issue: Dialog alias conflicts
**Symptom:** "Alias already exists" error when reopening dialogs
**Cause:** Using static tags for dialog widgets
**Solution:** Use UUID-based tags:
```python
import uuid
self._instance_id = str(uuid.uuid4())[:8]
dialog_tag = f"settings_dialog_{self._instance_id}"
```
**Files:** 
- `src/ui/dialogs/settings_dialog.py`
- `src/ui/dialogs/about_dialog.py`
- `src/ui/dialogs/plugin_details_dialog.py`
**Fixed:** 2026-01-03

### Issue: Parent cannot be deduced for child_window
**Symptom:** "Parent could not be deduced" error
**Cause:** Creating child_window outside parent context
**Solution:** Explicitly specify parent parameter:
```python
dpg.child_window(tag="plugins_child_window", parent="main_window")
```
**File:** `src/ui/main_window.py`
**Fixed:** 2026-01-03

### Issue: File dialog z-order issue
**Symptom:** File dialog appears behind main window
**Cause:** Dear PyGui file dialog doesn't work well on Windows
**Solution:** Use tkinter native file dialog:
```python
import tkinter as tk
from tkinter import filedialog

root = tk.Tk()
root.wm_attributes('-topmost', True)
root.withdraw()
file_path = filedialog.askdirectory(...)
root.destroy()
```
**File:** `src/ui/dialogs/settings_dialog.py`
**Fixed:** 2026-01-03

## Git & Installation Issues

### Issue: Subprocess git calls unreliable
**Symptom:** Git operations fail intermittently
**Cause:** Using subprocess to call git commands
**Solution:** Replace with GitPython package:
```python
# OLD: subprocess.run(["git", "clone", ...])
# NEW: git.Repo.clone_from(url, destination, branch=branch, depth=1)
```
**Benefits:**
- Direct Python API (no subprocess overhead)
- Better error handling
- Cross-platform compatibility
**Files:** 
- `src/github/client.py` (clone_repository, get_commit_hash, pull_repository)
- `src/core/installer.py` (uses get_commit_hash)
**Fixed:** 2026-01-03

### Issue: Version comparison fails for versions like "8.10" vs "8.9"
**Symptom:** Version "8.10" considered older than "8.9" (string comparison)
**Cause:** Comparing versions as strings instead of semantic versions
**Solution:** Created `IDAVersion` class:
```python
class IDAVersion:
    def __init__(self, version_str):
        self.major, self.minor, self.patch = ...
    
    def __lt__(self, other):
        # Proper numeric comparison
```
**File:** `src/utils/version_utils.py`
**Fixed:** 2026-01-03

## Plugin Detection Issues

### Issue: False positives from plugins.json detection
**Symptom:** Non-plugin repositories detected as plugins
**Cause:** `plugins.json` is used by npm/webpack, not IDA Pro
**Solution:** Only check for `ida-plugin.json` (IDA Pro 9.0+ official format)
**File:** `src/github/repo_parser.py`
**Fixed:** 2026-01-03

### Issue: Missing metadata in ValidationResult
**Symptom:** Cannot access plugin metadata after validation
**Cause:** ValidationResult didn't include metadata field
**Solution:** Added `metadata: Optional[PluginMetadata]` field
**File:** `src/models/plugin.py` (ValidationResult class)
**Fixed:** 2026-01-03

## Settings Dialog Issues

### Issue: Missing os import
**Symptom:** `NameError: name 'os' is not defined`
**Cause:** Forgot to import os module
**Solution:** Added `import os` at top of file
**File:** `src/ui/dialogs/settings_dialog.py`
**Fixed:** 2026-01-03

### Issue: Combo box callback receives wrong type
**Symptom:** TypeError when parsing combo box selection
**Cause:** Dear PyGui sends app_data as string, but code expected list
**Solution:** Parse combo box value correctly:
```python
def _on_combo_change(sender, app_data, user_data):
    # app_data is the selected value as string
    selected_value = str(app_data)
```
**File:** `src/ui/dialogs/settings_dialog.py`
**Fixed:** 2026-01-03

## Thread Safety Issues

### Issue: Race conditions in GitHub client cache
**Symptom:** Intermittent cache corruption or key errors
**Cause:** Multiple threads accessing cache without locks
**Solution:** Added thread-safe caching with `threading.Lock()`
**File:** `src/github/client.py`
**Fixed:** 2026-01-02

### Issue: Rate limit counter not thread-safe
**Symptom:** Incorrect rate limit tracking under concurrent requests
**Cause:** Counter updates without atomic operations
**Solution:** Use locks for counter updates
**File:** `src/github/client.py`
**Fixed:** 2026-01-02

## Resource Management Issues

### Issue: GitHub client session not closed
**Symptom:** Resource warnings, unclosed sessions
**Cause:** Not properly closing requests.Session()
**Solution:** Implement context manager:
```python
def __enter__(self): return self
def __exit__(self, exc_type, exc_val, exc_tb):
    self.close()
```
**File:** `src/github/client.py`
**Fixed:** 2026-01-02

## Current Known Issues

### Issue: Font settings disabled due to Dear PyGui 2.1.1 limitations
**Symptom:** Font family and font size controls hidden in settings dialog
**Cause:** Dear PyGui 2.1.1 has issues with custom font loading on Windows (C++ backend error when calling add_font())
**Status:** DISABLED - Font settings UI components commented out
**Impact:** Users cannot change font family or size through settings dialog
**Workaround:** Application uses Dear PyGui default font
**Future Fix:** Upgrade Dear PyGui version or implement workaround for custom font loading
**File:** `src/ui/dialogs/settings_dialog.py:213-247`
**Reported:** 2026-01-03

### Issue: Theme switching requires manual call to switch_theme()
**Symptom:** Theme only changes after saving settings if switch_theme() is called
**Cause:** Theme changes not automatically applied
**Status:** FIXED - switch_theme() now called in _on_save()
**File:** `src/ui/dialogs/settings_dialog.py:530-536`
**Fixed:** 2026-01-03

**As of 2026-01-03, only font loading limitation remains (disabled in UI).**

The application is running successfully with:
- Database migration v2 applied
- 1 plugin loaded from database
- All catalog features functional
- No errors or warnings

## Prevention Guidelines

### For Database Changes
1. Always create migration before changing schema
2. Test migration on fresh database
3. Provide down migration for rollback
4. Update DatabaseManager with new methods

### For Model Changes
1. Provide default values for new fields
2. Update `_db_to_model()` and `_model_to_db()` converters
3. Handle None values gracefully (use {} instead of None for dicts)
4. Consider `use_enum_values=True` implications

### For UI Changes
1. Always use UUID-based tags for dialogs
2. Specify parent explicitly for child_window
3. Test dialog open/close multiple times
4. Handle Dear PyGui callback quirks

### For Git Operations
1. Use GitPython instead of subprocess
2. Handle git.GitCommandError properly
3. Clean up partial clones on failure
4. Use shallow clones for faster operations

### For Thread Safety
1. Use locks for shared mutable state
2. Avoid global variables
3. Use context managers for resources
4. Test with concurrent operations

---

**Last Updated:** 2026-01-03
**Status:** All issues resolved ✅