import json
from typing import Any

from .utils import dict_hash

BATTLE_CATEGORY_KEYS = (
    "normal_attacks",
    "normal_defenses",
    "ranked_attacks",
    "ranked_defenses",
)

BattleBuckets = dict[str, list[dict[str, Any]]]


def empty_battle_buckets() -> BattleBuckets:
    return {key: [] for key in BATTLE_CATEGORY_KEYS}


def parse_hero_equipment(player_data: dict[str, Any]) -> dict[str, int]:
    hero_equipment = player_data.get("heroEquipment", [])
    return {
        item["name"]: item["level"]
        for item in hero_equipment
        if isinstance(item, dict) and "name" in item and "level" in item
    }


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_battle_view(
    battle: dict[str, Any],
    fallback_hash: str | None = None,
) -> dict[str, Any]:
    looted = battle.get("looted")
    if not isinstance(looted, dict):
        looted = {}

    return {
        "hash": _safe_str(battle.get("hash"), fallback_hash or ""),
        "opponent": _safe_str(battle.get("opponent")),
        "stars": _safe_int(battle.get("stars")),
        "destructionPercentage": _safe_int(battle.get("destructionPercentage")),
        "army": _safe_str(battle.get("army")),
        "looted": {
            "gold": _safe_int(looted.get("gold")),
            "elixir": _safe_int(looted.get("elixir")),
            "dark": _safe_int(looted.get("dark")),
        },
    }


def get_battle_category(battle_obj: dict[str, Any]) -> str | None:
    battle_type = battle_obj.get("battleType")
    is_attack = battle_obj.get("attack")

    if battle_type == "homeVillage":
        return "normal_attacks" if is_attack else "normal_defenses"

    if battle_type in {"ranked", "legend"}:
        return "ranked_attacks" if is_attack else "ranked_defenses"

    return None


def build_battle_view(
    battle_obj: dict[str, Any],
    fallback_hash: str | None = None,
) -> dict[str, Any]:
    army_share_code = battle_obj.get("armyShareCode")

    looted = {"gold": 0, "elixir": 0, "dark": 0}
    for resource in battle_obj.get("lootedResources", []):
        if not isinstance(resource, dict):
            continue

        if resource.get("name") == "Gold":
            looted["gold"] = _safe_int(resource.get("amount"))
        elif resource.get("name") == "Elixir":
            looted["elixir"] = _safe_int(resource.get("amount"))
        elif resource.get("name") == "DarkElixir":
            looted["dark"] = _safe_int(resource.get("amount"))

    return {
        "hash": fallback_hash or dict_hash(battle_obj),
        "opponent": _safe_str(battle_obj.get("opponentPlayerTag")),
        "stars": _safe_int(battle_obj.get("stars")),
        "destructionPercentage": _safe_int(battle_obj.get("destructionPercentage")),
        "army": _safe_str(army_share_code),
        "looted": looted,
    }


def parse_stored_battle(battle_json: str, fallback_hash: str) -> dict[str, Any]:
    stored_payload = json.loads(battle_json)
    if not isinstance(stored_payload, dict):
        stored_payload = {}

    return normalize_battle_view(stored_payload, fallback_hash=fallback_hash)


def parse_battle_log(battle_log_data: dict[str, Any]) -> BattleBuckets:
    battle_log = battle_log_data.get("items", [])
    buckets = empty_battle_buckets()

    for battle_obj in battle_log:
        if not isinstance(battle_obj, dict):
            continue

        category = get_battle_category(battle_obj)
        if category is None:
            continue

        buckets[category].append(build_battle_view(battle_obj))

    return buckets
