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

### File Dialog Z-Order Issue (FIXED)

#### Problem
Dear PyGui's `file_dialog` appears behind modal parent dialogs and cannot receive user interaction. Additionally, the `pos` parameter doesn't exist, causing errors:

```
Error: [1000]
Message: pos keyword does not exist.
```

#### Root Cause
Dear PyGui 2.x `file_dialog` has limitations:
- No `pos` parameter for positioning
- Modal dialogs block interaction with parent
- Z-order issues when created from within modal dialogs

#### Solution Implemented
Use **tkinter native file dialog** instead of Dear PyGui's file_dialog:

```python
import tkinter as tk
from tkinter import filedialog

def _on_browse_ida(self):
    try:
        # Create temporary tk root window (hidden)
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)  # Force on top
        
        # Show native Windows folder dialog
        selected_path = filedialog.askdirectory(
            title="Select IDA Pro Installation Directory",
            initialdir=current_path
        )
        
        # Clean up tk window
        root.destroy()
        
        # Update Dear PyGui input with selected path
        if selected_path:
            self.dpg.set_value(self._ida_path_tag, selected_path)
    except Exception as e:
        logger.error(f"Error showing file dialog: {e}")
```

#### Files Modified
- [src/ui/dialogs/settings_dialog.py](src/ui/dialogs/settings_dialog.py) - Added tkinter imports and native dialog

#### Benefits
- ✅ Native Windows UI (familiar to users)
- ✅ Correct z-order (always on top)
- ✅ Bypasses Dear PyGui limitations
- ✅ Simple, reliable implementation

---

## Combo Box Callback TypeError (FIXED)

### Problem
Dear PyGui combo callback passes selected item's text (string), not index:
```python
TypeError: '<=' not supported between instances of 'int' and 'str'
```

#### Root Cause
Combo `app_data` parameter contains the display text (e.g., `"C:\path (v9.1)"`), not an integer index.

#### Solution Implemented
Parse the display text to extract the path:

```python
def _on_installation_selected(self, sender, app_data, user_data):
    # app_data is display text: "C:\\path (v9.1)"
    selected_text = str(app_data)
    if " (v" in selected_text:
        path = selected_text.split(" (v")[0]  # Extract path before version
    else:
        path = selected_text
    
    self.dpg.set_value(self._ida_path_tag, path)
```

#### Files Modified
- [src/ui/dialogs/settings_dialog.py](src/ui/dialogs/settings_dialog.py) - Fixed combo callback parsing

---

## IDA Detection Future-Proofing (FIXED)

### Problem
Hardcoded IDA paths only detect specific versions (9.0, 8.4, etc.). Newer versions like 9.3, 9.4, 10.0 are not detected.

#### Solution Implemented
Use **glob patterns** instead of hardcoded paths:

```python
# Before (hardcoded):
IDA_DEFAULT_PATHS = [
    Path("C:/Program Files/IDA Pro 9.0"),  # ❌ Only 9.0
    Path("C:/Program Files/IDA Pro 8.4"),  # ❌ Only 8.4
]

# After (glob patterns):
IDA_DEFAULT_PATHS = [
    Path("C:/Program Files/IDA Pro*"),          # ✅ Any version
    Path("C:/Program Files/IDA Professional*"), # ✅ Any version
    Path("C:/Program Files/IDA*"),               # ✅ Fallback
]
```

#### Files Modified
- [src/config/constants.py](src/config/constants.py) - Replaced hardcoded paths with glob patterns
- Updated `IDA_VERSION_MAX` from "9.9" to "99.0" for future support

#### Supported Versions
Now detects: IDA Pro 8.x, 9.0, 9.1, 9.3, 9.4, 10.0, 11.x, and all future versions!

---
