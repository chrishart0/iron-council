from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from server.agent_registry import (
    AdvancedMatchTick,
    AuthenticatedAgentKeyRecord,
    InMemoryMatchRegistry,
    MatchAlliance,
    MatchAllianceMember,
    MatchRecord,
    build_seeded_agent_profiles,
)
from server.db.models import Alliance, ApiKey, Match, Player, TickLog
from server.models.api import (
    AgentProfileHistory,
    AgentProfileRating,
    AgentProfileResponse,
    CompletedMatchSummary,
    CompletedMatchSummaryListResponse,
    LeaderboardEntry,
    MatchHistoryEntry,
    MatchHistoryResponse,
    MatchListResponse,
    MatchReplayTickResponse,
    MatchSummary,
    PublicLeaderboardResponse,
    PublicMatchDetailResponse,
    PublicMatchRosterRow,
)
from server.models.domain import MatchStatus
from server.models.state import MatchState


class MatchHistoryNotFoundError(KeyError):
    pass


class TickHistoryNotFoundError(KeyError):
    pass


class PublicMatchDetailNotFoundError(KeyError):
    pass


@dataclass
class _LeaderboardAggregate:
    competitor_key: str
    display_name: str
    competitor_kind: Literal["human", "agent"]
    elo: int
    provisional: bool
    matches_played: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0


def load_match_registry_from_database(database_url: str) -> InMemoryMatchRegistry:
    registry = InMemoryMatchRegistry()
    engine = create_engine(database_url)
    with Session(engine) as session:
        matches = session.scalars(select(Match).order_by(Match.id)).all()
        alliance_rows = session.scalars(
            select(Alliance)
            .where(Alliance.dissolved_tick.is_(None))
            .order_by(Alliance.formed_tick, Alliance.id)
        ).all()
        player_rows = session.scalars(select(Player).order_by(Player.match_id, Player.id)).all()
        api_key_rows = session.scalars(select(ApiKey).order_by(ApiKey.id)).all()

        alliances_by_match = _load_persisted_alliances_by_match(
            matches=matches,
            alliance_rows=alliance_rows,
            player_rows=player_rows,
        )
        agent_profiles_by_match = _load_agent_profiles_by_match(
            matches=matches,
            player_rows=player_rows,
        )
        authenticated_keys_by_match = _load_authenticated_agent_keys_by_match(
            matches=matches,
            player_rows=player_rows,
            api_key_rows=api_key_rows,
        )
        joined_agents_by_match = _load_joined_agents_by_match(
            matches=matches,
            player_rows=player_rows,
        )

        for match in matches:
            match_id = str(match.id)
            persisted_alliances = alliances_by_match.get(match_id, [])
            state = MatchState.model_validate(match.state)
            record = MatchRecord(
                match_id=match_id,
                status=MatchStatus(match.status),
                tick_interval_seconds=int(match.config.get("turn_seconds", 0)),
                state=state,
                joinable_player_ids=(
                    sorted(state.players) if match.status == MatchStatus.PAUSED.value else []
                ),
                agent_profiles=agent_profiles_by_match.get(match_id, build_seeded_agent_profiles()),
                joined_agents=joined_agents_by_match.get(match_id, {}),
                alliances=persisted_alliances,
                authenticated_agent_keys=authenticated_keys_by_match.get(match_id, []),
            )
            registry.seed_match(record)

    return registry


def persist_advanced_match_tick(*, database_url: str, advanced_tick: AdvancedMatchTick) -> None:
    engine = create_engine(database_url)
    with Session(engine) as session, session.begin():
        match = session.get(Match, advanced_tick.match_id)
        if match is None:
            raise KeyError(f"Match '{advanced_tick.match_id}' was not found.")

        match.current_tick = advanced_tick.resolved_tick
        match.state = advanced_tick.next_state.model_dump(mode="json")
        session.add(
            TickLog(
                match_id=advanced_tick.match_id,
                tick=advanced_tick.resolved_tick,
                state_snapshot=advanced_tick.next_state.model_dump(mode="json"),
                orders=advanced_tick.accepted_orders.model_dump(mode="json"),
                events=[event.model_dump(mode="json") for event in advanced_tick.events],
            )
        )


