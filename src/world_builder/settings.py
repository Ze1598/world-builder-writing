"""Application settings and local data-directory resolution."""

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict

DATA_DIRECTORY_ENV_VAR = "WORLD_BUILDER_DATA_DIR"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseModel):
    """Resolved runtime settings."""

    model_config = ConfigDict(frozen=True)

    data_directory: Path

    @property
    def artwork_directory(self) -> Path:
        """Return the canonical root for managed artwork files."""
        return self.data_directory / "artwork"

    @property
    def database_path(self) -> Path:
        """Return the canonical SQLite database path."""
        return self.data_directory / "world_builder.sqlite"


def resolve_data_directory(override: str | Path | None = None) -> Path:
    """Resolve an explicit, environment, or repository-local data directory."""
    configured_path = override or os.environ.get(DATA_DIRECTORY_ENV_VAR)
    if configured_path is None:
        return (PROJECT_ROOT / "data").resolve()
    return Path(configured_path).expanduser().resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings for the running application."""
    return Settings(data_directory=resolve_data_directory())
