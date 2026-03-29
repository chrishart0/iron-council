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
    scenarios = build_regression_scenarios()
    result = run_simulation_regression_batch(scenarios)

    assert len(scenarios) >= 12
    assert result.total_runs == len(scenarios)
    assert result.failures == [], format_regression_failures(result.failures)


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
    first = run_simulation_regression_batch(build_regression_scenarios())
    second = run_simulation_regression_batch(build_regression_scenarios())

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


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
