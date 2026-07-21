# World Builder — Progress

This file is the durable execution log for the project. Update it at the end of every implementation feature or substantial maintenance session. It should describe completed outcomes and verification, not intentions; planned work belongs in `Roadmap.md`, while deferred work belongs in `Backlog.md`.

## Current status

- **Current roadmap feature:** F-02 — Universe workspace and isolation foundation
- **Feature status:** Not started
- **Last completed feature:** F-01 — Database foundation and migration workflow
- **Last updated:** 2026-07-21

## Completed work

### 2026-07-21 — F-01: Database foundation and migration workflow

**Status:** Complete

**Implemented:**

- Added SQLAlchemy engine and session helpers with SQLite foreign-key enforcement and busy timeout.
- Added initial mappings for universes, global lookup categories, and universe-scoped lookup values.
- Configured Alembic and created the first migration at revision `20260721_0001`.
- Added explicit schema states for missing, unversioned, outdated, current, and ahead databases.
- Added `world-builder schema-status` and `world-builder migrate` maintenance commands.
- Added consistent timestamped SQLite backups before upgrading an existing database.
- Prevented redundant backups when the database is already current.
- Added a Streamlit startup warning with the exact migration command when the schema is not ready.
- Documented database initialization and migration commands.

**Files or migrations:**

- `alembic.ini` and `alembic/` migration environment
- `alembic/versions/20260721_0001_initial_foundation.py`
- `src/world_builder/persistence/database.py`
- `src/world_builder/persistence/models.py`
- `src/world_builder/persistence/migrations.py`
- `src/world_builder/cli.py`
- Persistence and migration tests under `tests/persistence/`

**Verification:**

- `uv run ruff check .` passed.
- `uv run ruff format --check .` passed for 23 Python files.
- `uv run mypy` passed for 21 source files.
- `uv run pytest` passed all 11 tests.
- CLI smoke test reported a missing schema, migrated to `20260721_0001`, and then reported the schema as current.
- Headless Streamlit smoke test started against the migrated temporary database and stopped cleanly.
- Existing unversioned-database tests verified backup contents before migration.

**Decisions or deviations:**

- Lookup category definitions are global application concepts; lookup values are owned and managed independently by each universe.
- The migration command is idempotent and does not back up or rewrite a current database.
- Validation exposed an iCloud-hidden `.pth` import failure. The environment was immediately rebuilt with the prescribed `rm -rf .venv && uv cache clean && uv sync --all-packages` command, which restored installed entry-point imports.
- Corrected an Alembic transaction boundary that initially allowed SQLite DDL but rolled back the revision stamp; regression coverage now verifies the final revision.

**Backlog created:**

- None.

### 2026-07-21 — F-00: Project scaffold and quality baseline

**Status:** Complete

**Implemented:**

- Initialized a Python 3.12+ package managed by `uv` with a cross-platform lockfile.
- Added the Streamlit application entry point, multipage navigation shell, and health page.
- Established domain, persistence, storage, visualization, and page package boundaries.
- Added immutable Pydantic settings with repository-local and environment-configurable data paths.
- Added Ruff, mypy, and pytest configuration with strict type checking.
- Added settings tests and macOS/Windows installation, launch, and quality-check documentation.
- Ignored personal data, virtual environments, caches, and generated Python files.
- Added a root `justfile` as the stable command interface for setup, startup, migration, quality checks, and environment recovery.

**Files or migrations:**

- `pyproject.toml`, `uv.lock`, `.python-version`, and `.gitignore`
- `src/world_builder/` application package
- `tests/test_settings.py`
- `README.md`
- `justfile`
- No database migration was required for this scaffold feature.

**Verification:**

- `uv sync` completed using CPython 3.12.12.
- `uv run ruff check .` passed.
- `uv run ruff format --check .` passed for 13 Python files.
- `uv run mypy` passed for 13 source files.
- `uv run pytest` passed all 3 tests.
- Headless Streamlit smoke test started successfully on a local port and stopped cleanly.

**Decisions or deviations:**

- Supported Python is constrained to 3.12 and 3.13 for a predictable macOS/Windows baseline.
- Canonical data paths are resolved centrally and are not stored in Streamlit session state.
- Documented the required full environment rebuild command for import failures caused by iCloud hiding `.pth` files. The rebuild is only run when that failure signature occurs.
- Routine project commands are invoked through `just`; underlying `uv` commands remain encapsulated in recipes.

**Backlog created:**

- None.

### 2026-07-21 — Product and architecture definition

- Defined the character-first product model.
- Established strict separation between universes.
- Defined unassigned, active, and disabled character states.
- Defined cross-universe character movement as a destructive detachment of all non-artwork links while preserving character-owned artwork.
- Defined chapters as manually sequenced event groupings and stories as the substantive Markdown literature entries.
- Defined artwork ownership, association behavior, and GUID-only filesystem storage.
- Defined symmetric and directional character relationships.
- Simplified group membership to a current association with an optional description.
- Simplified milestones to linked planning ideas rather than canonical events.
- Chose a local Streamlit and Python architecture managed with `uv`.
- Chose SQLite, SQLAlchemy, and Alembic for persistence and migrations.
- Chose filesystem storage for original artwork.
- Defined the current-state character/group graph explorer.
- Created the technical implementation roadmap and project tracking documents.

## Verification history

No application code exists yet. Documentation was reviewed against the agreed product decisions.

## Feature log template

Copy this section when completing work:

```markdown
### YYYY-MM-DD — F-XX: Feature name

**Status:** Complete | Partial | Blocked

**Implemented:**

- Outcome delivered

**Files or migrations:**

- Important file or migration

**Verification:**

- Command and result

**Decisions or deviations:**

- Any implementation decision that changes or clarifies the roadmap

**Backlog created:**

- BL-XXX, or None
```
