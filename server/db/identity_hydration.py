from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Literal, cast

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from server.agent_registry import (
    AuthenticatedAgentKeyRecord,
    build_seeded_profiles_by_key_hash,
)
from server.db.identity import parse_human_actor_id, resolve_loaded_agent_identity
from server.db.models import ApiKey, Match, Player, PlayerMatchSettlement, Treaty
from server.db.player_ids import build_human_actor_id, build_persisted_player_mapping
from server.db.rating_settlement import SettlementAggregate, load_settlement_aggregates_by_identity
from server.models.api import (
    AgentProfileHistory,
    AgentProfileRating,
    AgentProfileResponse,
    HumanProfileResponse,
    ProfileTreatyHistoryRecord,
    ProfileTreatyReputation,
    ProfileTreatyReputationSummary,
    TreatyStatus,
    empty_treaty_reputation,
)
from server.models.state import MatchState


def load_agent_profiles_by_match(
    *,
    matches: Sequence[Match],
    player_rows: Sequence[Player],
    api_key_rows: Sequence[ApiKey],
    settlement_rows: Sequence[PlayerMatchSettlement] = (),
    treaty_rows: Sequence[Treaty] = (),
) -> dict[str, list[AgentProfileResponse]]:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    agent_player_rows = [player for player in player_rows if player.is_agent]
    completed_match_ids = {
        str(match.id) for match in matches if getattr(match, "status", None) == "completed"
    }
    profiles_by_agent_id = _build_agent_profiles_by_agent_id(
        player_rows=agent_player_rows,
        all_player_rows=player_rows,
        api_key_rows=api_key_rows,
        settlement_rows=settlement_rows,
        treaty_rows=treaty_rows,
        completed_match_ids=completed_match_ids,
    )
    profiles_by_identity = {profile.agent_id: profile for profile in profiles_by_agent_id.values()}
    api_keys_by_id = {str(api_key.id): api_key for api_key in api_key_rows}
    seeded_profiles_by_key_hash = build_seeded_profiles_by_key_hash()
    for player in player_rows:
        players_by_match[str(player.match_id)].append(player)

    profiles_by_match: dict[str, list[AgentProfileResponse]] = {}
    for match in matches:
        match_id = str(match.id)
        loaded_profiles: dict[str, AgentProfileResponse] = {}
        for player in sorted(
            players_by_match.get(match_id, []), key=lambda persisted: str(persisted.id)
        ):
            if not player.is_agent:
                continue
            api_key = (
                api_keys_by_id.get(str(player.api_key_id))
                if player.api_key_id is not None
                else None
            )
            agent_identity = resolve_loaded_agent_identity(
                player=player,
                api_key=api_key,
                seeded_profiles_by_key_hash=seeded_profiles_by_key_hash,
            )
            loaded_profiles[agent_identity.agent_id] = profiles_by_identity[agent_identity.agent_id]
        profiles_by_match[match_id] = [
            loaded_profiles[agent_id] for agent_id in sorted(loaded_profiles)
        ]

    return profiles_by_match


def get_agent_profile_from_db(*, database_url: str, agent_id: str) -> AgentProfileResponse | None:
    engine = create_engine(database_url)
    with Session(engine) as session:
        completed_match_ids = {
            str(match_id)
            for match_id in session.scalars(
                select(Match.id).where(Match.status == "completed").order_by(Match.id)
            ).all()
        }
        player_rows = session.scalars(select(Player).order_by(Player.match_id, Player.id)).all()
        api_key_ids = [
            player.api_key_id
            for player in player_rows
            if player.is_agent and player.api_key_id is not None
        ]
        api_key_rows = (
            session.scalars(
                select(ApiKey).where(ApiKey.id.in_(api_key_ids)).order_by(ApiKey.id)
            ).all()
            if api_key_ids
            else []
        )
        settlement_rows = session.scalars(
            select(PlayerMatchSettlement)
            .where(PlayerMatchSettlement.is_agent.is_(True))
            .order_by(PlayerMatchSettlement.settled_at, PlayerMatchSettlement.player_id)
        ).all()
        treaty_rows = session.scalars(select(Treaty).order_by(Treaty.signed_tick, Treaty.id)).all()

    profiles_by_agent_id = _build_agent_profiles_by_agent_id(
        player_rows=[player for player in player_rows if player.is_agent],
        all_player_rows=player_rows,
        api_key_rows=api_key_rows,
        settlement_rows=settlement_rows,
        treaty_rows=treaty_rows,
        completed_match_ids=completed_match_ids,
    )
    return profiles_by_agent_id.get(agent_id)


