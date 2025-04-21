from typing import Optional, Sequence
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Импортируем модель SQLAlchemy и схему Pydantic
from shared.models import AppUser # Модель БД
from auth_service.schemas.app_user import AppUserCreate, AppUserUpdate # Схемы Pydantic
from auth_service.utils.security import get_password_hash # Утилита хэширования

async def get_app_user(db: AsyncSession, user_id: uuid.UUID) -> Optional[AppUser]:
    """
    Получает пользователя приложения по его UUID.

    Args:
        db: Асинхронная сессия SQLAlchemy.
        user_id: UUID пользователя.

    Returns:
        Объект AppUser или None, если пользователь не найден.
    """
    result = await db.execute(select(AppUser).filter(AppUser.id == user_id))
    return result.scalar_one_or_none()

async def get_app_user_by_email(db: AsyncSession, email: str) -> Optional[AppUser]:
    """
    Получает пользователя приложения по его email.

    Args:
        db: Асинхронная сессия SQLAlchemy.
        email: Email пользователя.

    Returns:
        Объект AppUser или None, если пользователь не найден.
    """
    result = await db.execute(select(AppUser).filter(AppUser.email == email))
    return result.scalar_one_or_none()

async def create_app_user(db: AsyncSession, *, user_in: AppUserCreate) -> AppUser:
    """
    Создает нового пользователя приложения в базе данных.

    Args:
        db: Асинхронная сессия SQLAlchemy.
        user_in: Данные нового пользователя (из схемы AppUserCreate).

    Returns:
        Созданный объект AppUser.
    """
    # Хэшируем пароль перед сохранением
    hashed_password = get_password_hash(user_in.password)

    # Создаем объект модели SQLAlchemy
    # Передаем поля из user_in, кроме пароля в открытом виде
    db_user = AppUser(
        email=user_in.email,
        password_hash=hashed_password
        # Другие поля можно добавить здесь, если они есть в AppUserCreate и AppUser
    )

    # Добавляем объект в сессию
    db.add(db_user)
    # Коммитим транзакцию, чтобы сохранить пользователя в БД
    await db.commit()
    # Обновляем объект из БД (чтобы получить сгенерированный id, created_at и т.д.)
    await db.refresh(db_user)

    return db_user

async def update_app_user(db: AsyncSession, *, db_user: AppUser, user_in: AppUserUpdate) -> AppUser:
    """
    Обновляет данные существующего пользователя приложения. (Пока не используется)

    Args:
        db: Асинхронная сессия SQLAlchemy.
        db_user: Существующий объект AppUser из БД.
        user_in: Данные для обновления (из схемы AppUserUpdate).

    Returns:
        Обновленный объект AppUser.
    """
    update_data = user_in.model_dump(exclude_unset=True) # Pydantic V2
    # update_data = user_in.dict(exclude_unset=True) # Pydantic V1

    # Если пароль передан для обновления, хэшируем его
    if "password" in update_data and update_data["password"]:
        hashed_password = get_password_hash(update_data["password"])
        update_data["password_hash"] = hashed_password
        del update_data["password"] # Удаляем пароль в открытом виде

    # Обновляем поля объекта db_user
    for field, value in update_data.items():
        setattr(db_user, field, value)

    # Добавляем в сессию (хотя объект уже в сессии, если был получен через нее)
    db.add(db_user)
    # Коммитим изменения
    await db.commit()
    # Обновляем объект из БД
    await db.refresh(db_user)
    return db_user

# Можно добавить другие CRUD функции:
# - get_multi_app_users
# - delete_app_user