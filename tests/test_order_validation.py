from __future__ import annotations

from copy import deepcopy

from server.data.maps import CityCoordinates, CityDefinition, MapDefinition, MapEdge
from server.models.domain import ResourceType, UpgradeTrack
from server.models.orders import OrderEnvelope
from server.models.state import (
    ArmyState,
    CityState,
    CityUpgradeState,
    MatchState,
    PlayerState,
    ResourceState,
    VictoryState,
)
from server.order_validation import RECRUITMENT_COST_PER_TROOP, validate_order_envelope


def _test_map() -> MapDefinition:
    return MapDefinition(
        map_id="validation_test_map",
        name="Validation Test Map",
        cities={
            "alpha": _city_definition(ResourceType.FOOD),
            "bravo": _city_definition(ResourceType.PRODUCTION),
            "charlie": _city_definition(ResourceType.MONEY),
            "delta": _city_definition(ResourceType.FOOD),
            "echo": _city_definition(ResourceType.PRODUCTION),
        },
        edges=[
            MapEdge(city_a="alpha", city_b="bravo", distance_ticks=1),
            MapEdge(city_a="bravo", city_b="charlie", distance_ticks=1),
            MapEdge(city_a="charlie", city_b="delta", distance_ticks=1),
            MapEdge(city_a="alpha", city_b="echo", distance_ticks=2, traversal_mode="sea"),
        ],
    )


def _city_definition(primary_resource: ResourceType) -> CityDefinition:
    return CityDefinition(
        name=f"{primary_resource.value}-city",
        region="Test",
        primary_resource=primary_resource,
        notes="",
        position=CityCoordinates(x=1, y=1),
    )


def _match_state() -> MatchState:
    return MatchState(
        tick=5,
        cities={
            "alpha": _city_state(owner="player_1"),
            "bravo": _city_state(owner="player_1"),
            "charlie": _city_state(owner="player_2"),
            "delta": _city_state(owner="player_2"),
            "echo": _city_state(owner=None),
        },
        armies=[
            ArmyState(
                id="army_ready",
                owner="player_1",
                troops=8,
                location="alpha",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="army_transit",
                owner="player_1",
                troops=5,
                location=None,
                destination="bravo",
                path=["alpha", "bravo"],
                ticks_remaining=1,
            ),
            ArmyState(
                id="army_other",
                owner="player_2",
                troops=7,
                location="charlie",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=10, production=20, money=30),
                cities_owned=["alpha", "bravo"],
                alliance_id="alliance_red",
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=5, production=6, money=7),
                cities_owned=["charlie", "delta"],
                alliance_id="alliance_red",
                is_eliminated=False,
            ),
            "player_3": PlayerState(
                resources=ResourceState(food=9, production=9, money=9),
                cities_owned=[],
                alliance_id=None,
                is_eliminated=False,
            ),
        },
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            threshold=3,
            countdown_ticks_remaining=None,
        ),
    )


def _city_state(*, owner: str | None) -> CityState:
    return CityState(
        owner=owner,
        population=10,
        resources=ResourceState(food=1, production=1, money=1),
        upgrades=CityUpgradeState(economy=0, military=0, fortification=0),
        garrison=5,
        building_queue=[],
    )


def _order_envelope(
    *,
    player_id: str = "player_1",
    tick: int = 5,
    movements: list[dict[str, object]] | None = None,
    recruitment: list[dict[str, object]] | None = None,
    upgrades: list[dict[str, object]] | None = None,
    transfers: list[dict[str, object]] | None = None,
) -> OrderEnvelope:
    return OrderEnvelope.model_validate(
        {
            "match_id": "match_1",
            "player_id": player_id,
            "tick": tick,
            "orders": {
                "movements": movements or [],
                "recruitment": recruitment or [],
                "upgrades": upgrades or [],
                "transfers": transfers or [],
            },
        }
    )


def test_validate_order_envelope_accepts_valid_mixed_orders() -> None:
    result = validate_order_envelope(
        _order_envelope(
            movements=[{"army_id": "army_ready", "destination": "bravo"}],
            recruitment=[{"city": "alpha", "troops": 2}],
            upgrades=[{"city": "alpha", "track": "fortification", "target_tier": 1}],
            transfers=[
                {"to": "player_2", "resource": "food", "amount": 2},
                {"to": "player_3", "resource": "money", "amount": 4},
            ],
        ),
        _match_state(),
        _test_map(),
    )

    assert result.accepted.model_dump(mode="json") == {
        "movements": [{"army_id": "army_ready", "destination": "bravo"}],
        "recruitment": [{"city": "alpha", "troops": 2}],
        "upgrades": [{"city": "alpha", "track": "fortification", "target_tier": 1}],
        "transfers": [
            {"to": "player_2", "resource": "food", "amount": 2},
            {"to": "player_3", "resource": "money", "amount": 4},
        ],
    }
    assert result.rejected == []


