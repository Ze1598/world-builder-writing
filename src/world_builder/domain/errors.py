"""Application-level errors suitable for presentation by any interface."""


class DomainError(Exception):
    """Base class for expected application errors."""


class DuplicateNameError(DomainError):
    """Raised when a name must be unique within its scope."""


class RecordNotFoundError(DomainError):
    """Raised when a requested durable record does not exist."""


class ArtworkStorageError(DomainError):
    """Raised when an artwork file cannot be validated or safely managed."""


class UnsupportedArtworkError(ArtworkStorageError):
    """Raised when uploaded bytes or their extension are not allow-listed images."""


class ArtworkCollisionError(ArtworkStorageError):
    """Raised when a generated artwork destination already exists."""


class MissingArtworkFileError(ArtworkStorageError):
    """Raised when artwork metadata points to a missing managed file."""
