from fastapi import APIRouter

# Импортируем роутер для аутентификации
from auth_service.api.v1.endpoints import auth

# Создаем основной роутер для v1
api_router = APIRouter()

# Подключаем роутер аутентификации с префиксом /auth
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Сюда можно будет добавлять другие роутеры для v1
# Например, роутер для управления пользователями (если понадобится)
# from auth_service.api.v1.endpoints import users
# api_router.include_router(users.router, prefix="/users", tags=["Users"])