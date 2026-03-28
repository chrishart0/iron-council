from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator

from server.models.domain import PositiveTickDuration, ResourceType, StrictModel

MAP_DATA_DIR = Path(__file__).resolve().parent
UK_1900_MAP_PATH = MAP_DATA_DIR / "map_uk_1900.json"


class CityCoordinates(StrictModel):
    x: int
    y: int


class CityDefinition(StrictModel):
    name: str
    region: str
    primary_resource: ResourceType
    notes: str
    position: CityCoordinates
    is_neutral: bool = False
    spawn_allowed: bool = True


class MapEdge(StrictModel):
    city_a: str
    city_b: str
    distance_ticks: PositiveTickDuration
    traversal_mode: Literal["land", "sea"] = "land"
    has_landing_combat_penalty: bool = False


class MapDefinition(StrictModel):
    map_id: str
    name: str
    cities: dict[str, CityDefinition]
    edges: list[MapEdge]

    @model_validator(mode="after")
    def validate_graph_integrity(self) -> MapDefinition:
        city_ids = set(self.cities)
        extra_irish_sea_crossings: list[str] = []

        for index, edge in enumerate(self.edges):
            missing_city_ids = sorted({edge.city_a, edge.city_b} - city_ids)
            if missing_city_ids:
                missing_cities = ", ".join(missing_city_ids)
                raise ValueError(f"edges[{index}] references unknown city IDs: {missing_cities}")

            if (
                edge.traversal_mode == "sea"
                and "Ireland" in {self.cities[edge.city_a].region, self.cities[edge.city_b].region}
                and {edge.city_a, edge.city_b} != {"liverpool", "belfast"}
            ):
                extra_irish_sea_crossings.append(f"{edge.city_a}-{edge.city_b}")

        if extra_irish_sea_crossings:
            crossings = ", ".join(extra_irish_sea_crossings)
            raise ValueError(
                "Liverpool-Belfast must be the only sea crossing involving Ireland; "
                f"found extra crossing {crossings}"
            )

        return self


def validate_map_definition(raw_map: object) -> MapDefinition:
    return MapDefinition.model_validate(raw_map)


@lru_cache(maxsize=1)
def load_uk_1900_map() -> MapDefinition:
    raw_map = json.loads(UK_1900_MAP_PATH.read_text(encoding="utf-8"))
    return validate_map_definition(raw_map)
