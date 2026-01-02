# Known Issues & Solutions - IDA Plugin Manager

## Dear PyGui Tag Conflicts (FIXED)

### Problem
When opening dialogs (Settings, About, Plugin Details) multiple times, Dear PyGui throws "Alias already exists" error:

```
Error: [1000]
Command: add alias
Message: Alias already exists
```

### Root Cause
Dear PyGui doesn't allow multiple widgets with the same tag. When dialogs use fixed string tags like `"about_dialog"`, opening the dialog a second time fails because the tag already exists in Dear PyGui's internal registry.

### Solution Implemented
Use UUID-based instance IDs for all dialog widgets:

```python
import uuid

class AboutDialog:
    def __init__(self, dpg):
        self.dpg = dpg
        self._instance_id = str(uuid.uuid4())[:8]
        self._dialog_id: Optional[int] = None
    
    def show(self):
        dialog_tag = f"about_dialog_{self._instance_id}"
        with self.dpg.window(label="About", tag=dialog_tag):
            self._dialog_id = dialog_tag
            # ... dialog content
```

### Files Modified
- [src/ui/dialogs/settings_dialog.py](src/ui/dialogs/settings_dialog.py) - Added UUID to all widget tags
- [src/ui/dialogs/about_dialog.py](src/ui/dialogs/about_dialog.py) - Added UUID to dialog tag
- [src/ui/dialogs/plugin_details_dialog.py](src/ui/dialogs/plugin_details_dialog.py) - Added UUID to dialog and child tags

## MainWindow _refresh_ui Context Issue (FIXED)

### Problem
When `_refresh_ui()` is called from a callback, creating the plugins child window fails with:
```
Error: [1011]
Message: Parent could not be deduced.
```

### Root Cause
The `_create_plugin_list_panel()` method creates a child window without specifying a parent. When called from `_refresh_ui()` (which is triggered by a callback), the Dear PyGui context stack doesn't have the correct parent context.

### Solution Implemented
Explicitly specify the parent when creating the child window:

```python
# Before (broken):
with dpg.child_window(label="Plugins", tag="plugins_child_window"):
    pass

# After (fixed):
with dpg.child_window(label="Plugins", tag="plugins_child_window", parent="main_window"):
    pass
```

### File Modified
- [src/ui/main_window.py](src/ui/main_window.py) - Added `parent="main_window"` parameter

## Testing After Dear PyGui Changes

After any changes to dialogs or widget creation, always test:
1. Open/close each dialog 3+ times
2. Switch between Dark/Light themes
3. Use all buttons in each dialog
4. Test file dialogs (Settings → Browse)
5. Test UI refresh operations

## Other Known Patterns to Follow

### Progress Dialog Pattern
Always show progress before long operations:
```python
progress = ProgressDialog(dpg)
progress.show(title="Operation Name", status="Starting...")
try:
    # Do work
    progress.close()
except Exception as e:
    progress.close()
    # Handle error
```

### Dialog Cleanup Pattern
Always check if dialog exists before creating, and delete properly on close:
```python
def show(self):
    if self._dialog_id and self.dpg.does_item_exist(self._dialog_id):
        self.dpg.focus_item(self._dialog_id)
        return
    # Create dialog...

def _close(self):
    if self._dialog_id and self.dpg.does_item_exist(self._dialog_id):
        self.dpg.delete_item(self._dialog_id)
        self._dialog_id = None
```

### File Dialog Pattern
File dialogs should be created once and reused, with unique tags per parent dialog:
```python
def __init__(self, dpg):
    self._file_dialog_tag = f"file_dialog_{self._instance_id}"

def _on_browse(self):
    if not self.dpg.does_item_exist(self._file_dialog_tag):
        with self.dpg.file_dialog(tag=self._file_dialog_tag, ...):
            pass
    self.dpg.show_file_dialog(self._file_dialog_tag)
```
