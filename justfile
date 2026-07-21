set dotenv-load := true

# List the available project commands.
default:
    @just --list

# Resolve and install all project packages.
sync:
    uv sync --all-packages

# Start Streamlit on a configurable non-default port.
run port="8765":
    uv run streamlit run src/world_builder/app.py --server.port {{port}}

# Report whether the configured database matches the current migration head.
schema-status:
    uv run world-builder schema-status

# Back up an existing outdated database and migrate it to the current head.
migrate:
    uv run world-builder migrate

# Run static lint checks.
lint:
    uv run ruff check .

# Apply canonical formatting.
format:
    uv run ruff format .

# Verify canonical formatting without changing files.
format-check:
    uv run ruff format --check .

# Run strict static type checking.
typecheck:
    uv run mypy

# Run the complete automated test suite.
test:
    uv run pytest

# Run every non-mutating quality gate.
check: lint format-check typecheck test

# Rebuild an environment corrupted by iCloud-hidden .pth files.
rebuild-environment:
    rm -rf .venv
    uv cache clean
    uv sync --all-packages

