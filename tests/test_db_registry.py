from __future__ import annotations

import json
from pathlib import Path

from server.agent_registry import build_seeded_agent_api_key
from server.db.registry import load_match_registry_from_database, persist_advanced_match_tick
from server.db.testing import provision_seeded_database
from server.models.orders import OrderEnvelope
from sqlalchemy import create_engine, text


def test_load_match_registry_from_database_preserves_persisted_alliance_metadata(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'registry-seeded.db'}"
    provision_seeded_database(database_url=database_url, reset=True)

    registry = load_match_registry_from_database(database_url)

    primary_match = registry.get_match("00000000-0000-0000-0000-000000000101")
    assert primary_match is not None
    assert [alliance.alliance_id for alliance in primary_match.alliances] == ["alliance-red"]
    assert primary_match.alliances[0].name == "Western Accord"
    assert primary_match.alliances[0].leader_id == "player-1"
    assert primary_match.alliances[0].formed_tick == 120
    assert [
        (member.player_id, member.joined_tick) for member in primary_match.alliances[0].members
    ] == [("player-1", 120), ("player-2", 120)]
    assert primary_match.state.players["player-1"].alliance_id == "alliance-red"
    assert primary_match.state.players["player-2"].alliance_id == "alliance-red"


def test_load_match_registry_from_database_falls_back_to_derived_alliances(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'registry-fallback.db'}"
    provision_seeded_database(database_url=database_url, reset=True)

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO alliances (
                    id, match_id, name, leader_id, formed_tick, dissolved_tick
                ) VALUES (
                    :id, :match_id, :name, :leader_id, :formed_tick, :dissolved_tick
                )
                """
            ),
            {
                "id": "00000000-0000-0000-0000-000000000499",
                "match_id": "00000000-0000-0000-0000-000000000101",
                "name": "Contradictory Persisted Alliance",
                "leader_id": "00000000-0000-0000-0000-000000000501",
                "formed_tick": 119,
                "dissolved_tick": None,
            },
        )

    registry = load_match_registry_from_database(database_url)

    primary_match = registry.get_match("00000000-0000-0000-0000-000000000101")
    assert primary_match is not None
    assert [alliance.alliance_id for alliance in primary_match.alliances] == ["alliance-red"]
    assert primary_match.alliances[0].name == "alliance-red"
    assert primary_match.alliances[0].leader_id == "player-1"
    assert primary_match.alliances[0].formed_tick == 142
    assert [
        (member.player_id, member.joined_tick) for member in primary_match.alliances[0].members
    ] == [("player-1", 142), ("player-2", 142)]


def test_load_match_registry_from_database_matches_persisted_alliances_by_membership(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'registry-multi-alliance.db'}"
    provision_seeded_database(database_url=database_url, reset=True)

    engine = create_engine(database_url)
    with engine.begin() as connection:
        raw_state = connection.execute(
            text("SELECT state FROM matches WHERE id = :match_id"),
            {"match_id": "00000000-0000-0000-0000-000000000101"},
        ).scalar_one()
        state = json.loads(raw_state)
        state["players"]["player-3"]["alliance_id"] = "alliance-blue"
        connection.execute(
            text("UPDATE matches SET state = :state WHERE id = :match_id"),
            {
                "match_id": "00000000-0000-0000-0000-000000000101",
                "state": json.dumps(state),
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO alliances (
                    id, match_id, name, leader_id, formed_tick, dissolved_tick
                ) VALUES (
                    :id, :match_id, :name, :leader_id, :formed_tick, :dissolved_tick
                )
                """
            ),
            {
                "id": "00000000-0000-0000-0000-000000000402",
                "match_id": "00000000-0000-0000-0000-000000000101",
                "name": "Blue Banner",
                "leader_id": "00000000-0000-0000-0000-000000000503",
                "formed_tick": 130,
                "dissolved_tick": None,
            },
        )
        connection.execute(
            text(
                """
                UPDATE alliances
                SET leader_id = :leader_id, formed_tick = :formed_tick
                WHERE id = :id
                """
            ),
            {
                "id": "00000000-0000-0000-0000-000000000401",
                "leader_id": "00000000-0000-0000-0000-000000000501",
                "formed_tick": 120,
            },
        )
        connection.execute(
            text(
                """
                UPDATE players
                SET alliance_id = :alliance_id, alliance_joined_tick = :alliance_joined_tick
                WHERE id = :id
                """
            ),
            [
                {
                    "id": "00000000-0000-0000-0000-000000000501",
                    "alliance_id": "00000000-0000-0000-0000-000000000401",
                    "alliance_joined_tick": 125,
                },
                {
                    "id": "00000000-0000-0000-0000-000000000502",
                    "alliance_id": "00000000-0000-0000-0000-000000000401",
                    "alliance_joined_tick": 120,
                },
                {
                    "id": "00000000-0000-0000-0000-000000000503",
                    "alliance_id": "00000000-0000-0000-0000-000000000402",
                    "alliance_joined_tick": 130,
                },
            ],
        )

    registry = load_match_registry_from_database(database_url)

    primary_match = registry.get_match("00000000-0000-0000-0000-000000000101")
    assert primary_match is not None
    assert [alliance.alliance_id for alliance in primary_match.alliances] == [
        "alliance-blue",
        "alliance-red",
    ]
    assert [
        (
            alliance.alliance_id,
            alliance.name,
            alliance.leader_id,
            alliance.formed_tick,
            [(member.player_id, member.joined_tick) for member in alliance.members],
        )
        for alliance in primary_match.alliances
    ] == [
        (
            "alliance-blue",
            "Blue Banner",
            "player-3",
            130,
            [("player-3", 130)],
        ),
        (
            "alliance-red",
            "Western Accord",
            "player-1",
            120,
            [("player-1", 125), ("player-2", 120)],
        ),
    ]


