from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from server.db.testing import prepare_test_database


@pytest.fixture(autouse=True)
def reset_default_app_registry() -> Iterator[None]:
    from server.agent_registry import InMemoryMatchRegistry
    from server.main import app

    app.state.match_registry = InMemoryMatchRegistry()
    yield
    app.state.match_registry = InMemoryMatchRegistry()


@pytest.fixture
def representative_match_state_payload() -> dict[str, Any]:
    return {
        "tick": 142,
        "cities": {
            "london": {
                "owner": "player_uuid",
                "population": 12,
                "resources": {"food": 3, "production": 2, "money": 8},
                "upgrades": {"economy": 2, "military": 1, "fortification": 0},
                "garrison": 15,
                "building_queue": [
                    {"type": "fortification", "tier": 1, "ticks_remaining": 3},
                ],
            }
        },
        "armies": [
            {
                "id": "army_uuid",
                "owner": "player_uuid",
                "troops": 40,
                "location": "birmingham",
                "destination": None,
                "path": None,
                "ticks_remaining": 0,
            }
        ],
        "players": {
            "player_uuid": {
                "resources": {"food": 120, "production": 85, "money": 200},
                "cities_owned": ["london", "southampton", "portsmouth"],
                "alliance_id": None,
                "is_eliminated": False,
            }
        },
        "victory": {
            "leading_alliance": None,
            "cities_held": 13,
            "threshold": 13,
            "countdown_ticks_remaining": None,
        },
    }


@pytest.fixture
def representative_order_payload() -> dict[str, Any]:
    return {
        "match_id": "match_uuid",
        "player_id": "player_uuid",
        "tick": 142,
        "orders": {
            "movements": [{"army_id": "army_uuid", "destination": "birmingham"}],
            "recruitment": [{"city": "london", "troops": 5}],
            "upgrades": [{"city": "portsmouth", "track": "fortification", "target_tier": 1}],
            "transfers": [{"to": "player_ally_uuid", "resource": "money", "amount": 50}],
        },
    }


@pytest.fixture
def migrated_test_database_url(tmp_path: Path) -> str:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'test.db'}"
    prepare_test_database(database_url=database_url, reset=False)
    return database_url
