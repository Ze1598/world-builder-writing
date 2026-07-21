"""Tests for atomic artwork metadata and filesystem behavior."""

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.models import ArtworkInput, UniverseInput
from world_builder.domain.services.artworks import ArtworkService
from world_builder.domain.services.universes import UniverseService
from world_builder.persistence.models import ArtworkOwnerKind
from world_builder.storage.artwork import ArtworkStorage

CHARACTER_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
MISSING_UNIVERSE_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"


def png_file() -> BytesIO:
    payload = BytesIO()
    Image.new("RGB", (4, 4), color="blue").save(payload, format="PNG")
    payload.seek(0)
    return payload


def test_import_persists_relative_metadata_and_file(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    universe = UniverseService(session_factory).create_universe(UniverseInput(name="World"))
    storage = ArtworkStorage(tmp_path / "artwork")
    service = ArtworkService(session_factory, storage)

    artwork = service.import_artwork(
        ArtworkInput(
            universe_id=universe.id,
            owner_kind=ArtworkOwnerKind.CHARACTER,
            owner_id=CHARACTER_ID,
            title="Portrait",
            description="Primary character portrait.",
            original_filename="portrait.png",
            is_primary=True,
        ),
        png_file(),
    )

    assert not Path(artwork.relative_path).is_absolute()
    assert storage.absolute_path(artwork.relative_path).is_file()
    assert artwork.mime_type == "image/png"
    assert artwork.is_primary is True
    assert service.missing_files() == set()
    assert service.orphan_files() == set()


def test_database_failure_removes_imported_file(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    storage = ArtworkStorage(tmp_path / "artwork")
    service = ArtworkService(session_factory, storage)

    with pytest.raises(IntegrityError):
        service.import_artwork(
            ArtworkInput(
                universe_id=MISSING_UNIVERSE_ID,
                owner_kind=ArtworkOwnerKind.CHARACTER,
                owner_id=CHARACTER_ID,
                title="Portrait",
                description="Cannot persist.",
                original_filename="portrait.png",
            ),
            png_file(),
        )

    assert storage.orphan_files([]) == set()
