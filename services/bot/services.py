import aiohttp
import logging
from config import settings

logger = logging.getLogger(__name__)

class AdminAPI:
    def __init__(self):
        self.base_url = settings.ADMIN_API_URL

    async def _post(self, endpoint, data):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(f"{self.base_url}{endpoint}", json=data) as resp:
                    if resp.status >= 400:
                        logger.error(f"API Error {resp.status}: {await resp.text()}")
                        return None
                    return await resp.json()
            except Exception as e:
                logger.error(f"Request failed: {e}")
                return None

    async def _get(self, endpoint):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}{endpoint}") as resp:
                    if resp.status != 200:
                        return None
                    return await resp.json()
            except Exception as e:
                logger.error(f"Request failed: {e}")
                return None

    async def register_user(self, telegram_id: int, username: str, full_name: str):
        return await self._post("/users/", {
            "telegram_id": str(telegram_id),
            "username": username,
            "full_name": full_name
        })

    async def get_strategies(self):
        return await self._get("/strategies/") or []

    async def get_user_subscriptions(self, telegram_id: int):
        # This endpoint needs to be implemented in Admin API
        return await self._get(f"/users/{telegram_id}/subscriptions") or []

api_client = AdminAPI()
