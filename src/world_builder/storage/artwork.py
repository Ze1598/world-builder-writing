"""Validated filesystem storage for original artwork images."""

import base64
import os
import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import BinaryIO
from uuid import UUID, uuid4

from PIL import Image, UnidentifiedImageError

from world_builder.domain.errors import (
    ArtworkCollisionError,
    ArtworkStorageError,
    MissingArtworkFileError,
    UnsupportedArtworkError,
)
from world_builder.persistence.models import ArtworkOwnerKind

IMAGE_FORMATS = {
    "JPEG": ("image/jpeg", ".jpg", frozenset({".jpg", ".jpeg"})),
    "PNG": ("image/png", ".png", frozenset({".png"})),
    "WEBP": ("image/webp", ".webp", frozenset({".webp"})),
}


@dataclass(frozen=True)
class StoredArtworkFile:
    """Filesystem facts returned after a successful image import."""

    relative_path: str
    mime_type: str
    file_size: int
    original_filename: str


def canonical_identifier(value: str) -> str:
    """Validate and normalize one GUID used in a managed path."""
    return str(UUID(value))


def portable_basename(filename: str) -> str:
    """Extract a filename from either POSIX- or Windows-style input."""
    windows_name = PureWindowsPath(filename).name
    return PurePosixPath(windows_name).name


