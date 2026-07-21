"""Tests for validated GUID-only artwork storage."""

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from world_builder.domain.errors import (
    ArtworkCollisionError,
    ArtworkStorageError,
    MissingArtworkFileError,
    UnsupportedArtworkError,
)
from world_builder.persistence.models import ArtworkOwnerKind
from world_builder.storage.artwork import ArtworkStorage

ARTWORK_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
CHARACTER_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
UNIVERSE_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"


def image_file(image_format: str = "PNG") -> BytesIO:
    payload = BytesIO()
    Image.new("RGB", (4, 4), color="purple").save(payload, format=image_format)
    payload.seek(0)
    return payload


def test_character_paths_are_guid_only_and_relative(tmp_path: Path) -> None:
    storage = ArtworkStorage(tmp_path / "artwork")

    unassigned = storage.relative_path(
        artwork_id=ARTWORK_ID,
        owner_kind=ArtworkOwnerKind.CHARACTER,
        owner_id=CHARACTER_ID,
        universe_id=None,
        extension=".png",
    )
    assigned = storage.relative_path(
        artwork_id=ARTWORK_ID,
        owner_kind=ArtworkOwnerKind.CHARACTER,
        owner_id=CHARACTER_ID,
        universe_id=UNIVERSE_ID,
        extension=".png",
    )

    assert unassigned.as_posix() == (f"unassigned/characters/{CHARACTER_ID}/{ARTWORK_ID}.png")
    assert assigned.as_posix() == (
        f"universes/{UNIVERSE_ID}/characters/{CHARACTER_ID}/{ARTWORK_ID}.png"
    )


def test_group_path_is_flat_within_universe(tmp_path: Path) -> None:
    storage = ArtworkStorage(tmp_path / "artwork")

    relative = storage.relative_path(
        artwork_id=ARTWORK_ID,
        owner_kind=ArtworkOwnerKind.GROUP,
        owner_id=CHARACTER_ID,
        universe_id=UNIVERSE_ID,
        extension=".jpg",
    )

    assert relative.as_posix() == f"universes/{UNIVERSE_ID}/groups/{ARTWORK_ID}.jpg"


def test_import_normalizes_windows_filename_and_reads_image(tmp_path: Path) -> None:
    storage = ArtworkStorage(tmp_path / "artwork")

    stored = storage.import_image(
        image_file(),
        original_filename=r"C:\Users\Writer\portrait.png",
        artwork_id=ARTWORK_ID,
        owner_kind=ArtworkOwnerKind.CHARACTER,
        owner_id=CHARACTER_ID,
        universe_id=None,
    )

    assert stored.original_filename == "portrait.png"
    assert stored.mime_type == "image/png"
    assert stored.relative_path.endswith(f"/{ARTWORK_ID}.png")
    assert storage.read_bytes(stored.relative_path).startswith(b"\x89PNG")


@pytest.mark.parametrize(
    ("payload", "filename"),
    [(BytesIO(b"not an image"), "fake.png"), (image_file(), "portrait.exe")],
)
def test_invalid_content_or_extension_is_rejected_without_file(
    tmp_path: Path, payload: BytesIO, filename: str
) -> None:
    storage = ArtworkStorage(tmp_path / "artwork")

    with pytest.raises(UnsupportedArtworkError):
        storage.import_image(
            payload,
            original_filename=filename,
            artwork_id=ARTWORK_ID,
            owner_kind=ArtworkOwnerKind.CHARACTER,
            owner_id=CHARACTER_ID,
            universe_id=None,
        )

    assert not storage.root.exists()


def test_collision_does_not_overwrite_existing_file(tmp_path: Path) -> None:
    storage = ArtworkStorage(tmp_path / "artwork")
    stored = storage.import_image(
        image_file(),
        original_filename="first.png",
        artwork_id=ARTWORK_ID,
        owner_kind=ArtworkOwnerKind.CHARACTER,
        owner_id=CHARACTER_ID,
        universe_id=None,
    )
    original = storage.read_bytes(stored.relative_path)

    with pytest.raises(ArtworkCollisionError):
        storage.import_image(
            image_file(),
            original_filename="second.png",
            artwork_id=ARTWORK_ID,
            owner_kind=ArtworkOwnerKind.CHARACTER,
            owner_id=CHARACTER_ID,
            universe_id=None,
        )

    assert storage.read_bytes(stored.relative_path) == original


def test_missing_and_orphan_helpers(tmp_path: Path) -> None:
    storage = ArtworkStorage(tmp_path / "artwork")
    stored = storage.import_image(
        image_file(),
        original_filename="portrait.png",
        artwork_id=ARTWORK_ID,
        owner_kind=ArtworkOwnerKind.CHARACTER,
        owner_id=CHARACTER_ID,
        universe_id=None,
    )

    assert storage.missing_files([stored.relative_path, "missing/image.png"]) == {
        "missing/image.png"
    }
    assert storage.orphan_files([]) == {stored.relative_path}
    assert storage.orphan_files([stored.relative_path]) == set()

    storage.delete(stored.relative_path)
    with pytest.raises(MissingArtworkFileError):
        storage.read_bytes(stored.relative_path)


def test_unsafe_relative_paths_are_rejected(tmp_path: Path) -> None:
    storage = ArtworkStorage(tmp_path / "artwork")

    with pytest.raises(ArtworkStorageError):
        storage.absolute_path("../private.png")
    with pytest.raises(ArtworkStorageError):
        storage.absolute_path(r"universes\escape.png")
