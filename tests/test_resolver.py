from __future__ import annotations

from copy import deepcopy

from server.models.domain import FortificationTier, ResourceType, UpgradeTrack
from server.models.orders import (
    MovementOrder,
    OrderBatch,
    RecruitmentOrder,
    TransferOrder,
    UpgradeOrder,
)
from server.models.state import (
    ArmyState,
    CityState,
    CityUpgradeState,
    MatchState,
    PlayerState,
    ResourceState,
    VictoryState,
)
from server.resolver import resolve_tick


def _match_state() -> MatchState:
    return MatchState(
        tick=5,
        cities={
            "alpha": _city_state(owner="player_1"),
            "bravo": _city_state(owner="player_2"),
        },
        armies=[
            ArmyState(
                id="army_1",
                owner="player_1",
                troops=8,
                location="alpha",
                destination=None,
                path=None,
                ticks_remaining=0,
            )
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=10, production=20, money=30),
                cities_owned=["alpha"],
                alliance_id="alliance_red",
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=8, production=7, money=6),
                cities_owned=["bravo"],
                alliance_id="alliance_blue",
                is_eliminated=False,
            ),
        },
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            threshold=2,
            countdown_ticks_remaining=None,
        ),
    )


def _city_state(*, owner: str | None) -> CityState:
    return CityState(
        owner=owner,
        population=10,
        resources=ResourceState(food=1, production=1, money=1),
        upgrades=CityUpgradeState(economy=0, military=0, fortification=0),
        garrison=5,
        building_queue=[],
    )


def test_resolve_tick_returns_new_state_and_ordered_deterministic_phase_metadata() -> None:
    state = _match_state()
    original_dump = deepcopy(state.model_dump(mode="json"))
    orders = OrderBatch(
        movements=[MovementOrder(army_id="army_1", destination="bravo")],
        recruitment=[RecruitmentOrder(city="alpha", troops=1)],
        upgrades=[
            UpgradeOrder(
                city="alpha",
                track=UpgradeTrack.FORTIFICATION,
                target_tier=FortificationTier.TRENCHES,
            )
        ],
        transfers=[TransferOrder(to="player_2", resource=ResourceType.MONEY, amount=1)],
    )

    result = resolve_tick(state, orders)
    repeated_result = resolve_tick(state, orders)

    assert result.next_state is not state
    assert state.model_dump(mode="json") == original_dump
    assert result.next_state.model_dump(mode="json") == original_dump
    assert [phase.phase for phase in result.phases] == [
        "resource",
        "build",
        "movement",
        "combat",
        "siege",
        "attrition",
        "diplomacy",
        "victory",
    ]
    assert result.model_dump(mode="json") == repeated_result.model_dump(mode="json")
    assert result.events == [
        {
            "phase": "resource",
            "event": "phase.resource.completed",
        },
        {
            "phase": "build",
            "event": "phase.build.completed",
        },
        {
            "phase": "movement",
            "event": "phase.movement.completed",
        },
        {
            "phase": "combat",
            "event": "phase.combat.completed",
        },
        {
            "phase": "siege",
            "event": "phase.siege.completed",
        },
        {
            "phase": "attrition",
            "event": "phase.attrition.completed",
        },
        {
            "phase": "diplomacy",
            "event": "phase.diplomacy.completed",
        },
        {
            "phase": "victory",
            "event": "phase.victory.completed",
        },
    ]
