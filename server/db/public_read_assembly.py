from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from server.db.models import Alliance, Match, Player, TickLog
from server.models.api import (
    CompletedMatchSummary,
    CompletedMatchSummaryListResponse,
    LeaderboardEntry,
    MatchHistoryEntry,
    MatchHistoryResponse,
    MatchReplayTickResponse,
    MatchSummary,
    PublicLeaderboardResponse,
    PublicMatchDetailResponse,
    PublicMatchRosterRow,
)
from server.models.domain import MatchStatus


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


def build_public_match_summary(*, match: Match, current_player_count: int) -> MatchSummary:
    max_player_count = max(int(match.config.get("max_players", 0)), 0)
    return MatchSummary(
        match_id=str(match.id),
        status=MatchStatus(match.status),
        map=str(match.config.get("map", "")),
        tick=int(match.current_tick),
        tick_interval_seconds=int(match.config.get("turn_seconds", 0)),
        current_player_count=current_player_count,
        max_player_count=max_player_count,
        open_slot_count=max(max_player_count - current_player_count, 0),
    )


def build_public_match_detail(
    *,
    match: Match,
    players: Sequence[Player],
    persisted_player_mapping: dict[str, str],
) -> PublicMatchDetailResponse:
    summary = build_public_match_summary(match=match, current_player_count=len(players))
    return PublicMatchDetailResponse(
        match_id=summary.match_id,
        status=summary.status,
        map=summary.map,
        tick=summary.tick,
        tick_interval_seconds=summary.tick_interval_seconds,
        current_player_count=summary.current_player_count,
        max_player_count=summary.max_player_count,
        open_slot_count=summary.open_slot_count,
        roster=build_public_match_roster_rows(
            players=players,
            persisted_player_mapping=persisted_player_mapping,
        ),
    )


def build_match_history_response(*, match: Match, ticks: Sequence[int]) -> MatchHistoryResponse:
    return MatchHistoryResponse(
        match_id=str(match.id),
        status=MatchStatus(match.status),
        current_tick=int(match.current_tick),
        tick_interval_seconds=int(match.config.get("turn_seconds", 0)),
        history=[MatchHistoryEntry(tick=int(tick)) for tick in ticks],
    )


def build_match_replay_tick_response(
    *,
    match: Match,
    tick_row: TickLog,
) -> MatchReplayTickResponse:
    return MatchReplayTickResponse(
        match_id=str(match.id),
        tick=int(tick_row.tick),
        state_snapshot=tick_row.state_snapshot,
        orders=tick_row.orders,
        events=tick_row.events,
    )


def build_public_match_roster_rows(
    *,
    players: Sequence[Player],
    persisted_player_mapping: dict[str, str],
) -> list[PublicMatchRosterRow]:
    return [
        PublicMatchRosterRow(
            player_id=canonical_player_id,
            display_name=player.display_name,
            competitor_kind="agent" if player.is_agent else "human",
        )
        for player in sorted(players, key=public_match_roster_sort_key)
        if (canonical_player_id := persisted_player_mapping.get(str(player.id))) is not None
    ]


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


def leaderboard_competitor_identity(player: Player) -> str:
    if player.is_agent:
        if player.api_key_id is not None:
            return f"agent:{player.api_key_id}"
        return f"agent-user:{player.user_id}"
    return f"human:{player.user_id}"


def build_public_leaderboard(
    *,
    completed_matches: Sequence[Match],
    players: Sequence[Player],
) -> PublicLeaderboardResponse:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    players_by_match_and_id: dict[tuple[str, str], Player] = {}
    for player in players:
        match_id = str(player.match_id)
        players_by_match[match_id].append(player)
        players_by_match_and_id[(match_id, str(player.id))] = player

    ranked_matches = sorted(
        completed_matches,
        key=lambda match: (-to_utc(match.updated_at).timestamp(), str(match.id)),
    )
    aggregates: dict[str, LeaderboardAggregate] = {}
    for match in ranked_matches:
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
            winner_identity = winner_identity_for_player(
                match=match,
                player=player,
                players_by_match_and_id=players_by_match_and_id,
            )
            if winner_identity is None:
                aggregate.draws += 1
            elif winner_identity == "win":
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


def build_completed_match_summary_list(
    *,
    completed_matches: Sequence[Match],
    players: Sequence[Player],
    alliances: Sequence[Alliance],
) -> CompletedMatchSummaryListResponse:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    players_by_match_and_alliance: dict[tuple[str, str], list[Player]] = defaultdict(list)
    players_by_match_and_id: dict[tuple[str, str], Player] = {}
    for player in players:
        match_id = str(player.match_id)
        players_by_match[match_id].append(player)
        players_by_match_and_id[(match_id, str(player.id))] = player
        if player.alliance_id is not None:
            players_by_match_and_alliance[(match_id, str(player.alliance_id))].append(player)

    alliances_by_match_and_id = {
        (str(alliance.match_id), str(alliance.id)): alliance for alliance in alliances
    }
    return CompletedMatchSummaryListResponse(
        matches=[
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
                    players_by_match_and_id=players_by_match_and_id,
                ),
            )
            for match in completed_matches
        ]
    )


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
    players_by_match_and_id: dict[tuple[str, str], Player],
) -> list[str]:
    if match.winner_alliance is None:
        return []
    winners = players_by_match_and_alliance.get((str(match.id), str(match.winner_alliance)), [])
    if winners:
        return sorted(player.display_name for player in winners)
    solo_winner = players_by_match_and_id.get((str(match.id), str(match.winner_alliance)))
    if solo_winner is None:
        return []
    return [solo_winner.display_name]


def winner_identity_for_player(
    *,
    match: Match,
    player: Player,
    players_by_match_and_id: dict[tuple[str, str], Player],
) -> Literal["win", "loss"] | None:
    if match.winner_alliance is None:
        return None
    if player.alliance_id is not None and str(player.alliance_id) == str(match.winner_alliance):
        return "win"
    winner_player = players_by_match_and_id.get((str(match.id), str(match.winner_alliance)))
    if winner_player is None:
        return "loss"
    if str(player.id) == str(winner_player.id):
        return "win"
    return "loss"


def to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = [
    "build_match_history_response",
    "build_match_replay_tick_response",
    "build_completed_match_summary_list",
    "build_public_leaderboard",
    "build_public_match_detail",
    "build_public_match_roster_rows",
    "build_public_match_summary",
    "leaderboard_competitor_identity",
    "public_match_browse_sort_key",
    "to_utc",
]
