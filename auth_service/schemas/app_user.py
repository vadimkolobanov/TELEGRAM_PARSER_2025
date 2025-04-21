import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

# --- Базовая схема пользователя ---
# Содержит общие поля, которые могут быть возвращены API
class AppUserBase(BaseModel):
    email: EmailStr = Field(..., description="Уникальный email пользователя")
    # Дополнительные поля, если нужны (например, is_active, is_superuser)
    # is_active: bool = True

# --- Схема для создания пользователя (Регистрация) ---
# Наследуется от базовой и добавляет пароль
class AppUserCreate(AppUserBase):
    password: str = Field(..., min_length=8, description="Пароль пользователя (минимум 8 символов)")

# --- Схема для обновления пользователя (если понадобится) ---
# Все поля опциональны
class AppUserUpdate(BaseModel):
    email: Optional[EmailStr] = Field(None, description="Новый email пользователя")
    password: Optional[str] = Field(None, min_length=8, description="Новый пароль (минимум 8 символов)")
    # Другие поля...

# --- Схема для отображения пользователя (Ответ API) ---
# Не включает пароль и другие чувствительные данные
# Наследуется от базовой и добавляет ID и временные метки
class AppUserPublic(AppUserBase):
    id: uuid.UUID = Field(..., description="Уникальный идентификатор пользователя")
    created_at: datetime = Field(..., description="Дата и время создания пользователя")
    updated_at: datetime = Field(..., description="Дата и время последнего обновления")
    # session_file: Optional[str] = None # Не возвращаем путь к сессии по умолчанию

    # Конфигурация для работы с ORM моделями SQLAlchemy
    # Pydantic V2: from_attributes=True
    # Pydantic V1: orm_mode = True
    class Config:
        from_attributes = True # Позволяет создавать схему из ORM объекта

# --- Схема для пользователя в БД (для внутренних нужд, если отличается от Public) ---
# Обычно включает хэш пароля
class AppUserInDBBase(AppUserPublic):
    password_hash: str = Field(..., description="Хэш пароля пользователя")
    session_file: Optional[str] = Field(None, description="Путь к файлу сессии Telegram")

    class Config:
        from_attributes = True

# --- Схема для входа пользователя ---
class AppUserLogin(BaseModel):
    email: EmailStr = Field(..., description="Email пользователя для входа")
    password: str = Field(..., description="Пароль пользователя для входа")