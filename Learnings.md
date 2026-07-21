# World Builder — Learnings

This file is a problem-indexed reference for reusable technical findings. Chronological implementation and verification history belongs in `Progress.md`.

## Python environment

### Streamlit cannot import the installed `world_builder` package

**Symptom**

Streamlit starts and executes the nested `src/world_builder/app.py` entry point, then fails on application imports with:

```text
ModuleNotFoundError: No module named 'world_builder'
```

The traceback points to imports such as:

```python
from world_builder.domain.services.universes import UniverseService
```

Equivalent failures may appear from other application pages or modules.

**Cause**

The original `just run` recipe passed the nested package module `src/world_builder/app.py` directly to Streamlit. Streamlit uses the entry-point directory as its script context, while tests add `src` through pytest configuration. The live runner therefore could not reliably resolve the sibling `world_builder` package and depended on editable-install `.pth` behavior that is also disrupted by iCloud synchronization.

**Resolution**

Run Streamlit through the canonical source-root entry point:

```text
src/streamlit_app.py
```

The `just run` recipe targets this file, placing `src` in Streamlit's script context so `world_builder` is directly importable.

If the same error affects other installed commands, stop every running Streamlit or `uv` process for this project, then rebuild the complete environment:

```bash
just rebuild-environment
```

The recipe runs the required recovery sequence:

```bash
rm -rf .venv
uv cache clean
uv sync --all-packages
```

Run `just check` after rebuilding.

**Caveat**

An open `just run` process may hold uv's shared cache lock. In that case, `uv cache clean` waits with:

```text
Cache is currently in-use, waiting for other uv processes to finish
```

Stop the running application before rebuilding. Do not force cache removal while another uv process is active.