def get_match_history(*, database_url: str, match_id: str) -> MatchHistoryResponse:
    engine = create_engine(database_url)
    with Session(engine) as session:
        match = session.get(Match, match_id)
        if match is None:
            raise MatchHistoryNotFoundError(match_id)

        ticks = (
            session.execute(
                select(TickLog.tick)
                .where(TickLog.match_id == match_id)
                .order_by(TickLog.tick, TickLog.id)
            )
            .scalars()
            .all()
        )

    return MatchHistoryResponse(
        match_id=str(match.id),
        status=MatchStatus(match.status),
        current_tick=int(match.current_tick),
        tick_interval_seconds=int(match.config.get("turn_seconds", 0)),
        history=[MatchHistoryEntry(tick=int(tick)) for tick in ticks],
    )


def get_match_replay_tick(
    *, database_url: str, match_id: str, tick: int
) -> MatchReplayTickResponse:
    engine = create_engine(database_url)
    with Session(engine) as session:
        match = session.get(Match, match_id)
        if match is None:
            raise MatchHistoryNotFoundError(match_id)

        tick_row = session.scalar(
            select(TickLog)
            .where(TickLog.match_id == match_id, TickLog.tick == tick)
            .order_by(TickLog.id)
        )
        if tick_row is None:
            raise TickHistoryNotFoundError((match_id, tick))

    return MatchReplayTickResponse(
        match_id=str(match.id),
        tick=int(tick_row.tick),
        state_snapshot=tick_row.state_snapshot,
        orders=tick_row.orders,
        events=tick_row.events,
    )


def get_public_leaderboard(*, database_url: str) -> PublicLeaderboardResponse:
    engine = create_engine(database_url)
    with Session(engine) as session:
        completed_matches = session.scalars(
            select(Match)
            .where(Match.status == MatchStatus.COMPLETED.value)
            .order_by(Match.updated_at.desc(), Match.id.desc())
        ).all()
        if not completed_matches:
            return PublicLeaderboardResponse()

        match_ids = [match.id for match in completed_matches]
        players = session.scalars(
            select(Player)
            .where(Player.match_id.in_(match_ids))
            .order_by(Player.match_id, Player.id)
        ).all()

    players_by_match: dict[str, list[Player]] = defaultdict(list)
    for player in players:
        players_by_match[str(player.match_id)].append(player)

    ranked_matches = sorted(
        completed_matches,
        key=lambda match: (
            -_to_utc(match.updated_at).timestamp(),
            str(match.id),
        ),
    )
    aggregates: dict[str, _LeaderboardAggregate] = {}
    for match in ranked_matches:
        winner_alliance_id = (
            str(match.winner_alliance) if match.winner_alliance is not None else None
        )
        for player in players_by_match.get(str(match.id), []):
            competitor_kind: Literal["human", "agent"] = "agent" if player.is_agent else "human"
            competitor_identity = _leaderboard_competitor_identity(player)
            aggregate = aggregates.get(competitor_identity)
            if aggregate is None:
                aggregate = _LeaderboardAggregate(
                    competitor_key=competitor_identity,
                    display_name=player.display_name,
                    competitor_kind=competitor_kind,
                    elo=int(player.elo_rating),
                    provisional=True,
                )
                aggregates[competitor_identity] = aggregate

            aggregate.matches_played += 1
            player_alliance_id = str(player.alliance_id) if player.alliance_id is not None else None
            if winner_alliance_id is None:
                aggregate.draws += 1
            elif player_alliance_id == winner_alliance_id:
                aggregate.wins += 1
            else:
                aggregate.losses += 1

    ordered_aggregates = sorted(
        aggregates.values(),
        key=lambda aggregate: (
            -aggregate.elo,
            aggregate.display_name.casefold(),
            aggregate.competitor_kind,
            aggregate.competitor_key,
        ),
    )
    return PublicLeaderboardResponse(
        leaderboard=[
            LeaderboardEntry(
                rank=index,
                display_name=aggregate.display_name,
                competitor_kind=aggregate.competitor_kind,
                elo=aggregate.elo,
                provisional=aggregate.provisional,
                matches_played=aggregate.matches_played,
                wins=aggregate.wins,
                losses=aggregate.losses,
                draws=aggregate.draws,
            )
            for index, aggregate in enumerate(ordered_aggregates, start=1)
        ]
    )


