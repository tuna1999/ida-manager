# IDA Plugin Manager - GUI-Specific Task Completion Checklist

## UI Task Completion Checklist

After implementing any UI-related task, follow this additional checklist:

### Dear PyGui Specific Checks

- [ ] **No duplicate tags**: All dialog instances use UUID-based tags
- [ ] **Parent specified**: Child windows specify parent parameter when created outside initialization
- [ ] **Dialog cleanup**: All dialogs properly delete themselves on close
- [ ] **Context safety**: Operations that create widgets are in proper parent context

### Dialog Testing

- [ ] **Multiple opens**: Each dialog can be opened/closed 3+ times without errors
- [ ] **Settings Dialog**: All tabs work, browse button works, save/cancel work
- [ ] **About Dialog**: Opens and closes cleanly
- [ ] **Plugin Details**: Shows correct information for different plugins
- [ ] **File Dialog**: Opens correctly, selected path is captured
- [ ] **Progress Dialog**: Shows during operations, closes on completion/error

### UI Component Testing

- [ ] **MainWindow**: Opens with correct viewport size
- [ ] **Menu Bar**: All menu items work
- [ ] **Toolbar**: All buttons trigger correct actions
- [ ] **Filter Panel**: Search, checkboxes, combo all work
- [ ] **Plugin Table**: Displays correctly, selection works
- [ ] **Status Bar**: Updates with latest message
- [ ] **Theme Switching**: Dark/Light themes apply correctly
- [ ] **Responsive**: UI doesn't break on resize

### Integration Testing

- [ ] **Install from URL**: Dialog opens, URL validates, preview shows
- [ ] **Scan Local**: Progress shows, results populate table
- [ ] **Check Updates**: Progress shows, results display correctly
- [ ] **Settings changes**: Persist and reload correctly

### Code Quality for UI

- [ ] **Type hints**: All UI methods have proper type hints
- [ ] **Docstrings**: All UI classes and methods have Google-style docstrings
- [ ] **Error handling**: All callbacks handle exceptions gracefully
- [ ] **No hardcoded colors**: Use theme colors from `themes.py`
- [ ] **Consistent naming**: Widget tags follow naming convention
- [ ] **Clean imports**: All Dear PyGui imports are `import dearpygui.dearpygui as dpg`

### Performance

- [ ] **No blocking operations**: Long operations show progress dialog
- [ ] **UI remains responsive**: During all operations
- [ ] **No memory leaks**: Dialogs properly clean up widgets

### Before Committing UI Changes

1. Run `uv run python -m src.main` and test manually
2. Run `uv run black src/ui/` to format code
3. Run `uv run ruff check src/ui/` to lint
4. Run `uv run mypy src/ui/` for type checking
5. Test all dialogs multiple times
6. Verify theme switching works
7. Check for console errors/warnings

## Common UI Pitfalls to Avoid

### 1. Forgetting UUID Tags
```python
# WRONG - Fixed tags
class Dialog:
    def __init__(self):
        self.tag = "my_dialog"
    
# CORRECT - UUID tags
import uuid
class Dialog:
    def __init__(self):
        self._instance_id = str(uuid.uuid4())[:8]
        self.tag = f"my_dialog_{self._instance_id}"
```

### 2. Not Specifying Parent
```python
# WRONG - Context dependent
def refresh(self):
    with dpg.child_window(tag="child"):
        pass

# CORRECT - Explicit parent
def refresh(self):
    with dpg.child_window(tag="child", parent="main_window"):
        pass
```

### 3. Not Cleaning Up Dialogs
```python
# WRONG - Dialog persists
def show(self):
    with dpg.window(tag="dialog"):
        pass

# CORRECT - Cleanup on close
def _close(self):
    if self._dialog_id and self.dpg.does_item_exist(self._dialog_id):
        dpg.delete_item(self._dialog_id)
        self._dialog_id = None
```

### 4. Hardcoded Colors
```python
# WRONG - Hardcoded
dpg.add_text("Error", color=(255, 0, 0, 255))

# CORRECT - From theme
from src.ui.themes import get_status_color
dpg.add_text("Error", color=get_status_color("error", theme="Dark"))
```

## UI File Structure Reference

```
src/ui/
├── __init__.py
├── main_window.py          # Main window, viewport, menus, toolbar
├── plugin_browser.py       # Plugin list logic (no DPG)
├── status_panel.py         # Status messages (no DPG)
├── themes.py               # Theme definitions and application
└── dialogs/
    ├── __init__.py
    ├── about_dialog.py             # About information modal
    ├── confirm_dialog.py           # Yes/No confirmation
    ├── install_url_dialog.py       # Install from GitHub URL
    ├── plugin_details_dialog.py    # Full plugin information
    ├── progress_dialog.py          # Progress bar for long ops
    └── settings_dialog.py          # Application settings with tabs
```

## Dear PyGui Version Notes

This project uses **Dear PyGui 2.x** (>=1.1.0). Key API differences:

- `mvThemeCol_*` constants for colors
- `mvReservedUUID_2` for global theme application
- `dpg.set_primary_window()` for main window setup
- Context managers for window/widget creation
- Tag-based widget management is critical

For more info: https://dearpygui.readthedocs.io/