def test_validate_order_envelope_rejects_late_orders_with_structured_reasons() -> None:
    result = validate_order_envelope(
        _order_envelope(
            tick=4,
            movements=[{"army_id": "army_ready", "destination": "bravo"}],
            recruitment=[{"city": "alpha", "troops": 1}],
            upgrades=[{"city": "alpha", "track": "fortification", "target_tier": 1}],
            transfers=[{"to": "player_2", "resource": "money", "amount": 1}],
        ),
        _match_state(),
        _test_map(),
    )

    assert result.accepted.model_dump(mode="json") == {
        "movements": [],
        "recruitment": [],
        "upgrades": [],
        "transfers": [],
    }
    assert [rejection.reason_code for rejection in result.rejected] == [
        "late_order",
        "late_order",
        "late_order",
        "late_order",
    ]
    assert [rejection.order_type for rejection in result.rejected] == [
        "movement",
        "recruitment",
        "upgrade",
        "transfer",
    ]


def test_validate_order_envelope_rejects_all_orders_for_unknown_sender() -> None:
    result = validate_order_envelope(
        _order_envelope(
            player_id="missing_player",
            movements=[{"army_id": "army_ready", "destination": "bravo"}],
            recruitment=[{"city": "alpha", "troops": 1}],
            upgrades=[{"city": "alpha", "track": "fortification", "target_tier": 1}],
            transfers=[{"to": "player_2", "resource": "money", "amount": 1}],
        ),
        _match_state(),
        _test_map(),
    )

    assert result.accepted.model_dump(mode="json") == {
        "movements": [],
        "recruitment": [],
        "upgrades": [],
        "transfers": [],
    }
    assert [rejection.reason_code for rejection in result.rejected] == [
        "unknown_player",
        "unknown_player",
        "unknown_player",
        "unknown_player",
    ]


def test_validate_order_envelope_rejects_invalid_ownership_entities_and_adjacency() -> None:
    state = _match_state()
    state.armies.append(
        ArmyState(
            id="army_ready_2",
            owner="player_1",
            troops=6,
            location="alpha",
            destination=None,
            path=None,
            ticks_remaining=0,
        )
    )

    result = validate_order_envelope(
        _order_envelope(
            movements=[
                {"army_id": "missing_army", "destination": "bravo"},
                {"army_id": "army_ready", "destination": "missing_city"},
                {"army_id": "army_other", "destination": "delta"},
                {"army_id": "army_ready_2", "destination": "delta"},
                {"army_id": "army_transit", "destination": "alpha"},
            ],
            recruitment=[
                {"city": "missing_city", "troops": 1},
                {"city": "charlie", "troops": 1},
            ],
            upgrades=[
                {"city": "missing_city", "track": "fortification", "target_tier": 1},
                {"city": "charlie", "track": "fortification", "target_tier": 1},
            ],
            transfers=[{"to": "missing_player", "resource": "money", "amount": 1}],
        ),
        state,
        _test_map(),
    )

    assert result.accepted.model_dump(mode="json") == {
        "movements": [],
        "recruitment": [],
        "upgrades": [],
        "transfers": [],
    }
    assert [(rejection.order_type, rejection.reason_code) for rejection in result.rejected] == [
        ("movement", "unknown_army"),
        ("movement", "unknown_city"),
        ("movement", "invalid_ownership"),
        ("movement", "invalid_adjacency"),
        ("movement", "army_in_transit"),
        ("recruitment", "unknown_city"),
        ("recruitment", "invalid_ownership"),
        ("upgrade", "unknown_city"),
        ("upgrade", "invalid_ownership"),
        ("transfer", "unknown_player"),
    ]


