from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from iron_council_client import IronCouncilClient  # noqa: E402

DEFAULT_ORDERS: dict[str, list[dict[str, Any]]] = {
    "movements": [],
    "recruitment": [],
    "upgrades": [],
    "transfers": [],
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one deterministic Iron Council agent cycle.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("IRON_COUNCIL_BASE_URL"),
        help="Iron Council server base URL. Falls back to IRON_COUNCIL_BASE_URL.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("IRON_COUNCIL_API_KEY"),
        help="Iron Council agent API key. Falls back to IRON_COUNCIL_API_KEY.",
    )
    parser.add_argument(
        "--match-id",
        default=os.environ.get("IRON_COUNCIL_MATCH_ID"),
        help="Optional target match ID. Falls back to IRON_COUNCIL_MATCH_ID.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.base_url:
        raise SystemExit("Missing base URL. Set --base-url or IRON_COUNCIL_BASE_URL.")
    if not args.api_key:
        raise SystemExit("Missing API key. Set --api-key or IRON_COUNCIL_API_KEY.")

    client = IronCouncilClient(base_url=args.base_url, api_key=args.api_key)
    match_id = args.match_id or _select_first_match_id(client)
    profile = client.get_current_agent_profile()
    join = client.join_match(match_id)
    state = client.get_match_state(match_id)
    submission = client.submit_orders(
        match_id,
        tick=state.tick,
        orders=DEFAULT_ORDERS,
    )

    print(
        json.dumps(
            {
                "agent_id": profile.agent_id,
                "match_id": match_id,
                "player_id": join.player_id,
                "tick": state.tick,
                "submission_status": submission.status,
                "submission_index": submission.submission_index,
            }
        )
    )
    return 0


def _select_first_match_id(client: IronCouncilClient) -> str:
    matches = client.list_matches().matches
    if not matches:
        raise SystemExit("No matches are available to join.")
    return matches[0].match_id


if __name__ == "__main__":
    raise SystemExit(main())
