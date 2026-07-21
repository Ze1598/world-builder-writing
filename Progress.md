# World Builder — Progress

This file is the durable execution log for the project. Update it at the end of every implementation feature or substantial maintenance session. It should describe completed outcomes and verification, not intentions; planned work belongs in `Roadmap.md`, while deferred work belongs in `Backlog.md`.

## Current status

- **Current roadmap feature:** F-01 — Database foundation and migration workflow
- **Feature status:** Not started
- **Last completed feature:** F-00 — Project scaffold and quality baseline
- **Last updated:** 2026-07-21

## Completed work

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

**Files or migrations:**

- `pyproject.toml`, `uv.lock`, `.python-version`, and `.gitignore`
- `src/world_builder/` application package
- `tests/test_settings.py`
- `README.md`
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
