from __future__ import annotations

from datetime import UTC, datetime
from secrets import token_urlsafe
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from server.auth import hash_api_key
from server.db.identity import resolve_human_elo_rating
from server.db.models import ApiKey
from server.models.api import OwnedApiKeySummary


def list_owned_api_keys(*, database_url: str, user_id: str) -> list[OwnedApiKeySummary]:
    from sqlalchemy import create_engine

    engine = create_engine(database_url)
    with Session(engine) as session:
        rows = session.scalars(
            select(ApiKey)
            .where(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.asc(), ApiKey.id.asc())
        ).all()
        return [_build_summary(row) for row in rows]


def create_owned_api_key(*, database_url: str, user_id: str) -> tuple[str, OwnedApiKeySummary]:
    from sqlalchemy import create_engine

    engine = create_engine(database_url)
    with Session(engine) as session:
        raw_key = _generate_unique_api_key(session=session)
        api_key = ApiKey(
            id=str(uuid4()),
            user_id=user_id,
            key_hash=hash_api_key(raw_key),
            elo_rating=resolve_human_elo_rating(session=session, user_id=user_id),
            is_active=True,
            created_at=datetime.now(tz=UTC),
        )
        session.add(api_key)
        session.commit()
        session.refresh(api_key)
        return raw_key, _build_summary(api_key)


def revoke_owned_api_key(
    *,
    database_url: str,
    user_id: str,
    key_id: str,
) -> OwnedApiKeySummary | None:
    from sqlalchemy import create_engine

    engine = create_engine(database_url)
    with Session(engine) as session:
        api_key = session.scalar(
            select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
        )
        if api_key is None:
            return None

        api_key.is_active = False
        session.commit()
        session.refresh(api_key)
        return _build_summary(api_key)


def _generate_unique_api_key(*, session: Session) -> str:
    while True:
        raw_key = f"iron_{token_urlsafe(24)}"
        existing = session.scalar(select(ApiKey.id).where(ApiKey.key_hash == hash_api_key(raw_key)))
        if existing is None:
            return raw_key


def _build_summary(api_key: ApiKey) -> OwnedApiKeySummary:
    return OwnedApiKeySummary(
        key_id=str(api_key.id),
        elo_rating=int(api_key.elo_rating),
        is_active=bool(api_key.is_active),
        created_at=api_key.created_at,
    )
