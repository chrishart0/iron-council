from __future__ import annotations

from alembic import command
from alembic.config import Config


def upgrade_database(config: Config, revision: str = "head") -> None:
    command.upgrade(config, revision)


def reset_database(config: Config) -> None:
    command.downgrade(config, "base")
    command.upgrade(config, "head")
