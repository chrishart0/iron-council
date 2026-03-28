from __future__ import annotations

from collections.abc import Sequence

from pydantic import model_validator

from server.data.maps import MapDefinition, load_uk_1900_map
from server.models.domain import NonNegativeCount, StrictModel
from server.models.state import (
    CityState,
    CityUpgradeState,
    MatchState,
    PlayerState,
    ResourceState,
    VictoryState,
)

MIN_STARTING_CITY_COUNT = 2
MAX_STARTING_CITY_COUNT = 3
DEFAULT_CITY_POPULATION = 10
DEFAULT_NEUTRAL_GARRISON = 5
DEFAULT_OWNED_GARRISON = 15
PRIMARY_RESOURCE_YIELD = 3
SECONDARY_RESOURCE_YIELD = 1


class MatchInitializationError(ValueError):
    """Raised when match initialization inputs cannot produce a valid starting state."""


class MatchConfig(StrictModel):
    victory_city_threshold: NonNegativeCount
    starting_cities_per_player: NonNegativeCount
    starting_resources: ResourceState


class MatchRosterEntry(StrictModel):
    player_id: str
    starting_city_ids: list[str] | None = None

    @model_validator(mode="after")
    def validate_player_id(self) -> MatchRosterEntry:
        stripped_player_id = self.player_id.strip()
        if not stripped_player_id:
            raise ValueError("player_id must not be blank")
        if stripped_player_id != self.player_id:
            raise ValueError("player_id must not have leading or trailing whitespace")
        return self


def initialize_match_state(
    config: MatchConfig,
    roster: Sequence[MatchRosterEntry],
    *,
    map_definition: MapDefinition | None = None,
) -> MatchState:
    if not roster:
        raise MatchInitializationError("roster must contain at least one player")

    if not (
        MIN_STARTING_CITY_COUNT <= config.starting_cities_per_player <= MAX_STARTING_CITY_COUNT
    ):
        raise MatchInitializationError(
            "starting_cities_per_player must be between "
            f"{MIN_STARTING_CITY_COUNT} and {MAX_STARTING_CITY_COUNT}"
        )

    canonical_map = map_definition or load_uk_1900_map()
    adjacency = _build_adjacency_lookup(canonical_map)
    legal_spawn_city_ids = _legal_spawn_city_ids(canonical_map)
    assignments_by_player, assigned_city_owners = _assign_starting_cities(
        config=config,
        roster=roster,
        canonical_map=canonical_map,
        adjacency=adjacency,
        legal_spawn_city_ids=legal_spawn_city_ids,
    )

    cities = {
        city_id: _build_city_state(city_id, canonical_map, assigned_city_owners)
        for city_id in canonical_map.cities
    }
    players = {
        roster_entry.player_id: PlayerState(
            resources=config.starting_resources.model_copy(deep=True),
            cities_owned=list(assignments_by_player[roster_entry.player_id]),
            alliance_id=None,
            is_eliminated=False,
        )
        for roster_entry in roster
    }

    return MatchState(
        tick=0,
        cities=cities,
        armies=[],
        players=players,
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            threshold=config.victory_city_threshold,
            countdown_ticks_remaining=None,
        ),
    )


def _assign_starting_cities(
    *,
    config: MatchConfig,
    roster: Sequence[MatchRosterEntry],
    canonical_map: MapDefinition,
    adjacency: dict[str, set[str]],
    legal_spawn_city_ids: list[str],
) -> tuple[dict[str, list[str]], dict[str, str]]:
    assignments_by_player: dict[str, list[str]] = {}
    assigned_city_owners: dict[str, str] = {}
    seen_player_ids: set[str] = set()

    for roster_entry in roster:
        if roster_entry.player_id in seen_player_ids:
            raise MatchInitializationError(
                f"player '{roster_entry.player_id}' appears more than once in the roster"
            )
        seen_player_ids.add(roster_entry.player_id)
        assignments_by_player[roster_entry.player_id] = []

        if roster_entry.starting_city_ids is None:
            continue

        if len(roster_entry.starting_city_ids) != config.starting_cities_per_player:
            raise MatchInitializationError(
                f"player '{roster_entry.player_id}' must declare exactly "
                f"{config.starting_cities_per_player} starting cities when using overrides"
            )

        seen_player_city_ids: set[str] = set()
        for city_id in roster_entry.starting_city_ids:
            if city_id in seen_player_city_ids:
                raise MatchInitializationError(
                    f"player '{roster_entry.player_id}' includes duplicate "
                    f"starting city '{city_id}'"
                )
            seen_player_city_ids.add(city_id)
            _validate_starting_city(
                city_id=city_id,
                player_id=roster_entry.player_id,
                canonical_map=canonical_map,
                adjacency=adjacency,
                assigned_city_owners=assigned_city_owners,
            )
            assigned_city_owners[city_id] = roster_entry.player_id
            assignments_by_player[roster_entry.player_id].append(city_id)

    total_required_cities = len(roster) * config.starting_cities_per_player
    if total_required_cities > len(legal_spawn_city_ids):
        raise MatchInitializationError(
            "cannot assign "
            f"{config.starting_cities_per_player} starting cities to {len(roster)} players "
            f"from {len(legal_spawn_city_ids)} legal spawn cities on map "
            f"'{canonical_map.map_id}'"
        )

    assignment_order = _build_assignment_order(
        roster=roster,
        starting_cities_per_player=config.starting_cities_per_player,
        assignments_by_player=assignments_by_player,
    )
    if not _assign_remaining_cities(
        assignment_order=assignment_order,
        legal_spawn_city_ids=legal_spawn_city_ids,
        adjacency=adjacency,
        assignments_by_player=assignments_by_player,
        assigned_city_owners=assigned_city_owners,
    ):
        raise MatchInitializationError(
            "cannot assign "
            f"{config.starting_cities_per_player} starting cities to {len(roster)} players "
            f"from {len(legal_spawn_city_ids)} legal spawn cities on map "
            f"'{canonical_map.map_id}'"
        )

    return assignments_by_player, assigned_city_owners


