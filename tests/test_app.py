"""Streamlit shell tests for the universe workspace."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from world_builder.domain.models import UniverseInput
from world_builder.domain.services.universes import UniverseService
from world_builder.persistence.migrations import migrate_database
from world_builder.persistence.runtime import get_session_factory
from world_builder.settings import get_settings


def _configure_test_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data_directory = tmp_path / "data"
    migrate_database(data_directory / "world_builder.sqlite")
    monkeypatch.setenv("WORLD_BUILDER_DATA_DIR", str(data_directory))
    get_settings.cache_clear()
    return data_directory


def test_app_renders_empty_universe_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_test_data(tmp_path, monkeypatch)

    app = AppTest.from_file("src/streamlit_app.py", default_timeout=10).run()

    assert not app.exception
    assert app.title[0].value == "World Builder"
    assert any("Create a universe" in info.value for info in app.info)
    get_settings.cache_clear()


def test_lookup_page_renders_managed_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_directory = _configure_test_data(tmp_path, monkeypatch)
    session_factory = get_session_factory(data_directory / "world_builder.sqlite")
    UniverseService(session_factory).create_universe(UniverseInput(name="Test"))

    def lookup_page() -> None:
        from world_builder.domain.services.lookups import LookupService
        from world_builder.domain.services.universes import UniverseService
        from world_builder.pages.lookups import render_lookups
        from world_builder.persistence.runtime import get_session_factory
        from world_builder.settings import get_settings

        settings = get_settings()
        test_session_factory = get_session_factory(settings.database_path)
        selected = UniverseService(test_session_factory).list_universes()[0]
        render_lookups(LookupService(test_session_factory), selected)

    app = AppTest.from_function(lookup_page, default_timeout=10).run()

    assert not app.exception
    assert app.title[0].value == "Managed lookups"
    assert app.button[0].label == "Save values"
    get_settings.cache_clear()


def test_universe_page_renders_creation_form_and_management_table(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_directory = _configure_test_data(tmp_path, monkeypatch)
    session_factory = get_session_factory(data_directory / "world_builder.sqlite")
    UniverseService(session_factory).create_universe(UniverseInput(name="Test"))

    def universe_page() -> None:
        from world_builder.domain.services.universes import UniverseService
        from world_builder.pages.universes import render_universes
        from world_builder.persistence.runtime import get_session_factory
        from world_builder.settings import get_settings

        settings = get_settings()
        test_session_factory = get_session_factory(settings.database_path)
        selected = UniverseService(test_session_factory).list_universes()[0]
        render_universes(UniverseService(test_session_factory), selected)

    app = AppTest.from_function(universe_page, default_timeout=10).run()

    assert not app.exception
    assert app.title[0].value == "Universes"
    assert [button.label for button in app.button] == [
        "Create universe",
        "Save universes",
    ]
    get_settings.cache_clear()


def test_character_page_renders_creation_and_sidebar_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_directory = _configure_test_data(tmp_path, monkeypatch)

    def character_page() -> None:
        from world_builder.domain.services.characters import CharacterService
        from world_builder.pages.characters import render_characters
        from world_builder.persistence.runtime import get_session_factory
        from world_builder.settings import get_settings
        from world_builder.storage.artwork import ArtworkStorage

        settings = get_settings()
        service = CharacterService(
            get_session_factory(settings.database_path),
            ArtworkStorage(settings.artwork_directory),
        )
        render_characters(service, None)

    app = AppTest.from_function(character_page, default_timeout=10).run()

    assert not app.exception
    assert app.title[0].value == "Characters"
    assert app.expander[0].label == "Create character"
    assert any("sidebar filter" in info.value.lower() for info in app.info)
    assert data_directory.exists()
    get_settings.cache_clear()
