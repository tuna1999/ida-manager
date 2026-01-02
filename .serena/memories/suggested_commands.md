# IDA Plugin Manager - Development Commands

## Running the Application

```bash
# Primary method (with uv - recommended)
uv run python -m src.main

# Alternative method
python -m src.main

# Direct module execution
python src/main.py
```

## Testing

```bash
# Run all tests
uv run pytest

# Run single test file
uv run pytest tests/test_database.py

# Run with coverage report
uv run pytest --cov=src --cov-report=html

# Run with verbose output
uv run pytest -v

# Run specific test
uv run pytest tests/test_database.py::TestDatabaseManager::test_add_plugin
```

## Code Quality

### Formatting
```bash
# Format code with Black
uv run black src/

# Format specific file
uv run black src/core/plugin_manager.py

# Check formatting without making changes
uv run black --check src/
```

### Linting
```bash
# Run Ruff linter
uv run ruff check src/

# Auto-fix issues
uv run ruff check --fix src/

# Check specific file
uv run ruff check src/core/plugin_manager.py
```

### Type Checking
```bash
# Run mypy type checker
uv run mypy src/

# Check specific module
uv run mypy src/core/plugin_manager.py

# Show error codes
uv run mypy --show-error-codes src/
```

## Dependency Management

```bash
# Install dependencies with uv (recommended)
uv sync

# Add a new dependency
uv add <package-name>

# Add dev dependency
uv add --dev <package-name>

# Update dependencies
uv sync --upgrade

# Using pip instead of uv
pip install -e .
```

## Windows System Commands

Since this is a Windows project, these are commonly used commands:

```powershell
# List files
dir
ls

# Change directory
cd <path>

# Show current directory
pwd
cd

# Create directory
mkdir <name>

# Remove file/directory
rm <file>
rm -r <directory>

# Copy file
copy <source> <dest>

# Move file
move <source> <dest>

# Find in files (PowerShell)
Select-String -Path <path> -Pattern <pattern>

# Grep alternative (if Git installed or via WSL)
grep -r "pattern" src/

# Environment variables
echo $env:APPDATA
echo $env:PATH

# Check if process is running
Get-Process python

# Kill process
Stop-Process -Name python

# Open file with default app
start <file>

# Open URL in browser
start https://github.com
```

## Git Commands

```bash
# View status
git status

# Add files
git add .
git add <file>

# Commit
git commit -m "feat: add plugin installer"

# Push
git push

# Pull
git pull

# View log
git log --oneline
git log --graph --oneline --all

# Create branch
git checkout -b feature/plugin-installer

# Switch branch
git checkout main
git switch feature/plugin-installer

# View diff
git diff
git diff <file>

# Stash changes
git stash
git stash pop
```

## Configuration File Location

```powershell
# Open config directory in Explorer
start $env:APPDATA\IDA-Plugin-Manager

# View config file
cat $env:APPDATA\IDA-Plugin-Manager\config.json

# Edit config file
notepad $env:APPDATA\IDA-Plugin-Manager\config.json
```

## IDA Pro Plugin Directory

```powershell
# Typical IDA Pro installation paths
dir "C:\Program Files\IDA Pro 9.0\plugins"
dir "C:\Program Files (x86)\IDA Pro 8.4\plugins"

# User plugin directory
dir "$env:APPDATA\IDA Pro\plugins"
```

## Database Operations

```bash
# View database location (SQLite)
# Database is stored at: %APPDATA%\IDA-Plugin-Manager\plugins.db

# Open database with SQLite CLI (if installed)
sqlite "$env:APPDATA\IDA-Plugin-Manager\plugins.db"

# Or use Python to query
uv run python -c "import sqlite3; conn = sqlite3.connect(r'%APPDATA%\IDA-Plugin-Manager\plugins.db'); cursor = conn.cursor(); cursor.execute('SELECT * FROM plugins'); print(cursor.fetchall())"
```

## Development Workflow

```bash
# 1. Start development session
uv sync

# 2. Make code changes
# Edit files...

# 3. Format and lint
uv run black src/
uv run ruff check --fix src/

# 4. Run tests
uv run pytest

# 5. Type check
uv run mypy src/

# 6. Run application to test
uv run python -m src.main

# 7. Test dialogs multiple times (verify no tag conflicts)
# - Settings dialog: open/close multiple times
# - About dialog: open/close multiple times
# - Plugin Details: open/close multiple times
# - File dialog: test browse button

# 8. Commit when done
git add .
git commit -m "feat: description"
```

## GUI Testing Checklist

After any UI changes, manually test:
- [ ] Application launches without errors
- [ ] Settings dialog opens/closes multiple times without errors
- [ ] About dialog opens/closes multiple times without errors
- [ ] Plugin Details dialog opens/closes multiple times without errors
- [ ] File dialog (Settings → Browse) works correctly
- [ ] Theme switching (Dark/Light) works
- [ ] Filter panel updates correctly
- [ ] Progress dialogs show during operations
- [ ] Check updates displays results correctly

## Quick Reference

| Task | Command |
|------|---------|
| Run app | `uv run python -m src.main` |
| Run tests | `uv run pytest` |
| Format code | `uv run black src/` |
| Lint code | `uv run ruff check src/` |
| Type check | `uv run mypy src/` |
| Install deps | `uv sync` |
| View config | `cat $env:APPDATA\IDA-Plugin-Manager\config.json` |
| Git status | `git status` |
