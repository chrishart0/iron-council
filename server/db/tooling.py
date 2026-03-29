from __future__ import annotations

import argparse
import os

from server.db.testing import provision_seeded_database
from server.settings import DB_LANE_VARIABLE, get_settings


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Provision a worktree-local database with migrations and deterministic seed data."
        )
    )
    parser.add_argument("command", choices=("setup", "reset"))
    args = parser.parse_args()

    settings = get_settings()
    provision_seeded_database(database_url=settings.database_url, reset=args.command == "reset")

    lane_name = os.environ.get(DB_LANE_VARIABLE)
    lane = f" lane={lane_name}" if lane_name else ""
    print(f"{args.command} complete for {settings.database_url}{lane}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
