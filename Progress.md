# World Builder — Progress

This file is the durable execution log for the project. Update it at the end of every implementation feature or substantial maintenance session. It should describe completed outcomes and verification, not intentions; planned work belongs in `Roadmap.md`, while deferred work belongs in `Backlog.md`.

## Current status

- **Current roadmap feature:** F-07 — Character groups and memberships
- **Feature status:** Not started
- **Last completed feature:** F-06 — Character assignment and cross-universe movement
- **Last updated:** 2026-07-22

## Completed work

### 2026-07-22 — F-06: Character assignment and cross-universe movement

**Status:** Complete

**Implemented:**

- Added assignment from Unassigned to any universe.
- Added confirmed movement of disabled characters between universes and back to Unassigned.
- Added automatic disabling of active assigned characters within the confirmed move transaction.
- Added a preflight report covering relationships, group memberships, story links, chapter links, and milestone links.
- Added explicit confirmation before a character leaves an existing universe.
- Moved every character-owned artwork file to its GUID-only destination while preserving metadata and primary designation.
- Staged destination artwork copies before database changes, removed them on transaction failure, and retained source files until the database commit completed.
- Added a character-profile location management panel with destination selection and user-facing validation.

**Files or migrations:**

- Character movement models, errors, service, repositories, storage operations, and page UI
- Character movement and artwork-copy tests
- No database migration was required because character and artwork universe ownership already existed.

**Verification:**

- `just ready` passed Ruff formatting and linting, strict mypy, and all 57 tests.
- Tests cover assignment, automatic disabling during a confirmed move, confirmed universe movement, return to Unassigned, artwork preservation, primary designation, database failure rollback, and filesystem failure rollback.
- Live Streamlit verification confirmed the location panel on port 8913.

**Decisions or deviations:**

- Disabled assigned characters may move back to Unassigned as well as directly to another universe.
- Preflight connection categories report zero until their corresponding schemas are introduced; those later features must connect their records to the existing detachment contract.
- A failure removing obsolete source copies after a committed move does not reverse the successful move; the destination remains authoritative and the UI reports the cleanup warning.

**Backlog created:**

- None.

### 2026-07-21 — F-05: Character creation, profiles, and unassigned pool

**Status:** Complete

**Implemented:**

- Added character records with nullable universe ownership, Markdown summary, and active/disabled state.
- Added a partial unique database index that prevents more than one primary artwork per character.
- Added atomic character creation requiring name, summary, artwork title, artwork description, and a validated initial image.
- Added filesystem rollback when character creation or artwork metadata persistence fails.
- Added separate universe and unassigned character lists with active, disabled, and all filters.
- Added character profiles with Markdown summary, primary image, status, artwork gallery, and missing-file reporting.
- Added character editing, disable/re-enable operations, additional artwork uploads, and primary-artwork switching.
- Exposed no character deletion operation and blocked universe reassignment through generic character editing.
- Marked required character and artwork form fields with asterisks and replaced raw validation messages with field-specific user wording.
- Replaced the character list tables with page-specific sidebar status and profile controls.
- Standardized profile and gallery previews as square crops while retaining original image bytes for fullscreen viewing.

**Files or migrations:**

- `alembic/versions/20260721_0003_characters.py`
- `src/world_builder/domain/services/characters.py`
- `src/world_builder/persistence/repositories/characters.py`
- `src/world_builder/pages/characters.py`
- Character domain models and persistence mappings
- Character service and Streamlit tests

**Verification:**

- `just check` passed Ruff linting, formatting verification, strict mypy, and all 51 tests after the required environment rebuild.
- Tests cover atomic creation, primary-artwork invariants, assigned/unassigned isolation, rollback after invalid uploads, gallery additions, primary changes, editing, disabling, re-enabling, database uniqueness, and page rendering.
- Live browser verification confirmed the Characters navigation entry, creation form, upload field, status filter, and universe/unassigned selection.

**Decisions or deviations:**

- `None`/SQLite `NULL` is the canonical internal representation of the user-facing Unassigned location.
- Character names are not forced unique because the product requirements do not prohibit characters sharing names.
- Character movement is reserved for F-06 and cannot occur through the generic profile editor.

**Backlog created:**

- None.

### 2026-07-21 — F-04: Artwork filesystem service

**Status:** Complete

**Implemented:**

- Added artwork metadata with polymorphic character/group ownership, optional universe ownership, primary designation, original filename, MIME type, relative path, and byte size.
- Added GUID-only path builders for unassigned characters, universe characters, and flat universe group artwork.
- Added content-based JPEG, PNG, and WebP validation with extension matching and portable Windows/POSIX filename handling.
- Added atomic image imports that cannot overwrite an existing destination.
- Added safe relative-path resolution, image reads, explicit missing-file errors, missing-file reports, and orphan detection.
- Added an artwork repository and atomic application service that removes the imported file when database persistence fails.
- Kept image bytes outside SQLite; only metadata and POSIX-style relative paths are stored.

**Files or migrations:**

