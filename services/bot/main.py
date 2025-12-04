import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import settings
from handlers import router
from services import SignalListener

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    if not settings.BOT_TOKEN:
        logger.error("BOT_TOKEN is not set!")
        return

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()
    
    # Include routers
    dp.include_router(router)

    # Start Signal Listener
    signal_listener = SignalListener(bot)
    await signal_listener.start()

    logger.info("Starting Bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
