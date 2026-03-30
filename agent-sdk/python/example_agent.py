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
    parser.add_argument(
        "--create-lobby",
        action="store_true",
        help="Create a new lobby instead of targeting an existing match.",
    )
    parser.add_argument(
        "--joiner-api-key",
        default=os.environ.get("IRON_COUNCIL_JOINER_API_KEY"),
        help="Optional second agent API key used to join a created lobby.",
    )
    parser.add_argument(
        "--auto-start",
        action="store_true",
        help="Start a created lobby after enough players have joined.",
    )
    parser.add_argument(
        "--tick-interval-seconds",
        type=int,
        default=int(os.environ.get("IRON_COUNCIL_TICK_INTERVAL_SECONDS", "20")),
        help="Lobby tick interval when --create-lobby is used.",
    )
    parser.add_argument(
        "--max-players",
        type=int,
        default=int(os.environ.get("IRON_COUNCIL_MAX_PLAYERS", "4")),
        help="Lobby size when --create-lobby is used.",
    )
    parser.add_argument(
        "--victory-city-threshold",
        type=int,
        default=int(os.environ.get("IRON_COUNCIL_VICTORY_CITY_THRESHOLD", "13")),
        help="Victory threshold when --create-lobby is used.",
    )
    parser.add_argument(
        "--starting-cities-per-player",
        type=int,
        default=int(os.environ.get("IRON_COUNCIL_STARTING_CITIES_PER_PLAYER", "2")),
        help="Starting cities when --create-lobby is used.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.base_url:
        raise SystemExit("Missing base URL. Set --base-url or IRON_COUNCIL_BASE_URL.")
    if not args.api_key:
        raise SystemExit("Missing API key. Set --api-key or IRON_COUNCIL_API_KEY.")

    client = IronCouncilClient(base_url=args.base_url, api_key=args.api_key)
    if args.create_lobby:
        summary = _run_lobby_lifecycle(args, client)
    else:
        if not args.match_id:
            args.match_id = _select_first_match_id(client)
        summary = _run_existing_match_cycle(args, client)

    print(json.dumps(summary))
    return 0


def _select_first_match_id(client: IronCouncilClient) -> str:
    matches = client.list_matches().matches
    if not matches:
        raise SystemExit("No matches are available to join.")

    for match in matches:
        status = getattr(match, "status", None)
        open_slot_count = getattr(match, "open_slot_count", None)
        if status not in (None, "lobby", "paused"):
            continue
        if open_slot_count is not None and open_slot_count <= 0:
            continue
        return match.match_id

    raise SystemExit(
        "No joinable lobby or paused match is available. Pass --match-id or use --create-lobby."
    )


def _run_existing_match_cycle(
    args: argparse.Namespace,
    client: IronCouncilClient,
) -> dict[str, Any]:
    match_id = args.match_id or _select_first_match_id(client)
    joined = client.join_match(match_id)
    state = client.get_match_state(match_id)
    submission = client.submit_orders(
        match_id,
        tick=state.tick,
        orders=DEFAULT_ORDERS,
    )
    return {
        "agent_id": joined.agent_id,
        "mode": "existing-match",
        "match_id": match_id,
        "player_id": state.player_id,
        "tick": state.tick,
        "submission_status": submission.status,
        "submission_index": submission.submission_index,
    }


def _run_lobby_lifecycle(
    args: argparse.Namespace,
    client: IronCouncilClient,
) -> dict[str, Any]:
    created = client.create_match_lobby(
        map="britain",
        tick_interval_seconds=args.tick_interval_seconds,
        max_players=args.max_players,
        victory_city_threshold=args.victory_city_threshold,
        starting_cities_per_player=args.starting_cities_per_player,
    )
    profile = client.get_current_agent_profile()

    joined = None
    if args.joiner_api_key:
        joiner_client = IronCouncilClient(base_url=args.base_url, api_key=args.joiner_api_key)
        joined = joiner_client.join_match(created.match_id)

    started = None
    if args.auto_start:
        started = client.start_match_lobby(created.match_id)

    return {
        "agent_id": profile.agent_id,
        "mode": "lobby-lifecycle",
        "match_id": created.match_id,
        "creator_player_id": created.creator_player_id,
        "joined_player_id": None if joined is None else joined.player_id,
        "joined_status": None if joined is None else joined.status,
        "started": started is not None,
        "match_status": created.status if started is None else started.status,
        "current_player_count": (
            created.current_player_count if started is None else started.current_player_count
        ),
        "open_slot_count": created.open_slot_count if started is None else started.open_slot_count,
    }


if __name__ == "__main__":
    raise SystemExit(main())
