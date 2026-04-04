from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.engine import make_url

DEFAULT_DATABASE_URL = "postgresql+psycopg://iron_council:iron_council@127.0.0.1:54321/iron_council"
DEFAULT_ENV_FILE = Path(".env.local")
ENV_FILE_VARIABLE = "IRON_COUNCIL_ENV_FILE"
DB_LANE_VARIABLE = "IRON_COUNCIL_DB_LANE"
MATCH_REGISTRY_BACKEND_VARIABLE = "IRON_COUNCIL_MATCH_REGISTRY_BACKEND"
BROWSER_ORIGINS_VARIABLE = "IRON_COUNCIL_BROWSER_ORIGINS"
AUTHENTICATED_WRITE_MAX_BODY_BYTES_VARIABLE = "IRON_COUNCIL_AUTHENTICATED_WRITE_MAX_BODY_BYTES"
AUTHENTICATED_WRITE_RATE_LIMIT_VARIABLE = "IRON_COUNCIL_AUTHENTICATED_WRITE_RATE_LIMIT"
AUTHENTICATED_WRITE_RATE_WINDOW_SECONDS_VARIABLE = (
    "IRON_COUNCIL_AUTHENTICATED_WRITE_RATE_WINDOW_SECONDS"
)
DEFAULT_BROWSER_ORIGINS = (
    "http://127.0.0.1:3000",
    "http://localhost:3000",
)
DEFAULT_AUTHENTICATED_WRITE_MAX_BODY_BYTES = 64 * 1024
DEFAULT_AUTHENTICATED_WRITE_RATE_LIMIT = 30
DEFAULT_AUTHENTICATED_WRITE_RATE_WINDOW_SECONDS = 10
_MAX_IDENTIFIER_LENGTH = 63


@dataclass(frozen=True)
class AuthenticatedWriteAbuseSettings:
    max_body_bytes: int = DEFAULT_AUTHENTICATED_WRITE_MAX_BODY_BYTES
    rate_limit: int = DEFAULT_AUTHENTICATED_WRITE_RATE_LIMIT
    rate_window_seconds: int = DEFAULT_AUTHENTICATED_WRITE_RATE_WINDOW_SECONDS


@dataclass(frozen=True)
class Settings:
    database_url: str
    match_registry_backend: str = "memory"
    allowed_browser_origins: tuple[str, ...] = DEFAULT_BROWSER_ORIGINS
    human_jwt_secret: str | None = None
    human_jwt_issuer: str | None = None
    human_jwt_audience: str | None = None
    human_jwt_required_role: str = "authenticated"
    authenticated_write_abuse: AuthenticatedWriteAbuseSettings = field(
        default_factory=AuthenticatedWriteAbuseSettings
    )