def _build_assignment_order(
    *,
    roster: Sequence[MatchRosterEntry],
    starting_cities_per_player: int,
    assignments_by_player: dict[str, list[str]],
) -> list[str]:
    assignment_order: list[str] = []

    for slot_index in range(starting_cities_per_player):
        for roster_entry in roster:
            if len(assignments_by_player[roster_entry.player_id]) > slot_index:
                continue
            assignment_order.append(roster_entry.player_id)

    return assignment_order


def _assign_remaining_cities(
    *,
    assignment_order: Sequence[str],
    legal_spawn_city_ids: Sequence[str],
    adjacency: dict[str, set[str]],
    assignments_by_player: dict[str, list[str]],
    assigned_city_owners: dict[str, str],
    index: int = 0,
) -> bool:
    if index == len(assignment_order):
        return True

    player_id = assignment_order[index]

    for city_id in legal_spawn_city_ids:
        if not _can_assign_city(
            city_id=city_id,
            player_id=player_id,
            adjacency=adjacency,
            assigned_city_owners=assigned_city_owners,
        ):
            continue

        assigned_city_owners[city_id] = player_id
        assignments_by_player[player_id].append(city_id)

        if _assign_remaining_cities(
            assignment_order=assignment_order,
            legal_spawn_city_ids=legal_spawn_city_ids,
            adjacency=adjacency,
            assignments_by_player=assignments_by_player,
            assigned_city_owners=assigned_city_owners,
            index=index + 1,
        ):
            return True

        assignments_by_player[player_id].pop()
        del assigned_city_owners[city_id]

    return False


def _validate_starting_city(
    *,
    city_id: str,
    player_id: str,
    canonical_map: MapDefinition,
    adjacency: dict[str, set[str]],
    assigned_city_owners: dict[str, str],
) -> None:
    city_definition = canonical_map.cities.get(city_id)
    if city_definition is None:
        raise MatchInitializationError(
            f"starting city '{city_id}' for player '{player_id}' "
            f"does not exist on map '{canonical_map.map_id}'"
        )

    if city_definition.region == "Ireland":
        raise MatchInitializationError(
            f"starting city '{city_id}' is not a legal mainland spawn city"
        )

    if not city_definition.spawn_allowed:
        raise MatchInitializationError(f"starting city '{city_id}' is not a legal spawn city")

    existing_owner = assigned_city_owners.get(city_id)
    if existing_owner is not None:
        raise MatchInitializationError(f"starting city '{city_id}' is assigned to multiple players")

    for adjacent_city_id in adjacency[city_id]:
        adjacent_owner = assigned_city_owners.get(adjacent_city_id)
        if adjacent_owner is None or adjacent_owner == player_id:
            continue

        raise MatchInitializationError(
            f"starting city '{city_id}' for player '{player_id}' "
            f"is adjacent to '{adjacent_city_id}' owned by '{adjacent_owner}'"
        )


def _can_assign_city(
    *,
    city_id: str,
    player_id: str,
    adjacency: dict[str, set[str]],
    assigned_city_owners: dict[str, str],
) -> bool:
    existing_owner = assigned_city_owners.get(city_id)
    if existing_owner is not None:
        return False

    for adjacent_city_id in adjacency[city_id]:
        adjacent_owner = assigned_city_owners.get(adjacent_city_id)
        if adjacent_owner is not None and adjacent_owner != player_id:
            return False

    return True


def _build_city_state(
    city_id: str,
    map_definition: MapDefinition,
    assigned_city_owners: dict[str, str],
) -> CityState:
    owner = assigned_city_owners.get(city_id)

    return CityState(
        owner=owner,
        population=DEFAULT_CITY_POPULATION,
        resources=_build_city_resource_state(map_definition.cities[city_id].primary_resource.value),
        upgrades=CityUpgradeState(economy=0, military=0, fortification=0),
        garrison=DEFAULT_OWNED_GARRISON if owner is not None else DEFAULT_NEUTRAL_GARRISON,
        building_queue=[],
    )


def _build_city_resource_state(primary_resource: str) -> ResourceState:
    return ResourceState(
        food=PRIMARY_RESOURCE_YIELD if primary_resource == "food" else SECONDARY_RESOURCE_YIELD,
        production=(
            PRIMARY_RESOURCE_YIELD if primary_resource == "production" else SECONDARY_RESOURCE_YIELD
        ),
        money=PRIMARY_RESOURCE_YIELD if primary_resource == "money" else SECONDARY_RESOURCE_YIELD,
    )


def _build_adjacency_lookup(map_definition: MapDefinition) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = {city_id: set() for city_id in map_definition.cities}

    for edge in map_definition.edges:
        adjacency[edge.city_a].add(edge.city_b)
        adjacency[edge.city_b].add(edge.city_a)

    return adjacency


def _legal_spawn_city_ids(map_definition: MapDefinition) -> list[str]:
    return sorted(
        city_id
        for city_id, city_definition in map_definition.cities.items()
        if city_definition.spawn_allowed and city_definition.region != "Ireland"
    )
