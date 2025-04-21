import uuid
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload # Если нужно подгружать связи

# Импортируем модели SQLAlchemy и схемы Pydantic
from shared.models import TargetChat, AppUser
from data_collector_service.schemas.target import TargetChatCreate, TargetChatUpdate

async def get_target_chat_by_chat_id(db: AsyncSession, chat_id: int) -> Optional[TargetChat]:
    """
    Получает целевой чат из БД по его Telegram ID.
    """
    result = await db.execute(select(TargetChat).filter(TargetChat.chat_id == chat_id))
    return result.scalar_one_or_none()

async def create_or_update_target_chat(
    db: AsyncSession,
    *,
    chat_data: dict, # Словарь с данными, полученными из get_chat_info
    added_by_user: AppUser, # Пользователь приложения, инициировавший сбор
    initial_status: str = "collecting" # Статус при создании/начале сбора
) -> TargetChat:
    """
    Создает новую запись TargetChat или обновляет существующую на основе данных из Telegram.
    Использует chat_id для поиска существующей записи.

    Args:
        db: Асинхронная сессия SQLAlchemy.
        chat_data: Словарь с данными чата (из telegram.collector.get_chat_info).
        added_by_user: Пользователь AppUser, который добавляет/обновляет чат.
        initial_status: Статус, который будет установлен при создании или обновлении.

    Returns:
        Созданный или обновленный объект TargetChat.
    """
    chat_id = chat_data.get("id")
    if not chat_id:
        # Это не должно происходить, если chat_data валиден
        raise ValueError("Chat data must contain an 'id'")

    # Ищем существующий чат
    target_chat = await get_target_chat_by_chat_id(db, chat_id=chat_id)

    # Готовим данные для создания/обновления
    # Используем схему TargetChatUpdate для удобства, хотя вход - словарь
    chat_update_data = TargetChatUpdate(
        title=chat_data.get("title"),
        username=chat_data.get("username"),
        access_hash=chat_data.get("access_hash"),
        type=chat_data.get("type"),
        status=initial_status # Устанавливаем переданный статус
    ).model_dump(exclude_unset=True) # Pydantic V2
    # ).dict(exclude_unset=True) # Pydantic V1


    if target_chat:
        # --- Обновление существующего чата ---
        print(f"Updating existing target chat (ID: {chat_id}, Internal ID: {target_chat.internal_id})")
        # Обновляем только переданные поля
        for field, value in chat_update_data.items():
            setattr(target_chat, field, value)
        # Обновляем added_by только если он изменился? Или всегда оставляем первого?
        # target_chat.added_by = added_by_user.id # Пока не обновляем
        db.add(target_chat) # Добавляем в сессию для отслеживания изменений
    else:
        # --- Создание нового чата ---
        print(f"Creating new target chat (ID: {chat_id})")
        target_chat = TargetChat(
            chat_id=chat_id,
            added_by=added_by_user.id,
            **chat_update_data # Передаем остальные поля
        )
        db.add(target_chat) # Добавляем в сессию

    # Коммитим изменения (создание или обновление)
    await db.commit()
    # Обновляем объект из БД, чтобы получить актуальные данные (internal_id, updated_at)
    await db.refresh(target_chat)

    return target_chat

async def update_target_chat_status(db: AsyncSession, chat_id: int, status: str) -> Optional[TargetChat]:
    """
    Обновляет статус целевого чата.

    Args:
        db: Асинхронная сессия SQLAlchemy.
        chat_id: ID чата Telegram.
        status: Новый статус ('new', 'collected', 'monitoring', 'error').

    Returns:
        Обновленный объект TargetChat или None, если чат не найден.
    """
    target_chat = await get_target_chat_by_chat_id(db, chat_id=chat_id)
    if target_chat:
        target_chat.status = status
        db.add(target_chat)
        await db.commit()
        await db.refresh(target_chat)
        print(f"Updated status for target chat {chat_id} to '{status}'")
    else:
        print(f"Warning: Tried to update status for non-existent target chat {chat_id}")
    return target_chat