def test_load_match_registry_from_database_falls_back_when_persisted_leader_is_not_member(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'registry-invalid-leader.db'}"
    provision_seeded_database(database_url=database_url, reset=True)

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE alliances
                SET leader_id = :leader_id
                WHERE id = :id
                """
            ),
            {
                "id": "00000000-0000-0000-0000-000000000401",
                "leader_id": "00000000-0000-0000-0000-000000000503",
            },
        )

    registry = load_match_registry_from_database(database_url)

    primary_match = registry.get_match("00000000-0000-0000-0000-000000000101")
    assert primary_match is not None
    assert [alliance.alliance_id for alliance in primary_match.alliances] == ["alliance-red"]
    assert primary_match.alliances[0].name == "alliance-red"
    assert primary_match.alliances[0].leader_id == "player-1"
    assert primary_match.alliances[0].formed_tick == 142


def test_load_match_registry_from_database_falls_back_when_membership_sets_do_not_match(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'registry-mismatched-membership.db'}"
    provision_seeded_database(database_url=database_url, reset=True)

    engine = create_engine(database_url)
    with engine.begin() as connection:
        raw_state = connection.execute(
            text("SELECT state FROM matches WHERE id = :match_id"),
            {"match_id": "00000000-0000-0000-0000-000000000101"},
        ).scalar_one()
        state = json.loads(raw_state)
        state["players"]["player-3"]["alliance_id"] = "alliance-blue"
        connection.execute(
            text("UPDATE matches SET state = :state WHERE id = :match_id"),
            {
                "match_id": "00000000-0000-0000-0000-000000000101",
                "state": json.dumps(state),
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO alliances (
                    id, match_id, name, leader_id, formed_tick, dissolved_tick
                ) VALUES (
                    :id, :match_id, :name, :leader_id, :formed_tick, :dissolved_tick
                )
                """
            ),
            {
                "id": "00000000-0000-0000-0000-000000000402",
                "match_id": "00000000-0000-0000-0000-000000000101",
                "name": "Blue Banner",
                "leader_id": "00000000-0000-0000-0000-000000000503",
                "formed_tick": 130,
                "dissolved_tick": None,
            },
        )
        connection.execute(
            text(
                """
                UPDATE players
                SET alliance_id = :alliance_id, alliance_joined_tick = :alliance_joined_tick
                WHERE id = :id
                """
            ),
            [
                {
                    "id": "00000000-0000-0000-0000-000000000501",
                    "alliance_id": "00000000-0000-0000-0000-000000000401",
                    "alliance_joined_tick": 120,
                },
                {
                    "id": "00000000-0000-0000-0000-000000000502",
                    "alliance_id": "00000000-0000-0000-0000-000000000402",
                    "alliance_joined_tick": 120,
                },
                {
                    "id": "00000000-0000-0000-0000-000000000503",
                    "alliance_id": "00000000-0000-0000-0000-000000000402",
                    "alliance_joined_tick": 130,
                },
            ],
        )

    registry = load_match_registry_from_database(database_url)

    primary_match = registry.get_match("00000000-0000-0000-0000-000000000101")
    assert primary_match is not None
    assert [alliance.alliance_id for alliance in primary_match.alliances] == [
        "alliance-blue",
        "alliance-red",
    ]
    assert [alliance.name for alliance in primary_match.alliances] == [
        "alliance-blue",
        "alliance-red",
    ]
    assert [alliance.leader_id for alliance in primary_match.alliances] == [
        "player-3",
        "player-1",
    ]


