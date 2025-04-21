# telegram-intel/data_collector_service/schemas/target.py

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

# --- Схема для отображения целевого чата (из БД) ---
# Аналогично модели SQLAlchemy TargetChat, но без ORM-специфики
class TargetChatBase(BaseModel):
    chat_id: int = Field(..., description="ID чата/канала из Telegram")
    title: Optional[str] = Field(None, description="Название чата/канала")
    username: Optional[str] = Field(None, description="Username чата/канала (если есть)")
    type: Optional[str] = Field(None, description="Тип (group, channel, supergroup)")
    status: str = Field("new", description="Статус сбора (new, collected, monitoring, error)")

class TargetChatPublic(TargetChatBase):
    internal_id: int = Field(..., description="Внутренний ID записи в БД")
    added_by: uuid.UUID = Field(..., description="UUID пользователя, добавившего чат")
    created_at: datetime = Field(..., description="Время добавления в БД")
    updated_at: datetime = Field(..., description="Время последнего обновления в БД")
    # Поля access_hash не включаем в публичную схему

    class Config:
        from_attributes = True # Для создания из ORM-объекта

# --- Схема для добавления/обновления целевого чата в БД (может использоваться CRUD) ---
# Включает поля, которые могут быть добавлены/изменены
class TargetChatCreate(BaseModel):
    chat_id: int = Field(..., description="ID чата/канала Telegram")
    title: Optional[str] = None
    username: Optional[str] = None
    access_hash: Optional[int] = None
    type: Optional[str] = None
    # added_by - будет добавлен в CRUD из текущего пользователя
    # status - обычно устанавливается в CRUD

class TargetChatUpdate(BaseModel):
    title: Optional[str] = None
    username: Optional[str] = None
    access_hash: Optional[int] = None
    type: Optional[str] = None
    status: Optional[str] = None