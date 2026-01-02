# IDA Pro Plugin Manager - Documentation

Welcome to the official documentation for IDA Pro Plugin Manager.

## Quick Links

- [README (Root)](../README.md) - Project overview and getting started
- [CLAUDE.md](../CLAUDE.md) - Developer guidance for Claude Code
- [Architecture Documentation](./architecture/) - System design and architecture
- [Architecture Decision Records](./adr/) - Historical design decisions

---

## Documentation Structure

```
docs/
├── README.md                   # This file
├── architecture/               # Architecture documentation
│   ├── 00-overview.md         # System overview and principles
│   ├── 01-c4-model.md         # C4 model diagrams
│   ├── 02-data-model.md       # Database schema and models
│   ├── 03-api-design.md       # API contracts (TODO)
│   ├── 04-sequence-flows.md   # Sequence diagrams (TODO)
│   └── 05-deployment.md       # Deployment architecture (TODO)
├── adr/                        # Architecture Decision Records
│   ├── 000-use-sqlite.md      # Database technology choice
│   ├── 001-layered-architecture.md  # Layered architecture design
│   ├── 002-result-objects.md  # Error handling strategy
│   └── 003-pydantic-for-validation.md  # Validation approach
└── diagrams/                   # Source diagrams
    ├── c4-system-context.puml # PlantUML C4 diagrams
    ├── c4-containers.puml
    ├── c4-components.puml
    └── er-diagram.puml
```

---

## Getting Started

### For Users

If you just want to use the application:

1. **Installation**: See [README - Installation](../README.md#installation)
2. **Configuration**: See [README - Configuration](../README.md#configuration)
3. **Usage**: See [README - Usage](../README.md#usage)

### For Developers

If you want to contribute or understand the codebase:

1. **Start with**: [Architecture Overview](./architecture/00-overview.md)
2. **Understand**: [C4 Model](./architecture/01-c4-model.md)
3. **Learn**: [Data Model](./architecture/02-data-model.md)
4. **Review**: [Architecture Decision Records](./adr/)

---

## Architecture Overview

IDA Pro Plugin Manager follows a **layered architecture** with clear separation of concerns:

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

### Key Technologies

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **UI** | Dear PyGui | Native Windows GUI |
| **Core** | Python | Business logic orchestration |
| **GitHub** | requests + GitPython | GitHub API integration |
| **Database** | SQLite + SQLAlchemy 2.0 | Data persistence |
| **Models** | Pydantic 2.0 | Data validation |

---

## Architecture Decision Records (ADRs)

ADRs document significant architectural decisions and their rationale:

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [000](./adr/000-use-sqlite.md) | Use SQLite for Data Persistence | Accepted | 2026-01-02 |
| [001](./adr/001-layered-architecture.md) | Layered Architecture Design | Accepted | 2026-01-02 |
| [002](./adr/002-result-objects.md) | Result Objects Instead of Exceptions | Accepted | 2026-01-02 |
| [003](./adr/003-pydantic-for-validation.md) | Pydantic for Data Validation | Accepted | 2026-01-02 |

---

## Data Model Overview

### Database Schema

- **plugins** - Plugin metadata and installation status
- **github_repos** - Cached GitHub repository information
- **installation_history** - Track all plugin operations
- **settings** - Application configuration storage

### Pydantic Models

- **Plugin** - Main plugin data structure
- **GitHubRepo** - GitHub repository information
- **ValidationResult** - Plugin validation results
- **InstallationResult** - Installation operation results
- **UpdateInfo** - Update availability information

See [Data Model Documentation](./architecture/02-data-model.md) for details.

---

## Component Overview

### Core Layer

- **PluginManager** - Central orchestrator for all plugin operations
- **IDADetector** - Discovers IDA Pro installations on Windows
- **PluginInstaller** - Executes plugin installation/uninstallation
- **VersionManager** - Handles version parsing and compatibility

### GitHub Layer

- **GitHubClient** - GitHub API communication
- **RepoParser** - Extracts plugin metadata from repositories
- **ReleaseFetcher** - Selects appropriate releases for installation

### Database Layer

- **DatabaseManager** - CRUD operations for all entities
- **MigrationManager** - Database schema migrations

### UI Layer

- **MainWindow** - Main application window
- **PluginBrowser** - Plugin list view
- **StatusPanel** - Status message display

See [C4 Model](./architecture/01-c4-model.md) for component details.

---

## Development Guidelines

### Code Quality Standards

```bash
# Format code
uv run black src/

# Lint code
uv run ruff check src/

# Type checking
uv run mypy src/

# Run tests
uv run pytest
```

### Testing Strategy

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test interactions between layers
- **End-to-End Tests**: Test complete workflows

### Contributing Guidelines

1. Follow layered architecture principles
2. Write tests for all new functionality
3. Document public APIs with docstrings
4. Use Pydantic models for data validation
5. Return result objects, not exceptions

---

## Current Implementation Status

| Layer | Status | Test Coverage |
|-------|--------|---------------|
| **Config** | ✅ Complete | 28/28 tests passing |
| **Models** | ✅ Complete | Part of Config tests |
| **Database** | ✅ Complete | 28/28 tests passing |
| **GitHub** | ⏳ Skeleton | 0 tests |
| **Core** | ⏳ Skeleton | 0 tests |
| **UI** | ⏳ Skeleton | 0 tests |

See [todos.md](../todos.md) for detailed task list.

---

## Support

### Documentation Issues

If you find errors or omissions in the documentation:

1. Check the [GitHub Issues](https://github.com/yourusername/IDA-plugins-manager/issues)
2. Create a new issue with the `documentation` label
3. Describe the problem clearly
4. Suggest improvements if possible

### Code Issues

For code-related questions or bugs:

1. Check [CLAUDE.md](../CLAUDE.md) for development guidance
2. Review architecture documentation
3. Check existing GitHub issues
4. Create a new issue with appropriate labels

---

## License

This documentation is part of IDA Pro Plugin Manager and is licensed under the MIT License.

See [LICENSE](../LICENSE) for details.

---

## Document Metadata

- **Project**: IDA Pro Plugin Manager
- **Version**: 1.0.0
- **Last Updated**: 2026-01-02
- **Maintainer**: IDA Plugin Manager Team

---

**Quick Navigation:**

- [← Back to Project Root](../)
- [Architecture Overview](./architecture/00-overview.md)
- [C4 Model](./architecture/01-c4-model.md)
- [Data Model](./architecture/02-data-model.md)
- [ADRs](./adr/)
