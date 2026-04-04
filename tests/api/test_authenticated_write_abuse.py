from __future__ import annotations

from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from server.agent_registry import InMemoryMatchRegistry, build_seeded_agent_api_key
from server.db.testing import provision_seeded_database
from server.main import create_app
from server.registry_seed_data import build_seeded_match_records


def _human_jwt_token(
    *,
    user_id: str,
    role: str = "authenticated",
    secret: str = "test-human-secret-key-material-1234",
    issuer: str = "https://supabase.test/auth/v1",
    audience: str = "authenticated",
) -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "role": role,
            "iss": issuer,
            "aud": audience,
            "exp": datetime.now(tz=UTC) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )


def _auth_headers_for_human(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_human_jwt_token(user_id=user_id)}"}


@pytest.mark.asyncio
async def test_authenticated_write_routes_reject_oversized_request_bodies_with_structured_413() -> (
    None
):
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    app = create_app(
        match_registry=registry,
        settings_override={
            "HUMAN_JWT_SECRET": "test-human-secret-key-material-1234",
            "HUMAN_JWT_ISSUER": "https://supabase.test/auth/v1",
            "HUMAN_JWT_AUDIENCE": "authenticated",
            "HUMAN_JWT_REQUIRED_ROLE": "authenticated",
            "IRON_COUNCIL_AUTHENTICATED_WRITE_MAX_BODY_BYTES": "128",
        },
    )

    oversized_payload = (
        b'{"match_id":"match-alpha","tick":142,"orders":{"movements":[],'
        b'"recruitment":[{"city":"manchester","troops":5}],"upgrades":[],"transfers":[]}}'
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/matches/match-alpha/orders",
            content=oversized_payload,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": build_seeded_agent_api_key("agent-player-2"),
            },
        )

    assert response.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    assert response.json() == {
        "error": {
            "code": "payload_too_large",
            "message": (
                "Authenticated write request body exceeds the configured limit of 128 bytes."
            ),
        }
    }


@pytest.mark.asyncio
async def test_authenticated_write_routes_rate_limit_repeated_human_write_requests_with_structured_429(  # noqa: E501
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'authenticated-write-rate-limit.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    app = create_app(
        settings_override={
            "DATABASE_URL": database_url,
            "IRON_COUNCIL_MATCH_REGISTRY_BACKEND": "db",
            "HUMAN_JWT_SECRET": "test-human-secret-key-material-1234",
            "HUMAN_JWT_ISSUER": "https://supabase.test/auth/v1",
            "HUMAN_JWT_AUDIENCE": "authenticated",
            "HUMAN_JWT_REQUIRED_ROLE": "authenticated",
            "IRON_COUNCIL_AUTHENTICATED_WRITE_RATE_LIMIT": "2",
            "IRON_COUNCIL_AUTHENTICATED_WRITE_RATE_WINDOW_SECONDS": "60",
        }
    )
    human_headers = _auth_headers_for_human("00000000-0000-0000-0000-000000000301")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        first_response = await client.post("/api/v1/account/api-keys", headers=human_headers)
        second_response = await client.post("/api/v1/account/api-keys", headers=human_headers)
        third_response = await client.post("/api/v1/account/api-keys", headers=human_headers)

    assert first_response.status_code == HTTPStatus.CREATED
    assert second_response.status_code == HTTPStatus.CREATED
    assert third_response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert third_response.json() == {
        "error": {
            "code": "rate_limit_exceeded",
            "message": (
                "Authenticated write burst limit exceeded for this caller on this route. "
                "Retry after the current 60-second window."
            ),
        }
    }


@pytest.mark.asyncio
async def test_rate_limit_uses_human_identity_when_invalid_api_key_header_is_present(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'authenticated-write-rate-limit-fallback.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    app = create_app(
        settings_override={
            "DATABASE_URL": database_url,
            "IRON_COUNCIL_MATCH_REGISTRY_BACKEND": "db",
            "HUMAN_JWT_SECRET": "test-human-secret-key-material-1234",
            "HUMAN_JWT_ISSUER": "https://supabase.test/auth/v1",
            "HUMAN_JWT_AUDIENCE": "authenticated",
            "HUMAN_JWT_REQUIRED_ROLE": "authenticated",
            "IRON_COUNCIL_AUTHENTICATED_WRITE_RATE_LIMIT": "1",
            "IRON_COUNCIL_AUTHENTICATED_WRITE_RATE_WINDOW_SECONDS": "60",
        }
    )
    human_headers = {
        **_auth_headers_for_human("00000000-0000-0000-0000-000000000301"),
        "X-API-Key": "bogus-api-key",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        first_response = await client.post("/api/v1/account/api-keys", headers=human_headers)
        second_response = await client.post("/api/v1/account/api-keys", headers=human_headers)

    assert first_response.status_code == HTTPStatus.CREATED
    assert second_response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert second_response.json() == {
        "error": {
            "code": "rate_limit_exceeded",
            "message": (
                "Authenticated write burst limit exceeded for this caller on this route. "
                "Retry after the current 60-second window."
            ),
        }
    }


@pytest.mark.asyncio
async def test_mixed_auth_write_routes_preserve_invalid_api_key_semantics_with_bearer_present() -> (
    None
):
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    app = create_app(
        match_registry=registry,
        settings_override={
            "HUMAN_JWT_SECRET": "test-human-secret-key-material-1234",
            "HUMAN_JWT_ISSUER": "https://supabase.test/auth/v1",
            "HUMAN_JWT_AUDIENCE": "authenticated",
            "HUMAN_JWT_REQUIRED_ROLE": "authenticated",
            "IRON_COUNCIL_AUTHENTICATED_WRITE_RATE_LIMIT": "1",
            "IRON_COUNCIL_AUTHENTICATED_WRITE_RATE_WINDOW_SECONDS": "60",
        },
    )
    mixed_headers = {
        **_auth_headers_for_human("00000000-0000-0000-0000-000000000301"),
        "X-API-Key": "bogus-api-key",
    }
    submission = {
        "match_id": "match-alpha",
        "tick": 142,
        "orders": {
            "movements": [],
            "recruitment": [],
            "upgrades": [],
            "transfers": [],
        },
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        first_response = await client.post(
            "/api/v1/matches/match-alpha/orders",
            json=submission,
            headers=mixed_headers,
        )
        second_response = await client.post(
            "/api/v1/matches/match-alpha/orders",
            json=submission,
            headers=mixed_headers,
        )

    expected_error = {
        "error": {
            "code": "invalid_api_key",
            "message": "A valid active X-API-Key header is required.",
        }
    }
    assert first_response.status_code == HTTPStatus.UNAUTHORIZED
    assert first_response.json() == expected_error
    assert second_response.status_code == HTTPStatus.UNAUTHORIZED
    assert second_response.json() == expected_error
