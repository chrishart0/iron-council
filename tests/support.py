from __future__ import annotations

from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType


@dataclass(frozen=True)
class RunningApp:
    base_url: str
    primary_match_id: str
    secondary_match_id: str


def load_python_agent_sdk_module() -> ModuleType:
    sdk_path = Path(__file__).resolve().parents[1] / "agent-sdk/python/iron_council_client.py"
    spec = spec_from_file_location("iron_council_client", sdk_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load SDK module from {sdk_path}.")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
