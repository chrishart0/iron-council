from __future__ import annotations

from collections import defaultdict
from typing import Literal

from server.data.maps import MapDefinition, load_uk_1900_map
from server.models.fog import AgentStateProjection, VisibleArmyState, VisibleCityState
from server.models.state import ArmyState, MatchState

UNKNOWN: Literal["unknown"] = "unknown"


def project_agent_state(
    match_state: MatchState,
    *,
    player_id: str,
    map_definition: MapDefinition | None = None,
) -> AgentStateProjection:
    if player_id not in match_state.players:
        raise ValueError(f"unknown player_id: {player_id}")

    active_map = map_definition or load_uk_1900_map()
    allied_player_ids = _allied_player_ids(match_state=match_state, player_id=player_id)
    full_visibility_city_ids = {
        city_id
        for city_id, city_state in match_state.cities.items()
        if city_state.owner in allied_player_ids
    }
    visible_city_ids = full_visibility_city_ids | _adjacent_city_ids(
        city_ids=full_visibility_city_ids,
        map_definition=active_map,
    )

    projected_cities = {
        city_id: _project_city(
            city_id=city_id,
            match_state=match_state,
            full_visibility_city_ids=full_visibility_city_ids,
        )
        for city_id in sorted(visible_city_ids)
        if city_id in match_state.cities
    }
    projected_armies = [
        _project_army(
            army=army,
            allied_player_ids=allied_player_ids,
        )
        for army in sorted(match_state.armies, key=lambda army: army.id)
        if _army_is_visible(
            army=army,
            allied_player_ids=allied_player_ids,
            visible_city_ids=visible_city_ids,
        )
    ]

    requesting_player = match_state.players[player_id]
    return AgentStateProjection(
        tick=match_state.tick,
        player_id=player_id,
        resources=requesting_player.resources.model_copy(deep=True),
        cities=projected_cities,
        visible_armies=projected_armies,
        alliance_id=requesting_player.alliance_id,
        alliance_members=sorted(allied_player_ids),
        victory=match_state.victory.model_copy(deep=True),
    )


def _allied_player_ids(*, match_state: MatchState, player_id: str) -> set[str]:
    requesting_player = match_state.players[player_id]
    alliance_id = requesting_player.alliance_id
    if alliance_id is None:
        return {player_id}

    return {
        candidate_player_id
        for candidate_player_id, player_state in match_state.players.items()
        if player_state.alliance_id == alliance_id
    }


def _adjacent_city_ids(*, city_ids: set[str], map_definition: MapDefinition) -> set[str]:
    adjacency = _adjacency_by_city(map_definition)
    adjacent_city_ids: set[str] = set()
    for city_id in city_ids:
        adjacent_city_ids.update(adjacency.get(city_id, ()))
    return adjacent_city_ids


def _adjacency_by_city(map_definition: MapDefinition) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in map_definition.edges:
        adjacency[edge.city_a].add(edge.city_b)
        adjacency[edge.city_b].add(edge.city_a)
    return dict(adjacency)


def _project_city(
    *,
    city_id: str,
    match_state: MatchState,
    full_visibility_city_ids: set[str],
) -> VisibleCityState:
    city_state = match_state.cities[city_id]
    if city_id in full_visibility_city_ids:
        return VisibleCityState(
            owner=city_state.owner,
            visibility="full",
            population=city_state.population,
            resources=city_state.resources.model_copy(deep=True),
            upgrades=city_state.upgrades.model_copy(deep=True),
            garrison=city_state.garrison,
            building_queue=[item.model_copy(deep=True) for item in city_state.building_queue],
        )

    return VisibleCityState(
        owner=city_state.owner,
        visibility="partial",
        population=UNKNOWN,
        resources=UNKNOWN,
        upgrades=UNKNOWN,
        garrison=UNKNOWN,
        building_queue=UNKNOWN,
    )


def _army_is_visible(
    *,
    army: ArmyState,
    allied_player_ids: set[str],
    visible_city_ids: set[str],
) -> bool:
    if army.owner in allied_player_ids:
        return True
    if army.destination is None:
        return False
    return army.destination in visible_city_ids


def _project_army(*, army: ArmyState, allied_player_ids: set[str]) -> VisibleArmyState:
    if army.owner in allied_player_ids:
        return VisibleArmyState(
            id=army.id,
            owner=army.owner,
            visibility="full",
            troops=army.troops,
            location=army.location,
            destination=army.destination,
            path=None if army.path is None else list(army.path),
            ticks_remaining=army.ticks_remaining,
        )

    return VisibleArmyState(
        id=army.id,
        owner=army.owner,
        visibility="partial",
        troops=UNKNOWN,
        location=army.location,
        destination=army.destination,
        path=UNKNOWN if army.path is not None else None,
        ticks_remaining=army.ticks_remaining,
    )
