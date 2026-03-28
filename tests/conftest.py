import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def match_state_payload() -> dict:
    return {
        "tick": 142,
        "cities": {
            "london": {
                "owner": "player-1",
                "population": 12,
                "resources": {"food": 3, "production": 2, "money": 8},
                "upgrades": {"economy": 2, "military": 1, "fortification": 0},
                "garrison": 15,
                "building_queue": [{"type": "fortification", "tier": 1, "ticks_remaining": 3}],
            },
            "birmingham": {
                "owner": None,
                "population": 9,
                "resources": {"food": 1, "production": 4, "money": 2},
                "upgrades": {"economy": 0, "military": 0, "fortification": 0},
                "garrison": 0,
                "building_queue": [],
            },
        },
        "armies": [
            {
                "id": "army-1",
                "owner": "player-1",
                "troops": 40,
                "location": "london",
                "destination": None,
                "path": None,
                "ticks_remaining": 0,
            },
            {
                "id": "army-2",
                "owner": "player-1",
                "troops": 25,
                "location": None,
                "destination": "leeds",
                "path": ["manchester", "leeds"],
                "ticks_remaining": 2,
            },
        ],
        "players": {
            "player-1": {
                "resources": {"food": 120, "production": 85, "money": 200},
                "cities_owned": ["london"],
                "alliance_id": None,
                "is_eliminated": False,
            }
        },
        "victory": {
            "leading_alliance": None,
            "cities_held": 1,
            "threshold": 13,
            "countdown_ticks_remaining": None,
        },
    }


@pytest.fixture
def order_envelope_payload() -> dict:
    return {
        "match_id": "match-1",
        "player_id": "player-1",
        "tick": 142,
        "orders": {
            "movements": [{"army_id": "army-1", "destination": "birmingham"}],
            "recruitment": [{"city": "london", "troops": 5}],
            "upgrades": [
                {
                    "city": "portsmouth",
                    "track": "fortification",
                    "target_tier": 1,
                }
            ],
            "transfers": [{"to": "player-ally", "resource": "money", "amount": 50}],
        },
    }
