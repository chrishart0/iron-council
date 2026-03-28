from __future__ import annotations

from copy import deepcopy

from server.models.domain import FortificationTier, UpgradeTrack
from server.models.orders import MovementOrder, OrderBatch, RecruitmentOrder, UpgradeOrder
from server.models.state import (
    ArmyState,
    BuildingQueueItem,
    CityState,
    CityUpgradeState,
    MatchState,
    PlayerState,
    ResourceState,
    VictoryState,
)
from server.resolver import PHASE_ORDER, TickPhaseEvent, resolve_tick


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
                resources=ResourceState(food=30, production=20, money=30),
                cities_owned=["alpha"],
                alliance_id="alliance_red",
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=20, production=7, money=6),
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
        population=1,
        resources=ResourceState(food=1, production=1, money=1),
        upgrades=CityUpgradeState(economy=0, military=0, fortification=0),
        garrison=5,
        building_queue=[],
    )


def test_resolve_tick_adds_owned_city_yields_and_food_upkeep_without_mutating_input() -> None:
    state = MatchState(
        tick=5,
        cities={
            "alpha": CityState(
                owner="player_1",
                population=4,
                resources=ResourceState(food=3, production=1, money=1),
                upgrades=CityUpgradeState(economy=3, military=0, fortification=0),
                garrison=5,
                building_queue=[],
            ),
            "bravo": CityState(
                owner="player_1",
                population=2,
                resources=ResourceState(food=1, production=3, money=1),
                upgrades=CityUpgradeState(economy=2, military=0, fortification=0),
                garrison=5,
                building_queue=[],
            ),
            "charlie": CityState(
                owner="player_2",
                population=3,
                resources=ResourceState(food=1, production=1, money=3),
                upgrades=CityUpgradeState(economy=1, military=0, fortification=0),
                garrison=5,
                building_queue=[],
            ),
            "delta": CityState(
                owner=None,
                population=9,
                resources=ResourceState(food=3, production=1, money=1),
                upgrades=CityUpgradeState(economy=3, military=0, fortification=0),
                garrison=5,
                building_queue=[],
            ),
        },
        armies=[
            ArmyState(
                id="army_1",
                owner="player_1",
                troops=5,
                location="alpha",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="army_2",
                owner="player_1",
                troops=2,
                location="bravo",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="army_3",
                owner="player_2",
                troops=1,
                location="charlie",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=10, production=20, money=30),
                cities_owned=["alpha", "bravo"],
                alliance_id="alliance_red",
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=8, production=7, money=6),
                cities_owned=["charlie"],
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
    original_dump = deepcopy(state.model_dump(mode="json"))

    result = resolve_tick(state, OrderBatch())

    assert state.model_dump(mode="json") == original_dump
    assert result.next_state.players["player_1"].resources == ResourceState(
        food=4,
        production=26,
        money=32,
    )
    assert result.next_state.players["player_2"].resources == ResourceState(
        food=5,
        production=8,
        money=10,
    )


def test_resolve_tick_clamps_food_to_zero_when_upkeep_exceeds_available_food() -> None:
    state = MatchState(
        tick=5,
        cities={
            "alpha": CityState(
                owner="player_1",
                population=4,
                resources=ResourceState(food=1, production=1, money=1),
                upgrades=CityUpgradeState(economy=0, military=0, fortification=0),
                garrison=5,
                building_queue=[],
            )
        },
        armies=[
            ArmyState(
                id="army_1",
                owner="player_1",
                troops=3,
                location="alpha",
                destination=None,
                path=None,
                ticks_remaining=0,
            )
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=2, production=10, money=10),
                cities_owned=["alpha"],
                alliance_id="alliance_red",
                is_eliminated=False,
            )
        },
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            threshold=2,
            countdown_ticks_remaining=None,
        ),
    )
    original_dump = deepcopy(state.model_dump(mode="json"))

    result = resolve_tick(state, OrderBatch())

    assert state.model_dump(mode="json") == original_dump
    assert result.next_state.players["player_1"].resources == ResourceState(
        food=0,
        production=11,
        money=11,
    )


def test_resolve_tick_returns_copied_state_without_mutating_input() -> None:
    state = _match_state()
    original_dump = deepcopy(state.model_dump(mode="json"))
    orders = OrderBatch()

    result = resolve_tick(state, orders)

    assert result.next_state is not state
    assert state.model_dump(mode="json") == original_dump
    assert result.next_state.tick == state.tick
    assert result.next_state.model_dump(mode="json")["cities"] == original_dump["cities"]
    assert result.next_state.model_dump(mode="json")["armies"] == original_dump["armies"]
    assert result.next_state.victory == VictoryState(
        leading_alliance=None,
        cities_held=1,
        threshold=2,
        countdown_ticks_remaining=None,
    )


