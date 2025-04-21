from fastapi import APIRouter

# Импортируем роутер для сбора данных
from data_collector_service.api.v1.endpoints import collector

# Создаем основной роутер для v1
api_router = APIRouter()

# Подключаем роутер сбора данных
api_router.include_router(collector.router, prefix="/collector", tags=["Data Collection"])

# Сюда можно будет добавлять другие роутеры для v1 этого сервиса