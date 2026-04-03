from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from server.db.overrides import append_owned_agent_override, list_owned_agent_overrides
from server.db.player_ids import build_match_scoped_player_id
from server.db.testing import provision_seeded_database
from server.models.orders import OrderBatch


def _orders(*, destination: str) -> OrderBatch:
    return OrderBatch.model_validate(
        {
            "movements": [{"army_id": "army-b", "destination": destination}],
            "recruitment": [],
            "upgrades": [],
            "transfers": [],
        }
    )


def test_list_owned_agent_overrides_returns_empty_list_when_no_rows_exist(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'overrides-empty.db'}"
    provision_seeded_database(database_url=database_url, reset=True)

    overrides = list_owned_agent_overrides(
        database_url=database_url,
        match_id="00000000-0000-0000-0000-000000000101",
        owner_user_id="00000000-0000-0000-0000-000000000301",
        agent_player_id=build_match_scoped_player_id(
            match_id="00000000-0000-0000-0000-000000000101",
            join_index=1,
        ),
    )

    assert overrides == []


def test_owned_agent_override_round_trips_in_deterministic_tick_created_at_id_order(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'overrides-ordered.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    agent_player_id = build_match_scoped_player_id(
        match_id="00000000-0000-0000-0000-000000000101",
        join_index=1,
    )

    first = append_owned_agent_override(
        database_url=database_url,
        match_id="00000000-0000-0000-0000-000000000101",
        owner_user_id="00000000-0000-0000-0000-000000000301",
        agent_player_id=agent_player_id,
        tick=143,
        superseded_submission_count=1,
        orders=_orders(destination="london"),
        created_at=datetime(2026, 4, 3, 11, 1, tzinfo=UTC),
    )
    second = append_owned_agent_override(
        database_url=database_url,
        match_id="00000000-0000-0000-0000-000000000101",
        owner_user_id="00000000-0000-0000-0000-000000000301",
        agent_player_id=agent_player_id,
        tick=142,
        superseded_submission_count=2,
        orders=_orders(destination="york"),
        created_at=datetime(2026, 4, 3, 11, 5, tzinfo=UTC),
    )
    third = append_owned_agent_override(
        database_url=database_url,
        match_id="00000000-0000-0000-0000-000000000101",
        owner_user_id="00000000-0000-0000-0000-000000000301",
        agent_player_id=agent_player_id,
        tick=143,
        superseded_submission_count=3,
        orders=_orders(destination="oxford"),
        created_at=datetime(2026, 4, 3, 11, 1, tzinfo=UTC),
    )

    overrides = list_owned_agent_overrides(
        database_url=database_url,
        match_id="00000000-0000-0000-0000-000000000101",
        owner_user_id="00000000-0000-0000-0000-000000000301",
        agent_player_id=agent_player_id,
    )

    assert [item.tick for item in overrides] == [142, 143, 143]
    assert [item.created_at for item in overrides] == [
        datetime(2026, 4, 3, 11, 5, tzinfo=UTC),
        datetime(2026, 4, 3, 11, 1, tzinfo=UTC),
        datetime(2026, 4, 3, 11, 1, tzinfo=UTC),
    ]
    assert [
        (item.id, item.superseded_submission_count, item.orders.movements[0].destination)
        for item in overrides
    ] == [
        (second.id, 2, "york"),
        *sorted(
            [
                (first.id, 1, "london"),
                (third.id, 3, "oxford"),
            ]
        ),
    ]


def test_list_owned_agent_overrides_only_returns_rows_for_requested_owner(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'overrides-owner-filter.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    match_id = "00000000-0000-0000-0000-000000000101"
    agent_player_id = build_match_scoped_player_id(match_id=match_id, join_index=1)

    owned_entry = append_owned_agent_override(
        database_url=database_url,
        match_id=match_id,
        owner_user_id="00000000-0000-0000-0000-000000000301",
        agent_player_id=agent_player_id,
        tick=144,
        superseded_submission_count=1,
        orders=_orders(destination="leeds"),
        created_at=datetime(2026, 4, 3, 11, 10, tzinfo=UTC),
    )
    append_owned_agent_override(
        database_url=database_url,
        match_id=match_id,
        owner_user_id="00000000-0000-0000-0000-000000000302",
        agent_player_id=agent_player_id,
        tick=145,
        superseded_submission_count=4,
        orders=_orders(destination="bristol"),
        created_at=datetime(2026, 4, 3, 11, 11, tzinfo=UTC),
    )

    overrides = list_owned_agent_overrides(
        database_url=database_url,
        match_id=match_id,
        owner_user_id="00000000-0000-0000-0000-000000000301",
        agent_player_id=agent_player_id,
    )

    assert overrides == [owned_entry]
