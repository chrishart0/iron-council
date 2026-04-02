from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from server.agent_registry import AdvancedMatchTick, get_terminal_winner_alliance
from server.agent_registry_types import MatchAlliance
from server.db.models import Alliance, Match, Player, TickLog
from server.db.player_ids import build_persisted_player_mapping
from server.models.domain import MatchStatus


def persist_advanced_match_tick(*, database_url: str, advanced_tick: AdvancedMatchTick) -> None:
    engine = create_engine(database_url)
    with Session(engine) as session, session.begin():
        match = session.get(Match, advanced_tick.match_id)
        if match is None:
            raise KeyError(f"Match '{advanced_tick.match_id}' was not found.")

        match.current_tick = advanced_tick.resolved_tick
        match.state = advanced_tick.next_state.model_dump(mode="json")
        persisted_alliance_ids_by_canonical = _sync_terminal_alliance_rows(
            session=session,
            match=match,
            advanced_tick=advanced_tick,
        )
        terminal_winner_alliance = _resolve_terminal_winner_coalition_id(
            advanced_tick=advanced_tick,
            persisted_alliance_ids_by_canonical=persisted_alliance_ids_by_canonical,
            session=session,
            match=match,
        )
        if get_terminal_winner_alliance(advanced_tick) is not None:
            match.status = MatchStatus.COMPLETED.value
            match.updated_at = datetime.now(tz=UTC)
        if terminal_winner_alliance is not None:
            match.winner_alliance = terminal_winner_alliance
        session.add(
            TickLog(
                match_id=advanced_tick.match_id,
                tick=advanced_tick.resolved_tick,
                state_snapshot=advanced_tick.next_state.model_dump(mode="json"),
                orders=advanced_tick.accepted_orders.model_dump(mode="json"),
                events=[event.model_dump(mode="json") for event in advanced_tick.events],
            )
        )


def _resolve_terminal_winner_coalition_id(
    *,
    advanced_tick: AdvancedMatchTick,
    persisted_alliance_ids_by_canonical: dict[str, str],
    session: Session,
    match: Match,
) -> str | None:
    winner_alliance = get_terminal_winner_alliance(advanced_tick)
    if winner_alliance is None:
        return None

    persisted_winner_alliance = persisted_alliance_ids_by_canonical.get(winner_alliance)
    if persisted_winner_alliance is not None:
        return persisted_winner_alliance

    persisted_player_mapping = build_persisted_player_mapping(
        canonical_player_ids=sorted(advanced_tick.next_state.players),
        persisted_players=session.scalars(
            select(Player).where(Player.match_id == match.id).order_by(Player.id)
        ).all(),
    )
    for persisted_player_id, canonical_player_id in persisted_player_mapping.items():
        if canonical_player_id == winner_alliance:
            return persisted_player_id

    raise ValueError(
        "Terminal victory winner coalition could not be resolved from canonical coalition data."
    )


