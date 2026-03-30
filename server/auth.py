from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

import jwt
from jwt import InvalidTokenError

from server.settings import Settings


def hash_api_key(api_key: str) -> str:
    return sha256(api_key.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class AuthenticatedHumanContext:
    user_id: str
    role: str


class HumanJwtValidationError(Exception):
    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def extract_bearer_token(authorization: str) -> str:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HumanJwtValidationError(
            code="invalid_human_token",
            message="A valid human Bearer token is required.",
        )
    return token


def validate_human_jwt(token: str, *, settings: Settings) -> AuthenticatedHumanContext:
    if not settings.human_jwt_secret:
        raise HumanJwtValidationError(
            code="invalid_human_token",
            message="A valid human Bearer token is required.",
        )

    try:
        claims = jwt.decode(
            token,
            settings.human_jwt_secret,
            algorithms=["HS256"],
            audience=settings.human_jwt_audience,
            issuer=settings.human_jwt_issuer,
        )
    except InvalidTokenError as exc:
        raise HumanJwtValidationError(
            code="invalid_human_token",
            message="A valid human Bearer token is required.",
        ) from exc

    user_id = claims.get("sub")
    role = claims.get("role")
    if not isinstance(user_id, str) or not user_id:
        raise HumanJwtValidationError(
            code="invalid_human_token",
            message="A valid human Bearer token is required.",
        )
    if role != settings.human_jwt_required_role:
        raise HumanJwtValidationError(
            code="invalid_human_token_role",
            message=f"Human JWT role claim must be '{settings.human_jwt_required_role}'.",
        )
    return AuthenticatedHumanContext(user_id=user_id, role=role)