def get_human_profile_from_db(*, database_url: str, human_id: str) -> HumanProfileResponse | None:
    user_id = parse_human_actor_id(human_id)
    if user_id is None:
        return None

    engine = create_engine(database_url)
    with Session(engine) as session:
        completed_match_ids = {
            str(match_id)
            for match_id in session.scalars(
                select(Match.id).where(Match.status == "completed").order_by(Match.id)
            ).all()
        }
        settlement_rows = session.scalars(
            select(PlayerMatchSettlement)
            .where(
                PlayerMatchSettlement.is_agent.is_(False),
                PlayerMatchSettlement.user_id == user_id,
            )
            .order_by(PlayerMatchSettlement.settled_at, PlayerMatchSettlement.player_id)
        ).all()
        player_rows = session.scalars(select(Player).order_by(Player.match_id, Player.id)).all()
        api_key_ids = [
            player.api_key_id
            for player in player_rows
            if player.is_agent and player.api_key_id is not None
        ]
        api_key_rows = (
            session.scalars(
                select(ApiKey).where(ApiKey.id.in_(api_key_ids)).order_by(ApiKey.id)
            ).all()
            if api_key_ids
            else []
        )
        treaty_rows = session.scalars(select(Treaty).order_by(Treaty.signed_tick, Treaty.id)).all()

    settlement_aggregate = load_settlement_aggregates_by_identity(settlement_rows).get(human_id)
    treaty_reputation_by_identity = _build_treaty_reputation_by_identity(
        player_rows=player_rows,
        api_key_rows=api_key_rows,
        treaty_rows=treaty_rows,
        completed_match_ids=completed_match_ids,
    )
    human_player_rows = [
        player for player in player_rows if not player.is_agent and str(player.user_id) == user_id
    ]
    if settlement_aggregate is not None:
        return HumanProfileResponse(
            human_id=human_id,
            display_name=settlement_aggregate.display_name,
            rating=AgentProfileRating(
                elo=settlement_aggregate.elo,
                provisional=settlement_aggregate.provisional,
            ),
            history=AgentProfileHistory(
                matches_played=settlement_aggregate.matches_played,
                wins=settlement_aggregate.wins,
                losses=settlement_aggregate.losses,
                draws=settlement_aggregate.draws,
            ),
            treaty_reputation=treaty_reputation_by_identity.get(
                human_id, empty_treaty_reputation()
            ),
        )

    player = next(iter(human_player_rows), None)
    if player is None:
        return None

    return HumanProfileResponse(
        human_id=build_human_actor_id(str(player.user_id)),
        display_name=player.display_name,
        rating=AgentProfileRating(elo=int(player.elo_rating), provisional=True),
        history=AgentProfileHistory(matches_played=0, wins=0, losses=0, draws=0),
        treaty_reputation=treaty_reputation_by_identity.get(human_id, empty_treaty_reputation()),
    )


def load_authenticated_agent_keys_by_match(
    *,
    matches: Sequence[Match],
    player_rows: Sequence[Player],
    api_key_rows: Sequence[ApiKey],
) -> dict[str, list[AuthenticatedAgentKeyRecord]]:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    api_keys_by_id = {str(api_key.id): api_key for api_key in api_key_rows}
    seeded_profiles_by_key_hash = build_seeded_profiles_by_key_hash()
    for player in player_rows:
        players_by_match[str(player.match_id)].append(player)

    authenticated_keys_by_match: dict[str, list[AuthenticatedAgentKeyRecord]] = {}
    for match in matches:
        match_id = str(match.id)
        state = MatchState.model_validate(match.state)
        persisted_player_mapping = build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players_by_match.get(match_id, []),
        )
        authenticated_keys = [
            AuthenticatedAgentKeyRecord(
                agent_id=resolve_loaded_agent_identity(
                    player=player,
                    api_key=api_key,
                    seeded_profiles_by_key_hash=seeded_profiles_by_key_hash,
                ).agent_id,
                key_hash=api_key.key_hash,
                is_active=bool(api_key.is_active),
            )
            for player in sorted(
                players_by_match.get(match_id, []),
                key=lambda persisted: str(persisted.id),
            )
            if player.is_agent
            and player.api_key_id is not None
            and (api_key := api_keys_by_id.get(str(player.api_key_id))) is not None
            and persisted_player_mapping.get(str(player.id)) is not None
        ]
        if authenticated_keys:
            authenticated_keys_by_match[match_id] = authenticated_keys

    return authenticated_keys_by_match


