from __future__ import annotations

from collections.abc import Sequence

from server.db.models import Player


def build_persisted_player_mapping(
    *,
    canonical_player_ids: list[str],
    persisted_players: Sequence[Player],
) -> dict[str, str]:
    canonical_player_id_set = set(canonical_player_ids)
    persisted_player_mapping: dict[str, str] = {}
    seen_canonical_player_ids: set[str] = set()
    for player in persisted_players:
        canonical_player_id = canonical_player_id_from_persisted_player_id(
            persisted_player_id=str(player.id),
            canonical_player_ids=canonical_player_id_set,
        )
        if canonical_player_id is None:
            continue
        if canonical_player_id in seen_canonical_player_ids:
            return {}
        persisted_player_mapping[str(player.id)] = canonical_player_id
        seen_canonical_player_ids.add(canonical_player_id)

    return persisted_player_mapping


def canonical_player_id_from_persisted_player_id(
    *, persisted_player_id: str, canonical_player_ids: set[str]
) -> str | None:
    persisted_segments = persisted_player_id.split("-")
    if len(persisted_segments) != 5:
        return None
    try:
        join_index = int(persisted_segments[-1], 16)
    except ValueError:
        return None

    canonical_player_id = f"player-{join_index}"
    if canonical_player_id not in canonical_player_ids:
        return None
    return canonical_player_id


def build_joined_player_id(join_index: int) -> str:
    return f"ffffffff-ffff-ffff-ffff-{join_index:012x}"


def build_match_scoped_player_id(*, match_id: str, join_index: int) -> str:
    cleaned_match_id = match_id.replace("-", "")
    match_prefix = (cleaned_match_id[:16] + cleaned_match_id[-4:]).ljust(20, "f")
    return (
        f"{match_prefix[:8]}-"
        f"{match_prefix[8:12]}-"
        f"{match_prefix[12:16]}-"
        f"{match_prefix[16:20]}-"
        f"{join_index:012x}"
    )


def build_human_actor_id(user_id: str) -> str:
    return f"human:{user_id}"
