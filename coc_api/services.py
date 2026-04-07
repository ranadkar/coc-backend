import asyncio
import logging
from datetime import datetime, timezone

from .client import ClashOfClansClient
from .parsers import BATTLE_CATEGORY_KEYS, BattleBuckets, parse_battle_log
from .repository import BattleLogRepository
from .utils import normalize_player_tag


class BattleLogService:
    def __init__(
        self,
        client: ClashOfClansClient,
        repository: BattleLogRepository,
        sync_interval_seconds: int,
        logger: logging.Logger,
        tracked_tags: tuple[str, ...],
    ) -> None:
        self.client = client
        self.repository = repository
        self.sync_interval_seconds = sync_interval_seconds
        self.logger = logger
        self.tracked_tags = frozenset(normalize_player_tag(tag) for tag in tracked_tags)

    def is_tracked_tag(self, tag: str) -> bool:
        return normalize_player_tag(tag) in self.tracked_tags

    def _empty_battle_counts(self) -> dict[str, int]:
        return {category: 0 for category in BATTLE_CATEGORY_KEYS}

    def get_stored_battle_log(self, tag: str) -> BattleBuckets:
        if not self.is_tracked_tag(tag):
            return {category: [] for category in BATTLE_CATEGORY_KEYS}
        return self.repository.get_stored_battle_log(tag)

    async def get_live_battle_log(self, tag: str) -> BattleBuckets:
        battle_log_data = await self.client.fetch_battle_log(tag)
        return parse_battle_log(battle_log_data)

    async def get_or_sync_stored_battle_log(self, tag: str) -> BattleBuckets:
        normalized_tag = normalize_player_tag(tag)
        if not self.is_tracked_tag(normalized_tag):
            return await self.get_live_battle_log(normalized_tag)

        stored_battles = self.repository.get_stored_battle_log(normalized_tag)
        if any(stored_battles.values()):
            return stored_battles

        await self.sync_once(normalized_tag)
        return self.repository.get_stored_battle_log(normalized_tag)

    async def sync_once(self, tag: str) -> dict[str, object]:
        normalized_tag = normalize_player_tag(tag)
        battle_log_data = await self.client.fetch_battle_log(normalized_tag)
        parsed_battles = parse_battle_log(battle_log_data)
        seen_at = datetime.now(timezone.utc).isoformat()
        is_tracked = normalized_tag in self.tracked_tags

        if is_tracked:
            self.repository.store_battle_views(normalized_tag, parsed_battles, seen_at)

        return {
            "tag": normalized_tag,
            "persisted": is_tracked,
            "seenAt": seen_at,
            "fetchedCounts": {
                category: len(battles) for category, battles in parsed_battles.items()
            },
            "storedCounts": (
                self.repository.get_stored_battle_counts(normalized_tag)
                if is_tracked
                else self._empty_battle_counts()
            ),
        }

    async def periodic_sync(self, tag: str) -> None:
        normalized_tag = normalize_player_tag(tag)
        while True:
            try:
                await self.sync_once(normalized_tag)
            except Exception:
                self.logger.exception("Battle log sync failed for %s", normalized_tag)
            await asyncio.sleep(self.sync_interval_seconds)