def get_public_match_summaries(*, database_url: str) -> MatchListResponse:
    engine = create_engine(database_url)
    with Session(engine) as session:
        public_matches = session.scalars(
            select(Match).where(Match.status != MatchStatus.COMPLETED.value).order_by(Match.id)
        ).all()
        if not public_matches:
            return MatchListResponse()

        match_ids = [match.id for match in public_matches]
        players = session.scalars(
            select(Player)
            .where(Player.match_id.in_(match_ids))
            .order_by(Player.match_id, Player.id)
        ).all()

    player_counts_by_match: dict[str, int] = defaultdict(int)
    for player in players:
        player_counts_by_match[str(player.match_id)] += 1

    return MatchListResponse(
        matches=[
            MatchSummary(
                match_id=str(match.id),
                status=MatchStatus(match.status),
                map=str(match.config.get("map", "")),
                tick=int(match.current_tick),
                tick_interval_seconds=int(match.config.get("turn_seconds", 0)),
                current_player_count=player_counts_by_match.get(str(match.id), 0),
                max_player_count=max(int(match.config.get("max_players", 0)), 0),
                open_slot_count=max(
                    int(match.config.get("max_players", 0))
                    - player_counts_by_match.get(str(match.id), 0),
                    0,
                ),
            )
            for match in sorted(public_matches, key=_public_match_browse_sort_key)
        ]
    )


def get_public_match_detail(*, database_url: str, match_id: str) -> PublicMatchDetailResponse:
    engine = create_engine(database_url)
    with Session(engine) as session:
        match = session.scalar(
            select(Match).where(
                Match.id == match_id,
                Match.status != MatchStatus.COMPLETED.value,
            )
        )
        if match is None:
            raise PublicMatchDetailNotFoundError(match_id)

        players = session.scalars(
            select(Player)
            .where(Player.match_id == match.id)
            .order_by(Player.display_name, Player.is_agent, Player.id)
        ).all()

    return PublicMatchDetailResponse(
        match_id=str(match.id),
        status=MatchStatus(match.status),
        map=str(match.config.get("map", "")),
        tick=int(match.current_tick),
        tick_interval_seconds=int(match.config.get("turn_seconds", 0)),
        current_player_count=len(players),
        max_player_count=max(int(match.config.get("max_players", 0)), 0),
        open_slot_count=max(int(match.config.get("max_players", 0)) - len(players), 0),
        roster=[
            PublicMatchRosterRow(
                display_name=player.display_name,
                competitor_kind="agent" if player.is_agent else "human",
            )
            for player in sorted(players, key=_public_match_roster_sort_key)
        ],
    )


def _leaderboard_competitor_identity(player: Player) -> str:
    if player.is_agent:
        if player.api_key_id is not None:
            return f"agent:{player.api_key_id}"
        return f"agent-user:{player.user_id}"
    return f"human:{player.user_id}"


def _public_match_browse_sort_key(match: Match) -> tuple[int, float, int, str]:
    return (
        _public_status_priority(MatchStatus(match.status)),
        -_to_utc(match.updated_at).timestamp(),
        -int(match.current_tick),
        str(match.id),
    )


