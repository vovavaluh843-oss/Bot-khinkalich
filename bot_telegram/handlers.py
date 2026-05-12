"""
Хендлеры Telegram-бота.
Только API-логика, вся бизнес-логика в core/quiz_engine.py
"""

import json
import logging
from typing import Dict, Any

from aiogram import types, F
from aiogram.types import Message
from aiogram.filters import CommandStart

from core import (
    register_user, get_categories, start_quiz_session,
    check_answer, finish_quiz, get_random_question_for_user,
    get_user_full_stats, reset_progress, get_remaining_count
)
from .keyboards import (
    get_main_keyboard, get_settings_keyboard,
    get_reset_category_keyboard, get_confirm_reset_keyboard,
    get_quiz_keyboard, get_next_question_keyboard,
    get_random_question_keyboard
)

logger = logging.getLogger(__name__)

# Временное хранилище сессий (в продакшене лучше Redis)
user_sessions: Dict[int, Dict[str, Any]] = {}


async def cmd_start(message: Message):
    """/start — регистрация и приветствие"""
    user = register_user(
        platform="telegram",
        external_id=str(message.from_user.id),
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )

    remaining = get_remaining_count(user["id"])

    text = (
        f"👋 Привет, {message.from_user.first_name or 'друг'}!\n\n"
        "🍽️ Добро пожаловать в викторину по меню!\n\n"
        "🎯 <b>Что умеет бот:</b>\n"
        "• 🎮 <b>Викторина</b> — отвечай на вопросы через мини-приложение\n"
        "• 📜 <b>Случайный вопрос</b> — быстрая викторина прямо в чате\n"
        "• 📊 <b>Статистика</b> — следи за прогрессом\n"
        "• 🔄 <b>Сброс прогресса</b> — начни заново когда захочешь\n\n"
        f"❓ Осталось непройденных вопросов: <b>{remaining}</b>\n\n"
        "Нажми 🎮 <b>Начать викторину</b> чтобы играть!"
    )

    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="HTML")


async def handle_text(message: Message):
    """Обработка текстовых кнопок"""
    text = message.text
    user = register_user(
        platform="telegram",
        external_id=str(message.from_user.id),
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    user_id = user["id"]

    if text == "🎮 Начать викторину":
        await message.answer(
            "👇 Нажми кнопку ниже, чтобы открыть мини-приложение:",
            reply_markup=get_main_keyboard()
        )

    elif text == "📊 Моя статистика":
        await show_stats(message, user_id)

    elif text == "📜 Случайный вопрос":
        await send_random_question(message, user_id)

    elif text == "⚙️ Настройки":
        await show_settings(message)


async def show_stats(message: Message, user_id: int = None):
    """Показать статистику"""
    if user_id is None:
        user = register_user(
            platform="telegram",
            external_id=str(message.from_user.id),
            username=message.from_user.username,
            first_name=message.from_user.first_name
        )
        user_id = user["id"]

    stats = get_user_full_stats(user_id)

    text = (
        f"📊 <b>Ваша статистика</b>\n\n"
        f"🎮 Игр сыграно: <b>{stats['games_played']}</b>\n"
        f"❓ Всего ответов: <b>{stats['total_questions']}</b>\n"
        f"✅ Правильно: <b>{stats['correct_answers']}</b>\n"
        f"❌ Ошибок: <b>{stats['wrong_answers']}</b>\n"
        f"🎯 Точность: <b>{stats['accuracy']}%</b>\n"
        f"🔥 Лучшая серия: <b>{stats['best_streak']}</b>\n"
        f"🏆 Всего очков: <b>{stats['total_score']}</b>\n\n"
        f"📚 Прогресс: <b>{stats['answered_unique']}/{stats['total_questions_in_db']}</b> "
        f"(<b>{stats['progress_percent']}%</b> вопросов пройдено)"
    )

    await message.answer(text, parse_mode="HTML")


async def show_settings(message: Message):
    """Показать настройки"""
    await message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        "Здесь ты можешь сбросить свой прогресс и начать заново.",
        reply_markup=get_settings_keyboard(),
        parse_mode="HTML"
    )


async def callback_settings(callback: types.CallbackQuery):
    """Обработка настроек"""
    data = callback.data

    if data == "settings":
        await callback.message.edit_text(
            "⚙️ <b>Настройки</b>\n\n"
            "Здесь ты можешь сбросить свой прогресс и начать заново.",
            reply_markup=get_settings_keyboard(),
            parse_mode="HTML"
        )

    elif data == "reset_all":
        await callback.message.edit_text(
            "⚠️ <b>Сбросить весь прогресс?</b>\n\n"
            "Это удалит все ответы и обнулит статистику. Действие нельзя отменить!",
            reply_markup=get_confirm_reset_keyboard(),
            parse_mode="HTML"
        )

    elif data == "reset_cat":
        cats = get_categories()
        await callback.message.edit_text(
            "🗑 <b>Выберите категорию для сброса:</b>",
            reply_markup=get_reset_category_keyboard(cats),
            parse_mode="HTML"
        )

    elif data.startswith("reset_cat_"):
        cat_key = data.replace("reset_cat_", "")
        cats = get_categories()
        cat_name = next((c["name"] for c in cats if c["key"] == cat_key), cat_key)
        await callback.message.edit_text(
            f"⚠️ <b>Сбросить прогресс по категории '{cat_name}'?</b>\n\n"
            f"Ответы по этой категории будут удалены.",
            reply_markup=get_confirm_reset_keyboard(cat_key),
            parse_mode="HTML"
        )

    elif data == "confirm_reset_all":
        user = register_user(
            platform="telegram",
            external_id=str(callback.from_user.id)
        )
        reset_progress(user["id"])
        remaining = get_remaining_count(user["id"])
        await callback.message.edit_text(
            f"✅ <b>Прогресс полностью сброшен!</b>\n\n"
            f"❓ Доступно вопросов: <b>{remaining}</b>\n\n"
            f"Удачи в новой игре! 🍀",
            parse_mode="HTML"
        )

    elif data.startswith("confirm_reset_"):
        cat_key = data.replace("confirm_reset_", "")
        user = register_user(
            platform="telegram",
            external_id=str(callback.from_user.id)
        )
        reset_progress(user["id"], cat_key)
        remaining = get_remaining_count(user["id"], cat_key)
        await callback.message.edit_text(
            f"✅ <b>Прогресс по категории сброшен!</b>\n\n"
            f"❓ Осталось непройденных в этой категории: <b>{remaining}</b>",
            parse_mode="HTML"
        )

    elif data == "back_main":
        await callback.message.delete()
        await callback.message.answer(
            "Главное меню:", reply_markup=get_main_keyboard()
        )

    await callback.answer()


