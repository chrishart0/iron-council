from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DATABASE_URL = "postgresql://iron_counsil:iron_counsil@127.0.0.1:54321/iron_counsil"
DEFAULT_ENV_FILE = Path(".env.local")
ENV_FILE_VARIABLE = "IRON_COUNCIL_ENV_FILE"


@dataclass(frozen=True)
class Settings:
    database_url: str


def get_settings(
    *,
    env: Mapping[str, str] | None = None,
    env_file: Path | None = None,
) -> Settings:
    current_env = dict(os.environ if env is None else env)
    resolved_env_file = env_file or Path(current_env.get(ENV_FILE_VARIABLE, DEFAULT_ENV_FILE))
    file_values = _load_env_file(resolved_env_file)
    database_url = current_env.get("DATABASE_URL") or file_values.get(
        "DATABASE_URL",
        DEFAULT_DATABASE_URL,
    )
    return Settings(database_url=database_url)


def _load_env_file(env_file: Path) -> dict[str, str]:
    if not env_file.is_file():
        return {}

    values: dict[str, str] = {}
    for line in env_file.read_text().splitlines():
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("#"):
            continue

        key, separator, value = stripped_line.partition("=")
        if not separator:
            continue
        values[key.strip()] = value.strip()
    return values