def _public_match_roster_sort_key(player: Player) -> tuple[str, int, str, str]:
    return (
        player.display_name.casefold(),
        0 if not player.is_agent else 1,
        player.display_name,
        str(player.id),
    )


def _public_status_priority(status: MatchStatus) -> int:
    if status is MatchStatus.LOBBY:
        return 0
    if status is MatchStatus.ACTIVE:
        return 1
    if status is MatchStatus.PAUSED:
        return 2
    return 3


def get_completed_match_summaries(*, database_url: str) -> CompletedMatchSummaryListResponse:
    engine = create_engine(database_url)
    with Session(engine) as session:
        completed_matches = session.scalars(
            select(Match)
            .where(Match.status == MatchStatus.COMPLETED.value)
            .order_by(Match.updated_at.desc(), Match.current_tick.desc(), Match.id)
        ).all()
        if not completed_matches:
            return CompletedMatchSummaryListResponse()

        match_ids = [match.id for match in completed_matches]
        players = session.scalars(
            select(Player)
            .where(Player.match_id.in_(match_ids))
            .order_by(Player.match_id, Player.display_name, Player.id)
        ).all()
        alliances = session.scalars(
            select(Alliance)
            .where(Alliance.match_id.in_(match_ids))
            .order_by(Alliance.match_id, Alliance.id)
        ).all()

    players_by_match: dict[str, list[Player]] = defaultdict(list)
    players_by_match_and_alliance: dict[tuple[str, str], list[Player]] = defaultdict(list)
    for player in players:
        match_id = str(player.match_id)
        players_by_match[match_id].append(player)
        if player.alliance_id is not None:
            players_by_match_and_alliance[(match_id, str(player.alliance_id))].append(player)

    alliances_by_match_and_id = {
        (str(alliance.match_id), str(alliance.id)): alliance for alliance in alliances
    }
    summaries = [
        CompletedMatchSummary(
            match_id=str(match.id),
            map=str(match.config.get("map", "")),
            final_tick=int(match.current_tick),
            tick_interval_seconds=int(match.config.get("turn_seconds", 0)),
            player_count=len(players_by_match.get(str(match.id), [])),
            completed_at=_to_utc(match.updated_at),
            winning_alliance_name=_winning_alliance_name(
                match=match,
                alliances_by_match_and_id=alliances_by_match_and_id,
            ),
            winning_player_display_names=_winning_player_display_names(
                match=match,
                players_by_match_and_alliance=players_by_match_and_alliance,
            ),
        )
        for match in completed_matches
    ]
    return CompletedMatchSummaryListResponse(matches=summaries)


def _load_persisted_alliances_by_match(
    *,
    matches: Sequence[Match],
    alliance_rows: Sequence[Alliance],
    player_rows: Sequence[Player],
) -> dict[str, list[MatchAlliance]]:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    players_by_match_and_alliance: dict[tuple[str, str], list[Player]] = defaultdict(list)
    for player in player_rows:
        players_by_match[str(player.match_id)].append(player)
        if player.alliance_id is None:
            continue
        players_by_match_and_alliance[(str(player.match_id), str(player.alliance_id))].append(
            player
        )

    alliances_by_match: dict[str, list[MatchAlliance]] = {}
    for match in matches:
        match_id = str(match.id)
        state = MatchState.model_validate(match.state)
        derived_registry = InMemoryMatchRegistry()
        derived_alliances = derived_registry._derive_alliances_from_state(state)  # noqa: SLF001
        persisted_player_mapping = _build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players_by_match.get(match_id, []),
        )
        persisted_rows_for_match = [
            alliance_row for alliance_row in alliance_rows if str(alliance_row.match_id) == match_id
        ]
        persisted_alliances = _merge_persisted_alliance_metadata(
            derived_alliances=derived_alliances,
            persisted_rows=persisted_rows_for_match,
            players_by_match_and_alliance=players_by_match_and_alliance,
            persisted_player_mapping=persisted_player_mapping,
            match_id=match_id,
        )
        if persisted_alliances:
            alliances_by_match[match_id] = persisted_alliances

    return alliances_by_match