def test_resolve_tick_emits_phase_metadata_and_typed_events_in_phase_order() -> None:
    result = resolve_tick(_match_state(), OrderBatch())

    assert [phase.phase for phase in result.phases] == list(PHASE_ORDER)
    assert result.events == [
        TickPhaseEvent(phase=phase, event=f"phase.{phase}.completed") for phase in PHASE_ORDER
    ]


def test_resolve_tick_is_deterministic_for_same_state_and_orders() -> None:
    state = _match_state()
    orders = OrderBatch()

    result = resolve_tick(state, orders)
    repeated_result = resolve_tick(state, orders)

    assert result.model_dump(mode="json") == repeated_result.model_dump(mode="json")


def test_resolve_tick_build_phase_decrements_existing_upgrade_queue_and_completes_city_tier() -> (
    None
):
    state = MatchState(
        tick=5,
        cities={
            "alpha": CityState(
                owner="player_1",
                population=1,
                resources=ResourceState(food=1, production=1, money=1),
                upgrades=CityUpgradeState(economy=0, military=1, fortification=0),
                garrison=5,
                building_queue=[
                    BuildingQueueItem(
                        type=UpgradeTrack.MILITARY,
                        tier=FortificationTier.BUNKERS,
                        ticks_remaining=1,
                    )
                ],
            )
        },
        armies=[],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=10, production=10, money=10),
                cities_owned=["alpha"],
                alliance_id=None,
                is_eliminated=False,
            )
        },
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            threshold=1,
            countdown_ticks_remaining=None,
        ),
    )
    original_dump = deepcopy(state.model_dump(mode="json"))

    result = resolve_tick(state, OrderBatch())

    assert state.model_dump(mode="json") == original_dump
    assert result.next_state.cities["alpha"].upgrades == CityUpgradeState(
        economy=0,
        military=2,
        fortification=0,
    )
    assert result.next_state.cities["alpha"].building_queue == []
    assert result.events[PHASE_ORDER.index("build")] == TickPhaseEvent(
        phase="build",
        event="phase.build.completed",
    )


def test_resolve_tick_build_phase_starts_accepted_upgrade_queues_and_deducts_production_once() -> (
    None
):
    state = MatchState(
        tick=5,
        cities={
            "alpha": CityState(
                owner="player_1",
                population=1,
                resources=ResourceState(food=1, production=1, money=1),
                upgrades=CityUpgradeState(economy=0, military=0, fortification=0),
                garrison=5,
                building_queue=[],
            ),
            "bravo": CityState(
                owner="player_1",
                population=1,
                resources=ResourceState(food=1, production=1, money=1),
                upgrades=CityUpgradeState(economy=0, military=0, fortification=1),
                garrison=5,
                building_queue=[
                    BuildingQueueItem(
                        type=UpgradeTrack.ECONOMY,
                        tier=FortificationTier.TRENCHES,
                        ticks_remaining=2,
                    )
                ],
            ),
        },
        armies=[],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=10, production=30, money=10),
                cities_owned=["alpha", "bravo"],
                alliance_id=None,
                is_eliminated=False,
            )
        },
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            threshold=2,
            countdown_ticks_remaining=None,
        ),
    )

    result = resolve_tick(
        state,
        OrderBatch(
            upgrades=[
                UpgradeOrder(
                    city="alpha",
                    track=UpgradeTrack.ECONOMY,
                    target_tier=FortificationTier.TRENCHES,
                ),
                UpgradeOrder(
                    city="bravo",
                    track=UpgradeTrack.FORTIFICATION,
                    target_tier=FortificationTier.BUNKERS,
                ),
            ]
        ),
    )

    assert result.next_state.players["player_1"].resources.production == 15
    assert result.next_state.cities["alpha"].building_queue == [
        BuildingQueueItem(
            type=UpgradeTrack.ECONOMY,
            tier=FortificationTier.TRENCHES,
            ticks_remaining=1,
        )
    ]
    assert result.next_state.cities["bravo"].building_queue == [
        BuildingQueueItem(
            type=UpgradeTrack.ECONOMY,
            tier=FortificationTier.TRENCHES,
            ticks_remaining=1,
        ),
        BuildingQueueItem(
            type=UpgradeTrack.FORTIFICATION,
            tier=FortificationTier.BUNKERS,
            ticks_remaining=2,
        ),
    ]


