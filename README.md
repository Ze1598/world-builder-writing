# World Builder

World Builder is a local-first Streamlit application for managing fictional universes, with a character-centered view of stories, groups, relationships, artwork, and planning milestones.

The implementation roadmap is maintained in [Roadmap.md](Roadmap.md). Completed work is recorded in [Progress.md](Progress.md), and deferred work or technical debt is recorded in [Backlog.md](Backlog.md).

## Requirements

- macOS or Windows 11
- [`uv`](https://docs.astral.sh/uv/)

The project targets Python 3.12 and 3.13. `uv` can install and manage the required Python version when it is not already available.

## Install

From the repository root:

```bash
uv sync
```

The committed `uv.lock` file pins a reproducible, cross-platform dependency set.

## Run

```bash
uv run streamlit run src/world_builder/app.py
```

Streamlit prints a local URL and normally opens it in the default browser.

By default, personal content is stored in the repository's ignored `data/` directory. To use another location, set `WORLD_BUILDER_DATA_DIR` before starting the application.

macOS or Linux:

```bash
WORLD_BUILDER_DATA_DIR=/absolute/path/to/data \
  uv run streamlit run src/world_builder/app.py
```

Windows PowerShell:

```powershell
$env:WORLD_BUILDER_DATA_DIR = "C:\absolute\path\to\data"
uv run streamlit run src/world_builder/app.py
```

Do not copy the data directory while the application is running.

## Quality checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

To apply Ruff formatting locally:

```bash
uv run ruff format .
```

## Troubleshooting

### Broken imports caused by hidden `.pth` files

When the repository is stored in an iCloud-synchronized location, iCloud may hide `.pth` files inside the virtual environment and cause otherwise unexplained Python import failures.

If this signature appears, do not attempt an incremental dependency repair. From the repository root, rebuild the complete environment with:

```bash
rm -rf .venv && uv cache clean && uv sync --all-packages
```

This command intentionally removes only the repository-local virtual environment and uv's package cache. It does not touch the ignored `data/` directory.

## Project structure

```text
src/world_builder/
├── app.py             Streamlit entry point and navigation
├── domain/            Business rules and application services
├── pages/             Streamlit page renderers
├── persistence/       Database configuration and repositories
├── storage/           Artwork and portable-data services
└── visualizations/    Timeline and relationship graph projections
```

Streamlit pages must not issue SQL or mutate artwork files directly. They call the domain/application layer, which delegates persistence and file operations to the appropriate services.
