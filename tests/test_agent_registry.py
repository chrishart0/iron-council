from __future__ import annotations

from server.agent_registry import (
    AdvancedMatchTick,
    InMemoryMatchRegistry,
    MatchAccessError,
    MatchJoinError,
    MatchRecord,
    build_seeded_agent_api_key,
    build_seeded_match_records,
)
from server.models.api import AllianceActionRequest
from server.models.domain import MatchStatus
from server.models.orders import OrderEnvelope
from server.models.state import MatchState


def test_join_initializes_victory_countdown_for_new_sole_leader() -> None:
    registry = InMemoryMatchRegistry()
    registry.seed_match(
        MatchRecord(
            match_id="countdown-match",
            status=MatchStatus.ACTIVE,
            tick_interval_seconds=30,
            state=MatchState.model_validate(
                {
                    "tick": 12,
                    "cities": {
                        "alpha": {
                            "owner": "player-1",
                            "population": 5,
                            "resources": {"food": 1, "production": 1, "money": 1},
                            "upgrades": {"economy": 0, "military": 0, "fortification": 0},
                            "garrison": 3,
                            "building_queue": [],
                        },
                        "beta": {
                            "owner": "player-2",
                            "population": 5,
                            "resources": {"food": 1, "production": 1, "money": 1},
                            "upgrades": {"economy": 0, "military": 0, "fortification": 0},
                            "garrison": 3,
                            "building_queue": [],
                        },
                    },
                    "players": {
                        "player-1": {
                            "resources": {"food": 5, "production": 5, "money": 5},
                            "cities_owned": ["alpha"],
                            "alliance_id": None,
                            "is_eliminated": False,
                        },
                        "player-2": {
                            "resources": {"food": 5, "production": 5, "money": 5},
                            "cities_owned": ["beta"],
                            "alliance_id": None,
                            "is_eliminated": False,
                        },
                    },
                    "victory": {
                        "leading_alliance": None,
                        "cities_held": 1,
                        "threshold": 2,
                        "countdown_ticks_remaining": None,
                    },
                }
            ),
        )
    )

    created_alliance = registry.apply_alliance_action(
        match_id="countdown-match",
        action=AllianceActionRequest(
            match_id="countdown-match",
            action="create",
            name="Northern Pact",
        ),
        player_id="player-1",
    )
    joined_alliance = registry.apply_alliance_action(
        match_id="countdown-match",
        action=AllianceActionRequest(
            match_id="countdown-match",
            action="join",
            alliance_id=created_alliance.alliance_id if created_alliance is not None else None,
            name=None,
        ),
        player_id="player-2",
    )

    assert joined_alliance is not None
    match = registry.get_match("countdown-match")
    assert match is not None
    assert match.state.victory.model_dump(mode="json") == {
        "leading_alliance": joined_alliance.alliance_id,
        "cities_held": 2,
        "threshold": 2,
        "countdown_ticks_remaining": 2,
    }


def test_sync_victory_state_ignores_unowned_and_unknown_city_holders() -> None:
    registry = InMemoryMatchRegistry()
    state = MatchState.model_validate(
        {
            "tick": 8,
            "cities": {
                "alpha": {
                    "owner": None,
                    "population": 5,
                    "resources": {"food": 1, "production": 1, "money": 1},
                    "upgrades": {"economy": 0, "military": 0, "fortification": 0},
                    "garrison": 3,
                    "building_queue": [],
                },
                "beta": {
                    "owner": "ghost-player",
                    "population": 5,
                    "resources": {"food": 1, "production": 1, "money": 1},
                    "upgrades": {"economy": 0, "military": 0, "fortification": 0},
                    "garrison": 3,
                    "building_queue": [],
                },
            },
            "players": {
                "player-1": {
                    "resources": {"food": 5, "production": 5, "money": 5},
                    "cities_owned": [],
                    "alliance_id": None,
                    "is_eliminated": False,
                }
            },
            "victory": {
                "leading_alliance": "alliance-red",
                "cities_held": 2,
                "threshold": 2,
                "countdown_ticks_remaining": 1,
            },
        }
    )

    registry._sync_victory_state(state)  # noqa: SLF001

    assert state.victory.model_dump(mode="json") == {
        "leading_alliance": None,
        "cities_held": 0,
        "threshold": 2,
        "countdown_ticks_remaining": None,
    }


