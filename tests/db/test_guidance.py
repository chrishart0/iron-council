from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from server.db.guidance import append_owned_agent_guidance, list_owned_agent_guidance
from server.db.player_ids import build_match_scoped_player_id
from server.db.testing import provision_seeded_database


def test_list_owned_agent_guidance_returns_empty_list_when_no_rows_exist(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'guidance-empty.db'}"
    provision_seeded_database(database_url=database_url, reset=True)

    guidance = list_owned_agent_guidance(
        database_url=database_url,
        match_id="00000000-0000-0000-0000-000000000101",
        owner_user_id="00000000-0000-0000-0000-000000000301",
        agent_player_id=build_match_scoped_player_id(
            match_id="00000000-0000-0000-0000-000000000101",
            join_index=1,
        ),
    )

    assert guidance == []


def test_owned_agent_guidance_round_trips_in_deterministic_tick_created_at_id_order(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'guidance-ordered.db'}"
    provision_seeded_database(database_url=database_url, reset=True)

    first = append_owned_agent_guidance(
        database_url=database_url,
        match_id="00000000-0000-0000-0000-000000000101",
        owner_user_id="00000000-0000-0000-0000-000000000301",
        agent_player_id=build_match_scoped_player_id(
            match_id="00000000-0000-0000-0000-000000000101",
            join_index=1,
        ),
        content="Hold Liverpool.",
        tick=143,
        created_at=datetime(2026, 4, 3, 10, 1, tzinfo=UTC),
    )
    second = append_owned_agent_guidance(
        database_url=database_url,
        match_id="00000000-0000-0000-0000-000000000101",
        owner_user_id="00000000-0000-0000-0000-000000000301",
        agent_player_id=build_match_scoped_player_id(
            match_id="00000000-0000-0000-0000-000000000101",
            join_index=1,
        ),
        content="Prioritize defense.",
        tick=142,
        created_at=datetime(2026, 4, 3, 10, 5, tzinfo=UTC),
    )
    third = append_owned_agent_guidance(
        database_url=database_url,
        match_id="00000000-0000-0000-0000-000000000101",
        owner_user_id="00000000-0000-0000-0000-000000000301",
        agent_player_id=build_match_scoped_player_id(
            match_id="00000000-0000-0000-0000-000000000101",
            join_index=1,
        ),
        content="Protect the capital.",
        tick=143,
        created_at=datetime(2026, 4, 3, 10, 1, tzinfo=UTC),
    )

    guidance = list_owned_agent_guidance(
        database_url=database_url,
        match_id="00000000-0000-0000-0000-000000000101",
        owner_user_id="00000000-0000-0000-0000-000000000301",
        agent_player_id=build_match_scoped_player_id(
            match_id="00000000-0000-0000-0000-000000000101",
            join_index=1,
        ),
    )

    assert [item.tick for item in guidance] == [142, 143, 143]
    assert [item.created_at for item in guidance] == [
        datetime(2026, 4, 3, 10, 5, tzinfo=UTC),
        datetime(2026, 4, 3, 10, 1, tzinfo=UTC),
        datetime(2026, 4, 3, 10, 1, tzinfo=UTC),
    ]
    assert [(item.id, item.content) for item in guidance] == [
        (second.id, "Prioritize defense."),
        *sorted(
            [
                (first.id, "Hold Liverpool."),
                (third.id, "Protect the capital."),
            ]
        ),
    ]


def test_list_owned_agent_guidance_only_returns_rows_for_the_requested_owner(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'guidance-owner-filter.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    match_id = "00000000-0000-0000-0000-000000000101"
    agent_player_id = build_match_scoped_player_id(match_id=match_id, join_index=1)

    owned_entry = append_owned_agent_guidance(
        database_url=database_url,
        match_id=match_id,
        owner_user_id="00000000-0000-0000-0000-000000000301",
        agent_player_id=agent_player_id,
        content="Reinforce York.",
        tick=144,
        created_at=datetime(2026, 4, 3, 10, 10, tzinfo=UTC),
    )
    append_owned_agent_guidance(
        database_url=database_url,
        match_id=match_id,
        owner_user_id="00000000-0000-0000-0000-000000000302",
        agent_player_id=agent_player_id,
        content="This should stay hidden from the other owner read.",
        tick=145,
        created_at=datetime(2026, 4, 3, 10, 11, tzinfo=UTC),
    )

    guidance = list_owned_agent_guidance(
        database_url=database_url,
        match_id=match_id,
        owner_user_id="00000000-0000-0000-0000-000000000301",
        agent_player_id=agent_player_id,
    )

    assert guidance == [owned_entry]