async def send_random_question(message: Message, user_id: int = None):
    """Отправить случайный вопрос в чат"""
    if user_id is None:
        user = register_user(
            platform="telegram",
            external_id=str(message.from_user.id),
            username=message.from_user.username,
            first_name=message.from_user.first_name
        )
        user_id = user["id"]

    question = get_random_question_for_user(user_id, exclude_answered=True)
    if not question:
        # Все отвечены — берём любой
        question = get_random_question_for_user(user_id, exclude_answered=False)

    if not question:
        await message.answer("❌ В базе пока нет вопросов.")
        return

    # Сохраняем текущий вопрос в сессии
    user_sessions[user_id] = {
        "current_question": question
    }

    text = (
        f"🎲 <b>Случайный вопрос!</b>\n\n"
        f"🍽️ <b>{question['dish_name']}</b>\n"
        f"📁 {question.get('emoji', '')} {question['category_name']}\n\n"
        f"❓ {question['question']}"
    )

    await message.answer(
        text,
        reply_markup=get_quiz_keyboard(question["options"], question["id"]),
        parse_mode="HTML"
    )


async def callback_answer(callback: types.CallbackQuery):
    """Обработка ответа на случайный вопрос"""
    data = callback.data
    if not data.startswith("ans_"):
        return

    parts = data.split("_")
    if len(parts) != 3:
        return

    question_id = int(parts[1])
    selected_index = int(parts[2])

    user = register_user(
        platform="telegram",
        external_id=str(callback.from_user.id)
    )
    user_id = user["id"]

    # Получаем вопрос из сессии
    session = user_sessions.get(user_id, {})
    question = session.get("current_question")

    if not question or question["id"] != question_id:
        await callback.answer("Вопрос устарел, начни заново!", show_alert=True)
        return

    correct_index = question["correct_index"]
    is_correct = selected_index == correct_index

    # Сохраняем ответ через движок
    from core.database import save_answer, update_user_stats
    save_answer(user_id, question_id, selected_index, is_correct)

    points = 10 if is_correct else 0
    update_user_stats(user_id, is_correct, points)

    if is_correct:
        result_text = (
            f"✅ <b>Правильно!</b>\n"
            f"+{points} очков\n\n"
        )
    else:
        correct_option = question["options"][correct_index]
        result_text = (
            f"❌ <b>Неправильно!</b>\n"
            f"Правильный ответ: <b>{correct_option}</b>\n\n"
        )

    result_text += (
        f"🍽️ <b>{question['dish_name']}</b>\n"
        f"📝 {question.get('dish_description', '')}"
    )

    await callback.message.edit_text(
        result_text,
        reply_markup=get_random_question_keyboard(question_id),
        parse_mode="HTML"
    )
    await callback.answer("✅ Ответ принят!" if is_correct else "❌ Увы!")


async def callback_random(callback: types.CallbackQuery):
    """Ещё случайный вопрос"""
    if callback.data == "random_q":
        user = register_user(
            platform="telegram",
            external_id=str(callback.from_user.id)
        )
        await send_random_question(callback.message, user["id"])
        await callback.answer()
    elif callback.data == "show_stats":
        user = register_user(
            platform="telegram",
            external_id=str(callback.from_user.id)
        )
        await show_stats(callback.message, user["id"])
        await callback.answer()


async def handle_webapp_data(message: Message):
    """Обработка данных из мини-приложения"""
    if not message.web_app_data:
        return

    try:
        data = json.loads(message.web_app_data.data)
        user = register_user(
            platform="telegram",
            external_id=str(message.from_user.id),
            username=message.from_user.username,
            first_name=message.from_user.first_name
        )

        # Обновляем статистику из WebApp
        from core.database import increment_games_played, get_user_stats
        increment_games_played(user["id"])
        stats = get_user_stats(user["id"])

        total = data.get("total", 0)
        correct = data.get("correct", 0)
        accuracy = round((correct / total) * 100) if total > 0 else 0

        text = (
            f"🎮 <b>Игра завершена!</b>\n\n"
            f"🏆 Счёт: <b>{data.get('score', 0)}</b>\n"
            f"✅ Правильно: <b>{correct}/{total}</b>\n"
            f"🎯 Точность: <b>{accuracy}%</b>\n"
            f"🔥 Лучшая серия: <b>{data.get('bestStreak', 0)}</b>\n"
            f"🎮 Всего игр: <b>{stats['games_played']}</b>\n\n"
            f"Хочешь сыграть ещё раз?"
        )

        await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="HTML")

    except json.JSONDecodeError:
        logger.error("Ошибка декодирования данных WebApp")