def load_joined_agents_by_match(
    *,
    matches: Sequence[Match],
    player_rows: Sequence[Player],
    api_key_rows: Sequence[ApiKey],
) -> dict[str, dict[str, str]]:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    api_keys_by_id = {str(api_key.id): api_key for api_key in api_key_rows}
    seeded_profiles_by_key_hash = build_seeded_profiles_by_key_hash()
    for player in player_rows:
        players_by_match[str(player.match_id)].append(player)

    joined_agents_by_match: dict[str, dict[str, str]] = {}
    for match in matches:
        match_id = str(match.id)
        state = MatchState.model_validate(match.state)
        persisted_player_mapping = build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players_by_match.get(match_id, []),
        )
        joined_agents = {
            resolve_loaded_agent_identity(
                player=player,
                api_key=(
                    api_keys_by_id.get(str(player.api_key_id))
                    if player.api_key_id is not None
                    else None
                ),
                seeded_profiles_by_key_hash=seeded_profiles_by_key_hash,
            ).agent_id: canonical_player_id
            for player in players_by_match.get(match_id, [])
            if player.is_agent
            and (canonical_player_id := persisted_player_mapping.get(str(player.id))) is not None
        }
        if joined_agents:
            joined_agents_by_match[match_id] = joined_agents

    return joined_agents_by_match


def load_joined_humans_by_match(
    *,
    matches: Sequence[Match],
    player_rows: Sequence[Player],
) -> dict[str, dict[str, str]]:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    for player in player_rows:
        players_by_match[str(player.match_id)].append(player)

    joined_humans_by_match: dict[str, dict[str, str]] = {}
    for match in matches:
        match_id = str(match.id)
        state = MatchState.model_validate(match.state)
        persisted_player_mapping = build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players_by_match.get(match_id, []),
        )
        joined_humans = {
            str(player.user_id): canonical_player_id
            for player in players_by_match.get(match_id, [])
            if not player.is_agent
            and (canonical_player_id := persisted_player_mapping.get(str(player.id))) is not None
        }
        if joined_humans:
            joined_humans_by_match[match_id] = joined_humans

    return joined_humans_by_match


def load_public_competitor_kinds_by_match(
    *,
    matches: Sequence[Match],
    player_rows: Sequence[Player],
) -> dict[str, dict[str, Literal["human", "agent"]]]:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    for player in player_rows:
        players_by_match[str(player.match_id)].append(player)

    competitor_kinds_by_match: dict[str, dict[str, Literal["human", "agent"]]] = {}
    for match in matches:
        match_id = str(match.id)
        state = MatchState.model_validate(match.state)
        persisted_player_mapping = build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players_by_match.get(match_id, []),
        )
        competitor_kinds: dict[str, Literal["human", "agent"]] = {
            canonical_player_id: ("agent" if player.is_agent else "human")
            for player in players_by_match.get(match_id, [])
            if (canonical_player_id := persisted_player_mapping.get(str(player.id))) is not None
        }
        if competitor_kinds:
            competitor_kinds_by_match[match_id] = competitor_kinds

    return competitor_kinds_by_match


