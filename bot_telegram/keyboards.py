"""
Клавиатуры для Telegram-бота.
"""

import os
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-username.github.io/your-repo/")


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="🎮 Начать викторину", web_app=KeyboardButton.WebAppInfo(url=WEBAPP_URL))
    builder.button(text="📊 Моя статистика")
    builder.button(text="📜 Случайный вопрос")
    builder.button(text="⚙️ Настройки")
    builder.adjust(1, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Настройки"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Сбросить прогресс", callback_data="reset_all")
    builder.button(text="🗑 Сбросить по категории", callback_data="reset_cat")
    builder.button(text="🔙 Назад", callback_data="back_main")
    builder.adjust(1)
    return builder.as_markup()


def get_reset_category_keyboard(categories: list) -> InlineKeyboardMarkup:
    """Выбор категории для сброса"""
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(
            text=f"{cat.get('emoji', '')} {cat['name']}",
            callback_data=f"reset_cat_{cat['key']}"
        )
    builder.button(text="🔄 Сбросить всё", callback_data="reset_all_confirm")
    builder.button(text="🔙 Назад", callback_data="settings")
    builder.adjust(2)
    return builder.as_markup()


def get_confirm_reset_keyboard(category_key: str = None) -> InlineKeyboardMarkup:
    """Подтверждение сброса"""
    builder = InlineKeyboardBuilder()
    if category_key:
        builder.button(text="✅ Да, сбросить", callback_data=f"confirm_reset_{category_key}")
    else:
        builder.button(text="✅ Да, сбросить всё", callback_data="confirm_reset_all")
    builder.button(text="❌ Отмена", callback_data="settings")
    builder.adjust(2)
    return builder.as_markup()


def get_quiz_keyboard(options: list, question_id: int) -> InlineKeyboardMarkup:
    """Клавиатура вариантов ответа"""
    builder = InlineKeyboardBuilder()
    for i, option in enumerate(options):
        builder.button(text=option, callback_data=f"ans_{question_id}_{i}")
    builder.adjust(1)
    return builder.as_markup()


def get_next_question_keyboard() -> InlineKeyboardMarkup:
    """Кнопка следующего вопроса"""
    builder = InlineKeyboardBuilder()
    builder.button(text="➡️ Следующий вопрос", callback_data="next_question")
    return builder.as_markup()


def get_random_question_keyboard(question_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для случайного вопроса"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎲 Ещё вопрос", callback_data="random_q")
    builder.button(text="📊 Статистика", callback_data="show_stats")
    builder.adjust(2)
    return builder.as_markup()
