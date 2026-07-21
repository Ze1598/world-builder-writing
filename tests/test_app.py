"""Streamlit shell tests for the universe workspace."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from world_builder.persistence.migrations import migrate_database
from world_builder.settings import get_settings


def test_app_renders_empty_universe_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_directory = tmp_path / "data"
    migrate_database(data_directory / "world_builder.sqlite")
    monkeypatch.setenv("WORLD_BUILDER_DATA_DIR", str(data_directory))
    get_settings.cache_clear()

    app = AppTest.from_file("src/streamlit_app.py", default_timeout=10).run()

    assert not app.exception
    assert app.title[0].value == "World Builder"
    assert any("Create a universe" in info.value for info in app.info)

    get_settings.cache_clear()
