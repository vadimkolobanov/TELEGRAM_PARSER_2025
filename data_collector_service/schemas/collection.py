from datetime import datetime
from typing import Union, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

# --- Схема для запроса на сбор данных ---
class CollectChatRequest(BaseModel):
    # Пользователь может указать ID чата, username или ссылку t.me/...
    chat_target: Union[int, str] = Field(..., description="ID, username (@username) или ссылка (t.me/...) целевого чата/канала")
    # Опциональные параметры (например, лимит участников)
    # participant_limit: Optional[int] = Field(0, description="Лимит участников для сбора (0 = без лимита)")

    # Валидатор для chat_target (опционально, но полезно)
    @field_validator('chat_target')
    def target_must_be_valid(cls, v):
        if isinstance(v, str) and not v.strip():
            raise ValueError("chat_target не может быть пустой строкой")
        # Можно добавить более сложную валидацию ссылок/юзернеймов
        return v

# --- Схема для ответа после запуска сбора ---
# Пока просто сообщаем об успехе/ошибке
# В будущем может содержать ID задачи Celery
class CollectChatResponse(BaseModel):
    message: str = Field(..., description="Сообщение о результате запуска сбора")
    chat_id: Optional[int] = Field(None, description="ID чата, для которого запущен сбор (если удалось определить)")
    status: Optional[str] = Field(None, description="Текущий статус целевого чата в БД (если он там есть)")
    task_id: Optional[str] = Field(None, description="ID задачи Celery (если используется)") # Для асинхронного варианта

# --- Схема для данных пользователя (внутренняя, для валидации перед CRUD) ---
# Основана на данных, получаемых из get_chat_participants
# Повторяет поля модели User + поля участника
class CollectedUserSchema(BaseModel):
    id: int
    access_hash: Optional[int] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    is_bot: bool = False
    is_deleted: bool = False
    is_verified: bool = False
    is_restricted: bool = False
    is_scam: bool = False
    is_fake: bool = False
    lang_code: Optional[str] = None
    # Поля, которых нет в Telethon user, но есть в нашей модели User
    is_contact: bool = False # По умолчанию False
    status: Optional[str] = None # Telethon не дает статус в списке участников
    last_seen_at: Optional[datetime] = None # Telethon не дает в списке участников
    # added_by_user: Optional[uuid.UUID] = None # Будет установлено в CRUD

    # Дополнительные поля из participant_details
    participant_type: Optional[str] = 'member'
    inviter_user_id: Optional[int] = None
    joined_date: Optional[datetime] = None

    class Config:
        from_attributes = True # Позволяет создавать из словарей