def test_resolve_tick_build_phase_is_deterministic_and_keeps_input_unmutated() -> None:
    state = MatchState(
        tick=5,
        cities={
            "alpha": CityState(
                owner="player_1",
                population=1,
                resources=ResourceState(food=1, production=1, money=1),
                upgrades=CityUpgradeState(economy=0, military=0, fortification=0),
                garrison=5,
                building_queue=[
                    BuildingQueueItem(
                        type=UpgradeTrack.MILITARY,
                        tier=FortificationTier.TRENCHES,
                        ticks_remaining=1,
                    )
                ],
            ),
            "bravo": CityState(
                owner="player_1",
                population=1,
                resources=ResourceState(food=1, production=1, money=1),
                upgrades=CityUpgradeState(economy=1, military=0, fortification=0),
                garrison=5,
                building_queue=[],
            ),
        },
        armies=[],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=10, production=30, money=10),
                cities_owned=["alpha", "bravo"],
                alliance_id=None,
                is_eliminated=False,
            )
        },
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            threshold=2,
            countdown_ticks_remaining=None,
        ),
    )
    orders = OrderBatch(
        upgrades=[
            UpgradeOrder(
                city="bravo",
                track=UpgradeTrack.ECONOMY,
                target_tier=FortificationTier.BUNKERS,
            )
        ]
    )
    original_dump = deepcopy(state.model_dump(mode="json"))

    result = resolve_tick(state, orders)
    repeated_result = resolve_tick(state, orders)

    assert state.model_dump(mode="json") == original_dump
    assert result.model_dump(mode="json") == repeated_result.model_dump(mode="json")
    assert result.next_state.cities["alpha"].upgrades.military == 1
    assert result.next_state.cities["alpha"].building_queue == []
    assert result.next_state.cities["bravo"].building_queue == [
        BuildingQueueItem(
            type=UpgradeTrack.ECONOMY,
            tier=FortificationTier.BUNKERS,
            ticks_remaining=2,
        )
    ]
    assert result.next_state.players["player_1"].resources.production == 21


def test_resolve_tick_build_phase_blocks_same_track_upgrade_from_phase_start_queue() -> None:
    state = MatchState(
        tick=5,
        cities={
            "alpha": CityState(
                owner="player_1",
                population=1,
                resources=ResourceState(food=1, production=1, money=1),
                upgrades=CityUpgradeState(economy=0, military=0, fortification=0),
                garrison=5,
                building_queue=[
                    BuildingQueueItem(
                        type=UpgradeTrack.ECONOMY,
                        tier=FortificationTier.TRENCHES,
                        ticks_remaining=1,
                    )
                ],
            )
        },
        armies=[],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=10, production=30, money=10),
                cities_owned=["alpha"],
                alliance_id=None,
                is_eliminated=False,
            )
        },
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            threshold=1,
            countdown_ticks_remaining=None,
        ),
    )

    result = resolve_tick(
        state,
        OrderBatch(
            upgrades=[
                UpgradeOrder(
                    city="alpha",
                    track=UpgradeTrack.ECONOMY,
                    target_tier=FortificationTier.BUNKERS,
                )
            ]
        ),
    )

    assert result.next_state.cities["alpha"].upgrades == CityUpgradeState(
        economy=1,
        military=0,
        fortification=0,
    )
    assert result.next_state.cities["alpha"].building_queue == []
    assert result.next_state.players["player_1"].resources.production == 31


def test_resolve_tick_build_phase_reinforces_existing_stationed_army() -> None:
    state = MatchState(
        tick=5,
        cities={
            "alpha": _city_state(owner="player_1"),
            "bravo": _city_state(owner="player_1"),
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
                resources=ResourceState(food=20, production=30, money=10),
                cities_owned=["alpha", "bravo"],
                alliance_id=None,
                is_eliminated=False,
            )
        },
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            threshold=2,
            countdown_ticks_remaining=None,
        ),
    )
    original_dump = deepcopy(state.model_dump(mode="json"))

    result = resolve_tick(
        state,
        OrderBatch(recruitment=[RecruitmentOrder(city="alpha", troops=3)]),
    )

    assert state.model_dump(mode="json") == original_dump
    assert result.next_state.armies == [
        ArmyState(
            id="army_1",
            owner="player_1",
            troops=11,
            location="alpha",
            destination=None,
            path=None,
            ticks_remaining=0,
        )
    ]
    assert result.next_state.players["player_1"].resources == ResourceState(
        food=9,
        production=17,
        money=12,
    )
    assert result.events[PHASE_ORDER.index("build")] == TickPhaseEvent(
        phase="build",
        event="phase.build.completed",
    )


