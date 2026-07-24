# World Builder — Technical Implementation Roadmap

## 1. Product objective

Build a local-first writing companion for managing multiple, strictly isolated fictional universes. The primary unit is the character. The application connects characters to groups, relationships, chapters, stories, artwork, and idea milestones so that a writer can maintain a current 360-degree view of each character and visualize the current social graph.

The application runs locally on macOS and Windows through Streamlit. It does not require a hosted service, user accounts, synchronization, or collaborative editing. The complete data directory can be copied manually between computers while the application is stopped.

## 2. Confirmed product rules

### 2.1 Universe isolation

- The application supports any number of universes, including the two required at launch.
- Every universe-owned record belongs to exactly one universe.
- Characters, groups, chapters, stories, relationships, milestones, artwork associations, tags, and searches cannot cross universe boundaries.
- An all-universes view may display separated results but must never create cross-universe links.
- Each universe represents one canon.

### 2.2 Characters and unassigned characters

- A character is the primary product entity.
- A character is either assigned to one universe or held in the unassigned pool.
- Every character must be created with at least one artwork item and exactly one primary profile artwork.
- Characters are never permanently deleted.
- An assigned character can be active or disabled.
- Only a disabled character can be moved to another universe.
- Moving a character between universes removes every non-artwork connection before reassignment, including group memberships, story links, chapter links, milestone links, and relationships.
- Character-owned artwork and its metadata move with the character. Artwork associations to other universe records are removed.
- A moved character remains disabled in the destination universe until explicitly re-enabled.

### 2.3 Character groups

- A group belongs to exactly one universe.
- Characters may belong to multiple groups in their universe.
- A membership contains an optional Markdown description.
- Membership does not have historical chapter boundaries.
- Groups can own artwork.

### 2.4 Chapters and stories

- Chapters are ordered, conceptual boxes that group events within a universe.
- Each chapter has a title, Markdown description, and manual sequence position.
- Chapters may share a sequence position to mean that they occur at roughly the same time.
- Each story belongs to exactly one chapter.
- A story is the substantive literature entry, comparable to one DeviantArt literature post.
- A story contains a title and potentially lengthy Markdown text.
- Saving an edited story overwrites the current record; story revision history is out of scope.
- Story creation and editing include character and group multi-selects and an artwork selector.
- Stories can link existing artwork or upload new globally unassigned artwork.
- Chapters link existing artwork and do not originate artwork uploads.

### 2.5 Artwork

- Artwork can be owned by one character or one group, or remain in the global Unassigned pool.
- Artwork has a title and long Markdown description.
- Character artwork is stored in a folder belonging to the character.
- Group artwork is stored flat within the universe's group-artwork folder.
- Filesystem directory and file names use GUIDs only, apart from the image file extension.
- The database stores artwork metadata and relative paths; original image bytes remain outside SQLite.
- One artwork item can be associated with additional characters, groups, chapters, and stories in the same universe without duplicating the file.
- Physical ownership determines storage location. Semantic associations determine where artwork appears in the UI.

### 2.6 Relationships

- Relationships connect two characters in the same universe.
- Each unordered character pair can have at most one relationship record.
- Relationship types come from a user-managed lookup list.
- A relationship type may be symmetric or directional.
- Directional relationships preserve source and target character order.
- A relationship stores only its current managed type, direction, and optional Markdown description.
- Editing a relationship overwrites its current state; relationships have no chapter, story, or history layer.

### 2.7 Milestones

- A milestone is an idea, reminder, or planning note, not a canonical event.
- It has a title and Markdown text.
- It belongs to one universe.
- It may simultaneously link to zero or more characters, groups, chapters, and stories in that universe.
- Milestones may exist without a story or chapter.
- Unlinked milestones act as an idea inbox.
- Milestones do not automatically alter character summaries, relationships, or chronology.

### 2.8 Managed lookup values

- Lookup categories include relationship types, membership roles, and themes/tags.
- Values have a name, optional description, display order, and active/inactive status.
- Used values are deactivated rather than deleted.
- Renaming a value updates its display everywhere without changing its identity.

## 3. Technical architecture

### 3.1 Runtime and interface

- Python managed through `uv` with `pyproject.toml` and `uv.lock` committed.
- Streamlit provides the local, multipage browser interface.
- Streamlit session state stores transient UI state only, such as the selected universe and current filters.
- Canonical state is always read from and written to the database.
- Markdown is stored as source text and rendered with unsafe HTML disabled or sanitized.

### 3.2 Application layers

```text
Streamlit pages
    ↓
Application/domain services
    ↓
Repositories and storage services
    ↓
SQLite database + artwork filesystem
```

