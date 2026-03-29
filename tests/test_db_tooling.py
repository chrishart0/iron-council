from __future__ import annotations

import pytest
from server.db import tooling


def test_db_tooling_setup_provisions_seeded_database_and_reports_lane(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured_calls: list[tuple[str, bool]] = []

    monkeypatch.setattr("sys.argv", ["server.db.tooling", "setup"])
    monkeypatch.setattr(
        tooling,
        "get_settings",
        lambda: type("Settings", (), {"database_url": "postgresql://example/test_db"})(),
    )
    monkeypatch.setattr(
        tooling,
        "provision_seeded_database",
        lambda *, database_url, reset: captured_calls.append((database_url, reset)),
    )
    monkeypatch.setenv("IRON_COUNCIL_DB_LANE", "worker-2")

    result = tooling.main()

    assert result == 0
    assert captured_calls == [("postgresql://example/test_db", False)]
    assert (
        "setup complete for postgresql://example/test_db lane=worker-2" in capsys.readouterr().out
    )


def test_db_tooling_reset_provisions_seeded_database() -> None:
    captured_calls: list[tuple[str, bool]] = []

    from unittest.mock import patch

    with (
        patch("sys.argv", ["server.db.tooling", "reset"]),
        patch.object(
            tooling,
            "get_settings",
            return_value=type("Settings", (), {"database_url": "postgresql://example/test_db"})(),
        ),
        patch.object(
            tooling,
            "provision_seeded_database",
            side_effect=lambda *, database_url, reset: captured_calls.append((database_url, reset)),
        ),
    ):
        assert tooling.main() == 0

    assert captured_calls == [("postgresql://example/test_db", True)]