def test_resolve_tick_build_phase_creates_deterministic_stationed_armies() -> None:
    state = MatchState(
        tick=5,
        cities={
            "alpha": _city_state(owner="player_1"),
            "bravo": _city_state(owner="player_1"),
            "charlie": _city_state(owner="player_2"),
        },
        armies=[
            ArmyState(
                id="army_9",
                owner="player_1",
                troops=4,
                location="charlie",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="recruitment:player_1:alpha:1",
                owner="player_2",
                troops=6,
                location="charlie",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=20, production=30, money=10),
                cities_owned=["alpha", "bravo"],
                alliance_id=None,
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=20, production=20, money=10),
                cities_owned=["charlie"],
                alliance_id=None,
                is_eliminated=False,
            ),
        },
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            threshold=3,
            countdown_ticks_remaining=None,
        ),
    )
    orders = OrderBatch(
        recruitment=[
            RecruitmentOrder(city="bravo", troops=2),
            RecruitmentOrder(city="alpha", troops=1),
        ]
    )
    original_dump = deepcopy(state.model_dump(mode="json"))

    result = resolve_tick(state, orders)
    repeated_result = resolve_tick(state, orders)

    assert state.model_dump(mode="json") == original_dump
    assert result.model_dump(mode="json") == repeated_result.model_dump(mode="json")
    assert result.next_state.players["player_1"].resources == ResourceState(
        food=13,
        production=17,
        money=12,
    )
    assert result.next_state.armies == [
        ArmyState(
            id="army_9",
            owner="player_1",
            troops=4,
            location="charlie",
            destination=None,
            path=None,
            ticks_remaining=0,
        ),
        ArmyState(
            id="recruitment:player_1:alpha:1",
            owner="player_2",
            troops=6,
            location="charlie",
            destination=None,
            path=None,
            ticks_remaining=0,
        ),
        ArmyState(
            id="recruitment:player_1:alpha:2",
            owner="player_1",
            troops=1,
            location="alpha",
            destination=None,
            path=None,
            ticks_remaining=0,
        ),
        ArmyState(
            id="recruitment:player_1:bravo:1",
            owner="player_1",
            troops=2,
            location="bravo",
            destination=None,
            path=None,
            ticks_remaining=0,
        ),
    ]


def test_resolve_tick_build_phase_is_permutation_invariant_for_equivalent_recruitment_sets() -> (
    None
):
    state = MatchState(
        tick=5,
        cities={
            "alpha": _city_state(owner="player_1"),
            "bravo": _city_state(owner="player_1"),
            "charlie": _city_state(owner="player_2"),
        },
        armies=[
            ArmyState(
                id="army_9",
                owner="player_1",
                troops=4,
                location="charlie",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="recruitment:player_1:alpha:1",
                owner="player_2",
                troops=6,
                location="charlie",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=20, production=30, money=10),
                cities_owned=["alpha", "bravo"],
                alliance_id=None,
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=20, production=20, money=10),
                cities_owned=["charlie"],
                alliance_id=None,
                is_eliminated=False,
            ),
        },
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            threshold=3,
            countdown_ticks_remaining=None,
        ),
    )

    alpha_then_bravo = resolve_tick(
        state,
        OrderBatch(
            recruitment=[
                RecruitmentOrder(city="alpha", troops=1),
                RecruitmentOrder(city="bravo", troops=2),
            ]
        ),
    )
    bravo_then_alpha = resolve_tick(
        state,
        OrderBatch(
            recruitment=[
                RecruitmentOrder(city="bravo", troops=2),
                RecruitmentOrder(city="alpha", troops=1),
            ]
        ),
    )

    assert alpha_then_bravo.next_state == bravo_then_alpha.next_state


def test_resolve_tick_hands_neutral_city_to_single_surviving_occupier_after_combat() -> None:
    state = MatchState(
        tick=5,
        cities={
            "alpha": _city_state(owner="player_1"),
            "belfast": _city_state(owner=None),
        },
        armies=[
            ArmyState(
                id="army_1",
                owner="player_1",
                troops=9,
                location="belfast",
                destination=None,
                path=None,
                ticks_remaining=0,
            )
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=30, production=20, money=30),
                cities_owned=["alpha"],
                alliance_id="alliance_red",
                is_eliminated=False,
            )
        },
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            threshold=2,
            countdown_ticks_remaining=None,
        ),
    )
    original_dump = deepcopy(state.model_dump(mode="json"))

    result = resolve_tick(state, OrderBatch())

    assert state.model_dump(mode="json") == original_dump
    assert result.next_state.cities["belfast"].owner == "player_1"
    assert result.next_state.players["player_1"].cities_owned == ["alpha", "belfast"]


