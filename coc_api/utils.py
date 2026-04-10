import hashlib
import json
from typing import Any

from fastapi import HTTPException


def normalize_player_tag(tag: str) -> str:
    stripped = tag.strip().lstrip("#").upper().replace("0", "O")
    if not stripped:
        raise HTTPException(status_code=400, detail="Player tag cannot be empty.")
    return f"#{stripped}"


def dict_hash(data: dict[str, Any]) -> str:
    serialized = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.blake2b(serialized.encode()).hexdigest()
