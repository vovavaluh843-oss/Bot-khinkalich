"""
Движок викторины — чистая бизнес-логика.
Независим от платформы (Telegram, VK и т.д.)
"""

import random
import logging
from typing import List, Dict, Any, Optional, Tuple
from .database import (
    get_or_create_user, get_user_stats, update_user_stats,
    get_questions, get_question_by_id, save_answer,
    increment_games_played, reset_user_progress,
    get_answered_count, get_questions_count, get_all_categories
)

logger = logging.getLogger(__name__)


def register_user(platform: str, external_id: str, **kwargs) -> Dict[str, Any]:
    """Регистрация/получение пользователя"""
    return get_or_create_user(platform, external_id, **kwargs)


def get_categories() -> List[Dict[str, Any]]:
    """Получить список категорий"""
    return get_all_categories()


def start_quiz_session(user_id: int, mode: str = "classic",
                       category_key: Optional[str] = None,
                       exclude_answered: bool = True) -> Dict[str, Any]:
    """
    Начать сессию викторины.
    Возвращает набор вопросов и мета-информацию.
    """
    # Определяем количество вопросов
    if mode == "classic":
        limit = 10
    elif mode == "endless":
        limit = 100  # Практически бесконечно
    else:
        limit = 10

    # Получаем вопросы
    questions = get_questions(
        category_key=category_key if category_key != "all" else None,
        exclude_answered_by=user_id if exclude_answered else None,
        limit=limit
    )

    # Если с исключением не хватило — берём любые
    if len(questions) < limit:
        all_available = get_questions(
            category_key=category_key if category_key != "all" else None,
            limit=limit
        )
        # Добавляем недостающие
        existing_ids = {q["id"] for q in questions}
        for q in all_available:
            if q["id"] not in existing_ids:
                questions.append(q)
            if len(questions) >= limit:
                break

    return {
        "user_id": user_id,
        "mode": mode,
        "category": category_key,
        "total_questions": len(questions),
        "questions": questions,
        "current_index": 0,
        "score": 0,
        "correct": 0,
        "wrong": 0,
        "streak": 0,
        "best_streak": 0
    }


def check_answer(session: Dict[str, Any], question_index: int,
                 selected_index: int) -> Dict[str, Any]:
    """
    Проверить ответ. Обновляет сессию и сохраняет в БД.
    Возвращает результат с объяснением.
    """
    questions = session.get("questions", [])
    if question_index >= len(questions):
        return {"error": "Вопрос не найден"}

    question = questions[question_index]
    correct_index = question["correct_index"]
    is_correct = selected_index == correct_index

    user_id = session["user_id"]

    # Сохраняем ответ в БД
    save_answer(user_id, question["id"], selected_index, is_correct)

    # Обновляем сессию
    session["current_index"] = question_index + 1

    if is_correct:
        session["streak"] += 1
        session["correct"] += 1
        if session["streak"] > session["best_streak"]:
            session["best_streak"] = session["streak"]
        points = 10 + (session["streak"] - 1) * 2
        session["score"] += points
    else:
        session["streak"] = 0
        session["wrong"] += 1
        points = 0

    # Обновляем статистику в БД
    update_user_stats(user_id, is_correct, points)

    return {
        "is_correct": is_correct,
        "correct_index": correct_index,
        "selected_index": selected_index,
        "points": points,
        "total_score": session["score"],
        "streak": session["streak"],
        "question": question,
        "dish_name": question["dish_name"],
        "dish_description": question.get("dish_description", ""),
        "category_name": question.get("category_name", ""),
        "is_last": question_index >= len(questions) - 1
    }


def finish_quiz(session: Dict[str, Any]) -> Dict[str, Any]:
    """Завершить викторину, сохранить итоговую статистику"""
    user_id = session["user_id"]
    increment_games_played(user_id)

    stats = get_user_stats(user_id)

    total = session["total_questions"]
    correct = session["correct"]
    accuracy = round((correct / total) * 100) if total > 0 else 0

    return {
        "score": session["score"],
        "correct": correct,
        "wrong": session["wrong"],
        "total": total,
        "accuracy": accuracy,
        "best_streak": session["best_streak"],
        "user_best_score": stats["total_score"],
        "user_games_played": stats["games_played"]
    }


def get_random_question_for_user(user_id: int,
                                 category_key: Optional[str] = None,
                                 exclude_answered: bool = True) -> Optional[Dict[str, Any]]:
    """Получить один случайный вопрос для пользователя"""
    questions = get_questions(
        category_key=category_key,
        exclude_answered_by=user_id if exclude_answered else None,
        limit=1
    )
    if not questions:
        # Если все отвечены — берём любой
        questions = get_questions(category_key=category_key, limit=1)
    return questions[0] if questions else None


def get_user_full_stats(user_id: int) -> Dict[str, Any]:
    """Полная статистика пользователя"""
    stats = get_user_stats(user_id)
    answered = get_answered_count(user_id)
    total = get_questions_count()

    accuracy = 0
    if stats["total_questions"] > 0:
        accuracy = round((stats["correct_answers"] / stats["total_questions"]) * 100)

    return {
        **stats,
        "answered_unique": answered,
        "total_questions_in_db": total,
        "progress_percent": round((answered / total) * 100) if total > 0 else 0,
        "accuracy": accuracy
    }


def reset_progress(user_id: int, category_key: Optional[str] = None):
    """Сбросить прогресс пользователя"""
    reset_user_progress(user_id, category_key)


def get_remaining_count(user_id: int, category_key: Optional[str] = None) -> int:
    """Сколько вопросов осталось непройденными"""
    total = get_questions_count(category_key)
    answered = get_answered_count(user_id, category_key)
    return total - answered
