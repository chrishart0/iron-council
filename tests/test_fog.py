from __future__ import annotations

from copy import deepcopy
from typing import cast

from server.data.maps import CityCoordinates, CityDefinition, MapDefinition, MapEdge
from server.fog import project_agent_state
from server.models.domain import FortificationTier, ResourceType, UpgradeTrack
from server.models.state import (
    ArmyState,
    BuildingQueueItem,
    CityState,
    CityUpgradeState,
    MatchState,
    PlayerState,
    ResourceState,
    VictoryState,
)


def _map_definition() -> MapDefinition:
    return MapDefinition(
        map_id="fog_test_map",
        name="Fog Test Map",
        cities={
            city_id: CityDefinition(
                name=city_id.title(),
                region="Test Region",
                primary_resource=ResourceType.MONEY,
                notes="",
                position=CityCoordinates(x=index, y=1),
            )
            for index, city_id in enumerate(
                ["london", "manchester", "birmingham", "leeds", "inverness"],
                start=1,
            )
        },
        edges=[
            MapEdge(city_a="london", city_b="birmingham", distance_ticks=1),
            MapEdge(city_a="manchester", city_b="leeds", distance_ticks=1),
        ],
    )


def _match_state() -> MatchState:
    return MatchState(
        tick=12,
        cities={
            "london": _city_state(owner="player_1", garrison=12, economy=2),
            "manchester": _city_state(owner="player_2", garrison=9, military=1),
            "birmingham": _city_state(owner="player_3", garrison=7, fortification=1),
            "leeds": _city_state(owner="player_4", garrison=11, economy=1),
            "inverness": _city_state(owner="player_5", garrison=13, military=2),
        },
        armies=[
            ArmyState(
                id="army_c",
                owner="player_3",
                troops=18,
                location=None,
                destination="birmingham",
                path=["birmingham"],
                ticks_remaining=2,
            ),
            ArmyState(
                id="army_a",
                owner="player_2",
                troops=14,
                location=None,
                destination="leeds",
                path=["leeds"],
                ticks_remaining=1,
            ),
            ArmyState(
                id="army_b",
                owner="player_1",
                troops=20,
                location="london",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="army_z",
                owner="player_5",
                troops=25,
                location=None,
                destination="inverness",
                path=["inverness"],
                ticks_remaining=3,
            ),
        ],
        players={
            "player_1": _player_state(cities_owned=["london"], alliance_id="alliance_red"),
            "player_2": _player_state(cities_owned=["manchester"], alliance_id="alliance_red"),
            "player_3": _player_state(cities_owned=["birmingham"], alliance_id=None),
            "player_4": _player_state(cities_owned=["leeds"], alliance_id=None),
            "player_5": _player_state(cities_owned=["inverness"], alliance_id=None),
        },
        victory=VictoryState(
            leading_alliance="alliance_red",
            cities_held=2,
            threshold=3,
            countdown_ticks_remaining=None,
        ),
    )


def _city_state(
    *,
    owner: str | None,
    garrison: int,
    economy: int = 0,
    military: int = 0,
    fortification: int = 0,
) -> CityState:
    return CityState(
        owner=owner,
        population=5,
        resources=ResourceState(food=3, production=2, money=1),
        upgrades=CityUpgradeState(
            economy=economy,
            military=military,
            fortification=fortification,
        ),
        garrison=garrison,
        building_queue=[
            BuildingQueueItem(
                type=UpgradeTrack.FORTIFICATION,
                tier=FortificationTier.TRENCHES,
                ticks_remaining=2,
            ),
        ],
    )


def _player_state(*, cities_owned: list[str], alliance_id: str | None) -> PlayerState:
    return PlayerState(
        resources=ResourceState(food=20, production=15, money=10),
        cities_owned=cities_owned,
        alliance_id=alliance_id,
        is_eliminated=False,
    )


def test_project_agent_state_includes_owned_allied_and_adjacent_cities_with_masking() -> None:
    projected = project_agent_state(
        _match_state(),
        player_id="player_1",
        match_id="match-fog",
        map_definition=_map_definition(),
    )

    assert list(projected.cities) == ["birmingham", "leeds", "london", "manchester"]
    assert projected.cities["london"].visibility == "full"
    assert projected.cities["london"].garrison == 12
    assert projected.cities["manchester"].visibility == "full"
    manchester = projected.cities["manchester"]
    assert cast(CityUpgradeState, manchester.upgrades).military == 1

    assert projected.cities["birmingham"].owner == "player_3"
    assert projected.cities["birmingham"].visibility == "partial"
    assert projected.cities["birmingham"].garrison == "unknown"
    assert projected.cities["birmingham"].upgrades == "unknown"
    assert projected.cities["leeds"].owner == "player_4"
    assert projected.cities["leeds"].visibility == "partial"
    assert "inverness" not in projected.cities


def test_project_agent_state_keeps_exact_self_and_allied_armies_and_masks_visible_enemies() -> None:
    projected = project_agent_state(
        _match_state(),
        player_id="player_1",
        match_id="match-fog",
        map_definition=_map_definition(),
    )

    assert [army.id for army in projected.visible_armies] == ["army_a", "army_b", "army_c"]
    assert projected.visible_armies[0].owner == "player_2"
    assert projected.visible_armies[0].visibility == "full"
    assert projected.visible_armies[0].troops == 14
    assert projected.visible_armies[1].owner == "player_1"
    assert projected.visible_armies[1].visibility == "full"
    assert projected.visible_armies[1].location == "london"

    assert projected.visible_armies[2].owner == "player_3"
    assert projected.visible_armies[2].visibility == "partial"
    assert projected.visible_armies[2].troops == "unknown"
    assert projected.visible_armies[2].destination == "birmingham"
    assert projected.visible_armies[2].ticks_remaining == 2


def test_project_agent_state_includes_stationary_enemy_army_in_visible_city() -> None:
    match_state = _match_state()
    match_state.armies.append(
        ArmyState(
            id="army_d",
            owner="player_4",
            troops=16,
            location="leeds",
            destination=None,
            path=None,
            ticks_remaining=0,
        )
    )

    projected = project_agent_state(
        match_state,
        player_id="player_1",
        match_id="match-fog",
        map_definition=_map_definition(),
    )

    assert [army.id for army in projected.visible_armies] == [
        "army_a",
        "army_b",
        "army_c",
        "army_d",
    ]
    stationary_enemy = projected.visible_armies[3]
    assert stationary_enemy.owner == "player_4"
    assert stationary_enemy.visibility == "partial"
    assert stationary_enemy.troops == "unknown"
    assert stationary_enemy.location == "leeds"
    assert stationary_enemy.destination is None
    assert stationary_enemy.path is None
    assert stationary_enemy.ticks_remaining == 0


def test_project_agent_state_is_deterministic_and_does_not_mutate_input() -> None:
    match_state = _match_state()
    original_dump = deepcopy(match_state.model_dump(mode="json"))

    first_projection = project_agent_state(
        match_state,
        player_id="player_1",
        match_id="match-10-1",
        map_definition=_map_definition(),
    )
    second_projection = project_agent_state(
        match_state,
        player_id="player_1",
        match_id="match-10-1",
        map_definition=_map_definition(),
    )

    assert first_projection.model_dump(mode="json") == second_projection.model_dump(mode="json")
    assert first_projection.match_id == "match-10-1"
    assert match_state.model_dump(mode="json") == original_dump