- Pages render forms and results but do not contain SQL or filesystem mutation logic.
- Domain services enforce universe isolation and workflow rules.
- Repositories own database queries and transactions.
- Artwork storage services own path construction, validation, copying, moving, and removal.
- Visualization services project current relational data into an in-memory graph.

Suggested package layout:

```text
src/world_builder/
├── app.py
├── pages/
├── domain/
│   ├── models.py
│   ├── rules.py
│   └── services/
├── persistence/
│   ├── database.py
│   ├── models.py
│   └── repositories/
├── storage/
│   └── artwork.py
├── visualizations/
│   ├── network.py
│   └── timeline.py
└── settings.py
tests/
alembic/
data/
```

### 3.3 Persistence

- SQLite is the authoritative structured store.
- SQLAlchemy 2 provides database access and transaction management.
- Alembic provides numbered, reviewable migration scripts.
- Migration execution remains explicit and available through `uv run alembic upgrade head` or a project wrapper command.
- Application startup checks the schema version and gives a clear migration instruction if it is outdated.
- A timestamped SQLite backup is created before applying migrations.
- Story text, summaries, descriptions, and milestone text use SQLite `TEXT` columns.
- Full-text search uses SQLite FTS5 when introduced by its feature slice.
- Stable GUIDs identify every durable record.

### 3.4 Artwork storage

```text
data/
├── world_builder.sqlite
└── artwork/
    ├── unassigned/
    │   └── characters/
    │       └── <character-guid>/
    │           └── <artwork-guid>.<extension>
    └── universes/
        └── <universe-guid>/
            ├── characters/
            │   └── <character-guid>/
            │       └── <artwork-guid>.<extension>
            └── groups/
                └── <artwork-guid>.<extension>
```

- Database paths are relative to `data/artwork`.
- Original filenames may be retained as metadata but are never used as storage paths.
- Supported extensions and MIME types are explicitly allow-listed.
- Thumbnails, if introduced, are disposable cache files and not canonical assets.
- The application must be stopped before manually copying the complete `data/` directory between machines.

### 3.5 Graph projection

- SQLite remains the source of truth for characters, groups, relationships, and memberships.
- NetworkX builds a filtered in-memory graph.
- The initial renderer should use PyVis embedded in Streamlit, subject to a small compatibility spike during the graph feature.
- Character and group nodes have distinct styles.
- Symmetric relationships render as lines; directional relationships render as arrows.
- Only the current relationship state is shown.
- Disabled characters are excluded by default and may be included with a filter.

## 4. Initial logical data model

The exact columns and constraints will be finalized in migration feature slices.

### Primary tables

```text
universes
characters
character_groups
group_memberships
chapters
stories
artworks
relationships
milestones
lookup_categories
lookup_values
```

### Association tables

```text
story_characters
story_groups
story_artworks
chapter_characters
chapter_groups
chapter_artworks
artwork_characters
artwork_groups
milestone_characters
milestone_groups
milestone_chapters
milestone_stories
```

Implementation may consolidate redundant artwork association tables if ownership and association semantics remain explicit and referential integrity is preserved.

### Important database and domain constraints

- A story's universe is inherited from its required chapter.
- Every association is validated to contain records from one universe.
- A relationship cannot connect a character to a character in another universe or to an unassigned character.
- Directional relationships preserve source and target; symmetric relationships use a canonical character ordering to prevent duplicates.
- Chapter sequence values may repeat.
- A character must have exactly one primary artwork after its creation transaction completes.
- Group artwork has exactly one owning group even though the files are held in a flat universe folder.
- Character and artwork reassignment is handled through a dedicated service, never generic CRUD.

## 5. Feature implementation sequence

Each feature below is intended to fit into an isolated implementation chat. A feature should not begin until its listed dependencies are complete. Every completed feature must update `Progress.md`; discovered but deferred work must be recorded in `Backlog.md`.

### F-00 — Project scaffold and quality baseline

**Goal:** Produce a reproducible Python application that starts locally on macOS and Windows.

**Dependencies:** None.

**Deliverables:**

- Initialize the `uv` project and supported Python version.
- Add Streamlit, SQLAlchemy, Alembic, Pydantic, Pillow, pytest, Ruff, and type-checking dependencies.
- Create the layered source layout.
- Add configuration for the data-directory path with a repository-local default.
- Add a minimal Streamlit shell and health page.
- Add lint, format, type-check, and test commands.
- Add README launch instructions for macOS and Windows.

**Acceptance criteria:**