def _sync_terminal_alliance_rows(
    *,
    session: Session,
    match: Match,
    advanced_tick: AdvancedMatchTick,
) -> dict[str, str]:
    if get_terminal_winner_alliance(advanced_tick) is None:
        return {}

    players = session.scalars(
        select(Player).where(Player.match_id == match.id).order_by(Player.id)
    ).all()
    persisted_player_mapping = build_persisted_player_mapping(
        canonical_player_ids=sorted(advanced_tick.next_state.players),
        persisted_players=players,
    )
    players_by_persisted_id = {str(player.id): player for player in players}
    persisted_players_by_canonical = {
        canonical_player_id: players_by_persisted_id[persisted_player_id]
        for persisted_player_id, canonical_player_id in persisted_player_mapping.items()
    }

    active_alliances = session.scalars(
        select(Alliance)
        .where(Alliance.match_id == match.id, Alliance.dissolved_tick.is_(None))
        .order_by(Alliance.id)
    ).all()
    active_alliances_by_members = {
        _persisted_member_ids_for_alliance(players=players, alliance_id=str(alliance.id)): alliance
        for alliance in active_alliances
    }

    joined_ticks_by_alliance_and_player = _joined_ticks_by_alliance_and_player(
        advanced_tick.alliances
    )
    persisted_alliance_ids_by_canonical: dict[str, str] = {}
    matched_active_alliance_ids: set[str] = set()

    for alliance in advanced_tick.alliances:
        persisted_member_ids = _persisted_member_ids_for_canonical_alliance(
            alliance=alliance,
            persisted_players_by_canonical=persisted_players_by_canonical,
        )
        persisted_leader_id = _persisted_player_id_for_canonical_player(
            canonical_player_id=alliance.leader_id,
            persisted_players_by_canonical=persisted_players_by_canonical,
        )
        persisted_alliance = active_alliances_by_members.get(persisted_member_ids)
        if persisted_alliance is None:
            persisted_alliance = Alliance(
                id=str(uuid4()),
                match_id=match.id,
                name=alliance.name,
                leader_id=persisted_leader_id,
                formed_tick=alliance.formed_tick,
                dissolved_tick=None,
            )
            session.add(persisted_alliance)
        else:
            persisted_alliance.name = alliance.name
            persisted_alliance.leader_id = persisted_leader_id
            persisted_alliance.formed_tick = alliance.formed_tick
            persisted_alliance.dissolved_tick = None
        persisted_alliance_ids_by_canonical[alliance.alliance_id] = str(persisted_alliance.id)
        matched_active_alliance_ids.add(str(persisted_alliance.id))

    for active_alliance in active_alliances:
        if str(active_alliance.id) not in matched_active_alliance_ids:
            active_alliance.dissolved_tick = advanced_tick.resolved_tick

    for canonical_player_id, player_state in advanced_tick.next_state.players.items():
        persisted_player = persisted_players_by_canonical.get(canonical_player_id)
        if persisted_player is None:
            continue
        if player_state.alliance_id is None:
            persisted_player.alliance_id = None
            persisted_player.alliance_joined_tick = None
            continue
        persisted_alliance_id = persisted_alliance_ids_by_canonical.get(player_state.alliance_id)
        if persisted_alliance_id is None:
            raise ValueError(
                "Terminal alliance "
                f"'{player_state.alliance_id}' could not be synchronized to persistence."
            )
        persisted_player.alliance_id = persisted_alliance_id
        persisted_player.alliance_joined_tick = joined_ticks_by_alliance_and_player[
            (player_state.alliance_id, canonical_player_id)
        ]

    return persisted_alliance_ids_by_canonical


def _joined_ticks_by_alliance_and_player(
    alliances: list[MatchAlliance],
) -> dict[tuple[str, str], int]:
    return {
        (alliance.alliance_id, member.player_id): member.joined_tick
        for alliance in alliances
        for member in alliance.members
    }


def _persisted_member_ids_for_canonical_alliance(
    *,
    alliance: MatchAlliance,
    persisted_players_by_canonical: dict[str, Player],
) -> frozenset[str]:
    return frozenset(
        _persisted_player_id_for_canonical_player(
            canonical_player_id=member.player_id,
            persisted_players_by_canonical=persisted_players_by_canonical,
        )
        for member in alliance.members
    )


def _persisted_member_ids_for_alliance(
    *,
    players: Sequence[Player],
    alliance_id: str,
) -> frozenset[str]:
    return frozenset(
        str(player.id)
        for player in players
        if player.alliance_id is not None and str(player.alliance_id) == alliance_id
    )


def _persisted_player_id_for_canonical_player(
    *,
    canonical_player_id: str,
    persisted_players_by_canonical: dict[str, Player],
) -> str:
    persisted_player = persisted_players_by_canonical.get(canonical_player_id)
    if persisted_player is None:
        raise ValueError(
            f"Canonical player '{canonical_player_id}' could not be resolved to a persisted row."
        )
    return str(persisted_player.id)
