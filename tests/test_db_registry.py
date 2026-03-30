from __future__ import annotations

import json
from pathlib import Path

from server.agent_registry import build_seeded_agent_api_key
from server.db.registry import (
    MatchHistoryNotFoundError,
    TickHistoryNotFoundError,
    get_completed_match_summaries,
    get_match_history,
    get_match_replay_tick,
    get_public_leaderboard,
    get_public_match_summaries,
    load_match_registry_from_database,
    persist_advanced_match_tick,
)
from server.db.testing import provision_seeded_database
from server.models.orders import OrderEnvelope
from sqlalchemy import create_engine, text

from tests.support import insert_completed_match_fixture


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


def test_get_match_history_returns_deterministic_tick_entries_with_match_metadata(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'registry-history.db'}"
    provision_seeded_database(database_url=database_url, reset=True)

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO tick_log (
                    id, match_id, tick, state_snapshot, orders, events, created_at
                ) VALUES (
                    :id, :match_id, :tick, :state_snapshot, :orders, :events, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": 9000,
                "match_id": "00000000-0000-0000-0000-000000000101",
                "tick": 141,
                "state_snapshot": json.dumps({"tick": 141, "phase": "combat"}),
                "orders": json.dumps({"movements": [], "recruitment": []}),
                "events": json.dumps([{"event": "phase.combat.completed"}]),
            },
        )

    history = get_match_history(
        database_url=database_url,
        match_id="00000000-0000-0000-0000-000000000101",
    )

    assert history.model_dump(mode="json") == {
        "match_id": "00000000-0000-0000-0000-000000000101",
        "status": "active",
        "current_tick": 142,
        "tick_interval_seconds": 30,
        "history": [
            {"tick": 141},
            {"tick": 142},
        ],
    }


def test_get_match_replay_tick_returns_persisted_snapshot_orders_and_events(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'registry-replay.db'}"
    provision_seeded_database(database_url=database_url, reset=True)

    replay_tick = get_match_replay_tick(
        database_url=database_url,
        match_id="00000000-0000-0000-0000-000000000101",
        tick=142,
    )

    assert replay_tick.model_dump(mode="json") == {
        "match_id": "00000000-0000-0000-0000-000000000101",
        "tick": 142,
        "state_snapshot": {"cities": {"london": {"owner": "Arthur", "population": 12}}},
        "orders": {"movements": [{"army_id": "army-1", "destination": "york"}]},
        "events": {"summary": ["Convoy secured", "Trade revenue collected"]},
    }


def test_get_match_history_and_replay_tick_distinguish_missing_match_and_tick(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'registry-history-errors.db'}"
    provision_seeded_database(database_url=database_url, reset=True)

    try:
        get_match_history(
            database_url=database_url, match_id="00000000-0000-0000-0000-000000009999"
        )
    except MatchHistoryNotFoundError:
        pass
    else:
        raise AssertionError("Expected missing match history to raise MatchHistoryNotFoundError.")

    try:
        get_match_replay_tick(
            database_url=database_url,
            match_id="00000000-0000-0000-0000-000000000101",
            tick=999,
        )
    except TickHistoryNotFoundError:
        pass
    else:
        raise AssertionError("Expected missing replay tick to raise TickHistoryNotFoundError.")


