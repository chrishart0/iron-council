from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

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


@lru_cache(maxsize=1)
def load_uk_1900_map() -> MapDefinition:
    raw_map = json.loads(UK_1900_MAP_PATH.read_text(encoding="utf-8"))
    return MapDefinition.model_validate(raw_map)
