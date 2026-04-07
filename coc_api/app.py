import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .client import ClashOfClansClient
from .config import AppConfig, validate_coc_api_token
from .parsers import parse_hero_equipment
from .repository import BattleLogRepository
from .services import BattleLogService
from .utils import normalize_player_tag


def create_app(config: AppConfig) -> FastAPI:
    logger = logging.getLogger("uvicorn.error")
    tracked_tags = tuple(
        normalize_player_tag(tag)
        for tag in dict.fromkeys(config.tracked_battle_log_tags)
        if tag.strip()
    )
    client = ClashOfClansClient(config.coc_api_base_url, config.coc_api_token or "")
    repository = BattleLogRepository(
        db_path=config.battle_log_db_path,
        category_limit=config.battle_log_category_limit,
    )
    battle_log_service = BattleLogService(
        client=client,
        repository=repository,
        sync_interval_seconds=config.battle_log_sync_interval_seconds,
        logger=logger,
        tracked_tags=tracked_tags,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        validate_coc_api_token(config)
        repository.init_db()
        repository.purge_untracked_players(tracked_tags)
        app.state.tracked_battle_log_tags = list(tracked_tags)

        sync_tasks = [
            asyncio.create_task(battle_log_service.periodic_sync(tracked_tag))
            for tracked_tag in tracked_tags
        ]

        if tracked_tags:
            logger.info(
                "Started battle log sync for %s tracked players every %s seconds: %s",
                len(tracked_tags),
                config.battle_log_sync_interval_seconds,
                ", ".join(tracked_tags),
            )

        try:
            yield
        finally:
            for sync_task in sync_tasks:
                sync_task.cancel()
            if sync_tasks:
                with suppress(asyncio.CancelledError):
                    await asyncio.gather(*sync_tasks)

    app = FastAPI(title="COC Hero Equipment API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/hero-equipment/{tag}")
    async def get_hero_equipment(tag: str):
        player_data = await client.fetch_player_data(tag)
        return parse_hero_equipment(player_data)

    @app.get("/profile/{tag}")
    async def get_profile(tag: str):
        return await client.fetch_player_data(tag)

    @app.get("/battle-log/{tag}")
    async def get_battle_log(tag: str):
        return await battle_log_service.get_or_sync_stored_battle_log(tag)

    @app.get("/battle-log/{tag}/live")
    async def get_live_battle_log(tag: str):
        return await battle_log_service.get_live_battle_log(tag)

    @app.post("/battle-log/{tag}/sync")
    async def sync_battle_log(tag: str):
        return await battle_log_service.sync_once(tag)

    return app