def test_resolve_tick_hands_enemy_city_to_remaining_attacker_after_combat() -> None:
    state = MatchState(
        tick=5,
        cities={
            "alpha": _city_state(owner="player_1"),
            "bravo": _city_state(owner="player_2"),
        },
        armies=[
            ArmyState(
                id="army_1",
                owner="player_1",
                troops=40,
                location="bravo",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="army_2",
                owner="player_2",
                troops=4,
                location="bravo",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=30, production=20, money=30),
                cities_owned=["alpha"],
                alliance_id="alliance_red",
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=20, production=7, money=6),
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
    original_dump = deepcopy(state.model_dump(mode="json"))

    result = resolve_tick(state, OrderBatch())

    assert state.model_dump(mode="json") == original_dump
    assert [army.owner for army in result.next_state.armies if army.location == "bravo"] == [
        "player_1"
    ]
    assert result.next_state.cities["bravo"].owner == "player_1"
    assert result.next_state.players["player_1"].cities_owned == ["alpha", "bravo"]
    assert result.next_state.players["player_2"].cities_owned == []


def test_resolve_tick_handoff_is_deterministic_and_keeps_city_lists_synchronized() -> None:
    state = MatchState(
        tick=5,
        cities={
            "alpha": _city_state(owner="player_1"),
            "bravo": _city_state(owner="player_2"),
        },
        armies=[
            ArmyState(
                id="army_1",
                owner="player_1",
                troops=40,
                location="bravo",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="army_2",
                owner="player_2",
                troops=4,
                location="bravo",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=30, production=20, money=30),
                cities_owned=["alpha"],
                alliance_id="alliance_red",
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=20, production=7, money=6),
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

    first_result = resolve_tick(state, OrderBatch())
    repeated_result = resolve_tick(state, OrderBatch())

    assert first_result.model_dump(mode="json") == repeated_result.model_dump(mode="json")
    assert first_result.next_state.cities["bravo"].owner == "player_1"
    assert first_result.next_state.players["player_1"].cities_owned == ["alpha", "bravo"]
    assert first_result.next_state.players["player_2"].cities_owned == []


def test_resolve_tick_skips_city_handoff_when_occupier_is_missing_from_players() -> None:
    state = MatchState(
        tick=5,
        cities={"bravo": _city_state(owner="player_2")},
        armies=[
            ArmyState(
                id="orphan_army",
                owner="player_1",
                troops=7,
                location="bravo",
                destination=None,
                path=None,
                ticks_remaining=0,
            )
        ],
        players={
            "player_2": PlayerState(
                resources=ResourceState(food=20, production=7, money=6),
                cities_owned=["bravo"],
                alliance_id="alliance_blue",
                is_eliminated=False,
            )
        },
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            threshold=2,
            countdown_ticks_remaining=None,
        ),
    )

    result = resolve_tick(state, OrderBatch())

    assert result.next_state.cities["bravo"].owner == "player_2"
    assert result.next_state.players["player_2"].cities_owned == ["bravo"]


def test_resolve_tick_leaves_city_owner_unchanged_while_multiple_survivors_remain() -> None:
    state = MatchState(
        tick=5,
        cities={
            "alpha": _city_state(owner="player_1"),
            "bravo": _city_state(owner="player_2"),
        },
        armies=[
            ArmyState(
                id="army_1",
                owner="player_1",
                troops=6,
                location="bravo",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="army_2",
                owner="player_2",
                troops=6,
                location="bravo",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=30, production=20, money=30),
                cities_owned=["alpha"],
                alliance_id="alliance_red",
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=20, production=7, money=6),
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
    original_dump = deepcopy(state.model_dump(mode="json"))

    result = resolve_tick(state, OrderBatch())

    assert state.model_dump(mode="json") == original_dump
    assert {army.owner for army in result.next_state.armies if army.location == "bravo"} == {
        "player_1",
        "player_2",
    }
    assert result.next_state.cities["bravo"].owner == "player_2"


def test_resolve_tick_advances_transit_arrivals_and_starts_new_one_edge_marches() -> None:
    state = MatchState(
        tick=5,
        cities={
            "london": _city_state(owner="player_1"),
            "birmingham": _city_state(owner=None),
            "southampton": _city_state(owner="player_1"),
        },
        armies=[
            ArmyState(
                id="marching_army",
                owner="player_1",
                troops=8,
                location=None,
                destination="birmingham",
                path=["birmingham"],
                ticks_remaining=2,
            ),
            ArmyState(
                id="arriving_army",
                owner="player_1",
                troops=4,
                location=None,
                destination="southampton",
                path=["southampton"],
                ticks_remaining=1,
            ),
            ArmyState(
                id="stationed_army",
                owner="player_1",
                troops=6,
                location="london",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=30, production=20, money=30),
                cities_owned=["london", "southampton"],
                alliance_id="alliance_red",
                is_eliminated=False,
            )
        },
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            threshold=2,
            countdown_ticks_remaining=None,
        ),
    )
    original_dump = deepcopy(state.model_dump(mode="json"))
    orders = OrderBatch(
        movements=[MovementOrder(army_id="stationed_army", destination="birmingham")]
    )

    result = resolve_tick(state, orders)

    assert state.model_dump(mode="json") == original_dump
    armies_by_id = {army.id: army for army in result.next_state.armies}

    assert armies_by_id["marching_army"] == ArmyState(
        id="marching_army",
        owner="player_1",
        troops=8,
        location=None,
        destination="birmingham",
        path=["birmingham"],
        ticks_remaining=1,
    )
    assert armies_by_id["arriving_army"] == ArmyState(
        id="arriving_army",
        owner="player_1",
        troops=4,
        location="southampton",
        destination=None,
        path=None,
        ticks_remaining=0,
    )
    assert armies_by_id["stationed_army"] == ArmyState(
        id="stationed_army",
        owner="player_1",
        troops=6,
        location=None,
        destination="birmingham",
        path=["birmingham"],
        ticks_remaining=2,
    )


