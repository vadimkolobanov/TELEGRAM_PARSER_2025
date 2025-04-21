import uuid
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert # Для ON CONFLICT DO UPDATE (Upsert)

# Импортируем модели SQLAlchemy и схемы Pydantic
from shared.models import User, AppUser
from data_collector_service.schemas.collection import CollectedUserSchema # Схема с данными от Telethon

async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Получает пользователя Telegram по его ID."""
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalar_one_or_none()

async def upsert_user(db: AsyncSession, *, user_data: CollectedUserSchema, collected_by: AppUser) -> User:
    """
    Создает нового пользователя Telegram или обновляет существующего.
    Использует ID пользователя для поиска.

    Args:
        db: Асинхронная сессия SQLAlchemy.
        user_data: Данные пользователя из схемы CollectedUserSchema.
        collected_by: Пользователь AppUser, в рамках сбора которого был найден этот пользователь TG.

    Returns:
        Созданный или обновленный объект User.
    """
    # Преобразуем Pydantic схему в словарь, совместимый с моделью User
    # Исключаем поля, специфичные для участника чата (participant_type и т.д.)
    # и поля, которых нет в модели User или которые управляются иначе (is_contact)
    user_values = user_data.model_dump(
        exclude={"participant_type", "inviter_user_id", "joined_date", "is_contact", "status", "last_seen_at"}
    ) # Pydantic V2
    # user_values = user_data.dict(
    #     exclude={"participant_type", "inviter_user_id", "joined_date", "is_contact", "status", "last_seen_at"}
    # ) # Pydantic V1

    # Добавляем ID пользователя приложения, который его "нашел"
    user_values["added_by_user_id"] = collected_by.id

    # Используем insert().on_conflict_do_update() для Upsert
    # Определяем, какие поля обновлять при конфликте (когда user.id уже существует)
    # Обновляем все поля, кроме ID и added_by_user_id (кто первый нашел, тот и добавил)
    stmt = insert(User).values(**user_values)
    # Определяем поля для обновления в случае конфликта по первичному ключу (id)
    update_dict = {
        col.name: getattr(stmt.excluded, col.name)
        for col in stmt.excluded if col.name not in ["id", "added_by_user_id", "created_at"]
        # Обновляем updated_at при конфликте
        # "updated_at": func.now() # func не доступен в stmt.excluded, нужно будет обновить отдельно или триггером
    }

    # Создаем оператор ON CONFLICT DO UPDATE
    # index_elements=['id'] указывает на первичный ключ
    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=['id'],
        set_=update_dict
    ).returning(User) # Возвращаем вставленную/обновленную строку как объект User

    # Выполняем запрос
    result = await db.execute(upsert_stmt)
    await db.commit() # Коммитим транзакцию upsert
    upserted_user = result.scalar_one() # Получаем результат

    # print(f"Upserted user: ID={upserted_user.id}, Username={upserted_user.username}")
    return upserted_user

async def bulk_upsert_users(db: AsyncSession, *, users_data: List[CollectedUserSchema], collected_by: AppUser) -> List[User]:
    """
    Выполняет массовый Upsert пользователей Telegram.

    Args:
        db: Асинхронная сессия SQLAlchemy.
        users_data: Список данных пользователей (CollectedUserSchema).
        collected_by: Пользователь AppUser, который их нашел.

    Returns:
        Список созданных/обновленных объектов User.
    """
    if not users_data:
        return []

    users_values = []
    for user_data in users_data:
        user_values = user_data.model_dump(
            exclude={"participant_type", "inviter_user_id", "joined_date", "is_contact", "status", "last_seen_at"}
        )
        user_values["added_by_user_id"] = collected_by.id
        users_values.append(user_values)

    # Создаем оператор insert
    stmt = insert(User).values(users_values)

    # Определяем поля для обновления при конфликте
    update_dict = {
        col.name: getattr(stmt.excluded, col.name)
        for col in stmt.excluded if col.name not in ["id", "added_by_user_id", "created_at"]
    }

    # Создаем ON CONFLICT DO UPDATE
    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=['id'],
        set_=update_dict
    ).returning(User)

    # Выполняем
    result = await db.execute(upsert_stmt)
    await db.commit()
    upserted_users = result.scalars().all()
    print(f"Bulk upserted {len(upserted_users)} users.")

    return upserted_users