from typing import Optional
import uuid
from pydantic import BaseModel, Field

# --- Схема для данных внутри JWT токена ---
class TokenPayload(BaseModel):
    sub: uuid.UUID = Field(..., description="Subject (user ID)") # Идентификатор пользователя
    # Можно добавить другие данные в токен, например, email или роли
    # email: Optional[str] = None
    # exp: Optional[int] = None # Время истечения (добавляется при создании токена)

# --- Схема для ответа API при успешном входе ---
class TokenResponse(BaseModel):
    access_token: str = Field(..., description="Токен доступа JWT")
    token_type: str = Field("bearer", description="Тип токена (обычно Bearer)")
    user: Optional[dict] = Field(None, description="Информация о пользователе (опционально)") # Можно добавить AppUserPublic