def test_get_public_leaderboard_returns_ranked_competitors_with_stable_tiebreakers(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'registry-leaderboard.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    insert_completed_match_fixture(database_url)

    leaderboard = get_public_leaderboard(database_url=database_url)

    assert leaderboard.model_dump(mode="json") == {
        "leaderboard": [
            {
                "rank": 1,
                "display_name": "Arthur",
                "competitor_kind": "human",
                "elo": 1210,
                "provisional": True,
                "matches_played": 1,
                "wins": 1,
                "losses": 0,
                "draws": 0,
            },
            {
                "rank": 2,
                "display_name": "Bedivere",
                "competitor_kind": "human",
                "elo": 1190,
                "provisional": True,
                "matches_played": 1,
                "wins": 0,
                "losses": 0,
                "draws": 1,
            },
            {
                "rank": 3,
                "display_name": "Morgana",
                "competitor_kind": "agent",
                "elo": 1190,
                "provisional": True,
                "matches_played": 2,
                "wins": 1,
                "losses": 0,
                "draws": 1,
            },
            {
                "rank": 4,
                "display_name": "Gawain",
                "competitor_kind": "agent",
                "elo": 1175,
                "provisional": True,
                "matches_played": 1,
                "wins": 0,
                "losses": 1,
                "draws": 0,
            },
        ]
    }


def test_get_public_leaderboard_keeps_agent_rows_distinct_when_same_user_has_multiple_api_keys(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'registry-leaderboard-agent-identity.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    insert_completed_match_fixture(database_url)

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE players
                SET user_id = :shared_user_id
                WHERE id IN (:player_one_id, :player_two_id)
                """
            ),
            {
                "shared_user_id": "00000000-0000-0000-0000-000000009999",
                "player_one_id": "00000000-0000-0000-0000-000000000702",
                "player_two_id": "00000000-0000-0000-0000-000000000703",
            },
        )

    leaderboard = get_public_leaderboard(database_url=database_url)
    agent_rows = [row for row in leaderboard.leaderboard if row.competitor_kind == "agent"]

    assert [row.display_name for row in agent_rows] == ["Morgana", "Gawain"]
    assert [row.matches_played for row in agent_rows] == [2, 1]
    assert [row.wins for row in agent_rows] == [1, 0]
    assert [row.losses for row in agent_rows] == [0, 1]
    assert [row.draws for row in agent_rows] == [1, 0]


def test_get_completed_match_summaries_returns_compact_browse_rows_only_for_completed_matches(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'registry-completed-matches.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    insert_completed_match_fixture(database_url)

    summaries = get_completed_match_summaries(database_url=database_url)

    assert summaries.model_dump(mode="json") == {
        "matches": [
            {
                "match_id": "00000000-0000-0000-0000-000000000202",
                "map": "mediterranean",
                "final_tick": 200,
                "tick_interval_seconds": 45,
                "player_count": 2,
                "completed_at": "2026-03-29T12:15:00Z",
                "winning_alliance_name": None,
                "winning_player_display_names": [],
            },
            {
                "match_id": "00000000-0000-0000-0000-000000000201",
                "map": "britain",
                "final_tick": 155,
                "tick_interval_seconds": 30,
                "player_count": 3,
                "completed_at": "2026-03-29T08:30:00Z",
                "winning_alliance_name": "Iron Crown",
                "winning_player_display_names": ["Arthur", "Morgana"],
            },
        ]
    }


def test_get_public_match_browse_summaries_returns_compact_rows_for_only_non_completed_matches(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'registry-public-match-browse.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    insert_completed_match_fixture(database_url)

    summaries = get_public_match_summaries(database_url=database_url)

    assert summaries.model_dump(mode="json") == {
        "matches": [
            {
                "match_id": "00000000-0000-0000-0000-000000000101",
                "status": "active",
                "map": "britain",
                "tick": 142,
                "tick_interval_seconds": 30,
                "current_player_count": 3,
                "max_player_count": 5,
                "open_slot_count": 2,
            },
            {
                "match_id": "00000000-0000-0000-0000-000000000102",
                "status": "paused",
                "map": "britain",
                "tick": 7,
                "tick_interval_seconds": 45,
                "current_player_count": 0,
                "max_player_count": 5,
                "open_slot_count": 5,
            },
        ]
    }


def test_public_match_browse_summaries_order_rows_by_status_and_recency(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'registry-public-match-ordering.db'}"
    provision_seeded_database(database_url=database_url, reset=True)

    engine = create_engine(database_url)
    with engine.begin() as connection:
        seed_state = json.loads(
            connection.execute(
                text("SELECT state FROM matches WHERE id = :match_id"),
                {"match_id": "00000000-0000-0000-0000-000000000101"},
            ).scalar_one()
        )
        connection.execute(
            text(
                """
                INSERT INTO matches (
                    id, config, status, current_tick, state, winner_alliance, created_at, updated_at
                ) VALUES (
                    :id, :config, :status, :current_tick, :state, :winner_alliance,
                    :created_at, :updated_at
                )
                """
            ),
            [
                {
                    "id": "00000000-0000-0000-0000-000000000103",
                    "config": json.dumps({"map": "britain", "max_players": 6, "turn_seconds": 60}),
                    "status": "lobby",
                    "current_tick": 0,
                    "state": json.dumps({**seed_state, "tick": 0}),
                    "winner_alliance": None,
                    "created_at": "2026-03-29 00:30:00+00:00",
                    "updated_at": "2026-03-29 00:30:00+00:00",
                },
                {
                    "id": "00000000-0000-0000-0000-000000000104",
                    "config": json.dumps({"map": "britain", "max_players": 4, "turn_seconds": 20}),
                    "status": "active",
                    "current_tick": 99,
                    "state": json.dumps(seed_state),
                    "winner_alliance": None,
                    "created_at": "2026-03-29 01:30:00+00:00",
                    "updated_at": "2026-03-29 05:00:00+00:00",
                },
                {
                    "id": "00000000-0000-0000-0000-000000000100",
                    "config": json.dumps({"map": "britain", "max_players": 4, "turn_seconds": 20}),
                    "status": "active",
                    "current_tick": 98,
                    "state": json.dumps(seed_state),
                    "winner_alliance": None,
                    "created_at": "2026-03-29 01:00:00+00:00",
                    "updated_at": "2026-03-29 05:00:00+00:00",
                },
            ],
        )
        connection.execute(
            text(
                """
                INSERT INTO players (
                    id, user_id, match_id, display_name, is_agent, api_key_id, elo_rating,
                    alliance_id, alliance_joined_tick, eliminated_at
                ) VALUES (
                    :id, :user_id, :match_id, :display_name, :is_agent, :api_key_id, :elo_rating,
                    :alliance_id, :alliance_joined_tick, :eliminated_at
                )
                """
            ),
            [
                {
                    "id": "00000000-0000-0000-0000-000000000801",
                    "user_id": "00000000-0000-0000-0000-000000000901",
                    "match_id": "00000000-0000-0000-0000-000000000103",
                    "display_name": "Lobby Host",
                    "is_agent": False,
                    "api_key_id": None,
                    "elo_rating": 1200,
                    "alliance_id": None,
                    "alliance_joined_tick": None,
                    "eliminated_at": None,
                },
                {
                    "id": "00000000-0000-0000-0000-000000000802",
                    "user_id": "00000000-0000-0000-0000-000000000902",
                    "match_id": "00000000-0000-0000-0000-000000000104",
                    "display_name": "Recent Active",
                    "is_agent": False,
                    "api_key_id": None,
                    "elo_rating": 1200,
                    "alliance_id": None,
                    "alliance_joined_tick": None,
                    "eliminated_at": None,
                },
                {
                    "id": "00000000-0000-0000-0000-000000000803",
                    "user_id": "00000000-0000-0000-0000-000000000903",
                    "match_id": "00000000-0000-0000-0000-000000000100",
                    "display_name": "Older Active",
                    "is_agent": False,
                    "api_key_id": None,
                    "elo_rating": 1200,
                    "alliance_id": None,
                    "alliance_joined_tick": None,
                    "eliminated_at": None,
                },
            ],
        )

    summaries = get_public_match_summaries(database_url=database_url)

    assert [match.match_id for match in summaries.matches] == [
        "00000000-0000-0000-0000-000000000103",
        "00000000-0000-0000-0000-000000000104",
        "00000000-0000-0000-0000-000000000100",
        "00000000-0000-0000-0000-000000000101",
        "00000000-0000-0000-0000-000000000102",
    ]


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
