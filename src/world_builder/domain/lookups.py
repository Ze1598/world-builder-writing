"""Stable definitions and editable defaults for managed vocabularies."""

from dataclasses import dataclass

from world_builder.persistence.models import RelationshipDirectionality

RELATIONSHIP_TYPE = "relationship_type"
MEMBERSHIP_ROLE = "membership_role"
ARTWORK_ASSOCIATION_ROLE = "artwork_association_role"
THEME = "theme"


@dataclass(frozen=True)
class LookupDefinition:
    """Application definition of a supported lookup category."""

    code: str
    name: str
    description: str
    defaults: tuple[tuple[str, RelationshipDirectionality | None], ...]


LOOKUP_DEFINITIONS = (
    LookupDefinition(
        RELATIONSHIP_TYPE,
        "Relationship types",
        "Labels describing how two characters currently relate.",
        (
            ("Friend", RelationshipDirectionality.SYMMETRIC),
            ("Rival", RelationshipDirectionality.SYMMETRIC),
            ("Trusts", RelationshipDirectionality.DIRECTIONAL),
            ("Loves", RelationshipDirectionality.DIRECTIONAL),
        ),
    ),
    LookupDefinition(
        MEMBERSHIP_ROLE,
        "Membership roles",
        "Optional roles a character can hold within a group.",
        (("Member", None), ("Leader", None), ("Founder", None)),
    ),
    LookupDefinition(
        ARTWORK_ASSOCIATION_ROLE,
        "Artwork association roles",
        "How an artwork item is used by another record.",
        (
            ("Portrait", None),
            ("Cover artwork", None),
            ("Story illustration", None),
            ("Visual reference", None),
        ),
    ),
    LookupDefinition(
        THEME,
        "Themes / tags",
        "Writer-defined themes and tags used to classify content.",
        (),
    ),
)

LOOKUP_DEFINITIONS_BY_CODE = {definition.code: definition for definition in LOOKUP_DEFINITIONS}
