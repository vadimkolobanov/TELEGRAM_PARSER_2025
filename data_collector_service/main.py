import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

# Импортируем настройки и функции управления БД ИЗ ЭТОГО СЕРВИСА
from data_collector_service.core.config import settings
from data_collector_service.db.session import startup_db_client, shutdown_db_client
# Импортируем роутеры API (пока закомментировано, добавим позже)
# from data_collector_service.api.v1.api import api_router as api_v1_router

# --- Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events for Data Collector Service.
    Connects to the database on startup and disconnects on shutdown.
    """
    print(f"--- Starting up {settings.PROJECT_NAME} ---")
    await startup_db_client() # Подключаемся к БД этого сервиса
    yield # Приложение работает здесь
    print(f"--- Shutting down {settings.PROJECT_NAME} ---")
    await shutdown_db_client() # Отключаемся от БД этого сервиса

# --- Создание экземпляра FastAPI ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Collects public data (chats, participants, messages) from Telegram.",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# --- Подключение Роутеров API ---
# Раскомментируем, когда создадим роутер в data_collector_service/api/v1/api.py
# app.include_router(api_v1_router, prefix=settings.API_V1_STR)

# --- Корневой Эндпоинт ---
@app.get("/", tags=["Status"])
async def read_root():
    """
    Root endpoint providing basic service status.
    """
    return {"status": "OK", "message": f"Welcome to {settings.PROJECT_NAME}"}

# --- Запуск с Uvicorn (для локальной разработки) ---
if __name__ == "__main__":
    print("Attempting to run Data Collector Service directly using Uvicorn...")

    # Загрузка .env файла (на случай, если не загрузился в config.py)
    # Путь относительно main.py -> .. -> .env
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
    else:
        print(f"Warning: .env file not found at {dotenv_path}")

    # Получаем хост и порт из настроек этого сервиса
    run_host = settings.DATA_COLLECTOR_HOST
    run_port = settings.DATA_COLLECTOR_PORT

    print(f"--> Starting Uvicorn server on http://{run_host}:{run_port}")
    print(f"--> API docs available at http://{run_host}:{run_port}/docs")

    # Запускаем Uvicorn, указывая путь к app в этом файле
    uvicorn.run(
        "data_collector_service.main:app", # Путь к объекту FastAPI app
        host=run_host,
        port=run_port,
        reload=True, # Включаем автоперезагрузку для разработки
        log_level="info"
    )