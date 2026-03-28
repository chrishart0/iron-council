from typing import TYPE_CHECKING

import pytest
from server.models.state import MatchState, ResourceState

if TYPE_CHECKING:
    from server.data.maps import MapDefinition
    from server.match_initialization import MatchConfig


def _starting_resources() -> ResourceState:
    return ResourceState(food=120, production=85, money=200)


def _starting_config(*, starting_cities_per_player: int = 2) -> "MatchConfig":
    from server.match_initialization import MatchConfig

    return MatchConfig(
        victory_city_threshold=13,
        starting_cities_per_player=starting_cities_per_player,
        starting_resources=_starting_resources(),
    )


def test_initialize_match_assigns_legal_mainland_spawns_from_config_and_roster() -> None:
    from server.data.maps import load_uk_1900_map
    from server.match_initialization import MatchRosterEntry, initialize_match_state

    canonical_map = load_uk_1900_map()
    state = initialize_match_state(
        _starting_config(),
        [
            MatchRosterEntry(player_id="player_1"),
            MatchRosterEntry(player_id="player_2"),
        ],
    )

    dumped = state.model_dump(mode="json")
    assignments = {
        player_id: list(player_state.cities_owned)
        for player_id, player_state in state.players.items()
    }
    assigned_city_ids = {
        city_id for player_cities in assignments.values() for city_id in player_cities
    }

    assert isinstance(state, MatchState)
    assert dumped["tick"] == 0
    assert dumped["armies"] == []
    assert dumped["victory"] == {
        "leading_alliance": None,
        "cities_held": 0,
        "threshold": 13,
        "countdown_ticks_remaining": None,
    }
    assert dumped["players"]["player_1"]["resources"] == {
        "food": 120,
        "production": 85,
        "money": 200,
    }
    assert all(len(player_cities) == 2 for player_cities in assignments.values())
    assert len(assigned_city_ids) == 4

    for city_id in assigned_city_ids:
        assert canonical_map.cities[city_id].spawn_allowed is True
        assert canonical_map.cities[city_id].region != "Ireland"

    for player_id, player_cities in assignments.items():
        for city_id in player_cities:
            assert state.cities[city_id].owner == player_id

    for city_id in ("belfast", "dublin", "cork", "galway"):
        assert state.cities[city_id].owner is None

    adjacency = _build_adjacency_lookup(canonical_map)
    for player_id, player_cities in assignments.items():
        other_player_city_ids = {
            city_id
            for other_player_id, other_player_cities in assignments.items()
            if other_player_id != player_id
            for city_id in other_player_cities
        }
        for city_id in player_cities:
            assert adjacency[city_id].isdisjoint(other_player_city_ids)


def test_initialize_match_is_deterministic_for_identical_ordered_inputs() -> None:
    from server.match_initialization import MatchRosterEntry, initialize_match_state

    roster = [
        MatchRosterEntry(player_id="player_1"),
        MatchRosterEntry(player_id="player_2"),
        MatchRosterEntry(player_id="player_3"),
    ]

    first = initialize_match_state(_starting_config(), roster).model_dump(mode="json")
    second = initialize_match_state(_starting_config(), roster).model_dump(mode="json")

    assert first == second


def test_initialize_match_honors_optional_explicit_spawn_overrides() -> None:
    from server.data.maps import load_uk_1900_map
    from server.match_initialization import MatchRosterEntry, initialize_match_state

    canonical_map = load_uk_1900_map()
    state = initialize_match_state(
        _starting_config(),
        [
            MatchRosterEntry(
                player_id="player_1",
                starting_city_ids=["london", "plymouth"],
            ),
            MatchRosterEntry(player_id="player_2"),
        ],
    )

    assert state.players["player_1"].cities_owned == ["london", "plymouth"]
    assert len(state.players["player_2"].cities_owned) == 2
    for city_id in state.players["player_2"].cities_owned:
        assert canonical_map.cities[city_id].spawn_allowed is True
        assert canonical_map.cities[city_id].region != "Ireland"


def test_initialize_match_fails_clearly_when_spawn_assignment_is_impossible() -> None:
    from server.match_initialization import (
        MatchInitializationError,
        MatchRosterEntry,
        initialize_match_state,
    )

    roster = [MatchRosterEntry(player_id=f"player_{index}") for index in range(1, 12)]

    with pytest.raises(
        MatchInitializationError,
        match=(
            "cannot assign 2 starting cities to 11 players from 21 legal spawn cities "
            "on map 'uk_1900'"
        ),
    ):
        initialize_match_state(_starting_config(), roster)


