import aiohttp
import logging
import json
import asyncio
import redis.asyncio as redis
from config import settings
from aiogram import Bot

logger = logging.getLogger(__name__)

class SignalListener:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.redis = None
        self.pubsub = None

    async def start(self):
        """Start listening to Redis channels"""
        try:
            self.redis = redis.from_url(settings.REDIS_URL)
            self.pubsub = self.redis.pubsub()
            await self.pubsub.subscribe('strategy_signals')
            logger.info("Subscribed to Redis channel: strategy_signals")

            # Start the listening loop
            asyncio.create_task(self._listen_loop())
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")

    async def _listen_loop(self):
        """Infinite loop to process messages"""
        try:
            async for message in self.pubsub.listen():
                if message['type'] == 'message':
                    await self._handle_message(message['data'])
        except Exception as e:
            logger.error(f"Error in Redis listener loop: {e}")
            # Reconnect logic could go here

    async def _handle_message(self, data):
        """Process a signal message"""
        try:
            signal_data = json.loads(data)
            logger.info(f"Received signal: {signal_data}")
            
            # Format the message
            text = (
                f"🚨 <b>Signal Alert: {signal_data['strategy_name']}</b>\n\n"
                f"Symbol: <b>{signal_data['symbol']}</b>\n"
                f"Side: <b>{signal_data['side']}</b>\n"
                f"Price: {signal_data['price']}\n"
                f"Reason: {signal_data['reason']}\n"
                f"Time: {signal_data['timestamp']}"
            )

            # Fetch subscribed users from Admin API
            subscribed_users = await api_client.get_strategy_subscribers(signal_data['strategy_id'])
            
            if subscribed_users:
                for user in subscribed_users:
                    try:
                        await self.bot.send_message(chat_id=user['telegram_id'], text=text, parse_mode="HTML")
                        logger.info(f"Sent signal to user {user['telegram_id']}")
                    except Exception as e:
                        logger.error(f"Failed to send message to {user['telegram_id']}: {e}")
            else:
                logger.info(f"No subscribers found for strategy {signal_data['strategy_id']}")

        except Exception as e:
            logger.error(f"Error handling signal message: {e}")

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

    async def get_strategy_subscribers(self, strategy_id: int):
        """Fetch all users subscribed to a specific strategy"""
        return await self._get(f"/strategies/{strategy_id}/subscribers") or []

api_client = AdminAPI()
