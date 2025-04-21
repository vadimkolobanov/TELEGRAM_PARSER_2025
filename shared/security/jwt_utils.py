# telegram-intel/shared/security/jwt_utils.py

from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Any
import uuid

import jwt

# TODO: Решить проблему импорта settings. Пока импортируем из auth_service.
# В будущем можно сделать общий config loader или передавать settings.
try:
    from auth_service.core.config import settings
except ImportError:
    # Заглушка на случай, если auth_service недоступен при импорте из другого места
    print("Warning: Could not import settings from auth_service. Using default JWT values.")
    class MockSettings:
        JWT_SECRET_KEY = "fallback_secret"
        JWT_ALGORITHM = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES = 30
    settings = MockSettings()


def create_access_token(subject: Union[uuid.UUID, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Создает новый токен доступа JWT."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """Декодирует токен доступа JWT и возвращает его payload."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        print("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        print(f"Invalid token error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during token decoding: {e}")
        return None