def test_initialize_match_rejects_irish_explicit_spawn_override_even_if_spawnable() -> None:
    from server.data.maps import CityCoordinates, CityDefinition, MapDefinition, MapEdge
    from server.match_initialization import (
        MatchInitializationError,
        MatchRosterEntry,
        initialize_match_state,
    )
    from server.models.domain import ResourceType

    custom_map = MapDefinition(
        map_id="ireland_override_test",
        name="Ireland Override Test",
        cities={
            "london": CityDefinition(
                name="London",
                region="Southeast",
                primary_resource=ResourceType.MONEY,
                notes="",
                position=CityCoordinates(x=1, y=1),
                spawn_allowed=True,
            ),
            "plymouth": CityDefinition(
                name="Plymouth",
                region="Southwest",
                primary_resource=ResourceType.FOOD,
                notes="",
                position=CityCoordinates(x=2, y=1),
                spawn_allowed=True,
            ),
            "edinburgh": CityDefinition(
                name="Edinburgh",
                region="Scotland",
                primary_resource=ResourceType.MONEY,
                notes="",
                position=CityCoordinates(x=3, y=1),
                spawn_allowed=True,
            ),
            "leeds": CityDefinition(
                name="Leeds",
                region="Yorkshire",
                primary_resource=ResourceType.PRODUCTION,
                notes="",
                position=CityCoordinates(x=4, y=1),
                spawn_allowed=True,
            ),
            "dublin": CityDefinition(
                name="Dublin",
                region="Ireland",
                primary_resource=ResourceType.MONEY,
                notes="",
                position=CityCoordinates(x=5, y=1),
                spawn_allowed=True,
            ),
        },
        edges=[MapEdge(city_a="london", city_b="leeds", distance_ticks=1)],
    )

    with pytest.raises(
        MatchInitializationError,
        match="starting city 'dublin' is not a legal mainland spawn city",
    ):
        initialize_match_state(
            _starting_config(),
            [
                MatchRosterEntry(
                    player_id="player_1",
                    starting_city_ids=["dublin", "plymouth"],
                ),
                MatchRosterEntry(player_id="player_2", starting_city_ids=["edinburgh", "leeds"]),
            ],
            map_definition=custom_map,
        )


def test_initialize_match_rejects_empty_roster() -> None:
    from server.match_initialization import MatchInitializationError, initialize_match_state

    with pytest.raises(
        MatchInitializationError,
        match="roster must contain at least one player",
    ):
        initialize_match_state(_starting_config(), [])


def test_initialize_match_rejects_invalid_starting_city_count_config() -> None:
    from server.match_initialization import (
        MatchInitializationError,
        MatchRosterEntry,
        initialize_match_state,
    )

    with pytest.raises(
        MatchInitializationError,
        match="starting_cities_per_player must be between 2 and 3",
    ):
        initialize_match_state(
            _starting_config(starting_cities_per_player=1),
            [MatchRosterEntry(player_id="player_1")],
        )


def test_initialize_match_rejects_duplicate_players_in_roster() -> None:
    from server.match_initialization import (
        MatchInitializationError,
        MatchRosterEntry,
        initialize_match_state,
    )

    with pytest.raises(
        MatchInitializationError,
        match="player 'player_1' appears more than once in the roster",
    ):
        initialize_match_state(
            _starting_config(),
            [
                MatchRosterEntry(player_id="player_1"),
                MatchRosterEntry(player_id="player_1"),
            ],
        )


def test_match_roster_entry_rejects_blank_player_ids() -> None:
    from pydantic import ValidationError
    from server.match_initialization import MatchRosterEntry

    with pytest.raises(ValidationError, match="player_id must not be blank"):
        MatchRosterEntry(player_id="   ")


def test_match_roster_entry_rejects_whitespace_padded_player_ids() -> None:
    from pydantic import ValidationError
    from server.match_initialization import MatchRosterEntry

    with pytest.raises(
        ValidationError,
        match="player_id must not have leading or trailing whitespace",
    ):
        MatchRosterEntry(player_id=" player_1 ")


def test_initialize_match_rejects_explicit_override_with_wrong_city_count() -> None:
    from server.match_initialization import (
        MatchInitializationError,
        MatchRosterEntry,
        initialize_match_state,
    )

    with pytest.raises(
        MatchInitializationError,
        match="player 'player_1' must declare exactly 2 starting cities when using overrides",
    ):
        initialize_match_state(
            _starting_config(),
            [MatchRosterEntry(player_id="player_1", starting_city_ids=["london"])],
        )


