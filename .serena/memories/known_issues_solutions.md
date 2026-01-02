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

## IDAUSR Environment Variable Support (01/02/2026)

### Problem
IDADetector didn't support the IDAUSR environment variable, which is IDA Pro's official mechanism for user-specific plugins directory. The original implementation only used hardcoded default paths (`%APPDATA%/Hex-Rays/IDA Pro`) and didn't follow IDA's plugin loading order.

**Original limitations**:
- ❌ Only checked hardcoded default location
- ❌ Didn't read `%IDAUSR%` environment variable
- ❌ Didn't support multiple paths in IDAUSR
- ❌ Didn't follow IDA's loading order (IDAUSR → IDADIR)
- ❌ Required admin permissions for IDADIR/plugins installation

### Root Cause
According to [Hex-Rays documentation](https://docs.hex-rays.com/user-guide/general-concepts/environment-variables), IDA Pro uses two environment variables:
- **IDAUSR**: User directory for plugins and settings (priority)
- **IDADIR**: Installation directory

IDA loads plugins in this order:
1. `$IDAUSR/plugins` (user plugins - **priority**, overrides IDADIR)
2. `%IDADIR%/plugins` (installation plugins)

IDAUSR can contain **multiple paths** separated by platform-specific separators:
- Windows: semicolon (`;`)
- Linux/Mac: colon (`:`)

### Solution Implemented

#### 1. Added `get_idausr_directories()` method

**Purpose**: Parse IDAUSR environment variable and return all directories

**Implementation**:
```python
def get_idausr_directories(self) -> List[Path]:
    """
    Get all IDAUSR directories from environment variable.

    IDAUSR can contain multiple paths separated by platform separator:
    - Windows: semicolon (;)
    - Linux/Mac: colon (:)
    """
    idausr_env = os.environ.get("IDAUSR", "")

    if not idausr_env:
        # Return default location based on platform
        if os.name == "nt":  # Windows
            return [Path(os.environ.get("APPDATA", "")) / "Hex-Rays" / "IDA Pro"]
        else:  # Linux/Mac
            return [Path(os.path.expanduser("~")) / ".idapro"]

    # Split by platform separator
    separator = ";" if os.name == "nt" else ":"

    paths = []
    for path_str in idausr_env.split(separator):
        path = Path(path_str.strip())
        if path.exists():
            paths.append(path)

    return paths if paths else [Path(idausr_env.split(separator)[0])]
```

#### 2. Modified `get_plugin_directory()` method

**New behavior**: Follow IDA's loading order with `prefer_user` parameter

```python
def get_plugin_directory(self, ida_path: Path, prefer_user: bool = True) -> Path:
    """
    Get plugin directory for IDA installation.

    IDA loads plugins in this order:
    1. $IDAUSR/plugins (user plugins - priority)
    2. %IDADIR%/plugins (installation plugins)
    """
    # 1. Check IDAUSR directories (user plugins)
    if prefer_user:
        idausr_dirs = self.get_idausr_directories()
        for idausr_dir in idausr_dirs:
            user_plugin_dir = idausr_dir / "plugins"
            if user_plugin_dir.exists():
                logger.info(f"Using IDAUSR plugins directory: {user_plugin_dir}")
                return user_plugin_dir

    # 2. Fallback to installation directory
    plugin_dir = ida_path / "plugins"
    if plugin_dir.exists():
        logger.info(f"Using IDADIR plugins directory: {plugin_dir}")
        return plugin_dir

    # 3. Create IDAUSR plugins dir as last resort
    if prefer_user:
        idausr_dirs = self.get_idausr_directories()
        if idausr_dirs:
            user_plugin_dir = idausr_dirs[0] / "plugins"
            user_plugin_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created IDAUSR plugins directory: {user_plugin_dir}")
            return user_plugin_dir

    return plugin_dir
```

#### 3. Added `get_all_plugin_directories()` method

**Purpose**: Return ALL plugin directories in IDA's loading order

```python
def get_all_plugin_directories(self, ida_path: Path) -> List[Path]:
    """
    Get all plugin directories where IDA will look for plugins.

    Returns directories in IDA's loading order:
    1. All $IDAUSR/plugins directories (user plugins)
    2. %IDADIR%/plugins (installation plugins)
    """
    plugin_dirs = []

    # Add all IDAUSR/plugins directories
    idausr_dirs = self.get_idausr_directories()
    for idausr_dir in idausr_dirs:
        user_plugin_dir = idausr_dir / "plugins"
        if user_plugin_dir.exists():
            plugin_dirs.append(user_plugin_dir)

    # Add installation directory
    plugin_dir = ida_path / "plugins"
    if plugin_dir.exists():
        plugin_dirs.append(plugin_dir)

    return plugin_dirs
```

### Files Modified
- [src/core/ida_detector.py](src/core/ida_detector.py) - Added 3 new methods (lines 128-234)
- [src/ui/dialogs/settings_dialog.py](src/ui/dialogs/settings_dialog.py) - Added IDAUSR display section in IDA tab
- [src/ui/dialogs/install_url_dialog.py](src/ui/dialogs/install_url_dialog.py) - Fixed bug: was calling non-existent `install_plugin_from_github()` method

### Benefits
- ✅ **Follows IDA's official loading order** (IDAUSR/plugins → IDADIR/plugins)
- ✅ **Supports multiple paths** in IDAUSR with platform-specific separators
- ✅ **No admin permissions required** for IDAUSR/plugins installation
- ✅ **Plugins shared across IDA installations** - same plugins work for IDA 9.0, 9.1, etc.
- ✅ **Plugins in IDAUSR override IDADIR** - allows customizing built-in plugins
- ✅ **Cross-platform support** - Windows, Linux, Mac with correct separators
- ✅ **Graceful fallback** - Creates IDAUSR/plugins if it doesn't exist

### Usage Example
```python
# User sets environment variable
# Windows: set IDAUSR=C:\my_idausr;D:\shared_plugins
# Linux/Mac: export IDAUSR=/home/user/my_idausr:/opt/shared_plugins

detector = IDADetector()

# Get all IDAUSR directories
idausr_dirs = detector.get_idausr_directories()
# Returns: [Path("C:\\my_idausr"), Path("D:\\shared_plugins")]

# Get plugin directory (prioritizes IDAUSR)
plugin_dir = detector.get_plugin_directory(ida_path, prefer_user=True)
# Returns: C:\my_idausr\plugins (if exists)
# Or: C:\Program Files\IDA Pro 9.0\plugins (fallback)

# Get all plugin directories for scanning
all_dirs = detector.get_all_plugin_directories(ida_path)
# Returns: [C:\my_idausr\plugins, D:\shared_plugins\plugins, C:\Program Files\IDA Pro 9.0\plugins]
```

### Additional Bug Fix
During implementation, discovered and fixed bug in InstallURLDialog:
- **Bug**: Was calling non-existent `install_plugin_from_github()` method
- **Fix**: Changed to call correct `install_plugin(repo_url, method="clone", branch="main")` method

---