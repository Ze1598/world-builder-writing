"""Tests for cross-universe isolation rules."""

import pytest

from world_builder.domain.rules import (
    UniverseIsolationError,
    require_all_in_universe,
    require_same_universe,
)


def test_same_universe_is_accepted() -> None:
    require_same_universe("universe-a", "universe-a", entity_name="Character")


def test_foreign_universe_is_rejected() -> None:
    with pytest.raises(UniverseIsolationError, match="different universe"):
        require_same_universe("universe-a", "universe-b", entity_name="Character")


def test_collection_rejects_one_foreign_universe() -> None:
    with pytest.raises(UniverseIsolationError, match="different universe"):
        require_all_in_universe(
            "universe-a",
            ["universe-a", "universe-b"],
            entity_name="Character",
        )