def _load_agent_profiles_by_match(
    *,
    matches: Sequence[Match],
    player_rows: Sequence[Player],
) -> dict[str, list[AgentProfileResponse]]:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    persisted_agent_ids: set[str] = set()
    for player in player_rows:
        players_by_match[str(player.match_id)].append(player)

    for match in matches:
        state = MatchState.model_validate(match.state)
        persisted_player_mapping = _build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players_by_match.get(str(match.id), []),
        )
        for player in players_by_match.get(str(match.id), []):
            if not player.is_agent:
                continue
            canonical_player_id = persisted_player_mapping.get(str(player.id))
            if canonical_player_id is not None:
                persisted_agent_ids.add(f"agent-{canonical_player_id}")

    fallback_profiles_by_agent_id = {
        profile.agent_id: profile
        for profile in build_seeded_agent_profiles()
        if profile.agent_id in persisted_agent_ids
    }
    profiles_by_match: dict[str, list[AgentProfileResponse]] = {}
    for match in matches:
        match_id = str(match.id)
        state = MatchState.model_validate(match.state)
        persisted_player_mapping = _build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players_by_match.get(match_id, []),
        )
        loaded_profiles = [
            AgentProfileResponse(
                agent_id=f"agent-{canonical_player_id}",
                display_name=player.display_name,
                is_seeded=True,
                rating=AgentProfileRating(elo=int(player.elo_rating), provisional=True),
                history=AgentProfileHistory(
                    matches_played=0,
                    wins=0,
                    losses=0,
                    draws=0,
                ),
            )
            for player in sorted(
                players_by_match.get(match_id, []),
                key=lambda persisted: str(persisted.id),
            )
            if player.is_agent
            and (canonical_player_id := persisted_player_mapping.get(str(player.id))) is not None
        ]
        merged_profiles = {
            profile.agent_id: profile for profile in fallback_profiles_by_agent_id.values()
        }
        for profile in loaded_profiles:
            merged_profiles[profile.agent_id] = profile
        profiles_by_match[match_id] = [
            merged_profiles[agent_id] for agent_id in sorted(merged_profiles)
        ]

    return profiles_by_match


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _winning_alliance_name(
    *,
    match: Match,
    alliances_by_match_and_id: dict[tuple[str, str], Alliance],
) -> str | None:
    if match.winner_alliance is None:
        return None
    alliance = alliances_by_match_and_id.get((str(match.id), str(match.winner_alliance)))
    return alliance.name if alliance is not None else None


def _winning_player_display_names(
    *,
    match: Match,
    players_by_match_and_alliance: dict[tuple[str, str], list[Player]],
) -> list[str]:
    if match.winner_alliance is None:
        return []
    winners = players_by_match_and_alliance.get((str(match.id), str(match.winner_alliance)), [])
    return sorted(player.display_name for player in winners)


