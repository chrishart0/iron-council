from __future__ import annotations

from hashlib import sha256


def hash_api_key(api_key: str) -> str:
    return sha256(api_key.encode("utf-8")).hexdigest()
