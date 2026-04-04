from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from math import floor

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from server.db.models import (
    Alliance,
    ApiKey,
    Match,
    MatchSettlement,
    Player,
    PlayerMatchSettlement,
)
from server.db.player_ids import build_persisted_player_mapping
from server.models.domain import MatchStatus
from server.models.state import MatchState

_BASE_WIN_GAIN = 8
_TENURE_BONUS = 8
_TERRITORY_BONUS = 8
_LOSS_PENALTY = 12


@dataclass(frozen=True, slots=True)
class SettlementAggregate:
    display_name: str
    elo: int
    matches_played: int
    wins: int
    losses: int
    draws: int
    provisional: bool


def settle_completed_match_if_needed(*, session: Session, match: Match) -> None:
    if match.status != MatchStatus.COMPLETED.value:
        return
    if session.get(MatchSettlement, match.id) is not None:
        return

    players = session.scalars(
        select(Player).where(Player.match_id == match.id).order_by(Player.id)
    ).all()
    settled_at = datetime.now(tz=UTC)
    try:
        with session.begin_nested():
            session.add(MatchSettlement(match_id=match.id, settled_at=settled_at))
            session.flush()
            if not players:
                return

            api_keys_by_id = {
                str(api_key.id): api_key
                for api_key in session.scalars(
                    select(ApiKey)
                    .where(
                        ApiKey.id.in_(
                            [player.api_key_id for player in players if player.api_key_id]
                        )
                    )
                    .order_by(ApiKey.id)
                ).all()
            }
            state = MatchState.model_validate(match.state)
            persisted_player_mapping = build_persisted_player_mapping(
                canonical_player_ids=sorted(state.players),
                persisted_players=players,
            )
            canonical_player_by_persisted = {
                persisted_player_id: canonical_player_id
                for persisted_player_id, canonical_player_id in persisted_player_mapping.items()
            }
            winner_alliance = _winner_alliance_for_settlement(
                session=session,
                match=match,
                players=players,
                state=state,
                canonical_player_by_persisted=canonical_player_by_persisted,
            )
            winner_player_ids = _winner_player_ids(
                match=match,
                players=players,
                state=state,
                canonical_player_by_persisted=canonical_player_by_persisted,
            )
            winner_city_counts = {
                player_id: _territory_count_for_player(
                    canonical_player_id=canonical_player_by_persisted.get(player_id),
                    state=state,
                )
                for player_id in winner_player_ids
            }
            winner_total_cities = sum(winner_city_counts.values())
            winner_count = max(len(winner_player_ids), 1)

            for player in players:
                player_id = str(player.id)
                outcome = _outcome_for_player(
                    player_id=player_id,
                    winner_player_ids=winner_player_ids,
                )
                delta = _rating_delta_for_player(
                    player=player,
                    match=match,
                    winner_alliance=winner_alliance,
                    outcome=outcome,
                    winner_count=winner_count,
                    winner_total_cities=winner_total_cities,
                    winner_city_counts=winner_city_counts,
                )
                elo_before = int(player.elo_rating)
                elo_after = max(0, elo_before + delta)
                session.add(
                    PlayerMatchSettlement(
                        player_id=player.id,
                        match_id=match.id,
                        user_id=player.user_id,
                        api_key_id=player.api_key_id,
                        display_name=player.display_name,
                        is_agent=player.is_agent,
                        outcome=outcome,
                        elo_before=elo_before,
                        elo_after=elo_after,
                        settled_at=settled_at,
                    )
                )
                if player.is_agent and player.api_key_id is not None:
                    api_key = api_keys_by_id.get(str(player.api_key_id))
                    if api_key is not None:
                        api_key.elo_rating = elo_after
            session.flush()
    except IntegrityError:
        verification_session = Session(session.get_bind())
        try:
            if verification_session.get(MatchSettlement, match.id) is None:
                raise
            participant_count = verification_session.scalar(
                select(func.count())
                .select_from(PlayerMatchSettlement)
                .where(PlayerMatchSettlement.match_id == match.id)
            )
            if participant_count == len(players):
                return
        finally:
            verification_session.close()
        raise


def load_settlement_aggregates_by_identity(
    settlement_rows: Sequence[PlayerMatchSettlement],
) -> dict[str, SettlementAggregate]:
    rows_by_identity: dict[str, list[PlayerMatchSettlement]] = defaultdict(list)
    for settlement in settlement_rows:
        rows_by_identity[_settlement_identity(settlement)].append(settlement)

    aggregates: dict[str, SettlementAggregate] = {}
    for identity, rows in rows_by_identity.items():
        latest = max(rows, key=lambda row: (_settled_sort_key(row), str(row.player_id)))
        aggregates[identity] = SettlementAggregate(
            display_name=latest.display_name,
            elo=int(latest.elo_after),
            matches_played=len(rows),
            wins=sum(1 for row in rows if row.outcome == "win"),
            losses=sum(1 for row in rows if row.outcome == "loss"),
            draws=sum(1 for row in rows if row.outcome == "draw"),
            provisional=False,
        )
    return aggregates


def latest_human_settled_elo(*, session: Session, user_id: str) -> int | None:
    latest = session.scalar(
        select(PlayerMatchSettlement)
        .where(
            PlayerMatchSettlement.user_id == user_id,
            PlayerMatchSettlement.is_agent.is_(False),
        )
        .order_by(PlayerMatchSettlement.settled_at.desc(), PlayerMatchSettlement.player_id.desc())
    )
    if latest is None:
        return None
    return int(latest.elo_after)