def test_sync_victory_state_reinitializes_missing_countdown_for_same_leader() -> None:
    registry = InMemoryMatchRegistry()
    state = MatchState.model_validate(
        {
            "tick": 8,
            "cities": {
                "alpha": {
                    "owner": "player-1",
                    "population": 5,
                    "resources": {"food": 1, "production": 1, "money": 1},
                    "upgrades": {"economy": 0, "military": 0, "fortification": 0},
                    "garrison": 3,
                    "building_queue": [],
                },
                "beta": {
                    "owner": "player-2",
                    "population": 5,
                    "resources": {"food": 1, "production": 1, "money": 1},
                    "upgrades": {"economy": 0, "military": 0, "fortification": 0},
                    "garrison": 3,
                    "building_queue": [],
                },
            },
            "players": {
                "player-1": {
                    "resources": {"food": 5, "production": 5, "money": 5},
                    "cities_owned": ["alpha"],
                    "alliance_id": "alliance-red",
                    "is_eliminated": False,
                },
                "player-2": {
                    "resources": {"food": 5, "production": 5, "money": 5},
                    "cities_owned": ["beta"],
                    "alliance_id": "alliance-red",
                    "is_eliminated": False,
                },
            },
            "victory": {
                "leading_alliance": "alliance-red",
                "cities_held": 2,
                "threshold": 2,
                "countdown_ticks_remaining": None,
            },
        }
    )

    registry._sync_victory_state(state)  # noqa: SLF001

    assert state.victory.model_dump(mode="json") == {
        "leading_alliance": "alliance-red",
        "cities_held": 2,
        "threshold": 2,
        "countdown_ticks_remaining": 2,
    }


def test_join_assigns_first_open_slot_and_is_idempotent_for_seeded_agent() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    first_join = registry.join_match(match_id="match-beta", agent_id="agent-player-2")
    repeat_join = registry.join_match(match_id="match-beta", agent_id="agent-player-2")
    second_join = registry.join_match(match_id="match-beta", agent_id="agent-player-3")

    assert first_join.model_dump(mode="json") == {
        "status": "accepted",
        "match_id": "match-beta",
        "agent_id": "agent-player-2",
        "player_id": "player-1",
    }
    assert repeat_join.model_dump(mode="json") == first_join.model_dump(mode="json")
    assert second_join.model_dump(mode="json") == {
        "status": "accepted",
        "match_id": "match-beta",
        "agent_id": "agent-player-3",
        "player_id": "player-2",
    }


def test_require_joined_player_id_returns_existing_mapping_after_join() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    join_response = registry.join_match(match_id="match-beta", agent_id="agent-player-2")

    assert (
        registry.require_joined_player_id(match_id="match-beta", agent_id="agent-player-2")
        == join_response.player_id
    )


def test_require_joined_player_id_rejects_authenticated_agent_without_join_mapping() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    try:
        registry.require_joined_player_id(match_id="match-beta", agent_id="agent-player-2")
    except MatchAccessError as exc:
        assert exc.code == "agent_not_joined"
        assert exc.message == (
            "Agent 'agent-player-2' has not joined match 'match-beta' as a player."
        )
    else:
        raise AssertionError("expected MatchAccessError for unjoined authenticated access")


def test_registry_list_helpers_return_empty_for_unknown_match() -> None:
    registry = InMemoryMatchRegistry()

    assert registry.list_order_submissions("match-missing") == []
    assert registry.list_treaties(match_id="match-missing") == []
    assert registry.list_alliances(match_id="match-missing") == []


def test_get_agent_profile_returns_stable_seeded_placeholder_shape() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    profile = registry.get_agent_profile("agent-player-2")

    assert profile is not None
    assert profile.model_dump(mode="json") == {
        "agent_id": "agent-player-2",
        "display_name": "Morgana",
        "is_seeded": True,
        "rating": {"elo": 1190, "provisional": True},
        "history": {"matches_played": 0, "wins": 0, "losses": 0, "draws": 0},
    }


def test_resolve_authenticated_agent_returns_seeded_identity_without_raw_key_material() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    authenticated_agent = registry.resolve_authenticated_agent(
        build_seeded_agent_api_key("agent-player-2")
    )

    assert authenticated_agent is not None
    assert authenticated_agent.model_dump(mode="json") == {
        "agent_id": "agent-player-2",
        "display_name": "Morgana",
        "is_seeded": True,
    }


def test_resolve_authenticated_agent_rejects_unknown_and_inactive_keys() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)
    registry.deactivate_agent_api_key("agent-player-3")

    assert registry.resolve_authenticated_agent("missing-key") is None
    assert (
        registry.resolve_authenticated_agent(build_seeded_agent_api_key("agent-player-3")) is None
    )


def test_join_rejects_non_joinable_and_full_matches_without_side_effects() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    non_joinable_match = registry.get_match("match-alpha")
    assert non_joinable_match is not None
    baseline_non_joinable_assignments = dict(non_joinable_match.joined_agents)

    try:
        registry.join_match(match_id="match-alpha", agent_id="agent-player-new")
    except MatchJoinError as exc:
        error = exc
    else:  # pragma: no cover
        raise AssertionError("expected non-joinable match to reject join")

    assert error.code == "match_not_joinable"
    assert error.message == "Match 'match-alpha' does not support agent joins."
    assert non_joinable_match.joined_agents == baseline_non_joinable_assignments

    registry.join_match(match_id="match-beta", agent_id="agent-player-1")
    registry.join_match(match_id="match-beta", agent_id="agent-player-2")
    registry.join_match(match_id="match-beta", agent_id="agent-player-3")
    registry.join_match(match_id="match-beta", agent_id="agent-player-4")
    registry.join_match(match_id="match-beta", agent_id="agent-player-5")

    full_match = registry.get_match("match-beta")
    assert full_match is not None
    baseline_full_assignments = dict(full_match.joined_agents)

    try:
        registry.join_match(match_id="match-beta", agent_id="agent-overflow")
    except MatchJoinError as exc:
        error = exc
    else:  # pragma: no cover
        raise AssertionError("expected full match to reject join")

    assert error.code == "no_open_slots"
    assert error.message == "Match 'match-beta' has no open join slots."
    assert full_match.joined_agents == baseline_full_assignments