def test_resolve_tick_applies_simultaneous_casualties_to_contested_city_armies() -> None:
    state = MatchState(
        tick=5,
        cities={"alpha": _city_state(owner=None)},
        armies=[
            ArmyState(
                id="army_1",
                owner="player_1",
                troops=20,
                location="alpha",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="army_2",
                owner="player_2",
                troops=10,
                location="alpha",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=50, production=10, money=10),
                cities_owned=[],
                alliance_id=None,
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=50, production=10, money=10),
                cities_owned=[],
                alliance_id=None,
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

    result = resolve_tick(state, OrderBatch())

    armies_by_id = {army.id: army for army in result.next_state.armies}

    assert armies_by_id["army_1"].troops == 19
    assert armies_by_id["army_2"].troops == 8
    assert result.events[PHASE_ORDER.index("combat")] == TickPhaseEvent(
        phase="combat",
        event="phase.combat.completed",
    )


def test_resolve_tick_uses_zero_casualties_below_combat_divisor() -> None:
    state = MatchState(
        tick=5,
        cities={"alpha": _city_state(owner=None)},
        armies=[
            ArmyState(
                id="army_1",
                owner="player_1",
                troops=10,
                location="alpha",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="army_2",
                owner="player_2",
                troops=5,
                location="alpha",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=50, production=10, money=10),
                cities_owned=[],
                alliance_id=None,
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=50, production=10, money=10),
                cities_owned=[],
                alliance_id=None,
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

    result = resolve_tick(state, OrderBatch())

    armies_by_id = {army.id: army for army in result.next_state.armies}

    assert armies_by_id["army_1"].troops == 10
    assert armies_by_id["army_2"].troops == 4


def test_resolve_tick_applies_defender_and_fortification_advantage_only_to_city_owner() -> None:
    state = MatchState(
        tick=5,
        cities={
            "alpha": CityState(
                owner="player_1",
                population=1,
                resources=ResourceState(food=1, production=1, money=1),
                upgrades=CityUpgradeState(economy=0, military=0, fortification=2),
                garrison=5,
                building_queue=[],
            )
        },
        armies=[
            ArmyState(
                id="defender",
                owner="player_1",
                troops=10,
                location="alpha",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="attacker",
                owner="player_2",
                troops=10,
                location="alpha",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=50, production=10, money=10),
                cities_owned=["alpha"],
                alliance_id=None,
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=50, production=10, money=10),
                cities_owned=[],
                alliance_id=None,
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

    result = resolve_tick(state, OrderBatch())

    armies_by_id = {army.id: army for army in result.next_state.armies}

    assert armies_by_id["defender"].troops == 9
    assert armies_by_id["attacker"].troops == 8


def test_resolve_tick_allocates_same_owner_stack_casualties_proportionally() -> None:
    state = MatchState(
        tick=5,
        cities={"alpha": _city_state(owner=None)},
        armies=[
            ArmyState(
                id="small_stack",
                owner="player_1",
                troops=4,
                location="alpha",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="large_stack",
                owner="player_1",
                troops=8,
                location="alpha",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="opponent",
                owner="player_2",
                troops=20,
                location="alpha",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=50, production=10, money=10),
                cities_owned=[],
                alliance_id=None,
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=50, production=10, money=10),
                cities_owned=[],
                alliance_id=None,
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

    result = resolve_tick(state, OrderBatch())

    armies_by_id = {army.id: army for army in result.next_state.armies}

    assert armies_by_id["small_stack"].troops == 3
    assert armies_by_id["large_stack"].troops == 7
    assert armies_by_id["opponent"].troops == 19


def test_resolve_tick_combat_is_deterministic_and_keeps_input_unchanged() -> None:
    state = MatchState(
        tick=5,
        cities={"alpha": _city_state(owner="player_1")},
        armies=[
            ArmyState(
                id="defender",
                owner="player_1",
                troops=1,
                location="alpha",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="attacker",
                owner="player_2",
                troops=10,
                location="alpha",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=50, production=10, money=10),
                cities_owned=["alpha"],
                alliance_id=None,
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=50, production=10, money=10),
                cities_owned=[],
                alliance_id=None,
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
    original_dump = deepcopy(state.model_dump(mode="json"))

    result = resolve_tick(state, OrderBatch())
    repeated_result = resolve_tick(state, OrderBatch())

    assert state.model_dump(mode="json") == original_dump
    assert result.model_dump(mode="json") == repeated_result.model_dump(mode="json")
    assert [army.id for army in result.next_state.armies] == ["attacker"]
    assert result.next_state.armies[0].troops == 10


def test_resolve_tick_applies_starvation_attrition_only_to_players_left_with_zero_food() -> None:
    state = MatchState(
        tick=5,
        cities={
            "alpha": CityState(
                owner="player_1",
                population=1,
                resources=ResourceState(food=1, production=1, money=1),
                upgrades=CityUpgradeState(economy=0, military=0, fortification=0),
                garrison=5,
                building_queue=[],
            ),
            "bravo": CityState(
                owner="player_2",
                population=1,
                resources=ResourceState(food=3, production=1, money=1),
                upgrades=CityUpgradeState(economy=0, military=0, fortification=0),
                garrison=5,
                building_queue=[],
            ),
        },
        armies=[
            ArmyState(
                id="starving_army",
                owner="player_1",
                troops=2,
                location="alpha",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="fed_army",
                owner="player_2",
                troops=2,
                location="bravo",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=0, production=10, money=10),
                cities_owned=["alpha"],
                alliance_id="alliance_red",
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=2, production=10, money=10),
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

    result = resolve_tick(state, OrderBatch())

    armies_by_id = {army.id: army for army in result.next_state.armies}

    assert result.next_state.players["player_1"].resources.food == 0
    assert result.next_state.players["player_2"].resources.food == 2
    assert armies_by_id["starving_army"].troops == 1
    assert armies_by_id["fed_army"].troops == 2
    assert result.events[PHASE_ORDER.index("attrition")] == TickPhaseEvent(
        phase="attrition",
        event="phase.attrition.completed",
    )


def test_resolve_tick_removes_zero_troop_armies_and_updates_elimination() -> None:
    state = MatchState(
        tick=5,
        cities={},
        armies=[
            ArmyState(
                id="eliminated_army",
                owner="player_1",
                troops=1,
                location="wasteland",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="surviving_army",
                owner="player_2",
                troops=2,
                location="frontier",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=0, production=10, money=10),
                cities_owned=[],
                alliance_id=None,
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=0, production=10, money=10),
                cities_owned=[],
                alliance_id=None,
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

    result = resolve_tick(state, OrderBatch())

    assert [army.id for army in result.next_state.armies] == ["surviving_army"]
    assert result.next_state.armies[0].troops == 1
    assert result.next_state.players["player_1"].is_eliminated is True
    assert result.next_state.players["player_2"].is_eliminated is False


def test_resolve_tick_keeps_player_active_when_attrition_removes_last_army_but_city_remains() -> (
    None
):
    state = MatchState(
        tick=5,
        cities={"alpha": _city_state(owner="player_1")},
        armies=[
            ArmyState(
                id="starving_army",
                owner="player_1",
                troops=1,
                location="alpha",
                destination=None,
                path=None,
                ticks_remaining=0,
            )
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=0, production=10, money=10),
                cities_owned=["alpha"],
                alliance_id=None,
                is_eliminated=False,
            )
        },
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            threshold=2,
            countdown_ticks_remaining=None,
        ),
    )

    result = resolve_tick(state, OrderBatch())

    assert result.next_state.armies == []
    assert result.next_state.players["player_1"].is_eliminated is False


def test_resolve_tick_groups_allied_and_solo_city_control_for_victory_metadata() -> None:
    state = MatchState(
        tick=5,
        cities={
            "alpha": _city_state(owner="player_1"),
            "bravo": _city_state(owner="player_2"),
            "charlie": _city_state(owner="player_2"),
            "delta": _city_state(owner="player_3"),
        },
        armies=[],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=10, production=10, money=10),
                cities_owned=["alpha"],
                alliance_id="alliance_red",
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=10, production=10, money=10),
                cities_owned=["bravo", "charlie"],
                alliance_id="alliance_red",
                is_eliminated=False,
            ),
            "player_3": PlayerState(
                resources=ResourceState(food=10, production=10, money=10),
                cities_owned=["delta"],
                alliance_id=None,
                is_eliminated=False,
            ),
        },
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            threshold=3,
            countdown_ticks_remaining=None,
        ),
    )

    result = resolve_tick(state, OrderBatch())

    assert result.next_state.victory == VictoryState(
        leading_alliance="alliance_red",
        cities_held=3,
        # Temporary narrow story choice: threshold doubles as the initial countdown length.
        threshold=3,
        countdown_ticks_remaining=3,
    )
    assert result.events[PHASE_ORDER.index("victory")] == TickPhaseEvent(
        phase="victory",
        event="phase.victory.completed",
    )


