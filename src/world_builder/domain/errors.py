"""Application-level errors suitable for presentation by any interface."""


class DomainError(Exception):
    """Base class for expected application errors."""


class DuplicateNameError(DomainError):
    """Raised when a name must be unique within its scope."""


class RecordNotFoundError(DomainError):
    """Raised when a requested durable record does not exist."""
