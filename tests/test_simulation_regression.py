from __future__ import annotations

from server.data.maps import CityCoordinates, CityDefinition, MapDefinition, MapEdge
from server.models.domain import ResourceType
from server.models.state import (
    ArmyState,
    CityState,
    CityUpgradeState,
    MatchState,
    PlayerState,
    ResourceState,
    VictoryState,
)
from server.simulation_regression import (
    RegressionFailure,
    RegressionScenario,
    build_regression_scenarios,
    format_regression_failures,
    run_simulation_regression_batch,
)

EXPECTED_SCENARIO_RESULTS: list[tuple[str, int, str]] = [
    (
        "frontier-campaign/ticks=4/variant=opening-clash",
        4,
        "9da35d88ecf2e0ceb4b01eaac784a36ae3f2b458e7ef2d377a59b8d24b3d680d",
    ),
    (
        "frontier-campaign/ticks=6/variant=late-upgrade",
        6,
        "a512181dec6e276d91ecde8568d2b9790ead33c0bd6a7badcd09ec29d63288ed",
    ),
    (
        "frontier-campaign/ticks=6/variant=double-pressure",
        6,
        "82919c17f7257029af4473724b3faf1a07da90baa64f1e1253680cf1867a169e",
    ),
    (
        "frontier-campaign/ticks=8/variant=extended-pressure",
        8,
        "9269be3487a23517635ba9434c9331d78874eaa3e5f1a8bdf762e2ee5edc0858",
    ),
    (
        "attrition-line/ticks=2/variant=starving-start",
        2,
        "4092f982480fec038b81312bdbd905b0b1babfd0d16369fcd5589fadae47046c",
    ),
    (
        "attrition-line/ticks=3/variant=desperate-march",
        3,
        "4d550564b0b8c40ebb742d2ca239610808cde8b26171ba77b0a8abfeb22d73df",
    ),
    (
        "attrition-line/ticks=4/variant=counter-march",
        4,
        "85699a2ad78b93245016d4a00f289aecd166d67556da822765bea6ab8c390c70",
    ),
    (
        "attrition-line/ticks=5/variant=delayed-contact",
        5,
        "592ce2bee194f933a8482d2f1e4c06cfc2659ab22a4ae57efffd20d0cbed4ec3",
    ),
    (
        "victory-race/ticks=2/variant=alliance-hold",
        2,
        "c761a88bd768abb73bf800590f4f52c341d37ceb7de61c399a863135d449ada0",
    ),
    (
        "victory-race/ticks=4/variant=alliance-countdown",
        4,
        "caf7b883f738ba0a867e6a55d7ee263982c1700d8a1df2e09067507f1a4abda1",
    ),
    (
        "victory-race/ticks=4/variant=pressure-charlie",
        4,
        "22da85f78498c5234806752c3cdf8f1c4fd78c46dde5bc03ae7c0027a80acfd8",
    ),
    (
        "victory-race/ticks=5/variant=defender-shift",
        5,
        "14dfc70fc12723ce0ad7f231d9dbe40d039ba916509867a4122988b3eeab4901",
    ),
]


def _assert_expected_batch_outputs() -> None:
    scenarios = build_regression_scenarios()
    result = run_simulation_regression_batch(scenarios)

    assert [scenario.scenario_id for scenario in scenarios] == [
        scenario_id for scenario_id, _, _ in EXPECTED_SCENARIO_RESULTS
    ]
    assert result.total_runs == len(EXPECTED_SCENARIO_RESULTS)
    assert [
        (scenario.scenario_id, scenario.ticks, scenario.outcome_digest)
        for scenario in result.scenario_results
    ] == EXPECTED_SCENARIO_RESULTS
    assert result.failures == [], format_regression_failures(result.failures)


def _city_state(*, owner: str | None) -> CityState:
    return CityState(
        owner=owner,
        population=1,
        resources=ResourceState(food=1, production=1, money=1),
        upgrades=CityUpgradeState(economy=0, military=0, fortification=0),
        garrison=5,
        building_queue=[],
    )


