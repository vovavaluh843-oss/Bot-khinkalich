"""
Ядро системы викторины.
Содержит БД и бизнес-логику, независимую от платформы.
"""

from .database import init_db
from .quiz_engine import (
    register_user,
    get_categories,
    start_quiz_session,
    check_answer,
    finish_quiz,
    get_random_question_for_user,
    get_user_full_stats,
    reset_progress,
    get_remaining_count,
)

__all__ = [
    "init_db",
    "register_user",
    "get_categories",
    "start_quiz_session",
    "check_answer",
    "finish_quiz",
    "get_random_question_for_user",
    "get_user_full_stats",
    "reset_progress",
    "get_remaining_count",
]
