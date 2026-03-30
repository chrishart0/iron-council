from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from server.auth import (
    AuthenticatedHumanContext,
    HumanJwtValidationError,
    extract_bearer_token,
    validate_human_jwt,
)
from server.settings import Settings


def _settings() -> Settings:
    return Settings(
        database_url="sqlite+pysqlite:///tmp/test.db",
        human_jwt_secret="test-human-secret-key-material-1234",
        human_jwt_issuer="https://supabase.test/auth/v1",
        human_jwt_audience="authenticated",
        human_jwt_required_role="authenticated",
    )


def _human_token(
    *,
    sub: str = "00000000-0000-0000-0000-000000000301",
    role: str = "authenticated",
    issuer: str = "https://supabase.test/auth/v1",
    audience: str = "authenticated",
    secret: str = "test-human-secret-key-material-1234",
) -> str:
    return jwt.encode(
        {
            "sub": sub,
            "role": role,
            "iss": issuer,
            "aud": audience,
            "exp": datetime.now(tz=UTC) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )


def test_extract_bearer_token_requires_bearer_scheme() -> None:
    assert extract_bearer_token("Bearer token-value") == "token-value"

    with pytest.raises(HumanJwtValidationError) as exc_info:
        extract_bearer_token("Basic token-value")

    assert exc_info.value.code == "invalid_human_token"


def test_validate_human_jwt_returns_authenticated_identity() -> None:
    context = validate_human_jwt(_human_token(), settings=_settings())

    assert context == AuthenticatedHumanContext(
        user_id="00000000-0000-0000-0000-000000000301",
        role="authenticated",
    )


def test_validate_human_jwt_rejects_wrong_role_claim() -> None:
    with pytest.raises(HumanJwtValidationError) as exc_info:
        validate_human_jwt(_human_token(role="service_role"), settings=_settings())

    assert exc_info.value.code == "invalid_human_token_role"


def test_validate_human_jwt_rejects_invalid_signature() -> None:
    with pytest.raises(HumanJwtValidationError) as exc_info:
        validate_human_jwt(
            _human_token(secret="wrong-secret-key-material-56789012"),
            settings=_settings(),
        )

    assert exc_info.value.code == "invalid_human_token"


def test_validate_human_jwt_rejects_missing_secret_configuration() -> None:
    with pytest.raises(HumanJwtValidationError) as exc_info:
        validate_human_jwt(
            _human_token(),
            settings=Settings(
                database_url="sqlite+pysqlite:///tmp/test.db",
                human_jwt_secret=None,
                human_jwt_issuer="https://supabase.test/auth/v1",
                human_jwt_audience="authenticated",
                human_jwt_required_role="authenticated",
            ),
        )

    assert exc_info.value.code == "invalid_human_token"


def test_validate_human_jwt_rejects_missing_subject_claim() -> None:
    token = jwt.encode(
        {
            "role": "authenticated",
            "iss": "https://supabase.test/auth/v1",
            "aud": "authenticated",
            "exp": datetime.now(tz=UTC) + timedelta(minutes=5),
        },
        "test-human-secret-key-material-1234",
        algorithm="HS256",
    )

    with pytest.raises(HumanJwtValidationError) as exc_info:
        validate_human_jwt(token, settings=_settings())

    assert exc_info.value.code == "invalid_human_token"
