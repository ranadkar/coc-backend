from typing import Any

import httpx
from fastapi import HTTPException

from .utils import normalize_player_tag


class ClashOfClansClient:
    def __init__(self, base_url: str, api_token: str) -> None:
        self.base_url = base_url
        self.api_token = api_token

    async def fetch_json(self, url: str) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, headers=headers)

        if response.status_code != 200:
            detail: Any = response.text
            try:
                detail = response.json()
            except Exception:
                pass
            raise HTTPException(status_code=response.status_code, detail=detail)

        return response.json()

    async def fetch_player_data(self, tag: str) -> dict[str, Any]:
        normalized_tag = normalize_player_tag(tag)
        encoded_tag = f"%23{normalized_tag.lstrip('#')}"
        url = f"{self.base_url}/players/{encoded_tag}"
        return await self.fetch_json(url)

    async def fetch_battle_log(self, tag: str) -> dict[str, Any]:
        normalized_tag = normalize_player_tag(tag)
        encoded_tag = f"%23{normalized_tag.lstrip('#')}"
        url = f"{self.base_url}/players/{encoded_tag}/battlelog"
        return await self.fetch_json(url)