def test_load_match_registry_from_database_resolves_db_backed_agent_api_keys(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'registry-auth.db'}"
    provision_seeded_database(database_url=database_url, reset=True)

    registry = load_match_registry_from_database(database_url)

    authenticated_agent = registry.resolve_authenticated_agent(
        build_seeded_agent_api_key("agent-player-2")
    )

    assert authenticated_agent is not None
    assert authenticated_agent.model_dump(mode="json") == {
        "agent_id": "agent-player-2",
        "display_name": "Morgana",
        "is_seeded": True,
    }


def test_persist_advanced_match_tick_updates_match_and_appends_tick_log_transactionally(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'registry-persist-tick.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    registry = load_match_registry_from_database(database_url)

    registry.record_submission(
        match_id="00000000-0000-0000-0000-000000000101",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "00000000-0000-0000-0000-000000000101",
                "player_id": "player-2",
                "tick": 142,
                "orders": {
                    "movements": [],
                    "recruitment": [{"city": "manchester", "troops": 5}],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )
    advanced_tick = registry.advance_match_tick("00000000-0000-0000-0000-000000000101")

    persist_advanced_match_tick(database_url=database_url, advanced_tick=advanced_tick)

    engine = create_engine(database_url)
    with engine.connect() as connection:
        persisted_match = connection.execute(
            text("SELECT current_tick, state FROM matches WHERE id = :match_id"),
            {"match_id": "00000000-0000-0000-0000-000000000101"},
        ).one()
        persisted_tick_log = connection.execute(
            text(
                """
                SELECT tick, state_snapshot, orders, events
                FROM tick_log
                WHERE match_id = :match_id
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"match_id": "00000000-0000-0000-0000-000000000101"},
        ).one()

    assert persisted_match.current_tick == 143
    assert json.loads(persisted_match.state)["tick"] == 143
    assert persisted_tick_log.tick == 143
    assert json.loads(persisted_tick_log.state_snapshot)["tick"] == 143
    assert json.loads(persisted_tick_log.orders) == {
        "movements": [],
        "recruitment": [{"city": "manchester", "troops": 5}],
        "upgrades": [],
        "transfers": [],
    }
    assert json.loads(persisted_tick_log.events) == [
        {"phase": "resource", "event": "phase.resource.completed"},
        {"phase": "build", "event": "phase.build.completed"},
        {"phase": "movement", "event": "phase.movement.completed"},
        {"phase": "combat", "event": "phase.combat.completed"},
        {"phase": "siege", "event": "phase.siege.completed"},
        {"phase": "attrition", "event": "phase.attrition.completed"},
        {"phase": "diplomacy", "event": "phase.diplomacy.completed"},
        {"phase": "victory", "event": "phase.victory.completed"},
    ]

    reloaded_registry = load_match_registry_from_database(database_url)
    reloaded_match = reloaded_registry.get_match("00000000-0000-0000-0000-000000000101")
    assert reloaded_match is not None
    assert reloaded_match.state.tick == 143
    assert any(
        army.owner == "player-2" and army.location == "manchester" and army.troops == 5
        for army in reloaded_match.state.armies
    )


def test_load_match_registry_from_database_rejects_inactive_agent_api_keys(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'registry-inactive-auth.db'}"
    provision_seeded_database(database_url=database_url, reset=True)

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE api_keys
                SET is_active = 0
                WHERE id = :api_key_id
                """
            ),
            {"api_key_id": "00000000-0000-0000-0000-000000000202"},
        )

    registry = load_match_registry_from_database(database_url)

    assert (
        registry.resolve_authenticated_agent(build_seeded_agent_api_key("agent-player-2")) is None
    )


def test_load_match_registry_from_database_exposes_authenticated_join_mapping_for_agent_players(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'registry-joined-agents.db'}"
    provision_seeded_database(database_url=database_url, reset=True)

    registry = load_match_registry_from_database(database_url)

    assert (
        registry.require_joined_player_id(
            match_id="00000000-0000-0000-0000-000000000101",
            agent_id="agent-player-2",
        )
        == "player-2"
    )