def test_resolve_tick_keeps_solo_and_alliance_coalitions_distinct_when_ids_collide() -> None:
    state = MatchState(
        tick=5,
        cities={
            "alpha": _city_state(owner="player_1"),
            "bravo": _city_state(owner="player_1"),
            "charlie": _city_state(owner="player_2"),
            "delta": _city_state(owner="player_2"),
            "echo": _city_state(owner="player_3"),
        },
        armies=[],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=10, production=10, money=10),
                cities_owned=["alpha", "bravo"],
                alliance_id="player_3",
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=10, production=10, money=10),
                cities_owned=["charlie", "delta"],
                alliance_id="player_3",
                is_eliminated=False,
            ),
            "player_3": PlayerState(
                resources=ResourceState(food=10, production=10, money=10),
                cities_owned=["echo"],
                alliance_id=None,
                is_eliminated=False,
            ),
        },
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            threshold=3,
            countdown_ticks_remaining=None,
        ),
    )

    result = resolve_tick(state, OrderBatch())

    assert result.next_state.victory == VictoryState(
        leading_alliance="player_3",
        cities_held=4,
        threshold=3,
        countdown_ticks_remaining=3,
    )


def test_resolve_tick_clears_victory_countdown_when_top_city_control_is_tied() -> None:
    state = MatchState(
        tick=5,
        cities={
            "alpha": _city_state(owner="player_1"),
            "bravo": _city_state(owner="player_1"),
            "charlie": _city_state(owner="player_2"),
            "delta": _city_state(owner="player_3"),
            "echo": _city_state(owner="player_3"),
            "foxtrot": _city_state(owner="player_3"),
        },
        armies=[],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=10, production=10, money=10),
                cities_owned=["alpha", "bravo"],
                alliance_id="alliance_red",
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=10, production=10, money=10),
                cities_owned=["charlie"],
                alliance_id="alliance_red",
                is_eliminated=False,
            ),
            "player_3": PlayerState(
                resources=ResourceState(food=10, production=10, money=10),
                cities_owned=["delta", "echo", "foxtrot"],
                alliance_id=None,
                is_eliminated=False,
            ),
        },
        victory=VictoryState(
            leading_alliance="alliance_red",
            cities_held=3,
            threshold=2,
            countdown_ticks_remaining=1,
        ),
    )

    result = resolve_tick(state, OrderBatch())

    assert result.next_state.victory == VictoryState(
        leading_alliance=None,
        cities_held=3,
        threshold=2,
        countdown_ticks_remaining=None,
    )


