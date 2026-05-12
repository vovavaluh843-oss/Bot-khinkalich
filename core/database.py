"""
Слой работы с базой данных SQLite.
Единая БД для всех платформ (Telegram, VK и др.)
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "quiz.db"


def get_connection() -> sqlite3.Connection:
    """Получить соединение с БД"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Инициализация таблиц БД"""
    conn = get_connection()
    cursor = conn.cursor()

    # Категории
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            emoji TEXT
        )
    """)

    # Блюда
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dishes (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            description TEXT,
            ingredients TEXT,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    """)

    # Вопросы
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dish_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            options TEXT NOT NULL,
            correct_index INTEGER NOT NULL,
            FOREIGN KEY (dish_id) REFERENCES dishes(id)
        )
    """)

    # Пользователи (универсальные для всех платформ)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            external_id TEXT NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(platform, external_id)
        )
    """)

    # Статистика пользователя
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_stats (
            user_id INTEGER PRIMARY KEY,
            total_questions INTEGER DEFAULT 0,
            correct_answers INTEGER DEFAULT 0,
            wrong_answers INTEGER DEFAULT 0,
            current_streak INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0,
            total_score INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # История ответов (для исключения пройденных вопросов)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            selected_index INTEGER NOT NULL,
            is_correct BOOLEAN NOT NULL,
            answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (question_id) REFERENCES questions(id),
            UNIQUE(user_id, question_id)
        )
    """)

    conn.commit()
    conn.close()
    logger.info("✅ База данных инициализирована")


# ==================== CATEGORIES ====================

def add_category(key: str, name: str, emoji: str = "") -> int:
    """Добавить категорию"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO categories (key, name, emoji) VALUES (?, ?, ?)",
        (key, name, emoji)
    )
    conn.commit()
    category_id = cursor.lastrowid
    conn.close()
    return category_id


def get_all_categories() -> List[Dict[str, Any]]:
    """Получить все категории"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_category_by_key(key: str) -> Optional[Dict[str, Any]]:
    """Получить категорию по ключу"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ==================== DISHES ====================

def add_dish(dish_id: int, name: str, category_key: str, description: str,
             ingredients: List[str]) -> int:
    """Добавить блюдо"""
    category = get_category_by_key(category_key)
    if not category:
        raise ValueError(f"Категория {category_key} не найдена")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT OR REPLACE INTO dishes (id, name, category_id, description, ingredients)
           VALUES (?, ?, ?, ?, ?)""",
        (dish_id, name, category["id"], description, json.dumps(ingredients, ensure_ascii=False))
    )
    conn.commit()
    conn.close()
    return dish_id


def get_dish_by_id(dish_id: int) -> Optional[Dict[str, Any]]:
    """Получить блюдо по ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.*, c.key as category_key, c.name as category_name, c.emoji
        FROM dishes d
        JOIN categories c ON d.category_id = c.id
        WHERE d.id = ?
    """, (dish_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    result = dict(row)
    result["ingredients"] = json.loads(result["ingredients"]) if result["ingredients"] else []
    return result


# ==================== QUESTIONS ====================

def add_question(dish_id: int, question: str, options: List[str],
                 correct_index: int) -> int:
    """Добавить вопрос"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO questions (dish_id, question, options, correct_index)
           VALUES (?, ?, ?, ?)""",
        (dish_id, question, json.dumps(options, ensure_ascii=False), correct_index)
    )
    question_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return question_id


def get_question_by_id(question_id: int) -> Optional[Dict[str, Any]]:
    """Получить вопрос по ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT q.*, d.name as dish_name, d.description as dish_description,
               c.key as category_key, c.name as category_name, c.emoji
        FROM questions q
        JOIN dishes d ON q.dish_id = d.id
        JOIN categories c ON d.category_id = c.id
        WHERE q.id = ?
    """, (question_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    result = dict(row)
    result["options"] = json.loads(result["options"])
    return result


def get_questions(category_key: Optional[str] = None,
                  exclude_answered_by: Optional[int] = None,
                  limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Получить вопросы с фильтрами"""
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT q.*, d.name as dish_name, d.description as dish_description,
               c.key as category_key, c.name as category_name, c.emoji
        FROM questions q
        JOIN dishes d ON q.dish_id = d.id
        JOIN categories c ON d.category_id = c.id
        WHERE 1=1
    """
    params = []

    if category_key:
        query += " AND c.key = ?"
        params.append(category_key)

    if exclude_answered_by:
        query += """ AND q.id NOT IN (
            SELECT question_id FROM user_answers WHERE user_id = ?
        )"""
        params.append(exclude_answered_by)

    query += " ORDER BY RANDOM()"

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        item = dict(row)
        item["options"] = json.loads(item["options"])
        result.append(item)
    return result


def get_questions_count(category_key: Optional[str] = None) -> int:
    """Количество вопросов"""
    conn = get_connection()
    cursor = conn.cursor()
    if category_key:
        cursor.execute("""
            SELECT COUNT(*) FROM questions q
            JOIN dishes d ON q.dish_id = d.id
            JOIN categories c ON d.category_id = c.id
            WHERE c.key = ?
        """, (category_key,))
    else:
        cursor.execute("SELECT COUNT(*) FROM questions")
    count = cursor.fetchone()[0]
    conn.close()
    return count


# ==================== USERS ====================

def get_or_create_user(platform: str, external_id: str,
                       username: str = None, first_name: str = None,
                       last_name: str = None) -> Dict[str, Any]:
    """Получить или создать пользователя"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE platform = ? AND external_id = ?",
        (platform, str(external_id))
    )
    row = cursor.fetchone()

    if row:
        user = dict(row)
        # Обновляем имя если изменилось
        if first_name or username:
            cursor.execute(
                "UPDATE users SET username = COALESCE(?, username), first_name = COALESCE(?, first_name) WHERE id = ?",
                (username, first_name, user["id"])
            )
            conn.commit()
        conn.close()
        return user

    # Создаём нового пользователя
    cursor.execute(
        """INSERT INTO users (platform, external_id, username, first_name, last_name)
           VALUES (?, ?, ?, ?, ?)""",
        (platform, str(external_id), username, first_name, last_name)
    )
    user_id = cursor.lastrowid

    # Создаём пустую статистику
    cursor.execute(
        "INSERT INTO user_stats (user_id) VALUES (?)",
        (user_id,)
    )

    conn.commit()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = dict(cursor.fetchone())
    conn.close()
    return user


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Получить пользователя по внутреннему ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ==================== USER STATS ====================

