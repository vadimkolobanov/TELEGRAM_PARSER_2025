import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Определяем путь к корневой директории проекта
# data_collector_service/core -> data_collector_service -> telegram-intel
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Определяем путь к .env файлу в корне проекта
DOTENV_PATH = BASE_DIR / '.env'
# print(f"Attempting to load .env file from: {DOTENV_PATH}") # Отладка

# Загружаем переменные из .env файла
load_dotenv(dotenv_path=DOTENV_PATH, override=True)
# print(f"API_ID from env: {os.getenv('API_ID')}") # Отладка

class Settings(BaseSettings):
    """
    Application settings for Data Collector Service.
    """
    # --- Database Settings ---
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "default_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "default_password")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "default_db")

    # --- Construct Async Database URL ---
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # --- Telegram API Settings ---
    # Загружаем API_ID и API_HASH из .env
    # Преобразуем API_ID в int, так как Telethon ожидает число
    API_ID: int = int(os.getenv("API_ID", "0")) # 0 как невалидное значение по умолчанию
    API_HASH: str = os.getenv("API_HASH", "default_hash")

    # --- Service Settings ---
    # Определяем порт для этого сервиса (например, 8002)
    DATA_COLLECTOR_HOST: str = os.getenv("DATA_COLLECTOR_HOST", "127.0.0.1")
    DATA_COLLECTOR_PORT: int = int(os.getenv("DATA_COLLECTOR_PORT", "8002"))

    # --- API Info (for Swagger UI) ---
    PROJECT_NAME: str = "Telegram Intel - Data Collector Service"
    API_V1_STR: str = "/api/v1"

    # --- Paths ---
    # Путь для хранения файлов сессий Telegram (.session)
    # Можно сделать его настраиваемым через .env
    # BASE_DIR уже определен выше как корень проекта
    SESSION_FILES_DIR: Path = BASE_DIR / "sessions"

    class Config:
        env_file_encoding = 'utf-8'
        extra = 'ignore'

# Создаем экземпляр настроек
settings = Settings()

# --- Проверка загруженных настроек Telegram ---
if settings.API_ID == 0 or settings.API_HASH == "default_hash":
    print(f"Warning: API_ID or API_HASH not found or invalid in .env file ({DOTENV_PATH}).")
    # Можно добавить выход из приложения, если эти данные критичны для старта
    # import sys
    # sys.exit("Error: Telegram API credentials missing.")

# --- Создание директории для сессий, если ее нет ---
# Важно: Убедитесь, что у приложения есть права на запись в эту директорию
settings.SESSION_FILES_DIR.mkdir(parents=True, exist_ok=True)
print(f"Session files directory: {settings.SESSION_FILES_DIR}")

# --- Отладочный вывод ---
# print(f"Data Collector Service Config Loaded:")
# print(f"  PROJECT_NAME: {settings.PROJECT_NAME}")
# print(f"  DB URL: postgresql+asyncpg://{settings.POSTGRES_USER}:******@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}")
# print(f"  API_ID: {settings.API_ID}")
# print(f"  API_HASH: {'*' * len(settings.API_HASH) if settings.API_HASH else 'Not Set'}")
# print(f"  Service Host: {settings.DATA_COLLECTOR_HOST}")
# print(f"  Service Port: {settings.DATA_COLLECTOR_PORT}")