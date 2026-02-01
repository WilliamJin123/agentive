# Phase 13: Persistence & Plugins - Research

**Researched:** 2026-02-01
**Domain:** Session persistence, checkpointing, export/import, plugin architecture
**Confidence:** HIGH

## Summary

This phase implements four related subsystems: session persistence (saving/resuming conversations), checkpointing (state snapshots for rewind), export/import (markdown/JSON), and a plugin system (extensibility). The research confirms SQLAlchemy 2.x with AsyncSession and SQLite (via aiosqlite) as the standard approach for persistence, matching the project's existing async patterns. For plugins, the Python ecosystem offers two strong options: pluggy (used by pytest) and stevedore (used by OpenStack). Given HFS's simpler requirements (directory-based discovery, lifecycle hooks), a lightweight custom approach following pluggy patterns is recommended.

The existing codebase provides strong foundations: Pydantic models for state (`RunSnapshot`, `HFSEvent`), an EventBus for lifecycle events, and a user_config module with YAML patterns. The checkpoint system can leverage the existing `StateManager._event_history` and build on Pydantic's `model_dump(mode='json')` for serialization. Export formats align with existing patterns - the state models already serialize cleanly to JSON.

**Primary recommendation:** Use SQLAlchemy 2.x with AsyncSession + SQLite for sessions/checkpoints, implement directory-based plugin discovery with pluggy-style hooks for extensibility.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.1.x | ORM and database abstraction | Official Python ORM, mature async support, well-documented |
| aiosqlite | 0.20.x | Async SQLite driver | Required for SQLAlchemy async + SQLite, bridges sync SQLite to asyncio |
| Pydantic | 2.x | Data validation & serialization | Already in project, `model_dump(mode='json')` for export |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| greenlet | 3.x | Async bridge (auto-installed) | Required by SQLAlchemy[asyncio] |
| importlib.metadata | stdlib | Plugin entry point discovery | If plugins need installable package support |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQLAlchemy + SQLite | JSON files | Simpler but no querying, no transactions, file locking issues |
| SQLAlchemy + SQLite | TinyDB | Document-oriented but less standard, limited async |
| Custom plugins | pluggy | More features but heavier; custom fits HFS's simple needs |
| Custom plugins | stevedore | Entry-point focused; overkill for directory discovery |

**Installation:**
```bash
pip install "sqlalchemy[asyncio]" aiosqlite
```

## Architecture Patterns

### Recommended Project Structure
```
hfs/
  persistence/
    __init__.py
    engine.py         # AsyncEngine creation, db path config
    models.py         # SQLAlchemy ORM models (Session, Checkpoint, Message)
    repository.py     # CRUD operations (SessionRepository, CheckpointRepository)
  export/
    __init__.py
    markdown.py       # Conversation -> markdown export
    json_export.py    # Conversation -> JSON export
    json_import.py    # JSON -> conversation import
    migration.py      # Schema version detection and upgrade
  plugins/
    __init__.py
    discovery.py      # Scan ~/.hfs/plugins/, load manifests
    hooks.py          # Hookspec definitions (on_start, on_message, etc.)
    manager.py        # PluginManager for registration and calling
    permissions.py    # Permission prompts and tracking
```

### Pattern 1: AsyncSession Factory
**What:** Create async session factory at app startup, use context managers for each operation
**When to use:** All database operations
**Example:**
```python
# Source: SQLAlchemy 2.1 docs
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Create once at startup
engine = create_async_engine(
    "sqlite+aiosqlite:///~/.hfs/sessions.db",
    echo=False,
)
async_session = async_sessionmaker(engine, expire_on_commit=False)

# Use per-operation
async def save_message(message: Message) -> None:
    async with async_session() as session:
        async with session.begin():
            session.add(message)
        # Auto-commits on successful exit
```

### Pattern 2: Repository Pattern
**What:** Encapsulate database operations in repository classes
**When to use:** All CRUD operations for sessions, checkpoints
**Example:**
```python
class SessionRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def create(self, name: str) -> Session:
        async with self._session_factory() as session:
            async with session.begin():
                db_session = SessionModel(name=name, created_at=datetime.utcnow())
                session.add(db_session)
                await session.flush()  # Get ID
                return db_session

    async def list_recent(self, limit: int = 20) -> list[Session]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(SessionModel)
                .order_by(SessionModel.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
```