def test_initialize_match_rejects_duplicate_city_within_one_override() -> None:
    from server.match_initialization import (
        MatchInitializationError,
        MatchRosterEntry,
        initialize_match_state,
    )

    with pytest.raises(
        MatchInitializationError,
        match="player 'player_1' includes duplicate starting city 'london'",
    ):
        initialize_match_state(
            _starting_config(),
            [MatchRosterEntry(player_id="player_1", starting_city_ids=["london", "london"])],
        )


def test_initialize_match_rejects_unknown_explicit_override_city() -> None:
    from server.match_initialization import (
        MatchInitializationError,
        MatchRosterEntry,
        initialize_match_state,
    )

    with pytest.raises(
        MatchInitializationError,
        match="starting city 'atlantis' for player 'player_1' does not exist on map 'uk_1900'",
    ):
        initialize_match_state(
            _starting_config(),
            [MatchRosterEntry(player_id="player_1", starting_city_ids=["atlantis", "london"])],
        )


def test_initialize_match_rejects_duplicate_city_claims_across_overrides() -> None:
    from server.match_initialization import (
        MatchInitializationError,
        MatchRosterEntry,
        initialize_match_state,
    )

    with pytest.raises(
        MatchInitializationError,
        match="starting city 'london' is assigned to multiple players",
    ):
        initialize_match_state(
            _starting_config(),
            [
                MatchRosterEntry(player_id="player_1", starting_city_ids=["london", "plymouth"]),
                MatchRosterEntry(player_id="player_2", starting_city_ids=["london", "edinburgh"]),
            ],
        )


def test_initialize_match_rejects_adjacent_city_claims_across_overrides() -> None:
    from server.match_initialization import (
        MatchInitializationError,
        MatchRosterEntry,
        initialize_match_state,
    )

    with pytest.raises(
        MatchInitializationError,
        match=(
            "starting city 'birmingham' for player 'player_2' "
            "is adjacent to 'london' owned by 'player_1'"
        ),
    ):
        initialize_match_state(
            _starting_config(),
            [
                MatchRosterEntry(player_id="player_1", starting_city_ids=["london", "plymouth"]),
                MatchRosterEntry(
                    player_id="player_2",
                    starting_city_ids=["birmingham", "edinburgh"],
                ),
            ],
        )


def test_initialize_match_fails_clearly_when_non_adjacent_assignment_is_impossible() -> None:
    from server.data.maps import CityCoordinates, CityDefinition, MapDefinition, MapEdge
    from server.match_initialization import (
        MatchInitializationError,
        MatchRosterEntry,
        initialize_match_state,
    )
    from server.models.domain import ResourceType

    constrained_map = MapDefinition(
        map_id="test_map",
        name="Constrained Test Map",
        cities={
            city_id: CityDefinition(
                name=city_id.title(),
                region="Mainland",
                primary_resource=ResourceType.FOOD,
                notes="",
                position=CityCoordinates(x=index, y=0),
                spawn_allowed=True,
            )
            for index, city_id in enumerate(("a", "b", "c", "d"), start=1)
        },
        edges=[
            MapEdge(city_a="a", city_b="b", distance_ticks=1),
            MapEdge(city_a="b", city_b="c", distance_ticks=1),
            MapEdge(city_a="c", city_b="d", distance_ticks=1),
        ],
    )

    with pytest.raises(
        MatchInitializationError,
        match=(
            "cannot assign 2 starting cities to 2 players from 4 legal "
            "spawn cities on map 'test_map'"
        ),
    ):
        initialize_match_state(
            _starting_config(),
            [
                MatchRosterEntry(player_id="player_1"),
                MatchRosterEntry(player_id="player_2"),
            ],
            map_definition=constrained_map,
        )


def test_initialize_match_populates_all_cities_from_the_canonical_map() -> None:
    from server.data.maps import load_uk_1900_map
    from server.match_initialization import MatchRosterEntry, initialize_match_state

    state = initialize_match_state(
        _starting_config(),
        [
            MatchRosterEntry(player_id="player_1"),
            MatchRosterEntry(player_id="player_2"),
        ],
    )

    assert set(state.cities) == set(load_uk_1900_map().cities)
    assert all(city_state.building_queue == [] for city_state in state.cities.values())
    assert all(player_state.alliance_id is None for player_state in state.players.values())
    assert all(player_state.is_eliminated is False for player_state in state.players.values())


def _build_adjacency_lookup(map_definition: "MapDefinition") -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = {city_id: set() for city_id in map_definition.cities}

    for edge in map_definition.edges:
        adjacency[edge.city_a].add(edge.city_b)
        adjacency[edge.city_b].add(edge.city_a)

    return adjacency
