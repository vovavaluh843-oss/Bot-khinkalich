"""
Заготовка для VK-бота.
Использует то же ядро (core), что и Telegram-бот.

Для запуска установите:
    pip install vk-api

И добавьте в .env:
    VK_TOKEN=your_vk_group_token
"""

import os
import logging
from dotenv import load_dotenv

from core import init_db, register_user, get_categories, start_quiz_session, check_answer, finish_quiz

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
VK_TOKEN = os.getenv("VK_TOKEN", "")


def main():
    """Точка входа VK-бота"""
    if not VK_TOKEN:
        logger.error("❌ VK_TOKEN не указан! Добавьте его в .env файл")
        return

    init_db()
    logger.info("✅ VK-бот готов к запуску (заготовка)")
    logger.info("📝 Реализуйте интеграцию с vk-api по аналогии с Telegram-ботом")
    logger.info("   Используйте функции из core.quiz_engine для бизнес-логики")


if __name__ == "__main__":
    main()