### Pattern 3: Pluggy-Style Hook System
**What:** Define hookspecs, plugins implement hooks, manager calls them
**When to use:** Plugin lifecycle events
**Example:**
```python
# hooks.py - Define specs
from dataclasses import dataclass
from typing import Protocol, Callable

class HFSHookSpec(Protocol):
    """Hook specification that plugins can implement."""

    def on_start(self, session_id: str) -> None:
        """Called when HFS session starts."""
        ...

    def on_message(self, message: str, is_user: bool) -> str | None:
        """Called for each message. Can modify message or return None."""
        ...

    def on_run_complete(self, run_snapshot: RunSnapshot) -> None:
        """Called when an agent run completes."""
        ...

# Plugin implementation
class MyPlugin:
    def on_message(self, message: str, is_user: bool) -> str | None:
        if is_user and "fix" in message.lower():
            return f"[Enhanced] {message}"
        return None
```

### Pattern 4: Event-Driven Checkpointing
**What:** Subscribe to EventBus, create checkpoints on key events
**When to use:** Automatic checkpoint creation
**Example:**
```python
class CheckpointService:
    def __init__(self, event_bus: EventBus, checkpoint_repo: CheckpointRepository):
        self._event_bus = event_bus
        self._checkpoint_repo = checkpoint_repo
        self._checkpoint_events = {
            "run.ended",
            "negotiation.resolved",
            "phase.ended",
        }

    async def start(self) -> None:
        self._stream = await self._event_bus.subscribe("*")
        asyncio.create_task(self._process_events())

    async def _process_events(self) -> None:
        async for event in self._stream:
            if event.event_type in self._checkpoint_events:
                await self._create_checkpoint(event)
```

### Anti-Patterns to Avoid
- **Shared AsyncSession across tasks:** Each task must have its own session instance
- **Lazy loading in async context:** Use `selectinload()` or `expire_on_commit=False`
- **Blocking plugin hooks:** Plugin callbacks should be fast; long operations should be async
- **Storing credentials in session DB:** Keep API keys in env vars, not persisted state

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async SQLite | Custom threading | `aiosqlite` via SQLAlchemy | Thread-safety, connection pooling handled |
| JSON schema versioning | Custom version checks | Pydantic `model_json_schema()` + version field | Schema generation, validation built-in |
| Session management | Raw SQL strings | SQLAlchemy ORM | Type safety, migrations, relationships |
| YAML round-trip | `yaml.dump()` | `ruamel.yaml` (already in project) | Preserves comments, formatting |
| DB migrations | Manual ALTER TABLE | Alembic | Handles schema evolution, rollback |

**Key insight:** SQLAlchemy + Pydantic already handle 90% of persistence complexity. The project already uses Pydantic models that serialize to JSON via `model_dump(mode='json')` - leverage this for exports.

## Common Pitfalls

### Pitfall 1: AsyncSession Sharing Across Tasks
**What goes wrong:** Using same AsyncSession in multiple asyncio tasks causes race conditions
**Why it happens:** AsyncSession is not thread-safe; each concurrent task needs its own
**How to avoid:** Use `async_sessionmaker` factory, create new session per task
**Warning signs:** Random "object is already attached to session" errors

### Pitfall 2: SQLite Concurrent Write Blocking
**What goes wrong:** Multiple processes/threads writing to SQLite causes "database is locked"
**Why it happens:** SQLite allows multiple readers but only one writer
**How to avoid:** Use Write-Ahead Logging (WAL mode), keep transactions short
**Warning signs:** `sqlite3.OperationalError: database is locked`
```python
# Enable WAL mode on connection
async with engine.connect() as conn:
    await conn.execute(text("PRAGMA journal_mode=WAL"))
```

### Pitfall 3: Lazy Load in Async Context
**What goes wrong:** Accessing relationship attribute triggers blocking I/O
**Why it happens:** SQLAlchemy lazy loading is synchronous by default
**How to avoid:** Use `selectinload()` for eager loading, or `lazy="raise"` to catch issues
**Warning signs:** "greenlet_spawn has not been called" errors

### Pitfall 4: Plugin Import Errors Breaking App
**What goes wrong:** Bad plugin code crashes entire HFS application
**Why it happens:** Import errors propagate unless caught
**How to avoid:** Wrap plugin discovery in try/except, log errors, skip bad plugins
**Warning signs:** App won't start after adding new plugin

### Pitfall 5: Checkpoint Data Explosion
**What goes wrong:** Storing full state at every checkpoint exhausts disk
**Why it happens:** No retention policy, no deduplication
**How to avoid:** Limit checkpoint count (default 10), prune old checkpoints, store deltas
**Warning signs:** ~/.hfs/ directory grows unbounded