def _winner_player_ids(
    *,
    match: Match,
    players: Sequence[Player],
    state: MatchState,
    canonical_player_by_persisted: dict[str, str],
) -> set[str]:
    for winner_identity in _winner_identity_candidates(match=match, state=state):
        alliance_winners = {
            str(player.id)
            for player in players
            if _player_is_member_of_winner(
                player=player,
                winner_identity=winner_identity,
                state=state,
                canonical_player_by_persisted=canonical_player_by_persisted,
            )
        }
        if alliance_winners:
            return alliance_winners

        direct_persisted_winner = {
            str(player.id) for player in players if str(player.id) == winner_identity
        }
        if direct_persisted_winner:
            return direct_persisted_winner

        direct_canonical_winner = {
            str(player.id)
            for player in players
            if canonical_player_by_persisted.get(str(player.id)) == winner_identity
        }
        if direct_canonical_winner:
            return direct_canonical_winner

    return set()


def _winner_alliance_for_settlement(
    *,
    session: Session,
    match: Match,
    players: Sequence[Player],
    state: MatchState,
    canonical_player_by_persisted: dict[str, str],
) -> Alliance | None:
    for winner_identity in _winner_identity_candidates(match=match, state=state):
        if (winner_alliance := session.get(Alliance, winner_identity)) is not None:
            return winner_alliance

        for player in players:
            if not _player_is_member_of_winner(
                player=player,
                winner_identity=winner_identity,
                state=state,
                canonical_player_by_persisted=canonical_player_by_persisted,
            ):
                continue
            if player.alliance_id is None:
                continue
            winner_alliance = session.get(Alliance, player.alliance_id)
            if winner_alliance is not None:
                return winner_alliance

    return None


def _player_is_member_of_winner(
    *,
    player: Player,
    winner_identity: str,
    state: MatchState,
    canonical_player_by_persisted: dict[str, str],
) -> bool:
    if player.alliance_id is not None and str(player.alliance_id) == winner_identity:
        return True

    canonical_player_id = canonical_player_by_persisted.get(str(player.id))
    if canonical_player_id is None:
        return False

    player_state = state.players.get(canonical_player_id)
    return player_state is not None and player_state.alliance_id == winner_identity


def _winner_identity_candidates(*, match: Match, state: MatchState) -> list[str]:
    winner_identities: list[str] = []
    if state.victory.leading_alliance is not None:
        winner_identities.append(str(state.victory.leading_alliance))
    if match.winner_alliance is not None:
        persisted_winner = str(match.winner_alliance)
        if persisted_winner not in winner_identities:
            winner_identities.append(persisted_winner)
    return winner_identities


def _outcome_for_player(*, player_id: str, winner_player_ids: set[str]) -> str:
    if not winner_player_ids:
        return "draw"
    if player_id in winner_player_ids:
        return "win"
    return "loss"


def _rating_delta_for_player(
    *,
    player: Player,
    match: Match,
    winner_alliance: Alliance | None,
    outcome: str,
    winner_count: int,
    winner_total_cities: int,
    winner_city_counts: dict[str, int],
) -> int:
    if outcome == "draw":
        return 0
    if outcome == "loss":
        return -_LOSS_PENALTY

    player_id = str(player.id)
    territory_share = (
        winner_city_counts.get(player_id, 0) / winner_total_cities
        if winner_total_cities > 0
        else 1 / winner_count
    )
    tenure_ratio = _tenure_ratio_for_winner(
        player=player,
        match=match,
        winner_alliance=winner_alliance,
    )
    return (
        _BASE_WIN_GAIN
        + _round_half_up(_TENURE_BONUS * tenure_ratio)
        + _round_half_up(_TERRITORY_BONUS * territory_share)
    )


def _tenure_ratio_for_winner(
    *,
    player: Player,
    match: Match,
    winner_alliance: Alliance | None,
) -> float:
    if winner_alliance is None:
        return 1.0
    if player.alliance_joined_tick is None:
        return 1.0

    alliance_duration = max(int(match.current_tick) - int(winner_alliance.formed_tick) + 1, 1)
    player_tenure = max(int(match.current_tick) - int(player.alliance_joined_tick) + 1, 1)
    return min(player_tenure / alliance_duration, 1.0)


def _territory_count_for_player(*, canonical_player_id: str | None, state: MatchState) -> int:
    if canonical_player_id is None:
        return 0
    player_state = state.players.get(canonical_player_id)
    if player_state is None:
        return 0
    return len(player_state.cities_owned)


def _settlement_identity(settlement: PlayerMatchSettlement) -> str:
    if settlement.is_agent:
        if settlement.api_key_id is not None:
            return f"agent:{settlement.api_key_id}"
        return f"agent-user:{settlement.user_id}"
    return f"human:{settlement.user_id}"


def _settled_sort_key(row: PlayerMatchSettlement) -> float:
    if row.settled_at.tzinfo is None:
        return row.settled_at.replace(tzinfo=UTC).timestamp()
    return row.settled_at.astimezone(UTC).timestamp()


def _round_half_up(value: float) -> int:
    return floor(value + 0.5)