def _load_authenticated_agent_keys_by_match(
    *,
    matches: Sequence[Match],
    player_rows: Sequence[Player],
    api_key_rows: Sequence[ApiKey],
) -> dict[str, list[AuthenticatedAgentKeyRecord]]:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    api_keys_by_id = {str(api_key.id): api_key for api_key in api_key_rows}
    for player in player_rows:
        players_by_match[str(player.match_id)].append(player)

    authenticated_keys_by_match: dict[str, list[AuthenticatedAgentKeyRecord]] = {}
    for match in matches:
        match_id = str(match.id)
        state = MatchState.model_validate(match.state)
        persisted_player_mapping = _build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players_by_match.get(match_id, []),
        )
        authenticated_keys = [
            AuthenticatedAgentKeyRecord(
                agent_id=f"agent-{canonical_player_id}",
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
            and (canonical_player_id := persisted_player_mapping.get(str(player.id))) is not None
        ]
        if authenticated_keys:
            authenticated_keys_by_match[match_id] = authenticated_keys

    return authenticated_keys_by_match


def _load_joined_agents_by_match(
    *,
    matches: Sequence[Match],
    player_rows: Sequence[Player],
) -> dict[str, dict[str, str]]:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    for player in player_rows:
        players_by_match[str(player.match_id)].append(player)

    joined_agents_by_match: dict[str, dict[str, str]] = {}
    for match in matches:
        match_id = str(match.id)
        state = MatchState.model_validate(match.state)
        persisted_player_mapping = _build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players_by_match.get(match_id, []),
        )
        joined_agents = {
            f"agent-{canonical_player_id}": canonical_player_id
            for player in players_by_match.get(match_id, [])
            if player.is_agent
            and (canonical_player_id := persisted_player_mapping.get(str(player.id))) is not None
        }
        if joined_agents:
            joined_agents_by_match[match_id] = joined_agents

    return joined_agents_by_match


def _build_persisted_player_mapping(
    *,
    canonical_player_ids: list[str],
    persisted_players: Sequence[Player],
) -> dict[str, str]:
    sorted_players = sorted(persisted_players, key=lambda player: str(player.id))
    if len(sorted_players) > len(canonical_player_ids):
        return {}

    return {
        str(player.id): canonical_player_ids[index] for index, player in enumerate(sorted_players)
    }


def _merge_persisted_alliance_metadata(
    *,
    derived_alliances: list[MatchAlliance],
    persisted_rows: list[Alliance],
    players_by_match_and_alliance: dict[tuple[str, str], list[Player]],
    persisted_player_mapping: dict[str, str],
    match_id: str,
) -> list[MatchAlliance]:
    if not derived_alliances or len(derived_alliances) != len(persisted_rows):
        return []

    derived_alliances_by_members = {
        frozenset(member.player_id for member in alliance.members): alliance
        for alliance in derived_alliances
    }
    if len(derived_alliances_by_members) != len(derived_alliances):
        return []

    persisted_alliances: list[MatchAlliance] = []
    for persisted_row in persisted_rows:
        persisted_members = sorted(
            players_by_match_and_alliance.get((match_id, str(persisted_row.id)), []),
            key=lambda player: str(player.id),
        )
        canonical_member_ids: list[str] = []
        for player in persisted_members:
            canonical_player_id = persisted_player_mapping.get(str(player.id))
            if canonical_player_id is None:
                return []
            canonical_member_ids.append(canonical_player_id)
        member_key = frozenset(canonical_member_ids)
        derived_alliance = derived_alliances_by_members.get(member_key)
        if derived_alliance is None:
            return []

        canonical_members = sorted(derived_alliance.members, key=lambda member: member.player_id)
        member_joined_ticks = {
            persisted_player_mapping[str(player.id)]: (
                int(player.alliance_joined_tick)
                if player.alliance_joined_tick is not None
                else next(
                    member.joined_tick
                    for member in canonical_members
                    if member.player_id == persisted_player_mapping[str(player.id)]
                )
            )
            for player in persisted_members
        }
        leader_id = persisted_player_mapping.get(str(persisted_row.leader_id))
        if leader_id is None or leader_id not in member_key:
            return []

        persisted_alliances.append(
            MatchAlliance(
                alliance_id=derived_alliance.alliance_id,
                name=persisted_row.name,
                leader_id=leader_id,
                formed_tick=int(persisted_row.formed_tick),
                members=[
                    MatchAllianceMember(
                        player_id=member.player_id,
                        joined_tick=member_joined_ticks.get(member.player_id, member.joined_tick),
                    )
                    for member in canonical_members
                ],
            )
        )
        del derived_alliances_by_members[member_key]

    if derived_alliances_by_members:
        return []

    return sorted(persisted_alliances, key=lambda alliance: alliance.alliance_id)