def test_reset_clears_seeded_matches_and_profiles() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    registry.reset()

    assert registry.list_matches() == []
    assert registry.get_match("match-alpha") is None
    assert registry.get_agent_profile("agent-player-2") is None


def test_advance_match_tick_resolves_current_orders_and_keeps_future_submissions_queued() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    registry.record_submission(
        match_id="match-alpha",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-1",
                "tick": 142,
                "orders": {
                    "movements": [],
                    "recruitment": [{"city": "london", "troops": 5}],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )
    registry.record_submission(
        match_id="match-alpha",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-1",
                "tick": 143,
                "orders": {
                    "movements": [],
                    "recruitment": [{"city": "london", "troops": 1}],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )

    registry.advance_match_tick("match-alpha")

    match = registry.get_match("match-alpha")
    assert match is not None
    assert match.state.tick == 143
    assert next(army for army in match.state.armies if army.id == "army-b").troops == 25
    assert [submission.model_dump(mode="json") for submission in match.order_submissions] == [
        {
            "match_id": "match-alpha",
            "player_id": "player-1",
            "tick": 143,
            "orders": {
                "movements": [],
                "recruitment": [{"city": "london", "troops": 1}],
                "upgrades": [],
                "transfers": [],
            },
        }
    ]


def test_advance_match_tick_combines_same_player_submissions_before_validation() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    registry.record_submission(
        match_id="match-alpha",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-1",
                "tick": 142,
                "orders": {
                    "movements": [],
                    "recruitment": [{"city": "london", "troops": 4}],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )
    registry.record_submission(
        match_id="match-alpha",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-1",
                "tick": 142,
                "orders": {
                    "movements": [],
                    "recruitment": [{"city": "london", "troops": 4}],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )

    registry.advance_match_tick("match-alpha")

    match = registry.get_match("match-alpha")
    assert match is not None
    assert match.state.tick == 143
    assert match.state.players["player-1"].resources.model_dump(mode="json") == {
        "food": 83,
        "production": 47,
        "money": 213,
    }
    assert [
        (army.id, army.location, army.owner, army.troops)
        for army in match.state.armies
        if army.owner == "player-1" and army.location == "london"
    ] == [("army-b", "london", "player-1", 28)]
    assert match.order_submissions == []


def test_advance_match_tick_returns_resolved_tick_contract_for_persistence() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    registry.record_submission(
        match_id="match-alpha",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-1",
                "tick": 142,
                "orders": {
                    "movements": [],
                    "recruitment": [{"city": "london", "troops": 5}],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )
    registry.record_submission(
        match_id="match-alpha",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-1",
                "tick": 143,
                "orders": {
                    "movements": [],
                    "recruitment": [{"city": "london", "troops": 1}],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )

    advanced_tick = registry.advance_match_tick("match-alpha")

    assert isinstance(advanced_tick, AdvancedMatchTick)
    assert advanced_tick.match_id == "match-alpha"
    assert advanced_tick.resolved_tick == 143
    assert advanced_tick.next_state.tick == 143
    assert advanced_tick.accepted_orders.model_dump(mode="json") == {
        "movements": [],
        "recruitment": [{"city": "london", "troops": 5}],
        "upgrades": [],
        "transfers": [],
    }
    assert [event.model_dump(mode="json") for event in advanced_tick.events] == [
        {"phase": "resource", "event": "phase.resource.completed"},
        {"phase": "build", "event": "phase.build.completed"},
        {"phase": "movement", "event": "phase.movement.completed"},
        {"phase": "combat", "event": "phase.combat.completed"},
        {"phase": "siege", "event": "phase.siege.completed"},
        {"phase": "attrition", "event": "phase.attrition.completed"},
        {"phase": "diplomacy", "event": "phase.diplomacy.completed"},
        {"phase": "victory", "event": "phase.victory.completed"},
    ]

    match = registry.get_match("match-alpha")
    assert match is not None
    assert [submission.model_dump(mode="json") for submission in match.order_submissions] == [
        {
            "match_id": "match-alpha",
            "player_id": "player-1",
            "tick": 143,
            "orders": {
                "movements": [],
                "recruitment": [{"city": "london", "troops": 1}],
                "upgrades": [],
                "transfers": [],
            },
        }
    ]
