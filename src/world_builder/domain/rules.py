"""Framework-independent product rules."""


class UniverseIsolationError(ValueError):
    """Raised when an operation attempts to connect different universes."""


def require_same_universe(
    expected_universe_id: str,
    actual_universe_id: str,
    *,
    entity_name: str,
) -> None:
    """Reject an entity that does not belong to the expected universe."""
    if expected_universe_id != actual_universe_id:
        raise UniverseIsolationError(
            f"{entity_name} belongs to a different universe and cannot be linked."
        )


def require_all_in_universe(
    expected_universe_id: str,
    universe_ids: list[str],
    *,
    entity_name: str,
) -> None:
    """Reject a collection containing an entity from another universe."""
    for universe_id in universe_ids:
        require_same_universe(
            expected_universe_id,
            universe_id,
            entity_name=entity_name,
        )
