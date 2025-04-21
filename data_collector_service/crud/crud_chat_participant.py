from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

# Импортируем модели SQLAlchemy и схемы Pydantic
from shared.models import ChatParticipant, User, TargetChat
from data_collector_service.schemas.collection import CollectedUserSchema # Данные из Telethon содержат инфо об участнике

async def bulk_upsert_participants(
    db: AsyncSession,
    *,
    chat_id: int, # ID чата Telegram
    participants_data: List[CollectedUserSchema] # Список данных, включающих инфо об участнике
) -> int:
    """
    Выполняет массовый Upsert информации об участниках чата.
    Связывает пользователей (User) с чатом (TargetChat).

    Args:
        db: Асинхронная сессия SQLAlchemy.
        chat_id: ID чата Telegram, к которому относятся участники.
        participants_data: Список данных пользователей/участников.

    Returns:
        Количество успешно добавленных/обновленных записей об участии.
    """
    if not participants_data:
        return 0

    participants_values = []
    for p_data in participants_data:
        # Собираем данные для таблицы chat_participants
        values = {
            "chat_id": chat_id,
            "user_id": p_data.id, # ID пользователя TG
            "participant_type": p_data.participant_type,
            "inviter_user_id": p_data.inviter_user_id,
            "joined_date": p_data.joined_date,
            # added_at - устанавливается по умолчанию в модели
        }
        participants_values.append(values)

    # Создаем оператор insert
    stmt = insert(ChatParticipant).values(participants_values)

    # Определяем поля для обновления при конфликте
    # Конфликт определяется уникальным индексом ('chat_id', 'user_id')
    update_dict = {
        # Обновляем тип участника, пригласившего и дату входа, если они изменились
        "participant_type": getattr(stmt.excluded, 'participant_type'),
        "inviter_user_id": getattr(stmt.excluded, 'inviter_user_id'),
        "joined_date": getattr(stmt.excluded, 'joined_date'),
        # added_at не обновляем
    }

    # Создаем ON CONFLICT DO UPDATE
    # Указываем индекс, по которому проверяется конфликт
    upsert_stmt = stmt.on_conflict_do_update(
        constraint='uq_chat_participant', # Имя уникального ограничения
        set_=update_dict
    ) # Не используем returning(), т.к. нам нужно только количество

    # Выполняем запрос
    result = await db.execute(upsert_stmt)
    await db.commit() # Коммитим транзакцию

    count = result.rowcount # Количество обработанных строк
    print(f"Bulk upserted {count} chat participants for chat ID {chat_id}.")

    return count