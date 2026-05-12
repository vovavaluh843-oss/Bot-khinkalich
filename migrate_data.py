"""
Скрипт миграции данных из menu_data.py в SQLite БД.
Запускать один раз при первом развёртывании.
"""

import sys
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent))

from core.database import init_db, add_category, add_dish, add_question
from menu_data import MENU_CATEGORIES, DISHES


def migrate():
    print("🚀 Начинаю миграцию данных...")
    init_db()

    # 1. Категории
    print("📁 Добавляю категории...")
    category_map = {}
    for key, name in MENU_CATEGORIES.items():
        emoji = name.split()[0] if name else ""
        clean_name = " ".join(name.split()[1:]) if emoji else name
        cat_id = add_category(key, clean_name, emoji)
        category_map[key] = cat_id
        print(f"  ✅ {key} → {clean_name}")

    # 2. Блюда и вопросы
    print("🍽️ Добавляю блюда и вопросы...")
    total_questions = 0
    for dish in DISHES:
        add_dish(
            dish_id=dish["id"],
            name=dish["name"],
            category_key=dish["category"],
            description=dish.get("description", ""),
            ingredients=dish.get("ingredients", [])
        )

        for q in dish["questions"]:
            add_question(
                dish_id=dish["id"],
                question=q["question"],
                options=q["options"],
                correct_index=q["correct"]
            )
            total_questions += 1

        print(f"  ✅ {dish['name']} — {len(dish['questions'])} вопросов")

    print(f"\n🎉 Миграция завершена!")
    print(f"   Категорий: {len(category_map)}")
    print(f"   Блюд: {len(DISHES)}")
    print(f"   Вопросов: {total_questions}")


if __name__ == "__main__":
    migrate()
