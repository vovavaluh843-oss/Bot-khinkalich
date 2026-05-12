"""
Точка входа для Telegram-бота.
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart

from core import init_db
from .handlers import (
    cmd_start, handle_text, show_settings, callback_settings,
    callback_answer, callback_random, handle_webapp_data
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")


def register_handlers(dp: Dispatcher):
    """Регистрация всех хендлеров"""
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(handle_webapp_data, F.web_app_data)
    dp.message.register(handle_text)

    dp.callback_query.register(callback_settings, F.data.startswith("reset_") | F.data.startswith("confirm_reset_") | F.data.in_(["settings", "back_main"]))
    dp.callback_query.register(callback_answer, F.data.startswith("ans_"))
    dp.callback_query.register(callback_random, F.data.in_(["random_q", "show_stats"]))


async def main():
    """Запуск бота"""
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ BOT_TOKEN не указан! Добавьте его в .env файл")
        logger.error("📝 Получить токен: @BotFather в Telegram")
        return

    # Инициализация БД
    init_db()
    logger.info("✅ База данных готова")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    register_handlers(dp)

    logger.info("✅ Telegram-бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
