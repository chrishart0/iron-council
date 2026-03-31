from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

from server.db import registry as db_registry_module
from sqlalchemy import create_engine, text


@dataclass(frozen=True)
class RunningApp:
    base_url: str
    primary_match_id: str
    secondary_match_id: str
    database_url: str


_SEEDED_AGENT_PLAYER_ROWS = {
    "agent-player-2": {
        "user_id": "00000000-0000-0000-0000-000000000302",
        "display_name": "Morgana",
        "api_key_id": "00000000-0000-0000-0000-000000000202",
        "elo_rating": 1190,
    },
    "agent-player-3": {
        "user_id": "00000000-0000-0000-0000-000000000303",
        "display_name": "Gawain",
        "api_key_id": "00000000-0000-0000-0000-000000000203",
        "elo_rating": 1175,
    },
}

_SEEDED_HUMAN_PLAYER_ROWS = {
    "00000000-0000-0000-0000-000000000301": {
        "display_name": "Arthur",
        "elo_rating": 1210,
    },
    "00000000-0000-0000-0000-000000000304": {
        "display_name": "Bedivere",
        "elo_rating": 1190,
    },
}


def build_persisted_player_id(*, match_id: str, public_player_id: str) -> str:
    prefix = "player-"
    if not public_player_id.startswith(prefix):
        raise ValueError(f"Unsupported public player id: {public_player_id!r}")
    return db_registry_module._build_match_scoped_player_id(
        match_id=match_id,
        join_index=int(public_player_id.removeprefix(prefix)),
    )


def insert_seeded_agent_player(
    *,
    database_url: str,
    match_id: str,
    agent_id: str,
    persisted_player_id: str,
) -> None:
    seeded_player = _SEEDED_AGENT_PLAYER_ROWS[agent_id]
    engine = create_engine(database_url)
    with engine.begin() as connection:
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
            {
                "id": persisted_player_id,
                "user_id": seeded_player["user_id"],
                "match_id": match_id,
                "display_name": seeded_player["display_name"],
                "is_agent": True,
                "api_key_id": seeded_player["api_key_id"],
                "elo_rating": seeded_player["elo_rating"],
                "alliance_id": None,
                "alliance_joined_tick": None,
                "eliminated_at": None,
            },
        )


def insert_seeded_human_player(
    *,
    database_url: str,
    match_id: str,
    user_id: str,
    persisted_player_id: str,
) -> None:
    seeded_player = _SEEDED_HUMAN_PLAYER_ROWS[user_id]
    engine = create_engine(database_url)
    with engine.begin() as connection:
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
            {
                "id": persisted_player_id,
                "user_id": user_id,
                "match_id": match_id,
                "display_name": seeded_player["display_name"],
                "is_agent": False,
                "api_key_id": None,
                "elo_rating": seeded_player["elo_rating"],
                "alliance_id": None,
                "alliance_joined_tick": None,
                "eliminated_at": None,
            },
        )


