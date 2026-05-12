"""
Универсальный скрипт запуска бота.
"""

import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description="Запуск бота викторины")
    parser.add_argument(
        "--platform",
        choices=["telegram", "vk"],
        default="telegram",
        help="Платформа для запуска (по умолчанию: telegram)"
    )
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Выполнить миграцию данных из menu_data.py перед запуском"
    )

    args = parser.parse_args()

    if args.migrate:
        print("🚀 Запуск миграции данных...")
        from migrate_data import migrate
        migrate()
        print()

    if args.platform == "telegram":
        print("🤖 Запуск Telegram-бота...")
        from bot_telegram.main import main as tg_main
        import asyncio
        asyncio.run(tg_main())

    elif args.platform == "vk":
        print("🤖 Запуск VK-бота...")
        from bot_vk.main import main as vk_main
        vk_main()


if __name__ == "__main__":
    main()
