from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from server.db.models import Match, Player
from server.models.api import MatchSummary, PublicMatchDetailResponse, PublicMatchRosterRow
from server.models.domain import MatchStatus


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


def to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = [
    "build_public_match_detail",
    "build_public_match_roster_rows",
    "build_public_match_summary",
    "leaderboard_competitor_identity",
    "public_match_browse_sort_key",
    "to_utc",
]
