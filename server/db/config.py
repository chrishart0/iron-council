from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from alembic.config import Config

from server.settings import get_settings

_PLACEHOLDER_DATABASE_URL = "from-settings"


def configure_alembic_database_url(
    config: Config,
    *,
    env: Mapping[str, str] | None = None,
    env_file: Path | None = None,
) -> str:
    configured_url = config.get_main_option("sqlalchemy.url")
    if configured_url and configured_url != _PLACEHOLDER_DATABASE_URL:
        return configured_url

    database_url = get_settings(env=env, env_file=env_file).database_url
    config.set_main_option("sqlalchemy.url", database_url)
    return database_url