def insert_completed_match_fixture(database_url: str) -> None:
    engine = create_engine(database_url)
    with engine.begin() as connection:
        seed_state = json.loads(
            connection.execute(
                text("SELECT state FROM matches WHERE id = :match_id"),
                {"match_id": "00000000-0000-0000-0000-000000000101"},
            ).scalar_one()
        )
        completed_state_one = {**seed_state, "tick": 155}
        completed_state_two = {**seed_state, "tick": 200}
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
                    "id": "00000000-0000-0000-0000-000000000201",
                    "config": json.dumps({"map": "britain", "max_players": 4, "turn_seconds": 30}),
                    "status": "completed",
                    "current_tick": 155,
                    "state": json.dumps(completed_state_one),
                    "winner_alliance": "00000000-0000-0000-0000-000000000801",
                    "created_at": "2026-03-29 08:00:00+00:00",
                    "updated_at": "2026-03-29 08:30:00+00:00",
                },
                {
                    "id": "00000000-0000-0000-0000-000000000202",
                    "config": json.dumps(
                        {"map": "mediterranean", "max_players": 4, "turn_seconds": 45}
                    ),
                    "status": "completed",
                    "current_tick": 200,
                    "state": json.dumps(completed_state_two),
                    "winner_alliance": None,
                    "created_at": "2026-03-29 12:00:00+00:00",
                    "updated_at": "2026-03-29 12:15:00+00:00",
                },
            ],
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
                "id": "00000000-0000-0000-0000-000000000801",
                "match_id": "00000000-0000-0000-0000-000000000201",
                "name": "Iron Crown",
                "leader_id": build_persisted_player_id(
                    match_id="00000000-0000-0000-0000-000000000201",
                    public_player_id="player-1",
                ),
                "formed_tick": 120,
                "dissolved_tick": None,
            },
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
                    "id": build_persisted_player_id(
                        match_id="00000000-0000-0000-0000-000000000201",
                        public_player_id="player-1",
                    ),
                    "user_id": "00000000-0000-0000-0000-000000000301",
                    "match_id": "00000000-0000-0000-0000-000000000201",
                    "display_name": "Arthur",
                    "is_agent": False,
                    "api_key_id": None,
                    "elo_rating": 1210,
                    "alliance_id": "00000000-0000-0000-0000-000000000801",
                    "alliance_joined_tick": 120,
                    "eliminated_at": None,
                },
                {
                    "id": build_persisted_player_id(
                        match_id="00000000-0000-0000-0000-000000000201",
                        public_player_id="player-2",
                    ),
                    "user_id": "00000000-0000-0000-0000-000000000302",
                    "match_id": "00000000-0000-0000-0000-000000000201",
                    "display_name": "Morgana",
                    "is_agent": True,
                    "api_key_id": "00000000-0000-0000-0000-000000000202",
                    "elo_rating": 1190,
                    "alliance_id": "00000000-0000-0000-0000-000000000801",
                    "alliance_joined_tick": 120,
                    "eliminated_at": None,
                },
                {
                    "id": build_persisted_player_id(
                        match_id="00000000-0000-0000-0000-000000000201",
                        public_player_id="player-3",
                    ),
                    "user_id": "00000000-0000-0000-0000-000000000303",
                    "match_id": "00000000-0000-0000-0000-000000000201",
                    "display_name": "Gawain",
                    "is_agent": True,
                    "api_key_id": "00000000-0000-0000-0000-000000000203",
                    "elo_rating": 1175,
                    "alliance_id": None,
                    "alliance_joined_tick": None,
                    "eliminated_at": None,
                },
                {
                    "id": build_persisted_player_id(
                        match_id="00000000-0000-0000-0000-000000000202",
                        public_player_id="player-1",
                    ),
                    "user_id": "00000000-0000-0000-0000-000000000302",
                    "match_id": "00000000-0000-0000-0000-000000000202",
                    "display_name": "Morgana",
                    "is_agent": True,
                    "api_key_id": "00000000-0000-0000-0000-000000000202",
                    "elo_rating": 1190,
                    "alliance_id": None,
                    "alliance_joined_tick": None,
                    "eliminated_at": None,
                },
                {
                    "id": build_persisted_player_id(
                        match_id="00000000-0000-0000-0000-000000000202",
                        public_player_id="player-2",
                    ),
                    "user_id": "00000000-0000-0000-0000-000000000304",
                    "match_id": "00000000-0000-0000-0000-000000000202",
                    "display_name": "Bedivere",
                    "is_agent": False,
                    "api_key_id": None,
                    "elo_rating": 1190,
                    "alliance_id": None,
                    "alliance_joined_tick": None,
                    "eliminated_at": None,
                },
            ],
        )


def load_python_agent_sdk_module() -> ModuleType:
    sdk_path = Path(__file__).resolve().parents[1] / "agent-sdk/python/iron_council_client.py"
    spec = spec_from_file_location("iron_council_client", sdk_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load SDK module from {sdk_path}.")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