def get_settings(
    *,
    env: Mapping[str, str] | None = None,
    env_file: Path | None = None,
    worktree_path: Path | None = None,
) -> Settings:
    current_env = dict(os.environ if env is None else env)
    resolved_env_file = env_file or Path(current_env.get(ENV_FILE_VARIABLE, DEFAULT_ENV_FILE))
    file_values = _load_env_file(resolved_env_file)
    database_url = current_env.get("DATABASE_URL") or file_values.get(
        "DATABASE_URL",
        DEFAULT_DATABASE_URL,
    )
    database_url = derive_worktree_database_url(
        database_url,
        worktree_path=worktree_path or Path.cwd(),
        lane=current_env.get(DB_LANE_VARIABLE),
    )
    browser_origins = _load_browser_origins(
        current_env.get(BROWSER_ORIGINS_VARIABLE) or file_values.get(BROWSER_ORIGINS_VARIABLE)
    )
    return Settings(
        database_url=database_url,
        match_registry_backend=current_env.get(MATCH_REGISTRY_BACKEND_VARIABLE, "memory"),
        allowed_browser_origins=browser_origins,
        human_jwt_secret=current_env.get("HUMAN_JWT_SECRET") or file_values.get("HUMAN_JWT_SECRET"),
        human_jwt_issuer=current_env.get("HUMAN_JWT_ISSUER") or file_values.get("HUMAN_JWT_ISSUER"),
        human_jwt_audience=current_env.get("HUMAN_JWT_AUDIENCE")
        or file_values.get("HUMAN_JWT_AUDIENCE"),
        human_jwt_required_role=current_env.get("HUMAN_JWT_REQUIRED_ROLE")
        or file_values.get("HUMAN_JWT_REQUIRED_ROLE")
        or "authenticated",
        authenticated_write_abuse=AuthenticatedWriteAbuseSettings(
            max_body_bytes=_load_positive_int(
                value=current_env.get(AUTHENTICATED_WRITE_MAX_BODY_BYTES_VARIABLE)
                or file_values.get(AUTHENTICATED_WRITE_MAX_BODY_BYTES_VARIABLE),
                default=DEFAULT_AUTHENTICATED_WRITE_MAX_BODY_BYTES,
                variable_name=AUTHENTICATED_WRITE_MAX_BODY_BYTES_VARIABLE,
            ),
            rate_limit=_load_positive_int(
                value=current_env.get(AUTHENTICATED_WRITE_RATE_LIMIT_VARIABLE)
                or file_values.get(AUTHENTICATED_WRITE_RATE_LIMIT_VARIABLE),
                default=DEFAULT_AUTHENTICATED_WRITE_RATE_LIMIT,
                variable_name=AUTHENTICATED_WRITE_RATE_LIMIT_VARIABLE,
            ),
            rate_window_seconds=_load_positive_int(
                value=current_env.get(AUTHENTICATED_WRITE_RATE_WINDOW_SECONDS_VARIABLE)
                or file_values.get(AUTHENTICATED_WRITE_RATE_WINDOW_SECONDS_VARIABLE),
                default=DEFAULT_AUTHENTICATED_WRITE_RATE_WINDOW_SECONDS,
                variable_name=AUTHENTICATED_WRITE_RATE_WINDOW_SECONDS_VARIABLE,
            ),
        ),
    )


def derive_worktree_database_url(
    database_url: str,
    *,
    worktree_path: Path,
    lane: str | None = None,
) -> str:
    normalized_database_url = normalize_database_url(database_url)
    url = make_url(normalized_database_url)
    if url.get_backend_name() != "postgresql" or url.database is None:
        return normalized_database_url

    identity = _build_worktree_identity(worktree_path=worktree_path, lane=lane)
    base_database_name = _slugify_identifier(url.database) or "iron_council"
    database_name = _limit_identifier_length(f"{base_database_name}_{identity}")
    return url.set(database=database_name).render_as_string(hide_password=False)


def normalize_database_url(database_url: str) -> str:
    url = make_url(database_url)
    if url.get_backend_name() != "postgresql" or url.drivername != "postgresql":
        return database_url
    return url.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)


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


def _load_browser_origins(configured_value: str | None) -> tuple[str, ...]:
    if configured_value is None:
        return DEFAULT_BROWSER_ORIGINS

    parsed_origins = tuple(
        origin.strip() for origin in configured_value.split(",") if origin.strip()
    )
    if parsed_origins:
        return parsed_origins
    return DEFAULT_BROWSER_ORIGINS


def _load_positive_int(*, default: int, variable_name: str, value: str | None) -> int:
    if value is None:
        return default

    parsed_value = int(value)
    if parsed_value <= 0:
        raise ValueError(f"{variable_name} must be a positive integer.")
    return parsed_value


def _build_worktree_identity(*, worktree_path: Path, lane: str | None) -> str:
    resolved_path = worktree_path.resolve()
    worktree_slug = _slugify_identifier(resolved_path.name) or "workspace"
    digest = hashlib.sha1(resolved_path.as_posix().encode("utf-8")).hexdigest()[:8]
    identity = f"{worktree_slug}_{digest}"
    if lane:
        lane_slug = _slugify_identifier(lane)
        if lane_slug:
            identity = f"{identity}_{lane_slug}"
    return _limit_identifier_length(identity)


def _slugify_identifier(value: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value.lower())).strip("_")


def _limit_identifier_length(value: str) -> str:
    return value[:_MAX_IDENTIFIER_LENGTH].rstrip("_")
