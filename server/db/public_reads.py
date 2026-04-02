from __future__ import annotations

from collections import defaultdict

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from server.db.models import Alliance, Match, Player, PlayerMatchSettlement, TickLog
from server.db.player_ids import build_persisted_player_mapping
from server.db.public_read_assembly import (
    build_completed_match_summary_list,
    build_match_history_response,
    build_match_replay_tick_response,
    build_public_leaderboard,
    build_public_match_detail,
    build_public_match_summary,
    public_match_browse_sort_key,
)
from server.models.api import (
    CompletedMatchSummaryListResponse,
    MatchHistoryResponse,
    MatchListResponse,
    MatchReplayTickResponse,
    PublicLeaderboardResponse,
    PublicMatchDetailResponse,
)
from server.models.domain import MatchStatus
from server.models.state import MatchState


class MatchHistoryNotFoundError(KeyError):
    pass


class TickHistoryNotFoundError(KeyError):
    pass


class PublicMatchDetailNotFoundError(KeyError):
    pass


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

    return build_match_history_response(match=match, ticks=ticks)


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

    return build_match_replay_tick_response(match=match, tick_row=tick_row)


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
        settlements = session.scalars(
            select(PlayerMatchSettlement)
            .where(PlayerMatchSettlement.match_id.in_(match_ids))
            .order_by(PlayerMatchSettlement.match_id, PlayerMatchSettlement.player_id)
        ).all()

    return build_public_leaderboard(
        completed_matches=completed_matches,
        players=players,
        settlements=settlements,
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
            build_public_match_summary(
                match=match,
                current_player_count=player_counts_by_match.get(str(match.id), 0),
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

    return build_public_match_detail(
        match=match,
        players=players,
        persisted_player_mapping=persisted_player_mapping,
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

    return build_completed_match_summary_list(
        completed_matches=completed_matches,
        players=players,
        alliances=alliances,
    )


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
