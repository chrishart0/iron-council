from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from server.db.models import Alliance, Match, Player, TickLog
from server.db.player_ids import build_persisted_player_mapping
from server.models.api import (
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
class LeaderboardAggregate:
    competitor_key: str
    display_name: str
    competitor_kind: Literal["human", "agent"]
    elo: int
    provisional: bool
    matches_played: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0


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
        key=lambda match: (-to_utc(match.updated_at).timestamp(), str(match.id)),
    )
    aggregates: dict[str, LeaderboardAggregate] = {}
    for match in ranked_matches:
        winner_alliance_id = (
            str(match.winner_alliance) if match.winner_alliance is not None else None
        )
        for player in players_by_match.get(str(match.id), []):
            competitor_kind: Literal["human", "agent"] = "agent" if player.is_agent else "human"
            competitor_identity = leaderboard_competitor_identity(player)
            aggregate = aggregates.get(competitor_identity)
            if aggregate is None:
                aggregate = LeaderboardAggregate(
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
            for match in sorted(public_matches, key=public_match_browse_sort_key)
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

        state = MatchState.model_validate(match.state)
        players = session.scalars(
            select(Player)
            .where(Player.match_id == match.id)
            .order_by(Player.display_name, Player.is_agent, Player.id)
        ).all()
        persisted_player_mapping = build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players,
        )

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
                player_id=canonical_player_id,
                display_name=player.display_name,
                competitor_kind="agent" if player.is_agent else "human",
            )
            for player in sorted(players, key=public_match_roster_sort_key)
            if (canonical_player_id := persisted_player_mapping.get(str(player.id))) is not None
        ],
    )


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
            completed_at=to_utc(match.updated_at),
            winning_alliance_name=winning_alliance_name(
                match=match,
                alliances_by_match_and_id=alliances_by_match_and_id,
            ),
            winning_player_display_names=winning_player_display_names(
                match=match,
                players_by_match_and_alliance=players_by_match_and_alliance,
            ),
        )
        for match in completed_matches
    ]
    return CompletedMatchSummaryListResponse(matches=summaries)


def leaderboard_competitor_identity(player: Player) -> str:
    if player.is_agent:
        if player.api_key_id is not None:
            return f"agent:{player.api_key_id}"
        return f"agent-user:{player.user_id}"
    return f"human:{player.user_id}"


def public_match_browse_sort_key(match: Match) -> tuple[int, float, int, str]:
    return (
        public_status_priority(MatchStatus(match.status)),
        -to_utc(match.updated_at).timestamp(),
        -int(match.current_tick),
        str(match.id),
    )


def public_match_roster_sort_key(player: Player) -> tuple[str, int, str, str]:
    return (
        player.display_name.casefold(),
        0 if not player.is_agent else 1,
        player.display_name,
        str(player.id),
    )


def public_status_priority(status: MatchStatus) -> int:
    if status is MatchStatus.LOBBY:
        return 0
    if status is MatchStatus.ACTIVE:
        return 1
    if status is MatchStatus.PAUSED:
        return 2
    return 3


def to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def winning_alliance_name(
    *,
    match: Match,
    alliances_by_match_and_id: dict[tuple[str, str], Alliance],
) -> str | None:
    if match.winner_alliance is None:
        return None
    alliance = alliances_by_match_and_id.get((str(match.id), str(match.winner_alliance)))
    return alliance.name if alliance is not None else None


def winning_player_display_names(
    *,
    match: Match,
    players_by_match_and_alliance: dict[tuple[str, str], list[Player]],
) -> list[str]:
    if match.winner_alliance is None:
        return []
    winners = players_by_match_and_alliance.get((str(match.id), str(match.winner_alliance)), [])
    return sorted(player.display_name for player in winners)


__all__ = [
    "MatchHistoryNotFoundError",
    "PublicMatchDetailNotFoundError",
    "TickHistoryNotFoundError",
    "get_completed_match_summaries",
    "get_match_history",
    "get_match_replay_tick",
    "get_public_leaderboard",
    "get_public_match_detail",
    "get_public_match_summaries",
]
