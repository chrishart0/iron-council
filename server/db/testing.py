from __future__ import annotations

from pathlib import Path

from alembic.config import Config

from server.db.config import configure_alembic_database_url
from server.db.migrations import reset_database, upgrade_database

ALEMBIC_INI_PATH = Path(__file__).resolve().parents[2] / "alembic.ini"


def build_alembic_config(database_url: str) -> Config:
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("sqlalchemy.url", database_url)
    configure_alembic_database_url(config)
    return config


def prepare_test_database(
    *, config: Config | None = None, database_url: str | None = None, reset: bool
) -> None:
    resolved_config = config or build_alembic_config(_require_database_url(database_url))
    if reset:
        reset_database(resolved_config)
        return
    upgrade_database(resolved_config)


def _require_database_url(database_url: str | None) -> str:
    if database_url is None:
        raise ValueError("database_url is required when config is not provided.")
    return database_url
