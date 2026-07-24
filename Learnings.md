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

## Streamlit runtime

### Data editor returns the same tabular type it receives

**Symptom**

Submitting a new managed lookup value fails with:

```text
AttributeError: 'list' object has no attribute 'to_dict'
```

The failure occurs when the save handler calls `edited.to_dict(orient="records")`.

**Cause**

`st.data_editor` received a list of dictionaries and therefore returned a list. The handler incorrectly assumed the result would always be a pandas DataFrame.

**Resolution**

Construct a pandas DataFrame before passing data to `st.data_editor`. The returned value remains a DataFrame and can be processed with pandas before conversion at the service boundary. Declare pandas and its mypy stubs as direct project dependencies.

**Caveat**

Streamlit preserves supported input types for `st.data_editor`; changing the input container changes the return type contract.

### Running app continues to serve UI removed from the source

**Symptom**

The source and automated tests contain a revised Streamlit page, but refreshing the browser still shows the previous widgets and layout.

**Cause**

The long-running Streamlit process did not reload after the source change and continued executing the previously loaded page module.

**Resolution**

Stop the existing `just run` process, restart it on the same non-default port, and reload the browser page. Verify the rendered widget structure rather than relying only on the source and AppTest.

**Caveat**

A browser refresh cannot load revised Python code when the server process itself is stale.

### Form widgets cannot dynamically enable their own submit button

**Symptom**

A confirmation checkbox and disabled submit button render inside the same `st.form`, but checking the box does not enable the button.

**Cause**

Streamlit batches form widget changes until form submission. Changing the checkbox does not rerun the script, so the submit button retains the `disabled` value calculated before the checkbox changed.

**Resolution**

Keep the form submit button enabled. On submission, validate the confirmation value and show a user-facing error without executing the operation when confirmation is absent.

**Caveat**

Dynamic enablement can be used when the controlling widget is outside the form, because that widget triggers a rerun.

## SQLAlchemy persistence

### SQLite reloads timezone-aware timestamps without UTC metadata

**Symptom**

A domain view returned immediately after creation does not compare equal to the same
record reloaded from SQLite. Every business field matches, but `created_at` and
`updated_at` differ because one value is timezone-aware and the reloaded value is
naive.

**Cause**

SQLite does not preserve timezone metadata for SQLAlchemy `DateTime(timezone=True)`
columns. Python-side defaults retain UTC metadata until the value is persisted and
reloaded.

**Resolution**

Normalize timestamp fields in every public domain view: attach UTC when SQLite
returns a naive value and convert aware values to UTC.

**Caveat**

Normalization belongs at the domain boundary. Altering tests to ignore timezone
differences would leave inconsistent timestamp contracts in application code.

### Uniform mutations across association tables require Core table metadata

**Symptom**

Code that applies the same delete operation to several declarative association models either duplicates one operation per model or fails strict typing with errors such as:

```text
FromClause has no attribute "delete"
```

**Cause**

SQLAlchemy's declarative `__table__` attribute is typed as the broad `FromClause` interface even though mapped database tables resolve to concrete `Table` objects at runtime. ORM model-class unions also produce incompatible generic types when one variable is reused across unrelated mapped classes.

**Resolution**

Validate and narrow each declarative `__table__` value to `sqlalchemy.Table` once at the repository boundary. Store the resulting tables and their entity-column metadata in shared collections, then iterate those collections for transactional Core `DELETE` statements.

**Caveat**

Core bulk mutations bypass loaded ORM relationship collections. Use them within a short transaction where those collections are not subsequently treated as authoritative, or expire affected ORM state before reading it again.