def test_validate_order_envelope_rejects_second_conflicting_movement_order() -> None:
    result = validate_order_envelope(
        _order_envelope(
            movements=[
                {"army_id": "army_ready", "destination": "bravo"},
                {"army_id": "army_ready", "destination": "echo"},
            ]
        ),
        _match_state(),
        _test_map(),
    )

    assert result.accepted.model_dump(mode="json") == {
        "movements": [{"army_id": "army_ready", "destination": "bravo"}],
        "recruitment": [],
        "upgrades": [],
        "transfers": [],
    }
    assert [(rejection.order_type, rejection.reason_code) for rejection in result.rejected] == [
        ("movement", "conflicting_duplicate_order"),
    ]
    assert result.rejected[0].message == (
        "movement order 1 conflicts with an earlier movement order for "
        "army 'army_ready' in the same envelope"
    )


def test_validate_order_envelope_accepts_valid_movement_after_invalid_duplicate_candidate() -> None:
    result = validate_order_envelope(
        _order_envelope(
            movements=[
                {"army_id": "army_ready", "destination": "delta"},
                {"army_id": "army_ready", "destination": "bravo"},
            ]
        ),
        _match_state(),
        _test_map(),
    )

    assert result.accepted.model_dump(mode="json") == {
        "movements": [{"army_id": "army_ready", "destination": "bravo"}],
        "recruitment": [],
        "upgrades": [],
        "transfers": [],
    }
    assert [(rejection.order_type, rejection.reason_code) for rejection in result.rejected] == [
        ("movement", "invalid_adjacency"),
    ]


def test_validate_order_envelope_rejects_second_conflicting_upgrade_order() -> None:
    result = validate_order_envelope(
        _order_envelope(
            upgrades=[
                {"city": "alpha", "track": "fortification", "target_tier": 1},
                {"city": "alpha", "track": "fortification", "target_tier": 1},
            ]
        ),
        _match_state(),
        _test_map(),
    )

    assert result.accepted.model_dump(mode="json") == {
        "movements": [],
        "recruitment": [],
        "upgrades": [{"city": "alpha", "track": "fortification", "target_tier": 1}],
        "transfers": [],
    }
    assert [(rejection.order_type, rejection.reason_code) for rejection in result.rejected] == [
        ("upgrade", "conflicting_duplicate_order"),
    ]
    assert result.rejected[0].message == (
        "upgrade order 1 conflicts with an earlier upgrade order for "
        "city 'alpha' track 'fortification' in the same envelope"
    )


def test_validate_order_envelope_accepts_valid_upgrade_after_invalid_duplicate_candidate() -> None:
    result = validate_order_envelope(
        _order_envelope(
            upgrades=[
                {"city": "alpha", "track": "fortification", "target_tier": 2},
                {"city": "alpha", "track": "fortification", "target_tier": 1},
            ]
        ),
        _match_state(),
        _test_map(),
    )

    assert result.accepted.model_dump(mode="json") == {
        "movements": [],
        "recruitment": [],
        "upgrades": [{"city": "alpha", "track": "fortification", "target_tier": 1}],
        "transfers": [],
    }
    assert [(rejection.order_type, rejection.reason_code) for rejection in result.rejected] == [
        ("upgrade", "invalid_tier_progression"),
    ]


def test_validate_order_envelope_rejects_resource_shortfalls_and_invalid_upgrade_progression() -> (
    None
):
    state = _match_state()
    state.cities["alpha"] = state.cities["alpha"].model_copy(
        update={
            "upgrades": CityUpgradeState(economy=0, military=0, fortification=1),
        }
    )

    result = validate_order_envelope(
        _order_envelope(
            recruitment=[
                {"city": "alpha", "troops": 3},
                {"city": "bravo", "troops": 3},
            ],
            upgrades=[
                {"city": "alpha", "track": UpgradeTrack.FORTIFICATION, "target_tier": 3},
                {"city": "bravo", "track": UpgradeTrack.MILITARY, "target_tier": 1},
            ],
            transfers=[{"to": "player_2", "resource": "production", "amount": 10}],
        ),
        state,
        _test_map(),
    )

    assert result.accepted.model_dump(mode="json") == {
        "movements": [],
        "recruitment": [{"city": "alpha", "troops": 3}],
        "upgrades": [],
        "transfers": [],
    }
    assert result.rejected[0].reason_code == "insufficient_resources"
    assert result.rejected[0].message == (
        "recruitment order 1 requires 3 food and "
        f"{3 * RECRUITMENT_COST_PER_TROOP.production} production, "
        "but only 7 food and 5 production remain in the validation budget"
    )
    assert result.rejected[1].reason_code == "invalid_tier_progression"
    assert result.rejected[2].reason_code == "insufficient_resources"
    assert result.rejected[3].reason_code == "insufficient_resources"