- `uv sync` succeeds from a clean checkout.
- `just run` starts `src/streamlit_app.py` on a configurable non-default port.
- Lint, type-check, and test commands pass.
- No canonical data is stored in Streamlit session state.

### F-01 — Database foundation and migration workflow

**Goal:** Establish SQLite persistence and explicit, safe schema migrations.

**Dependencies:** F-00.

**Deliverables:**

- Configure SQLAlchemy and SQLite foreign-key enforcement.
- Configure Alembic using project models and the configured data directory.
- Add schema-version detection on application startup.
- Add a migration wrapper that backs up the SQLite file before upgrading.
- Create the initial migration for universes and lookup categories/values.
- Add repository transaction helpers and test database fixtures.

**Acceptance criteria:**

- A fresh database migrates to the current revision.
- An outdated database produces a clear instruction rather than silently changing.
- Migration backup behavior is tested.
- Foreign-key violations fail explicitly.

### F-02 — Universe workspace and isolation foundation

**Goal:** Create, select, edit, and navigate universes while establishing universe scoping throughout the UI.

**Dependencies:** F-01.

**Deliverables:**

- Universe create, list, edit, and detail operations.
- Persistent current-universe selector in Streamlit session state.
- Shared page guard requiring a universe where appropriate.
- Domain helpers for same-universe validation.
- Empty states for a new universe.

**Acceptance criteria:**

- At least two universes can be created and switched independently.
- A universe page never displays another universe's records.
- Same-universe validation has unit tests.
- Universe deletion is not exposed.

### F-03 — Managed lookup administration

**Goal:** Allow product vocabulary to be managed without code changes.

**Dependencies:** F-01, F-02.

**Deliverables:**

- Lookup management page for relationship types, membership roles, artwork association roles, and themes/tags.
- Create, rename, reorder, describe, activate, and deactivate operations.
- Symmetric/directional configuration on relationship-type values.
- Seed sensible defaults without making them immutable.
- Shared active-value selectors for later forms.

**Acceptance criteria:**

- Inactive values disappear from new-entry selectors but remain resolvable on existing records.
- Used values cannot be permanently deleted.
- Relationship directionality is persisted and validated.

### F-04 — Artwork filesystem service

**Goal:** Safely store and retrieve artwork outside the database using GUID-only paths.

**Dependencies:** F-01, F-02.

**Deliverables:**

- Artwork metadata model and migration.
- Character-owned and group-owned path builders.
- Allow-listed image MIME and extension validation.
- Safe import that copies files into managed storage.
- Collision prevention, missing-file reporting, and orphan detection helpers.
- Image read/display helpers for Streamlit.
- Filesystem rollback behavior when a database operation fails.

**Acceptance criteria:**

- Stored directories and filenames contain GUIDs only, excluding extensions.
- Paths in SQLite are relative.
- Unsupported or invalid files are rejected without partial records.
- Unit tests cover macOS- and Windows-style path behavior.

### F-05 — Character creation, profiles, and unassigned pool

**Goal:** Deliver the first useful character-first workflow.

**Dependencies:** F-02, F-04.

**Deliverables:**

- Character schema with nullable universe ownership and active/disabled state.
- One-form character creation requiring profile fields and initial artwork.
- Atomic creation of character, initial artwork, and primary-artwork designation.
- Unassigned-character list.
- Universe character list with active/disabled filters.
- Character profile with Markdown summary, primary image, and artwork gallery.
- Add artwork, change primary artwork, edit character, disable, and re-enable operations.
- No character delete action.

**Acceptance criteria:**

- A character cannot be committed without primary artwork.
- Exactly one artwork item is primary for each character.
- Unassigned and universe-owned characters are visually separated.
- Disabling a character preserves all data.

### F-06 — Character assignment and cross-universe movement

**Goal:** Assign unassigned characters and safely move disabled characters between universes.

**Dependencies:** F-05.

**Deliverables:**

- Assign an unassigned character to a selected universe.
- Move a disabled character from one universe to another.
- Move a disabled character from a universe back to Unassigned.
- Preflight report listing every non-artwork connection that will be removed.
- Explicit confirmation before detachment.
- Removal of relationships, memberships, story links, chapter links, milestone links, and artwork associations to universe records.
- Move all character-owned artwork files and update relative paths.
- Recovery strategy for failures between filesystem and database operations.
- Preserve disabled status in the destination universe.

**Acceptance criteria:**

- Moving an active assigned character disables it within the confirmed move operation.
- No cross-universe association survives a move.
- All character-owned artwork and primary designation survive.
- Failure-injection tests demonstrate that the operation does not leave half-moved content.

### F-07 — Character groups and memberships