def _city(name: str, primary_resource: ResourceType) -> CityDefinition:
    return CityDefinition(
        name=name,
        region="Regression",
        primary_resource=primary_resource,
        notes="",
        position=CityCoordinates(x=1, y=1),
    )


def _broken_reference_scenario() -> RegressionScenario:
    return RegressionScenario(
        scenario_id="broken-reference",
        map_definition=MapDefinition(
            map_id="broken_reference_map",
            name="Broken Reference Map",
            cities={
                "alpha": _city("Alpha", ResourceType.FOOD),
                "bravo": _city("Bravo", ResourceType.PRODUCTION),
            },
            edges=[MapEdge(city_a="alpha", city_b="bravo", distance_ticks=1)],
        ),
        initial_state=MatchState(
            tick=3,
            cities={
                "alpha": _city_state(owner="player_1"),
                "bravo": _city_state(owner=None),
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
                ).model_copy(update={"owner": "ghost"})
            ],
            players={
                "player_1": PlayerState(
                    resources=ResourceState(food=30, production=20, money=30),
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
        ),
        ticks=1,
    )


def test_regression_harness_executes_declared_batch() -> None:
    _assert_expected_batch_outputs()


def test_regression_harness_reports_reproducible_invariant_failures() -> None:
    failing_result = run_simulation_regression_batch([_broken_reference_scenario()])

    assert failing_result.failures == [
        RegressionFailure(
            scenario_id="broken-reference",
            invariant="army-owner-exists",
            tick=3,
            detail="army 'army_1' references unknown owner 'ghost'",
        )
    ]


def test_regression_harness_is_deterministic_across_repeated_runs() -> None:
    _assert_expected_batch_outputs()
    _assert_expected_batch_outputs()


def test_regression_harness_formats_multiple_corrupt_state_failures() -> None:
    scenario = _broken_reference_scenario()
    broken_city = scenario.initial_state.cities["alpha"].model_copy(
        update={
            "owner": "ghost-city-owner",
            "population": -1,
            "garrison": -2,
            "resources": scenario.initial_state.cities["alpha"].resources.model_copy(
                update={"food": -1}
            ),
        }
    )
    broken_army = scenario.initial_state.armies[0].model_copy(
        update={
            "owner": "ghost-army-owner",
            "troops": 0,
            "location": "void",
            "destination": "phantom-city",
            "path": ["alpha", "void"],
            "ticks_remaining": 1,
        }
    )
    broken_player = scenario.initial_state.players["player_1"].model_copy(
        update={
            "resources": scenario.initial_state.players["player_1"].resources.model_copy(
                update={"money": -1}
            ),
            "cities_owned": ["phantom-city"],
            "is_eliminated": False,
        }
    )
    malformed_scenario = RegressionScenario(
        scenario_id="malformed-state",
        map_definition=scenario.map_definition,
        initial_state=scenario.initial_state.model_copy(
            update={
                "cities": {"alpha": broken_city},
                "armies": [broken_army],
                "players": {"player_1": broken_player},
            }
        ),
        ticks=1,
    )

    result = run_simulation_regression_batch([malformed_scenario])
    formatted = format_regression_failures(result.failures)

    assert result.total_runs == 1
    assert result.scenario_results == []
    assert "scenario_id=malformed-state tick=3 invariant=state-cities-match-map" in formatted
    assert "invariant=city-owner-exists" in formatted
    assert "invariant=city-population-non-negative" in formatted
    assert "invariant=city-garrison-non-negative" in formatted
    assert "invariant=city-resource:alpha:food-non-negative" in formatted
    assert "invariant=army-owner-exists" in formatted
    assert "invariant=army-troops-positive" in formatted
    assert "invariant=army-location-exists" in formatted
    assert "invariant=army-destination-exists" in formatted
    assert "invariant=army-path-cities-exist" in formatted
    assert "invariant=player-resource:player_1:money-non-negative" in formatted
    assert "invariant=player-city-reference-exists" in formatted
    assert "invariant=player-city-ownership-consistent" in formatted
    assert "invariant=player-elimination-consistent" in formatted
