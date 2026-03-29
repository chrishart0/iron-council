from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunningApp:
    base_url: str
    primary_match_id: str
    secondary_match_id: str
