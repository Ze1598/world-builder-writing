"""Tests for application settings."""

from pathlib import Path

from world_builder.settings import PROJECT_ROOT, Settings, resolve_data_directory


def test_default_data_directory_is_repository_local(monkeypatch: object) -> None:
    monkeypatch.delenv("WORLD_BUILDER_DATA_DIR", raising=False)  # type: ignore[attr-defined]

    assert resolve_data_directory() == (PROJECT_ROOT / "data").resolve()


def test_explicit_data_directory_takes_precedence(tmp_path: Path) -> None:
    assert resolve_data_directory(tmp_path) == tmp_path.resolve()


def test_settings_derive_storage_paths(tmp_path: Path) -> None:
    settings = Settings(data_directory=tmp_path)

    assert settings.database_path == tmp_path / "world_builder.sqlite"
    assert settings.artwork_directory == tmp_path / "artwork"
