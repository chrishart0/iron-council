from __future__ import annotations

from typing import TYPE_CHECKING, Any

from server.auth import hash_api_key
from server.models.api import (
    AgentProfileHistory,
    AgentProfileRating,
    AgentProfileResponse,
)
from server.models.domain import MatchStatus
from server.models.state import MatchState

if TYPE_CHECKING:
    from server.agent_registry import AuthenticatedAgentKeyRecord, MatchRecord


def build_seeded_match_records(
    *,
    primary_match_id: str = "match-alpha",
    secondary_match_id: str = "match-beta",
) -> list[MatchRecord]:
    from server.agent_registry import MatchRecord

    seeded_profiles = build_seeded_agent_profiles()
    seeded_authenticated_keys = build_seeded_authenticated_agent_keys()
    return [
        MatchRecord(
            match_id=primary_match_id,
            status=MatchStatus.ACTIVE,
            tick_interval_seconds=30,
            state=MatchState.model_validate(_seeded_match_state_payload()),
            max_player_count=5,
            current_player_count=3,
            agent_profiles=seeded_profiles,
            public_competitor_kinds={
                "player-1": "human",
                "player-2": "agent",
                "player-3": "agent",
            },
            joined_agents={
                f"agent-{player_id}": player_id
                for player_id in _seeded_match_state_payload()["players"]
            },
            joined_humans={
                "00000000-0000-0000-0000-000000000301": "player-1",
                "00000000-0000-0000-0000-000000000302": "player-2",
                "00000000-0000-0000-0000-000000000303": "player-3",
            },
            authenticated_agent_keys=seeded_authenticated_keys,
        ),
        MatchRecord(
            match_id=secondary_match_id,
            status=MatchStatus.PAUSED,
            tick_interval_seconds=45,
            max_player_count=5,
            current_player_count=0,
            joinable_player_ids=sorted(_seeded_match_state_payload()["players"]),
            state=MatchState.model_validate(
                {
                    **_seeded_match_state_payload(),
                    "tick": 7,
                }
            ),
            agent_profiles=seeded_profiles,
            authenticated_agent_keys=seeded_authenticated_keys,
        ),
    ]


def build_seeded_agent_profiles() -> list[AgentProfileResponse]:
    seeded_profile_specs = (
        ("player-1", "Arthur", 1210),
        ("player-2", "Morgana", 1190),
        ("player-3", "Gawain", 1175),
        ("player-4", "Lancelot", 1160),
        ("player-5", "Percival", 1140),
    )
    return [
        AgentProfileResponse(
            agent_id=f"agent-{player_id}",
            display_name=display_name,
            is_seeded=True,
            rating=AgentProfileRating(elo=elo_rating, provisional=True),
            history=AgentProfileHistory(
                matches_played=0,
                wins=0,
                losses=0,
                draws=0,
            ),
        )
        for player_id, display_name, elo_rating in seeded_profile_specs
    ]


def build_seeded_agent_api_key(agent_id: str) -> str:
    return f"seed-api-key-for-{agent_id}"


def build_seeded_authenticated_agent_keys() -> list[AuthenticatedAgentKeyRecord]:
    from server.agent_registry import AuthenticatedAgentKeyRecord

    return [
        AuthenticatedAgentKeyRecord(
            agent_id=profile.agent_id,
            key_hash=hash_api_key(build_seeded_agent_api_key(profile.agent_id)),
            is_active=True,
        )
        for profile in build_seeded_agent_profiles()
    ]


def build_seeded_profiles_by_key_hash() -> dict[str, AgentProfileResponse]:
    return {
        hash_api_key(build_seeded_agent_api_key(profile.agent_id)): profile
        for profile in build_seeded_agent_profiles()
    }


def _seeded_match_state_payload() -> dict[str, Any]:
    return {
        "tick": 142,
        "cities": {
            "london": {
                "owner": "player-1",
                "population": 12,
                "resources": {"food": 3, "production": 2, "money": 8},
                "upgrades": {"economy": 2, "military": 1, "fortification": 0},
                "garrison": 15,
                "building_queue": [{"type": "fortification", "tier": 1, "ticks_remaining": 3}],
            },
            "manchester": {
                "owner": "player-2",
                "population": 10,
                "resources": {"food": 2, "production": 4, "money": 1},
                "upgrades": {"economy": 0, "military": 1, "fortification": 0},
                "garrison": 9,
                "building_queue": [],
            },
            "birmingham": {
                "owner": "player-3",
                "population": 8,
                "resources": {"food": 1, "production": 5, "money": 1},
                "upgrades": {"economy": 0, "military": 0, "fortification": 1},
                "garrison": 7,
                "building_queue": [],
            },
            "leeds": {
                "owner": "player-4",
                "population": 7,
                "resources": {"food": 1, "production": 3, "money": 1},
                "upgrades": {"economy": 1, "military": 0, "fortification": 0},
                "garrison": 11,
                "building_queue": [],
            },
            "inverness": {
                "owner": "player-5",
                "population": 5,
                "resources": {"food": 3, "production": 1, "money": 0},
                "upgrades": {"economy": 0, "military": 2, "fortification": 0},
                "garrison": 13,
                "building_queue": [],
            },
        },
        "armies": [
            {
                "id": "army-c",
                "owner": "player-3",
                "troops": 18,
                "location": None,
                "destination": "birmingham",
                "path": ["birmingham"],
                "ticks_remaining": 2,
            },
            {
                "id": "army-a",
                "owner": "player-2",
                "troops": 14,
                "location": None,
                "destination": "leeds",
                "path": ["leeds"],
                "ticks_remaining": 1,
            },
            {
                "id": "army-b",
                "owner": "player-1",
                "troops": 20,
                "location": "london",
                "destination": None,
                "path": None,
                "ticks_remaining": 0,
            },
            {
                "id": "army-z",
                "owner": "player-5",
                "troops": 25,
                "location": None,
                "destination": "inverness",
                "path": ["inverness"],
                "ticks_remaining": 3,
            },
        ],
        "players": {
            "player-1": {
                "resources": {"food": 120, "production": 85, "money": 200},
                "cities_owned": ["london"],
                "alliance_id": "alliance-red",
                "is_eliminated": False,
            },
            "player-2": {
                "resources": {"food": 90, "production": 70, "money": 110},
                "cities_owned": ["manchester"],
                "alliance_id": "alliance-red",
                "is_eliminated": False,
            },
            "player-3": {
                "resources": {"food": 75, "production": 65, "money": 80},
                "cities_owned": ["birmingham"],
                "alliance_id": None,
                "is_eliminated": False,
            },
            "player-4": {
                "resources": {"food": 60, "production": 55, "money": 70},
                "cities_owned": ["leeds"],
                "alliance_id": None,
                "is_eliminated": False,
            },
            "player-5": {
                "resources": {"food": 40, "production": 35, "money": 30},
                "cities_owned": ["inverness"],
                "alliance_id": None,
                "is_eliminated": False,
            },
        },
        "victory": {
            "leading_alliance": "alliance-red",
            "cities_held": 2,
            "threshold": 13,
            "countdown_ticks_remaining": None,
        },
    }