def _build_agent_profiles_by_agent_id(
    *,
    player_rows: Sequence[Player],
    all_player_rows: Sequence[Player],
    api_key_rows: Sequence[ApiKey],
    settlement_rows: Sequence[PlayerMatchSettlement],
    treaty_rows: Sequence[Treaty],
    completed_match_ids: set[str],
) -> dict[str, AgentProfileResponse]:
    api_keys_by_id = {str(api_key.id): api_key for api_key in api_key_rows}
    seeded_profiles_by_key_hash = build_seeded_profiles_by_key_hash()
    settlement_aggregates_by_identity = load_settlement_aggregates_by_identity(
        [settlement for settlement in settlement_rows if settlement.is_agent]
    )
    treaty_reputation_by_identity = _build_treaty_reputation_by_identity(
        player_rows=all_player_rows,
        api_key_rows=api_key_rows,
        treaty_rows=treaty_rows,
        completed_match_ids=completed_match_ids,
    )

    profiles_by_agent_id: dict[str, AgentProfileResponse] = {}
    for player in sorted(player_rows, key=lambda persisted: str(persisted.id)):
        if not player.is_agent:
            continue
        api_key = (
            api_keys_by_id.get(str(player.api_key_id)) if player.api_key_id is not None else None
        )
        agent_identity = resolve_loaded_agent_identity(
            player=player,
            api_key=api_key,
            seeded_profiles_by_key_hash=seeded_profiles_by_key_hash,
        )
        settlement_aggregate = settlement_aggregates_by_identity.get(
            _player_competitor_identity(player)
        )
        profiles_by_agent_id[agent_identity.agent_id] = _build_agent_profile(
            agent_id=agent_identity.agent_id,
            is_seeded=agent_identity.is_seeded,
            player=player,
            settlement_aggregate=settlement_aggregate,
            treaty_reputation=treaty_reputation_by_identity.get(
                agent_identity.agent_id, empty_treaty_reputation()
            ),
        )
    return profiles_by_agent_id


def _build_agent_profile(
    *,
    agent_id: str,
    is_seeded: bool,
    player: Player,
    settlement_aggregate: SettlementAggregate | None,
    treaty_reputation: ProfileTreatyReputation,
) -> AgentProfileResponse:
    if settlement_aggregate is None:
        return AgentProfileResponse(
            agent_id=agent_id,
            display_name=player.display_name,
            is_seeded=is_seeded,
            rating=AgentProfileRating(elo=int(player.elo_rating), provisional=True),
            history=AgentProfileHistory(matches_played=0, wins=0, losses=0, draws=0),
            treaty_reputation=treaty_reputation,
        )

    return AgentProfileResponse(
        agent_id=agent_id,
        display_name=settlement_aggregate.display_name,
        is_seeded=is_seeded,
        rating=AgentProfileRating(
            elo=settlement_aggregate.elo,
            provisional=settlement_aggregate.provisional,
        ),
        history=AgentProfileHistory(
            matches_played=settlement_aggregate.matches_played,
            wins=settlement_aggregate.wins,
            losses=settlement_aggregate.losses,
            draws=settlement_aggregate.draws,
        ),
        treaty_reputation=treaty_reputation,
    )


