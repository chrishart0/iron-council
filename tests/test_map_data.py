import pytest
from pydantic import ValidationError
from server.data.maps import load_uk_1900_map, validate_map_definition
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


def test_uk_1900_map_has_only_one_sea_crossing_involving_ireland() -> None:
    map_definition = load_uk_1900_map()

    irish_sea_crossings = {
        tuple(sorted((edge.city_a, edge.city_b)))
        for edge in map_definition.edges
        if edge.traversal_mode == "sea"
        and (
            map_definition.cities[edge.city_a].region == "Ireland"
            or map_definition.cities[edge.city_b].region == "Ireland"
        )
    }

    assert irish_sea_crossings == {("belfast", "liverpool")}


def test_validate_map_definition_accepts_the_canonical_uk_1900_map() -> None:
    canonical_payload = load_uk_1900_map().model_dump(mode="json")

    validated_map = validate_map_definition(canonical_payload)

    assert validated_map.model_dump(mode="json") == canonical_payload


def test_validate_map_definition_rejects_edge_references_to_missing_cities() -> None:
    malformed_payload = load_uk_1900_map().model_dump(mode="json")
    malformed_payload["edges"][0]["city_b"] = "atlantis"

    with pytest.raises(
        ValidationError,
        match=r"edges\[0\] references unknown city IDs: atlantis",
    ):
        validate_map_definition(malformed_payload)


def test_validate_map_definition_rejects_non_positive_edge_distances() -> None:
    malformed_payload = load_uk_1900_map().model_dump(mode="json")
    malformed_payload["edges"][0]["distance_ticks"] = 0

    with pytest.raises(ValidationError, match="greater than 0"):
        validate_map_definition(malformed_payload)


def test_validate_map_definition_rejects_extra_irish_sea_crossings() -> None:
    malformed_payload = load_uk_1900_map().model_dump(mode="json")
    malformed_payload["edges"].append(
        {
            "city_a": "glasgow",
            "city_b": "dublin",
            "distance_ticks": 4,
            "traversal_mode": "sea",
        }
    )

    with pytest.raises(
        ValidationError,
        match=(
            r"Liverpool-Belfast must be the only sea crossing involving Ireland; "
            r"found extra crossing glasgow-dublin"
        ),
    ):
        validate_map_definition(malformed_payload)
