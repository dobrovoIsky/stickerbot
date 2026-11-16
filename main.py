import asyncio
import logging
import os
import shutil
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import config
from database.db import init_db
from handlers import start, menu, stickers, packs, admin

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger("StickerBot")

def cleanup_temp_dir():
    """Removes leftover files from temp directory on startup."""
    if os.path.exists(config.TEMP_DIR):
        for item in os.listdir(config.TEMP_DIR):
            item_path = os.path.join(config.TEMP_DIR, item)
            try:
                if os.path.isfile(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except Exception as e:
                logger.warning(f"Could not delete temp item {item_path}: {e}")
    os.makedirs(config.TEMP_DIR, exist_ok=True)

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Головне меню / перезапуск"),
        BotCommand(command="mypack", description="Мій стікерпак"),
        BotCommand(command="help", description="Інструкція з використання"),
        BotCommand(command="ref", description="Реферальна програма"),
        BotCommand(command="admin", description="Адмін-панель"),
    ]
    await bot.set_my_commands(commands)

async def start_health_server():
    """
    Starts a lightweight HTTP server on $PORT (defaults to 10000 for Render Web Services).
    """
    port_str = os.getenv("PORT", "10000")
    try:
        port = int(port_str)
        app = web.Application()

        async def health_handler(request):
            return web.Response(text="Sticker Factory Bot is running OK!", content_type="text/plain")

        app.router.add_get("/", health_handler)
        app.router.add_get("/health", health_handler)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"Render healthcheck server started on http://0.0.0.0:{port}")
        return runner
    except Exception as e:
        logger.warning(f"Could not start health server on port {port_str}: {e}")
        return None

async def main():
    logger.info("Starting Sticker Factory Bot...")

    # 1. Start Render HTTP health server FIRST so deploy never times out
    health_runner = await start_health_server()

    if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or not config.BOT_TOKEN:
        logger.error(
            "⚠️ BOT_TOKEN is not set! Please edit your .env file or environment variables and set your Telegram bot token."
        )
        return

    # 2. Clean temp directory
    cleanup_temp_dir()

    # 3. Initialize Database
    await init_db()

    # 4. Pre-warm background removal AI model
    logger.info("Pre-warming background remover model...")
    try:
        from services.background_remover import get_session
        await asyncio.to_thread(get_session)
        logger.info("Background remover model ready in memory!")
    except Exception as e:
        logger.warning(f"Background remover pre-warm skipped or failed: {e}")

    # 5. Initialize Bot & Dispatcher
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # 5. Register Handlers (Routers)
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(packs.router)
    dp.include_router(stickers.router)

    # 6. Fetch bot info
    bot_me = await bot.get_me()
    logger.info(f"Bot authorized as @{bot_me.username} (ID: {bot_me.id})")

    # 7. Set Commands
    await set_bot_commands(bot)

    # 8. Start Polling
    logger.info("Bot started and listening for messages!")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        if health_runner:
            await health_runner.cleanup()
        await bot.session.close()
        logger.info("Bot stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user.")
