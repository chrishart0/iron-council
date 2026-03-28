from server.data.maps import load_uk_1900_map
from server.models.domain import ResourceType


def test_load_uk_1900_map_exposes_canonical_public_contract() -> None:
    map_definition = load_uk_1900_map()

    assert map_definition.map_id == "uk_1900"
    assert map_definition.name == "United Kingdom 1900"
    assert len(map_definition.cities) == 25
    assert "london" in map_definition.cities
    assert "belfast" in map_definition.cities
    assert len(map_definition.edges) > 0


def test_uk_1900_map_exposes_representative_city_facts() -> None:
    map_definition = load_uk_1900_map()

    london = map_definition.cities["london"]
    belfast = map_definition.cities["belfast"]

    assert london.region == "Southeast"
    assert london.primary_resource is ResourceType.MONEY
    assert london.is_neutral is False
    assert london.spawn_allowed is True

    assert belfast.region == "Ireland"
    assert belfast.primary_resource is ResourceType.PRODUCTION
    assert belfast.is_neutral is True
    assert belfast.spawn_allowed is False


def test_uk_1900_map_marks_all_irish_cities_neutral_and_no_spawn() -> None:
    map_definition = load_uk_1900_map()

    irish_city_ids = {"belfast", "dublin", "cork", "galway"}

    assert irish_city_ids == {
        city_id for city_id, city in map_definition.cities.items() if city.region == "Ireland"
    }
    assert all(map_definition.cities[city_id].is_neutral for city_id in irish_city_ids)
    assert all(not map_definition.cities[city_id].spawn_allowed for city_id in irish_city_ids)


def test_uk_1900_map_encodes_the_liverpool_belfast_special_crossing() -> None:
    map_definition = load_uk_1900_map()

    crossing = next(
        edge
        for edge in map_definition.edges
        if {edge.city_a, edge.city_b} == {"liverpool", "belfast"}
    )

    assert crossing.traversal_mode == "sea"
    assert crossing.distance_ticks > 3
    assert crossing.has_landing_combat_penalty is True