### Pitfall 6: Schema Migration Failures on Import
**What goes wrong:** Old JSON exports fail to import due to schema changes
**Why it happens:** No version field, no migration path
**How to avoid:** Include schema version in exports, write migration functions
**Warning signs:** ValidationError on import with old files

## Code Examples

Verified patterns from official sources:

### SQLAlchemy Async Model Definition
```python
# Source: SQLAlchemy 2.1 docs - AsyncAttrs pattern
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(AsyncAttrs, DeclarativeBase):
    pass

class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime]
    updated_at: Mapped[Optional[datetime]]

    messages: Mapped[list["MessageModel"]] = relationship(
        back_populates="session",
        lazy="selectin"  # Eager load to avoid async issues
    )
    checkpoints: Mapped[list["CheckpointModel"]] = relationship(
        back_populates="session",
        lazy="selectin"
    )

class MessageModel(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    role: Mapped[str] = mapped_column(String(50))  # user, assistant, system
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime]

    session: Mapped["SessionModel"] = relationship(back_populates="messages")

class CheckpointModel(Base):
    __tablename__ = "checkpoints"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    trigger_event: Mapped[str] = mapped_column(String(100))
    state_json: Mapped[str] = mapped_column(Text)  # RunSnapshot serialized
    created_at: Mapped[datetime]

    session: Mapped["SessionModel"] = relationship(back_populates="checkpoints")
```

### Async Engine Setup
```python
# Source: SQLAlchemy 2.1 docs
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

async def create_db_engine(db_path: Path | None = None):
    """Create async SQLite engine with proper configuration."""
    if db_path is None:
        db_path = Path.home() / ".hfs" / "sessions.db"

    db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=False,
    )

    # Enable WAL mode for better concurrency
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return engine
```

### Markdown Export
```python
# Pattern for full-trace markdown export
from datetime import datetime
from hfs.state.models import RunSnapshot

def export_to_markdown(
    messages: list[MessageModel],
    run_snapshot: RunSnapshot | None = None,
) -> str:
    """Export conversation to markdown with full trace."""
    lines = [
        f"# HFS Session Export",
        f"",
        f"**Exported:** {datetime.utcnow().isoformat()}",
        f"**Messages:** {len(messages)}",
    ]

    if run_snapshot:
        lines.extend([
            f"**Tokens:** {run_snapshot.usage.total_tokens}",
            f"**Duration:** {run_snapshot.timeline.total_duration_ms}ms",
            f"",
            f"## Agent Activity",
            f"",
        ])
        for triad in run_snapshot.agent_tree.triads:
            lines.append(f"### Triad: {triad.triad_id} ({triad.preset})")
            for agent in triad.agents:
                lines.append(f"- {agent.role}: {agent.status.value}")

    lines.extend([f"", f"## Conversation", f""])

    for msg in messages:
        role_label = "User" if msg.role == "user" else "Assistant"
        lines.append(f"### {role_label}")
        lines.append(f"")
        lines.append(msg.content)
        lines.append(f"")

    return "\n".join(lines)
```

### JSON Export with Schema Version
```python
# Pattern for versioned JSON export
import json
from datetime import datetime
from pydantic import BaseModel
from typing import Any

EXPORT_SCHEMA_VERSION = "1.0.0"

class ExportMetadata(BaseModel):
    schema_version: str = EXPORT_SCHEMA_VERSION
    exported_at: datetime
    hfs_version: str
    session_name: str

class SessionExport(BaseModel):
    metadata: ExportMetadata
    messages: list[dict[str, Any]]
    checkpoints: list[dict[str, Any]] | None = None
    run_snapshot: dict[str, Any] | None = None

def export_to_json(
    session: SessionModel,
    run_snapshot: RunSnapshot | None = None,
    include_checkpoints: bool = False,
) -> str:
    """Export session to JSON with schema version."""
    export = SessionExport(
        metadata=ExportMetadata(
            exported_at=datetime.utcnow(),
            hfs_version="0.1.0",
            session_name=session.name,
        ),
        messages=[
            {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
            for m in session.messages
        ],
        checkpoints=[
            {"trigger": c.trigger_event, "created_at": c.created_at.isoformat()}
            for c in session.checkpoints
        ] if include_checkpoints else None,
        run_snapshot=run_snapshot.model_dump(mode="json") if run_snapshot else None,
    )

    return export.model_dump_json(indent=2)
```

