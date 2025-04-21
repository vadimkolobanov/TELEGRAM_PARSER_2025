import uuid
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer # Стандартный способ получения Bearer токена
from sqlalchemy.ext.asyncio import AsyncSession
import jwt # Для специфичных исключений jwt

# Импортируем нужные компоненты
from auth_service.core.config import settings
from auth_service.db.session import get_db
from auth_service import crud, schemas # Схемы могут понадобиться для типизации
from auth_service.utils.security import decode_access_token
from shared.models import AppUser # Модель SQLAlchemy для возврата

# --- Схема OAuth2 для получения токена из заголовка ---
# tokenUrl указывает на эндпоинт, где можно получить токен (для Swagger UI)
# Используем относительный путь к нашему эндпоинту логина
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

# --- Зависимость для получения текущего пользователя ---
async def get_current_user(
    token: str = Depends(oauth2_scheme), # Получаем токен из заголовка Authorization: Bearer <token>
    db: AsyncSession = Depends(get_db)   # Получаем сессию БД
) -> AppUser: # Возвращаем ORM-модель AppUser
    """
    Зависимость FastAPI для проверки JWT токена и получения текущего пользователя из БД.

    Извлекает токен, декодирует его, получает ID пользователя ('sub')
    и загружает пользователя из базы данных.

    Вызывает HTTPException 401, если токен невалиден, истек или пользователь не найден.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные", # Общее сообщение об ошибке
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1. Декодировать токен
    payload = decode_access_token(token)
    if payload is None:
        # decode_access_token вернул None (токен истек или невалиден)
        raise credentials_exception

    # 2. Извлечь ID пользователя (subject)
    user_id_str: Optional[str] = payload.get("sub")
    if user_id_str is None:
        # В токене нет поля 'sub'
        raise credentials_exception

    # 3. Преобразовать ID в UUID
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        # 'sub' не является валидным UUID
        raise credentials_exception

    # 4. Получить пользователя из БД
    user = await crud.get_app_user(db, user_id=user_id)
    if user is None:
        # Пользователь с таким ID не найден в БД (возможно, удален после выдачи токена)
        raise credentials_exception

    # 5. Вернуть объект пользователя
    return user

# --- (Опционально) Зависимость для получения активного пользователя ---
# Если бы у AppUser было поле is_active:
# async def get_current_active_user(
#     current_user: AppUser = Depends(get_current_user)
# ) -> AppUser:
#     if not current_user.is_active: # Пример проверки
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неактивный пользователь")
#     return current_user

# --- (Опционально) Зависимость для суперпользователя ---
# Если бы у AppUser было поле is_superuser:
# async def get_current_superuser(
#     current_user: AppUser = Depends(get_current_active_user) # Зависит от активного пользователя
# ) -> AppUser:
#     if not current_user.is_superuser: # Пример проверки
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Требуются права суперпользователя",
#         )
#     return current_user