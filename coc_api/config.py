import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True, slots=True)
class AppConfig:
    coc_api_base_url: str
    coc_api_token: str | None
    tracked_battle_log_tags: list[str]
    battle_log_sync_interval_seconds: int
    battle_log_category_limit: int
    battle_log_db_path: Path


def load_coc_api_token() -> str | None:
    return os.getenv("COC_API_TOKEN")


def validate_coc_api_token(config: AppConfig) -> str:
    if not config.coc_api_token:
        raise RuntimeError("Missing COC_API_TOKEN environment variable.")
    return config.coc_api_token
