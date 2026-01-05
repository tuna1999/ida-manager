# IDA Pro Plugin Manager

A standalone Windows application for managing IDA Pro plugins. Supports both legacy (IDA < 9.0) and modern (IDA >= 9.0) plugin formats.

> **📊 Project Quality:** 7.4/10 ⭐⭐⭐⭐ | [View Full Evaluation](EVALUATION-SUMMARY.md) | [Vietnamese Report](DANH-GIA-DU-AN.md)

## Features

- **Plugin Discovery**: Search and discover IDA Pro plugins from GitHub
- **Installation Methods**: Install via git clone or download releases
- **Version Management**: Track installed versions and check for updates
- **Compatibility**: Validates plugin compatibility with your IDA Pro version
- **Modern & Legacy**: Supports both legacy Python plugins and modern plugins with `plugins.json`
- **Native Windows UI**: Built with Dear PyGui for a native feel

## Requirements

- Python 3.10+
- Windows 10 or later
- IDA Pro (for plugin installation)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/IDA-plugins-manager.git
cd IDA-plugins-manager
```

2. Install dependencies using uv:
```bash
uv sync
```

Or with pip:
```bash
pip install -e .
```

## Usage

Run the application:
```bash
python -m src.main
```

Or using uv:
```bash
uv run python -m src.main
```

## Project Structure

```
IDA-plugins-manager/
├── src/
│   ├── main.py                  # Application entry point
│   ├── config/                  # Configuration management
│   ├── core/                    # Core business logic
│   │   ├── ida_detector.py      # IDA Pro detection
│   │   ├── installer.py         # Plugin installation
│   │   ├── plugin_manager.py    # Main orchestration
│   │   └── version_manager.py   # Version handling
│   ├── database/                # SQLite database layer
│   ├── github/                  # GitHub API integration
│   ├── ui/                      # Dear PyGui interface
│   ├── utils/                   # Utilities
│   └── models/                  # Pydantic data models
├── tests/
├── resources/
└── pyproject.toml
```

## Configuration

Configuration is stored in `%APPDATA%\IDA-Plugin-Manager\config.json`:

```json
{
  "ida": {
    "install_path": "C:/Program Files/IDA Pro 9.0",
    "version": "9.0",
    "auto_detect": true
  },
  "github": {
    "token": "",
    "api_base": "https://api.github.com"
  },
  "updates": {
    "auto_check": true,
    "check_interval_hours": 24
  },
  "ui": {
    "theme": "Dark"
  }
}
```

## Development

### Running Tests

```bash
uv run pytest
```

### Code Formatting

```bash
uv run black src/
uv run ruff check src/
```

### Type Checking

```bash
uv run mypy src/
```

## License

MIT License

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