def test_resolve_tick_clears_victory_countdown_when_leading_coalition_changes() -> None:
    state = MatchState(
        tick=5,
        cities={
            "alpha": _city_state(owner="player_1"),
            "bravo": _city_state(owner="player_2"),
            "charlie": _city_state(owner="player_2"),
            "delta": _city_state(owner="player_3"),
            "echo": _city_state(owner="player_3"),
            "foxtrot": _city_state(owner="player_3"),
            "golf": _city_state(owner="player_3"),
        },
        armies=[],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=10, production=10, money=10),
                cities_owned=["alpha"],
                alliance_id="alliance_red",
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=10, production=10, money=10),
                cities_owned=["bravo", "charlie"],
                alliance_id="alliance_red",
                is_eliminated=False,
            ),
            "player_3": PlayerState(
                resources=ResourceState(food=10, production=10, money=10),
                cities_owned=["delta", "echo", "foxtrot", "golf"],
                alliance_id="alliance_blue",
                is_eliminated=False,
            ),
        },
        victory=VictoryState(
            leading_alliance="alliance_red",
            cities_held=3,
            threshold=2,
            countdown_ticks_remaining=1,
        ),
    )

    result = resolve_tick(state, OrderBatch())

    assert result.next_state.victory == VictoryState(
        leading_alliance="alliance_blue",
        cities_held=4,
        threshold=2,
        countdown_ticks_remaining=None,
    )


def test_resolve_tick_clears_victory_countdown_when_control_drops_below_threshold() -> None:
    state = MatchState(
        tick=5,
        cities={
            "alpha": _city_state(owner="player_1"),
            "bravo": _city_state(owner="player_2"),
            "charlie": _city_state(owner="player_3"),
        },
        armies=[],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=10, production=10, money=10),
                cities_owned=["alpha"],
                alliance_id="alliance_red",
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=10, production=10, money=10),
                cities_owned=["bravo"],
                alliance_id=None,
                is_eliminated=False,
            ),
            "player_3": PlayerState(
                resources=ResourceState(food=10, production=10, money=10),
                cities_owned=["charlie"],
                alliance_id=None,
                is_eliminated=False,
            ),
        },
        victory=VictoryState(
            leading_alliance="alliance_red",
            cities_held=3,
            threshold=2,
            countdown_ticks_remaining=1,
        ),
    )

    result = resolve_tick(state, OrderBatch())

    assert result.next_state.victory == VictoryState(
        leading_alliance=None,
        cities_held=1,
        threshold=2,
        countdown_ticks_remaining=None,
    )