- `alembic/versions/20260721_0002_artwork_metadata.py`
- `src/world_builder/storage/artwork.py`
- `src/world_builder/domain/services/artworks.py`
- `src/world_builder/persistence/repositories/artworks.py`
- Artwork domain models, persistence mappings, and storage errors
- Artwork service and filesystem tests under `tests/domain/` and `tests/storage/`

**Verification:**

- `just ready` passed Ruff formatting and linting, strict mypy, and all 43 tests.
- Tests cover unassigned, assigned, and flat group paths; Windows-style filenames; invalid files and extensions; collision protection; safe path resolution; reads; missing files; orphans; metadata persistence; and filesystem rollback on a database foreign-key failure.

**Decisions or deviations:**

- Artwork ownership uses `owner_kind` and `owner_id` because character and group tables are introduced by later feature migrations; their services will enforce owner existence and universe alignment.
- The storage layer normalizes JPEG files to `.jpg` while preserving the portable original filename as metadata.
- Temporary import files use GUID names and are promoted atomically within the destination filesystem.

**Backlog created:**

- None.

### 2026-07-21 — F-03: Managed lookup administration

**Status:** Complete

**Implemented:**

- Added stable definitions for relationship types, membership roles, artwork association roles, and themes/tags.
- Added editable, universe-scoped defaults with idempotent provisioning for existing universes.
- Added repository and service operations to create, rename, describe, activate, and deactivate lookup values.
- Added category-specific validation requiring symmetric or directional behavior for relationship types.
- Added active-only lookup queries for future creation and editing forms while retaining inactive records for existing references.
- Added the Managed Lookups Streamlit page with one compact editable table and one save action per category.
- Added `just ready` to format the codebase and then run every non-mutating quality gate before handoff.
- Standardized the managed lookup editor and tabular transformations on pandas DataFrames.
- Added rerun-safe success toasts and immediate failure toasts for managed lookup saves.
- Color-coded success and failure toasts and set their visible dismissal animation to 1.5 seconds.
- Replaced the existing-universe card matrix and detail editor with a pandas-backed management table while retaining the dedicated creation form.

**Files or migrations:**

- `src/world_builder/domain/lookups.py`
- `src/world_builder/domain/models.py`
- `src/world_builder/domain/services/lookups.py`
- `src/world_builder/persistence/repositories/lookups.py`
- `src/world_builder/pages/lookups.py`
- `src/world_builder/app.py`
- `tests/domain/test_lookup_service.py`
- `tests/test_app.py`
- `justfile`
- No database migration was required because F-01 already introduced the lookup tables and constraints.

**Verification:**

- `just ready` passed Ruff formatting and linting, strict mypy, and all 29 tests.
- Streamlit AppTest rendered the lookup page and its provisioned relationship defaults without an exception.
- Service tests cover default provisioning, editing, activation filtering, uniqueness, directionality, ordering, and universe isolation.

**Decisions or deviations:**

- Category definitions remain stable application concepts while all values and defaults are editable per universe.
- Themes/tags begin empty; other categories receive editable starter values.
- Used values have no deletion operation and remain resolvable after deactivation.
- Lookup values are displayed alphabetically; manual ordering is not exposed.
- `just check` remains non-mutating for CI; `just ready` is the development handoff command that formats before checking.

**Backlog created:**

- None.

### 2026-07-21 — F-02: Universe workspace and isolation foundation

**Status:** Complete

**Implemented:**

- Added validated universe input and immutable universe view models.
- Added universe repository and application service boundaries for create, list, retrieve, and update operations.
- Enforced trimmed required names and case-insensitive name uniqueness.
- Added reusable same-universe and collection isolation rules.
- Added cached process-level database engine and session-factory resources outside Streamlit session state.
- Added a global sidebar universe selector with safe recovery when the stored selection no longer exists.
- Added a reusable guard for universe-dependent pages.
- Added the Universes page with creation, selection, detail, Markdown description, editing, and empty states.
- Updated the home page to show the current universe and use `just migrate` in startup guidance.
- Deliberately exposed no universe deletion operation.

**Files or migrations:**

- `src/world_builder/domain/errors.py`
- `src/world_builder/domain/models.py`
- `src/world_builder/domain/rules.py`
- `src/world_builder/domain/services/universes.py`
- `src/world_builder/persistence/repositories/universes.py`
- `src/world_builder/persistence/runtime.py`
- `src/world_builder/pages/context.py`
- `src/world_builder/pages/universes.py`
- Universe service, isolation-rule, and Streamlit shell tests
- No database migration was required because the universe table was introduced by F-01.

**Verification:**

- `just check` passed Ruff linting, formatting verification, strict mypy, and all 21 tests.
- Streamlit AppTest verified the empty, migrated universe workspace starts without UI exceptions.
- `just run 8911` started successfully on a non-default port against a migrated temporary database and stopped cleanly.

**Decisions or deviations:**

- Global lookup category definitions remain application-level; universe selection scopes their values in subsequent features.
- SQLite-loaded timestamps are normalized to UTC in domain views because SQLite omits timezone metadata.
- Streamlit pages use explicit stable URL paths so callable page names cannot collide.
- The known `.pth` import failure recurred during live startup; the prescribed `just rebuild-environment` recovery restored installed package imports.

**Backlog created:**

- None.

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
