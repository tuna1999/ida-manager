# IDA Pro Plugin Manager - Architecture Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Principles](#architecture-principles)
3. [Technology Stack](#technology-stack)
4. [Architecture Patterns](#architecture-patterns)
5. [Documentation Structure](#documentation-structure)

---

## System Overview

### Purpose

IDA Pro Plugin Manager is a standalone Windows desktop application designed to simplify the discovery, installation, and management of IDA Pro plugins. It bridges the gap between the IDA Pro disassembler ecosystem and the vibrant community of plugin developers hosting their work on GitHub.

### Key Capabilities

- **Plugin Discovery**: Search and browse IDA Pro plugins from GitHub repositories
- **Intelligent Installation**: Support for both git clone (development) and release download (stable) installation methods
- **Version Management**: Track installed versions, check for updates, and manage plugin lifecycle
- **Compatibility Validation**: Ensure plugins work with your IDA Pro version (supports both legacy <9.0 and modern ≥9.0 formats)
- **Native Windows Experience**: Built with Dear PyGui for seamless desktop integration

### Target Users

- **Reverse Engineers**: Who need specialized plugins for their analysis workflows
- **Malware Analysts**: Who require automation and custom analysis tools
- **Security Researchers**: Who develop and share IDA Pro extensions
- **IDA Pro Power Users**: Who want to extend and customize their IDA Pro installation

---

## Architecture Principles

### 1. Layered Architecture

The application follows a strict layered architecture with clear separation of concerns:

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

**Benefits:**
- Clear dependency direction (top-down)
- Easy to test each layer in isolation
- Simple to swap implementations (e.g., change UI framework)
- Facilitates parallel development

### 2. Dependency Inversion

High-level modules don't depend on low-level modules. Both depend on abstractions:

- Core layer depends on Pydantic models, not concrete database implementations
- UI layer depends on PluginManager interface, not internal details
- GitHub integration returns Pydantic models, not SQLAlchemy objects

### 3. Single Responsibility

Each component has one clear purpose:

- `PluginManager`: Orchestrate plugin operations
- `IDADetector`: Find IDA Pro installations
- `GitHubClient`: Handle GitHub API communication
- `DatabaseManager`: Persist and retrieve data

### 4. Testability First

All layers are designed for easy testing:

- Pure functions with no side effects where possible
- Dependency injection for testability
- Result objects instead of exceptions for flow control
- Comprehensive test coverage for all critical paths

### 5. Type Safety

Strong typing throughout the codebase:

- Pydantic models for data validation
- SQLAlchemy 2.0 with Mapped[] types
- Full type hints on all public APIs
- mypy static type checking

---

## Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Language** | Python | 3.10+ | Core application logic |
| **UI Framework** | Dear PyGui | 1.1.0+ | Native Windows GUI |
| **Database** | SQLite | 3.x | Local data persistence |
| **ORM** | SQLAlchemy | 2.0+ | Database abstraction |
| **Validation** | Pydantic | 2.0+ | Data validation & serialization |
| **HTTP Client** | requests | 2.31+ | GitHub API calls |
| **Git Operations** | GitPython | 3.1+ | Plugin installation via git |
| **Version Parsing** | packaging | 23.0+ | Semantic version comparison |

### Development Tools

| Tool | Purpose |
|------|---------|
| **uv** | Fast Python package manager |
| **pytest** | Testing framework |
| **pytest-cov** | Code coverage reporting |
| **black** | Code formatting |
| **ruff** | Fast Python linter |
| **mypy** | Static type checking |

---

## Architecture Patterns

### 1. Repository Pattern

**DatabaseManager** implements the Repository pattern:

```python
# Abstract database operations behind a clean interface
db_manager = DatabaseManager()
db_manager.add_plugin(plugin)
db_manager.get_plugin(plugin_id)
db_manager.update_plugin(plugin)
db_manager.delete_plugin(plugin_id)
```

**Benefits:**
- Hides SQL complexity from business logic
- Easy to mock for testing
- Centralized query logic
- Caching opportunities

### 2. Result Object Pattern

Operations return result objects instead of raising exceptions:

```python
result: InstallationResult = plugin_manager.install(plugin_id)
if result.success:
    logger.info(f"Installed {result.new_version}")
else:
    logger.error(f"Failed: {result.error}")
```

**Benefits:**
- Explicit error handling
- No hidden control flow
- Easier to test error paths
- Better error messages

### 3. Factory Pattern

**SessionFactory** creates database sessions:

```python
class DatabaseManager:
    def __init__(self):
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)

    def get_session(self) -> Session:
        return self.Session()
```

**Benefits:**
- Centralized session configuration
- Consistent session behavior
- Easy to add connection pooling

### 4. Observer Pattern

UI updates based on plugin state changes:

```python
# PluginManager emits events
# StatusPanel observes and displays messages
```

**Benefits:**
- Decoupled UI from business logic
- Multiple observers possible
- Easy to add logging/monitoring

### 5. Strategy Pattern

Multiple installation strategies:

```python
if method == "git":
    install_via_git_clone(repo_url, install_path)
elif method == "release":
    download_and_extract_release(asset_url, install_path)
```

**Benefits:**
- Encapsulates installation algorithms
- Easy to add new methods
- Testable strategies

---

## Documentation Structure

### Architecture Documents

```
docs/
├── architecture/
│   ├── 00-overview.md           # This file
│   ├── 01-c4-model.md           # C4 diagrams (System, Container, Component)
│   ├── 02-data-model.md         # Database schema and relationships
│   ├── 03-api-design.md         # Internal API contracts
│   ├── 04-sequence-flows.md     # Key sequence diagrams
│   └── 05-deployment.md         # Deployment architecture
```

### Architecture Decision Records (ADRs)

```
docs/
├── adr/
│   ├── 000-use-sqlite.md
│   ├── 001-layered-architecture.md
│   ├── 002-dearpygui-over-web.md
│   ├── 003-pydantic-for-validation.md
│   └── 004-result-objects.md
```

### Diagrams

```
docs/
├── diagrams/
│   ├── c4-system-context.puml    # System context diagram
│   ├── c4-containers.puml         # Container diagram
│   ├── c4-components.puml         # Component diagram
│   ├── er-diagram.puml            # Entity relationship diagram
│   └── sequence-flows.puml        # Key sequence diagrams
```

---

## Related Documentation

- [README.md](../../README.md) - Project overview and getting started
- [CLAUDE.md](../../CLAUDE.md) - Developer guidance for Claude Code
- [tests/](../../tests/) - Test specifications and examples
- [src/](../../src/) - Source code with inline documentation

---

## Document Metadata

- **Version**: 1.0.0
- **Last Updated**: 2026-01-02
- **Author**: IDA Plugin Manager Team
- **Status**: Active
- **Review Cycle**: Quarterly
