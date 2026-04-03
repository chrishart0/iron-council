from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, cast

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from server.db.models import AgentEntitlementGrant, ApiKey

AGENT_ENTITLEMENT_REQUIRED_CODE = "agent_entitlement_required"
AGENT_ENTITLEMENT_REQUIRED_MESSAGE = (
    "Authenticated account lacks an active agent entitlement grant with positive "
    "concurrent match allowance."
)


class AgentEntitlementRequiredError(Exception):
    def __init__(self) -> None:
        self.code = AGENT_ENTITLEMENT_REQUIRED_CODE
        self.message = AGENT_ENTITLEMENT_REQUIRED_MESSAGE
        super().__init__(self.message)


AgentEntitlementGrantSource = Literal["manual", "dev"]


@dataclass(frozen=True)
class EffectiveAgentEntitlement:
    user_id: str
    is_entitled: bool
    grant_source: AgentEntitlementGrantSource | None
    concurrent_match_allowance: int
    granted_at: datetime | None


@dataclass(frozen=True)
class ApiKeyMatchEntitlement:
    api_key_id: str
    active_match_occupancy: int
    entitlement: EffectiveAgentEntitlement

    @property
    def has_capacity(self) -> bool:
        return self.entitlement.is_entitled and (
            self.active_match_occupancy < self.entitlement.concurrent_match_allowance
        )


def require_agent_entitlement(entitlement: EffectiveAgentEntitlement) -> None:
    if not entitlement.is_entitled:
        raise AgentEntitlementRequiredError()


def resolve_effective_agent_entitlement(
    *,
    session: Session,
    user_id: str,
) -> EffectiveAgentEntitlement:
    grant = session.scalar(
        select(AgentEntitlementGrant)
        .where(
            AgentEntitlementGrant.user_id == user_id,
            AgentEntitlementGrant.is_active.is_(True),
        )
        .order_by(
            desc(AgentEntitlementGrant.concurrent_match_allowance),
            desc(AgentEntitlementGrant.created_at),
            desc(AgentEntitlementGrant.id),
        )
    )
    if grant is None:
        return EffectiveAgentEntitlement(
            user_id=user_id,
            is_entitled=False,
            grant_source=None,
            concurrent_match_allowance=0,
            granted_at=None,
        )

    allowance = int(grant.concurrent_match_allowance)
    return EffectiveAgentEntitlement(
        user_id=user_id,
        is_entitled=allowance > 0,
        grant_source=cast(AgentEntitlementGrantSource, grant.grant_source),
        concurrent_match_allowance=max(allowance, 0),
        granted_at=grant.created_at,
    )


def resolve_api_key_match_entitlement(
    *,
    session: Session,
    api_key_id: str,
    active_match_occupancy: int,
) -> ApiKeyMatchEntitlement:
    api_key = session.get(ApiKey, api_key_id)
    if api_key is None:
        raise ValueError(f"API key '{api_key_id}' was not found.")

    return ApiKeyMatchEntitlement(
        api_key_id=api_key_id,
        active_match_occupancy=active_match_occupancy,
        entitlement=resolve_effective_agent_entitlement(
            session=session,
            user_id=str(api_key.user_id),
        ),
    )
