# telegram-intel/shared/dependencies/auth.py

import uuid
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

# Импортируем утилиты и модели/схемы
from shared.security.jwt_utils import decode_access_token
from shared.models import AppUser # Модель SQLAlchemy из shared
# TODO: Решить проблему импорта settings и crud. Пока импортируем из auth_service.
try:
    from auth_service.core.config import settings
    from auth_service import crud # Зависит от CRUD auth_service для поиска AppUser
    # Зависимость get_db должна быть предоставлена вызывающим сервисом
    # from auth_service.db.session import get_db # НЕЛЬЗЯ импортировать get_db отсюда
except ImportError:
    print("Warning: Could not import settings/crud from auth_service.")
    # Заглушки
    class MockSettings:
        API_V1_STR = "/api/v1"
    settings = MockSettings()
    crud = None # CRUD будет недоступен

# Определяем схему OAuth2 здесь, чтобы она была доступна всем сервисам
# tokenUrl указывает на эндпоинт логина в auth_service
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login") # Путь к логину auth_service

async def get_current_user(
    token: str = Depends(oauth2_scheme), # Используем общую схему
    # db: AsyncSession = Depends(get_db) # get_db должен быть передан из сервиса!
    # Вместо этого получим его как аргумент от вызывающего кода
    db: AsyncSession = Depends(), # Placeholder - будет заменено при вызове Depends(get_current_user)
) -> Optional[AppUser]: # Возвращаем Optional, чтобы обработать случай с недоступным CRUD
    """
    Общая зависимость FastAPI для проверки JWT и получения AppUser из БД.

    Args:
        token: Токен из заголовка (через oauth2_scheme).
        db: Асинхронная сессия БД, предоставленная вызывающим сервисом.

    Returns:
        Объект AppUser или вызывает HTTPException.
    """
    # Проверяем, что CRUD доступен (был импортирован)
    if crud is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User CRUD operations are not available.",
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id_str: Optional[str] = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    # Используем переданную сессию db для запроса пользователя через CRUD auth_service
    user = await crud.get_app_user(db, user_id=user_id)
    if user is None:
        raise credentials_exception

    return user

# --- Важное примечание по использованию ---
# В сервисе, который хочет использовать эту зависимость (например, data_collector_service),
# нужно будет сделать следующее:
#
# 1. Импортировать get_current_user из shared:
#    from shared.dependencies.auth import get_current_user
#
# 2. Импортировать свою локальную зависимость get_db:
#    from .db.session import get_db # Локальная get_db этого сервиса
#
# 3. Использовать в эндпоинте так:
#    async def protected_endpoint(
#        db: AsyncSession = Depends(get_db), # Получаем локальную сессию
#        # Передаем локальную сессию в get_current_user через Depends
#        current_user: AppUser = Depends(lambda: get_current_user(db=db)) # Используем lambda
#        # ИЛИ более явный способ:
#        # current_user: AppUser = Depends(get_current_user_wrapper(Depends(get_db)))
#    ):
#        # ...
#
# Это связано с тем, как FastAPI обрабатывает вложенные зависимости.
# Альтернативно, можно переделать get_current_user, чтобы она не зависела от db напрямую,
# а возвращала, например, user_id, а сервис сам бы загружал пользователя.