**Goal:** Manage groups, group artwork, and current character membership.

**Dependencies:** F-03, F-04, F-05.

**Deliverables:**

- Group create, list, edit, and detail screens.
- Group artwork upload into the universe's flat `groups` folder.
- Character membership with an optional Markdown description and no role field.
- Add and remove membership operations.
- Group profile showing members and artwork.
- Universe isolation on every membership and artwork operation.

**Acceptance criteria:**

- A group cannot include an unassigned or foreign-universe character.
- Group artwork retains a single owning group despite flat physical storage.
- Membership removal does not alter character, group, or artwork records.

### F-08 — Sequenced chapters and universe timeline

**Goal:** Represent the universe's relative chronology as ordered chapter boxes.

**Dependencies:** F-02, F-05, F-07.

**Deliverables:**

- Chapter create, list, edit, and detail screens.
- Title, Markdown description, sequence position, character links, and group links.
- UI actions to move earlier, move later, and mark concurrent.
- Timeline/list visualization grouped by sequence position.
- Safe chapter removal rules in preparation for stories.

**Acceptance criteria:**

- Multiple chapters can share a sequence position.
- Reordering produces deterministic results.
- Moving one chapter out of a concurrent position changes only that chapter's timing.
- Character and group links remain universe-scoped.
- Timeline order is independent of creation time.
- Before stories exist, removing a chapter also removes its character and group links.
- Once stories exist, chapter removal is blocked while any story references it.

### F-09 — Story CRUD and Markdown content

**Goal:** Import and manage substantial story text as the primary literary content.

**Dependencies:** F-04, F-05, F-07, F-08.

**Deliverables:**

- Story schema and association tables.
- Story creation/edit form with required title, optional large Markdown field, required chapter, character multi-select, group multi-select, and existing-artwork selector.
- Optional upload of new globally unassigned artwork while creating or editing a story.
- Optional `.md` upload that populates the form.
- Markdown preview and safe rendering.
- Story detail page and Markdown download.
- Story deletion with explicit confirmation.
- Chapter deletion blocked while it contains stories.
- Reverse lookups on chapters, characters, groups, and artwork.

**Acceptance criteria:**

- Editing overwrites the current story without creating revisions.
- A title-only story is a valid placeholder.
- Long Markdown content round-trips without truncation.
- A story belongs to exactly one chapter.
- Selected entities and artwork must belong to the story's universe.
- Deleting a story removes associations but never deletes artwork.

### F-10 — Artwork associations and galleries

**Goal:** Complete reusable artwork linkage across the universe.

**Dependencies:** F-03, F-07, F-08, F-09.

**Deliverables:**

- Associate existing artwork with additional characters, groups, chapters, and stories.
- Artwork detail page showing owner and every usage.
- Transfer artwork ownership between characters, groups, and the global Unassigned pool.
- Character, group, chapter, and story galleries.
- Usage report before artwork deletion.
- Safe artwork deletion that removes associations and its owned file only after confirmation.

**Acceptance criteria:**

- One file can appear in multiple galleries without duplication.
- Cross-universe artwork associations are rejected.
- Ownership remains unchanged when associations change.
- Primary character artwork cannot be deleted until another primary is selected.

### F-11 — Current character relationships

**Goal:** Record the current relationship between character pairs.

**Dependencies:** F-03, F-05.

**Deliverables:**

- One canonical relationship record per unordered character pair.
- Create symmetric and directional relationships.
- Relationship fields: managed type, optional Markdown description, and directional source when required.
- Direct create, edit, and remove controls on character profiles.
- Relationship counts and deletion within the character-move transaction.
- Validation preventing self-links, invalid directionality, and cross-universe edges.

**Acceptance criteria:**

- A directional relationship stores one explicit direction for the character pair.
- Symmetric duplicates are prevented regardless of character selection order.
- Reverse-order creation cannot create a second relationship for the same pair.
- Editing overwrites the existing record rather than creating history.
- Moving either character reports and removes the relationship.

### F-12 — Milestone idea inbox

**Goal:** Centralize loose ideas and connect them to existing universe content.

**Dependencies:** F-05, F-07, F-08, F-09.

**Deliverables:**

- Milestone schema and association tables.
- Fast-capture form requiring only title and Markdown text.
- Optional multi-select links to characters, groups, chapters, and stories.
- Unlinked milestone inbox.
- Filters and reverse lookup from every supported entity.
- Edit and delete operations.

**Acceptance criteria:**

- A milestone can exist without story or chapter links.
- A milestone can link to multiple records at every supported level.
- Foreign-universe links are rejected.
- Milestones do not mutate canonical summaries or relationships.