def _build_treaty_reputation_by_identity(
    *,
    player_rows: Sequence[Player],
    api_key_rows: Sequence[ApiKey],
    treaty_rows: Sequence[Treaty],
    completed_match_ids: set[str],
) -> dict[str, ProfileTreatyReputation]:
    if not treaty_rows:
        return {}

    api_keys_by_id = {str(api_key.id): api_key for api_key in api_key_rows}
    seeded_profiles_by_key_hash = build_seeded_profiles_by_key_hash()
    identity_by_player_id: dict[str, str] = {}
    display_name_by_player_id: dict[str, str] = {}
    for player in sorted(player_rows, key=lambda persisted: str(persisted.id)):
        identity = _public_competitor_identity(
            player=player,
            api_key=(
                api_keys_by_id.get(str(player.api_key_id))
                if player.api_key_id is not None
                else None
            ),
            seeded_profiles_by_key_hash=seeded_profiles_by_key_hash,
        )
        identity_by_player_id[str(player.id)] = identity
        display_name_by_player_id[str(player.id)] = player.display_name

    summaries_by_identity: dict[str, ProfileTreatyReputationSummary] = {}
    history_by_identity: dict[str, list[ProfileTreatyHistoryRecord]] = defaultdict(list)
    for treaty in sorted(
        treaty_rows, key=lambda persisted: (persisted.signed_tick, str(persisted.id))
    ):
        player_a_id = str(treaty.player_a_id)
        player_b_id = str(treaty.player_b_id)
        if player_a_id not in identity_by_player_id or player_b_id not in identity_by_player_id:
            continue

        player_a_identity = identity_by_player_id[player_a_id]
        player_b_identity = identity_by_player_id[player_b_id]
        player_a_display_name = display_name_by_player_id[player_a_id]
        player_b_display_name = display_name_by_player_id[player_b_id]

        _record_treaty_reputation(
            identity=player_a_identity,
            counterparty_display_name=player_b_display_name,
            treaty=treaty,
            profile_break_status="broken_by_a",
            completed_match_ids=completed_match_ids,
            summaries_by_identity=summaries_by_identity,
            history_by_identity=history_by_identity,
        )
        _record_treaty_reputation(
            identity=player_b_identity,
            counterparty_display_name=player_a_display_name,
            treaty=treaty,
            profile_break_status="broken_by_b",
            completed_match_ids=completed_match_ids,
            summaries_by_identity=summaries_by_identity,
            history_by_identity=history_by_identity,
        )

    return {
        identity: ProfileTreatyReputation(
            summary=summary,
            history=history_by_identity.get(identity, []),
        )
        for identity, summary in summaries_by_identity.items()
    }


def _record_treaty_reputation(
    *,
    identity: str,
    counterparty_display_name: str,
    treaty: Treaty,
    profile_break_status: TreatyStatus,
    completed_match_ids: set[str],
    summaries_by_identity: dict[str, ProfileTreatyReputationSummary],
    history_by_identity: dict[str, list[ProfileTreatyHistoryRecord]],
) -> None:
    history_status: TreatyStatus
    summary = summaries_by_identity.setdefault(
        identity,
        ProfileTreatyReputationSummary(
            signed=0,
            active=0,
            honored=0,
            withdrawn=0,
            broken_by_self=0,
            broken_by_counterparty=0,
        ),
    )
    summary.signed += 1
    if treaty.status == "active" and str(treaty.match_id) in completed_match_ids:
        summary.honored += 1
        history_status = "honored"
    elif treaty.status == "active":
        summary.active += 1
        history_status = "active"
    elif treaty.status == "withdrawn":
        summary.withdrawn += 1
        history_status = "withdrawn"
    elif treaty.status in {"broken_by_a", "broken_by_b"}:
        if treaty.status == profile_break_status:
            summary.broken_by_self += 1
        else:
            summary.broken_by_counterparty += 1
        history_status = cast("TreatyStatus", treaty.status)
    else:
        history_status = cast("TreatyStatus", treaty.status)

    history_by_identity[identity].append(
        ProfileTreatyHistoryRecord(
            match_id=str(treaty.match_id),
            counterparty_display_name=counterparty_display_name,
            treaty_type=cast("Literal['non_aggression', 'defensive', 'trade']", treaty.treaty_type),
            status=history_status,
            signed_tick=treaty.signed_tick,
            ended_tick=treaty.broken_tick,
            broken_by_self=treaty.status == profile_break_status,
        )
    )


def _public_competitor_identity(
    *,
    player: Player,
    api_key: ApiKey | None,
    seeded_profiles_by_key_hash: dict[str, AgentProfileResponse],
) -> str:
    if player.is_agent:
        return resolve_loaded_agent_identity(
            player=player,
            api_key=api_key,
            seeded_profiles_by_key_hash=seeded_profiles_by_key_hash,
        ).agent_id
    return build_human_actor_id(str(player.user_id))


def _player_competitor_identity(player: Player) -> str:
    if player.api_key_id is not None:
        return f"agent:{player.api_key_id}"
    return f"agent-user:{player.user_id}"


__all__ = [
    "get_agent_profile_from_db",
    "get_human_profile_from_db",
    "load_agent_profiles_by_match",
    "load_authenticated_agent_keys_by_match",
    "load_joined_agents_by_match",
    "load_joined_humans_by_match",
    "load_public_competitor_kinds_by_match",
]