### Plugin Discovery from Directory
```python
# Pattern for ~/.hfs/plugins/ discovery
import importlib.util
import sys
from pathlib import Path
from typing import Any
import yaml

class PluginManifest(BaseModel):
    """Plugin manifest schema."""
    name: str
    version: str
    description: str | None = None
    entry_point: str = "__init__"  # Module to import
    capabilities: list[str] = []  # commands, widgets, hooks

def discover_plugins(plugins_dir: Path | None = None) -> list[tuple[PluginManifest, Any]]:
    """Discover and load plugins from directory."""
    if plugins_dir is None:
        plugins_dir = Path.home() / ".hfs" / "plugins"

    if not plugins_dir.exists():
        return []

    plugins = []

    for plugin_path in plugins_dir.iterdir():
        if not plugin_path.is_dir():
            continue

        manifest_path = plugin_path / "manifest.yaml"
        if not manifest_path.exists():
            continue

        try:
            # Load manifest
            with open(manifest_path) as f:
                manifest_data = yaml.safe_load(f)
            manifest = PluginManifest(**manifest_data)

            # Load plugin module
            entry_path = plugin_path / f"{manifest.entry_point}.py"
            if entry_path.exists():
                spec = importlib.util.spec_from_file_location(
                    f"hfs_plugin_{manifest.name}",
                    entry_path
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[spec.name] = module
                    spec.loader.exec_module(module)
                    plugins.append((manifest, module))
        except Exception as e:
            # Log but don't crash on bad plugins
            print(f"Failed to load plugin {plugin_path.name}: {e}")

    return plugins
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SQLAlchemy 1.x sync | SQLAlchemy 2.x AsyncSession | 2023 | Native async support, better typing |
| `declarative_base()` | `DeclarativeBase` class | SQLAlchemy 2.0 | Better IDE support, type hints |
| `__get_validators__` | `__get_pydantic_core_schema__` | Pydantic 2.0 | Performance, better JSON schema |
| `parse_obj_as()` | `TypeAdapter` | Pydantic 2.0 | Cleaner API for arbitrary types |
| pkg_resources entry_points | `importlib.metadata.entry_points()` | Python 3.10+ | Stdlib, faster |

**Deprecated/outdated:**
- SQLAlchemy `Query` class: Use `select()` statements instead
- Pydantic V1 `schema()` method: Use `model_json_schema()`
- `pkg_resources` for entry points: Use `importlib.metadata`

## Open Questions

Things that couldn't be fully resolved:

1. **Alembic for migrations?**
   - What we know: Alembic is the standard migration tool for SQLAlchemy
   - What's unclear: Whether schema changes will be frequent enough to need it
   - Recommendation: Start without Alembic, add if schema evolves significantly

2. **Checkpoint storage format**
   - What we know: Can store as JSON blob (RunSnapshot) or normalized tables
   - What's unclear: Performance tradeoffs for large states
   - Recommendation: JSON blob in `state_json` column - simpler, Pydantic handles serialization

3. **Plugin widget integration**
   - What we know: Plugins can define Textual widgets
   - What's unclear: Exact mount points in UI, how widgets declare where they go
   - Recommendation: Define specific extension points (sidebar, status bar, panel)

## Sources

### Primary (HIGH confidence)
- [SQLAlchemy 2.1 AsyncIO docs](https://docs.sqlalchemy.org/en/21/orm/extensions/asyncio.html) - AsyncSession patterns, engine creation, eager loading
- [SQLAlchemy Session Basics](https://docs.sqlalchemy.org/en/21/orm/session_basics.html) - Session lifecycle, context managers
- [Pydantic JSON Schema docs](https://docs.pydantic.dev/latest/concepts/json_schema/) - Schema generation, versioning

### Secondary (MEDIUM confidence)
- [Pluggy documentation](https://pluggy.readthedocs.io/en/stable/) - Hook system patterns (verified with pytest usage)
- [Python Packaging Guide - Plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/) - Discovery patterns
- [aiosqlite GitHub](https://github.com/omnilib/aiosqlite) - Async SQLite patterns

### Tertiary (LOW confidence)
- WebSearch results for plugin architectures - community patterns for directory-based discovery
- py-undo-stack patterns - checkpoint/rewind conceptual approach

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - SQLAlchemy 2.x and aiosqlite are well-documented official solutions
- Architecture: HIGH - Repository pattern and async session management from official docs
- Pitfalls: MEDIUM - Based on official docs + common patterns; some from experience
- Plugin system: MEDIUM - Pluggy patterns verified; custom implementation specifics are discretionary

**Research date:** 2026-02-01
**Valid until:** 2026-03-01 (30 days - stable technologies)