### F-13 — Character 360-degree profile

**Goal:** Assemble the complete usable view of one character.

**Dependencies:** F-07 through F-12.

**Deliverables:**

- Current Markdown summary and primary artwork.
- Complete artwork gallery.
- Current group memberships and descriptions.
- Current relationships with their direction and description.
- Linked chapters and stories.
- Linked milestones clearly labeled as ideas.
- Disabled status and universe ownership.
- Consistent navigation to all source records.

**Acceptance criteria:**

- The page contains no data from another universe.
- Current facts and planning ideas are visually distinct.
- Every listed association navigates to or identifies its source record.

### F-14 — Current social graph explorer

**Goal:** Visualize current character and group connections interactively.

**Dependencies:** F-07, F-11.

**Deliverables:**

- Compatibility spike and documented choice of Streamlit graph renderer.
- NetworkX graph projection from current SQLite records.
- Scope by selected universe, characters, and/or groups.
- Character and group nodes with different styles.
- Relationship and membership edges with different styles.
- Arrowheads for directional relationships.
- Relationship-type edge labels or tooltips.
- Filters for relationship type, disabled characters, and connection distance.
- Views for direct connections, two-hop connections, and connected component.
- No historical chapter-snapshot mode.

**Acceptance criteria:**

- Default universe graph shows only active characters and current relationship states.
- Selecting a character clearly shows who that character currently has ties with.
- Selecting a group shows its members and their current relationships.
- Directional and symmetric relationships are visually distinguishable.

### F-15 — Universe-scoped search and filtering

**Goal:** Make all stored content quickly retrievable.

**Dependencies:** F-09, F-12, F-13.

**Deliverables:**

- FTS5 indexes for names, titles, summaries, descriptions, story Markdown, and milestone text.
- Index maintenance through repository operations or database triggers.
- Current-universe search by default.
- Separate unassigned-character search.
- Entity-type, status, chapter, character, group, theme, and relationship filters where relevant.
- Link-based queries such as all stories involving a character.

**Acceptance criteria:**

- Search never leaks results across the selected universe boundary.
- Removed/disabled characters are marked rather than silently omitted when included.
- Text search and structured-link filtering can be combined.
- Index rebuild is supported and tested.

### F-16 — Data integrity, portability documentation, and release hardening

**Goal:** Make the local library dependable enough for ongoing personal use on both operating systems.

**Dependencies:** F-00 through F-15.

**Deliverables:**

- Startup database integrity and artwork consistency checks.
- Report for missing files, orphan files, invalid paths, and broken associations.
- Documented manual Mac-to-Windows and Windows-to-Mac copy procedure.
- Documented migration procedure before opening data with newer code.
- End-to-end smoke tests for two universes plus unassigned characters.
- Representative seed/demo data kept separate from personal data.
- Accessibility, large-story, and large-image checks.
- Final README and troubleshooting guide.

**Acceptance criteria:**

- Copying the stopped application's full `data/` directory preserves all content and artwork.
- A representative two-universe library passes integrity checks on macOS and Windows.
- All automated checks pass from a clean `uv sync`.
- No known data-loss defect remains open.

## 6. Cross-cutting testing strategy

- Unit-test domain rules without Streamlit.
- Integration-test repositories against temporary SQLite databases.
- Use temporary directories for artwork-service tests.
- Test every cross-universe rejection path.
- Test database and filesystem failure recovery for character creation, artwork deletion, and character movement.
- Test migrations both from a blank database and from fixtures representing previous revisions.
- Add Streamlit app tests for critical forms and navigation where practical.
- Maintain one end-to-end fixture containing two universes, concurrent chapters, directional and symmetric relationships, unassigned characters, and shared artwork associations.

## 7. Definition of done for every feature

A feature is complete only when:

- Its acceptance criteria are satisfied.
- Relevant tests pass.
- Linting and type checking pass.
- New schema changes include an Alembic migration.
- Universe-isolation behavior is explicitly tested.
- User-facing behavior is documented where needed.
- `Progress.md` records the completed work and verification.
- Deferred work or compromises are entered in `Backlog.md` with impact and rationale.

## 8. Explicitly deferred scope

- LLM integration and generated summary proposals.
- Cloud hosting, synchronization, and concurrent editing.
- User accounts and permissions.
- Alternate canons within a universe.
- Story revision history.
- Historical graph snapshots.
- Calendar dates or exact fictional timestamps.
- Automatic story parsing or entity extraction.
- Full manuscript composition features.
- Native desktop packaging.
- Automatic merging of libraries edited on separate machines.