def test_validate_order_envelope_requires_land_routes_for_food_and_production_transfers_only() -> (
    None
):
    state = _match_state()
    state.players["player_2"] = state.players["player_2"].model_copy(
        update={"cities_owned": ["delta"], "alliance_id": None}
    )
    state.cities["charlie"] = state.cities["charlie"].model_copy(update={"owner": None})
    state.cities["delta"] = state.cities["delta"].model_copy(update={"owner": "player_2"})

    result = validate_order_envelope(
        _order_envelope(
            transfers=[
                {"to": "player_2", "resource": "food", "amount": 1},
                {"to": "player_2", "resource": "production", "amount": 1},
                {"to": "player_2", "resource": "money", "amount": 1},
            ]
        ),
        state,
        _test_map(),
    )

    assert result.accepted.model_dump(mode="json") == {
        "movements": [],
        "recruitment": [],
        "upgrades": [],
        "transfers": [{"to": "player_2", "resource": "money", "amount": 1}],
    }
    assert [(rejection.order_type, rejection.reason_code) for rejection in result.rejected] == [
        ("transfer", "disconnected_route"),
        ("transfer", "disconnected_route"),
    ]


def test_validate_order_envelope_rejects_transfer_to_enemy_player() -> None:
    state = _match_state()
    state.players["player_2"] = state.players["player_2"].model_copy(
        update={"alliance_id": "alliance_blue"}
    )

    result = validate_order_envelope(
        _order_envelope(transfers=[{"to": "player_2", "resource": "money", "amount": 1}]),
        state,
        _test_map(),
    )

    assert result.accepted.model_dump(mode="json") == {
        "movements": [],
        "recruitment": [],
        "upgrades": [],
        "transfers": [],
    }
    assert [(rejection.order_type, rejection.reason_code) for rejection in result.rejected] == [
        ("transfer", "invalid_recipient_relation"),
    ]
    assert result.rejected[0].message == (
        "transfer order 0 cannot target enemy player 'player_2'; "
        "transfers are limited to allied or neutral players"
    )


def test_validate_order_envelope_accepts_land_transfer_over_allied_route_from_city_ownership() -> (
    None
):
    state = _match_state()
    state.cities["charlie"] = state.cities["charlie"].model_copy(update={"owner": "player_4"})
    state.cities["delta"] = state.cities["delta"].model_copy(update={"owner": "player_2"})
    state.players["player_2"] = state.players["player_2"].model_copy(
        update={"cities_owned": [], "alliance_id": "alliance_red"}
    )
    state.players["player_4"] = PlayerState(
        resources=ResourceState(food=4, production=4, money=4),
        cities_owned=[],
        alliance_id="alliance_red",
        is_eliminated=False,
    )

    result = validate_order_envelope(
        _order_envelope(transfers=[{"to": "player_2", "resource": "production", "amount": 2}]),
        state,
        _test_map(),
    )

    assert result.accepted.model_dump(mode="json") == {
        "movements": [],
        "recruitment": [],
        "upgrades": [],
        "transfers": [{"to": "player_2", "resource": "production", "amount": 2}],
    }
    assert result.rejected == []


def test_validate_order_envelope_rejects_land_transfer_to_player_without_any_cities() -> None:
    result = validate_order_envelope(
        _order_envelope(transfers=[{"to": "player_3", "resource": "food", "amount": 1}]),
        _match_state(),
        _test_map(),
    )

    assert result.accepted.model_dump(mode="json") == {
        "movements": [],
        "recruitment": [],
        "upgrades": [],
        "transfers": [],
    }
    assert [(rejection.order_type, rejection.reason_code) for rejection in result.rejected] == [
        ("transfer", "disconnected_route"),
    ]


def test_validate_order_envelope_does_not_mutate_match_state() -> None:
    state = _match_state()
    state_before = deepcopy(state.model_dump(mode="python"))

    result = validate_order_envelope(
        _order_envelope(
            recruitment=[{"city": "alpha", "troops": 2}],
            upgrades=[{"city": "alpha", "track": "fortification", "target_tier": 1}],
            transfers=[{"to": "player_2", "resource": "money", "amount": 3}],
        ),
        state,
        _test_map(),
    )

    assert result.accepted.model_dump(mode="json") == {
        "movements": [],
        "recruitment": [{"city": "alpha", "troops": 2}],
        "upgrades": [{"city": "alpha", "track": "fortification", "target_tier": 1}],
        "transfers": [{"to": "player_2", "resource": "money", "amount": 3}],
    }
    assert state.model_dump(mode="python") == state_before