class ArtworkStorage:
    """Own path construction, validation, import, reads, and diagnostics."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def relative_path(
        self,
        *,
        artwork_id: str,
        owner_kind: ArtworkOwnerKind | None,
        owner_id: str | None,
        universe_id: str | None,
        extension: str,
    ) -> PurePosixPath:
        """Build the canonical relative path for an owned artwork file."""
        artwork = canonical_identifier(artwork_id)
        if extension not in {details[1] for details in IMAGE_FORMATS.values()}:
            raise UnsupportedArtworkError("The artwork extension is not supported.")
        filename = f"{artwork}{extension}"
        if owner_kind is None and owner_id is None and universe_id is None:
            return PurePosixPath("unassigned", "artwork", filename)
        if owner_kind is None or owner_id is None:
            raise ArtworkStorageError(
                "Artwork owner type and identifier must be supplied together."
            )
        owner = canonical_identifier(owner_id)
        if owner_kind is ArtworkOwnerKind.CHARACTER and universe_id is None:
            return PurePosixPath("unassigned", "characters", owner, filename)
        if universe_id is None:
            raise ArtworkStorageError("Assigned artwork requires a universe identifier.")
        universe = canonical_identifier(universe_id)
        if owner_kind is ArtworkOwnerKind.CHARACTER:
            return PurePosixPath("universes", universe, "characters", owner, filename)
        return PurePosixPath("universes", universe, "groups", filename)

    def import_image(
        self,
        source: BinaryIO,
        *,
        original_filename: str,
        artwork_id: str,
        owner_kind: ArtworkOwnerKind | None,
        owner_id: str | None,
        universe_id: str | None,
    ) -> StoredArtworkFile:
        """Validate image content and atomically copy it into managed storage."""
        filename = portable_basename(original_filename)
        if not filename:
            raise UnsupportedArtworkError("The artwork filename is missing.")
        suffix = Path(filename).suffix.casefold()
        try:
            payload = source.read()
        except OSError as error:
            raise ArtworkStorageError("The artwork file could not be read.") from error
        if not payload:
            raise UnsupportedArtworkError("The artwork file is empty.")

        try:
            with Image.open(BytesIO(payload)) as image:
                image_format = image.format
                image.verify()
        except (UnidentifiedImageError, OSError) as error:
            raise UnsupportedArtworkError("The uploaded file is not a valid image.") from error
        if image_format not in IMAGE_FORMATS:
            raise UnsupportedArtworkError("Only JPEG, PNG, and WebP artwork is supported.")
        mime_type, extension, accepted_extensions = IMAGE_FORMATS[image_format]
        if suffix not in accepted_extensions:
            raise UnsupportedArtworkError(
                f'The file extension "{suffix or "(none)"}" does not match its image content.'
            )

        relative = self.relative_path(
            artwork_id=artwork_id,
            owner_kind=owner_kind,
            owner_id=owner_id,
            universe_id=universe_id,
            extension=extension,
        )
        destination = self.absolute_path(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise ArtworkCollisionError("The artwork destination already exists.")
        temporary = destination.parent / f"{uuid4()}.tmp"
        try:
            with temporary.open("xb") as output:
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            try:
                os.link(temporary, destination)
            except FileExistsError as error:
                raise ArtworkCollisionError("The artwork destination already exists.") from error
            temporary.unlink()
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

        return StoredArtworkFile(
            relative_path=relative.as_posix(),
            mime_type=mime_type,
            file_size=len(payload),
            original_filename=filename,
        )

    def absolute_path(self, relative_path: str | PurePosixPath) -> Path:
        """Resolve a safe database-relative artwork path beneath the storage root."""
        relative = PurePosixPath(relative_path)
        if relative.is_absolute() or ".." in relative.parts or "\\" in str(relative):
            raise ArtworkStorageError("The artwork path is not a safe relative path.")
        resolved = self.root.joinpath(*relative.parts).resolve()
        if not resolved.is_relative_to(self.root):
            raise ArtworkStorageError("The artwork path escapes managed storage.")
        return resolved

    def read_bytes(self, relative_path: str) -> bytes:
        """Read artwork bytes or report a missing managed file."""
        path = self.absolute_path(relative_path)
        try:
            return path.read_bytes()
        except FileNotFoundError as error:
            raise MissingArtworkFileError(
                f'Managed artwork file "{relative_path}" is missing.'
            ) from error

    def data_uri(self, relative_path: str, mime_type: str) -> str:
        """Expose original artwork bytes as a browser-safe data URI."""
        supported_mime_types = {details[0] for details in IMAGE_FORMATS.values()}
        if mime_type not in supported_mime_types:
            raise UnsupportedArtworkError("The artwork MIME type is not supported.")
        payload = base64.b64encode(self.read_bytes(relative_path)).decode("ascii")
        return f"data:{mime_type};base64,{payload}"

    def copy(self, source_relative_path: str, destination_relative_path: str) -> None:
        """Atomically copy one managed file while retaining the source for rollback."""
        source = self.absolute_path(source_relative_path)
        destination = self.absolute_path(destination_relative_path)
        if not source.is_file():
            raise MissingArtworkFileError(
                f'Managed artwork file "{source_relative_path}" is missing.'
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise ArtworkCollisionError("The artwork destination already exists.")
        temporary = destination.parent / f"{uuid4()}.tmp"
        try:
            with source.open("rb") as input_file, temporary.open("xb") as output_file:
                shutil.copyfileobj(input_file, output_file)
                output_file.flush()
                os.fsync(output_file.fileno())
            try:
                os.link(temporary, destination)
            except FileExistsError as error:
                raise ArtworkCollisionError("The artwork destination already exists.") from error
            temporary.unlink()
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def delete(self, relative_path: str) -> None:
        """Remove one managed file without deleting shared parent directories."""
        self.absolute_path(relative_path).unlink(missing_ok=True)

    def missing_files(self, relative_paths: Iterable[str]) -> set[str]:
        """Return database paths whose managed files are absent."""
        return {path for path in relative_paths if not self.absolute_path(path).is_file()}

    def orphan_files(self, known_relative_paths: Iterable[str]) -> set[str]:
        """Return managed image files not represented by supplied database paths."""
        known = {PurePosixPath(path).as_posix() for path in known_relative_paths}
        if not self.root.exists():
            return set()
        extensions = {details[1] for details in IMAGE_FORMATS.values()}
        actual = {
            path.relative_to(self.root).as_posix()
            for path in self.root.rglob("*")
            if path.is_file() and path.suffix.casefold() in extensions
        }
        return actual - known
