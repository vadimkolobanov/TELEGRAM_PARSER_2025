import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

# Импортируем настройки и функции управления БД
from auth_service.core.config import settings
from auth_service.db.session import startup_db_client, shutdown_db_client
# Импортируем роутеры API (пока закомментировано, добавим позже)
from auth_service.api.v1.api import api_router as api_v1_router

# --- Lifespan Management ---
# Контекстный менеджер для управления ресурсами при старте и остановке приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    Connects to the database on startup and disconnects on shutdown.
    """
    print(f"--- Starting up {settings.PROJECT_NAME} ---")
    await startup_db_client() # Подключаемся к БД
    yield # Приложение работает здесь
    print(f"--- Shutting down {settings.PROJECT_NAME} ---")
    await shutdown_db_client() # Отключаемся от БД

# --- Создание экземпляра FastAPI ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Handles user registration, authentication, and session management for Telegram Intel.",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json", # Путь к OpenAPI схеме
    docs_url="/docs", # Путь к Swagger UI
    redoc_url="/redoc", # Путь к ReDoc
    lifespan=lifespan # Подключаем менеджер жизненного цикла
)

# --- Подключение Роутеров API ---
# Раскомментируем, когда создадим роутер в api/v1/api.py
app.include_router(api_v1_router, prefix=settings.API_V1_STR)

# --- Корневой Эндпоинт ---
@app.get("/", tags=["Status"])
async def read_root():
    """
    Root endpoint providing basic service status.
    """
    return {"status": "OK", "message": f"Welcome to {settings.PROJECT_NAME}"}

# --- Запуск с Uvicorn (для локальной разработки) ---
# Блок выполняется, только если файл запущен напрямую (python auth_service/main.py)
if __name__ == "__main__":
    print("Attempting to run Auth Service directly using Uvicorn...")

    # Загрузка .env файла (на всякий случай, если не загрузился в config.py)
    # Путь относительно main.py -> .. -> .env
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        # print(f"Loaded .env from: {dotenv_path}")
    else:
        print(f"Warning: .env file not found at {dotenv_path}")

    # Получаем хост и порт из настроек (которые уже загрузили переменные)
    run_host = settings.AUTH_SERVICE_HOST
    run_port = settings.AUTH_SERVICE_PORT

    print(f"--> Starting Uvicorn server on http://{run_host}:{run_port}")
    print(f"--> API docs available at http://{run_host}:{run_port}/docs")

    # Запускаем Uvicorn
    uvicorn.run(
        "auth_service.main:app", # Путь к объекту FastAPI app
        host=run_host,
        port=run_port,
        reload=True, # Автоматическая перезагрузка при изменении кода (удобно для разработки)
        log_level="info" # Уровень логирования uvicorn
    )