def get_user_stats(user_id: int) -> Dict[str, Any]:
    """Получить статистику пользователя"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        "user_id": user_id,
        "total_questions": 0,
        "correct_answers": 0,
        "wrong_answers": 0,
        "current_streak": 0,
        "best_streak": 0,
        "total_score": 0,
        "games_played": 0
    }


def update_user_stats(user_id: int, is_correct: bool, points: int = 0):
    """Обновить статистику после ответа"""
    conn = get_connection()
    cursor = conn.cursor()

    stats = get_user_stats(user_id)

    if is_correct:
        new_streak = stats["current_streak"] + 1
        new_best = max(stats["best_streak"], new_streak)
        cursor.execute("""
            UPDATE user_stats SET
                total_questions = total_questions + 1,
                correct_answers = correct_answers + 1,
                current_streak = ?,
                best_streak = ?,
                total_score = total_score + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (new_streak, new_best, points, user_id))
    else:
        cursor.execute("""
            UPDATE user_stats SET
                total_questions = total_questions + 1,
                wrong_answers = wrong_answers + 1,
                current_streak = 0,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (user_id,))

    conn.commit()
    conn.close()


def increment_games_played(user_id: int):
    """Увеличить счётчик игр"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_stats SET
            games_played = games_played + 1,
            current_streak = 0,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
    """, (user_id,))
    conn.commit()
    conn.close()


# ==================== USER ANSWERS (PROGRESS) ====================

def save_answer(user_id: int, question_id: int, selected_index: int,
                is_correct: bool):
    """Сохранить ответ пользователя"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT OR REPLACE INTO user_answers
           (user_id, question_id, selected_index, is_correct, answered_at)
           VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
        (user_id, question_id, selected_index, is_correct)
    )
    conn.commit()
    conn.close()


def has_answered(user_id: int, question_id: int) -> bool:
    """Отвечал ли пользователь на этот вопрос"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM user_answers WHERE user_id = ? AND question_id = ?",
        (user_id, question_id)
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None


def get_answered_count(user_id: int, category_key: Optional[str] = None) -> int:
    """Количество отвеченных вопросов"""
    conn = get_connection()
    cursor = conn.cursor()
    if category_key:
        cursor.execute("""
            SELECT COUNT(*) FROM user_answers ua
            JOIN questions q ON ua.question_id = q.id
            JOIN dishes d ON q.dish_id = d.id
            JOIN categories c ON d.category_id = c.id
            WHERE ua.user_id = ? AND c.key = ?
        """, (user_id, category_key))
    else:
        cursor.execute(
            "SELECT COUNT(*) FROM user_answers WHERE user_id = ?",
            (user_id,)
        )
    count = cursor.fetchone()[0]
    conn.close()
    return count


def reset_user_progress(user_id: int, category_key: Optional[str] = None):
    """Сбросить прогресс пользователя"""
    conn = get_connection()
    cursor = conn.cursor()

    if category_key:
        cursor.execute("""
            DELETE FROM user_answers
            WHERE user_id = ? AND question_id IN (
                SELECT q.id FROM questions q
                JOIN dishes d ON q.dish_id = d.id
                JOIN categories c ON d.category_id = c.id
                WHERE c.key = ?
            )
        """, (user_id, category_key))
    else:
        cursor.execute(
            "DELETE FROM user_answers WHERE user_id = ?",
            (user_id,)
        )
        cursor.execute(
            """UPDATE user_stats SET
                total_questions = 0,
                correct_answers = 0,
                wrong_answers = 0,
                current_streak = 0,
                best_streak = 0,
                total_score = 0,
                games_played = 0,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?""",
            (user_id,)
        )

    conn.commit()
    conn.close()
    logger.info(f"🔄 Прогресс пользователя {user_id} сброшен (category={category_key})")


def get_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    """Таблица лидеров"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.username, u.first_name, us.total_score, us.correct_answers,
               us.total_questions, us.best_streak
        FROM user_stats us
        JOIN users u ON us.user_id = u.id
        WHERE us.total_score > 0
        ORDER BY us.total_score DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
