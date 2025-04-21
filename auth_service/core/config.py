import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Определяем путь к корневой директории проекта
# auth_service/core -> auth_service -> telegram-intel
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Определяем путь к .env файлу в корне проекта
DOTENV_PATH = BASE_DIR / '.env'
# print(f"Attempting to load .env file from: {DOTENV_PATH}") # Отладка

# Загружаем переменные из .env файла
# override=True означает, что переменные из .env перезапишут существующие системные переменные
load_dotenv(dotenv_path=DOTENV_PATH, override=True)
# print(f"POSTGRES_USER from env: {os.getenv('POSTGRES_USER')}") # Отладка

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables using Pydantic.
    """
    # --- Database Settings ---
    # Значения по умолчанию добавлены на случай отсутствия переменных в .env
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "default_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "default_password")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "default_db")

    # --- Construct Async Database URL ---
    # Используем asyncpg для асинхронного взаимодействия с PostgreSQL
    # Собираем URL динамически после загрузки переменных
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # --- JWT Settings ---
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "a_very_default_secret_key_that_should_be_changed")
    JWT_ALGORITHM: str = "HS256"
    # Время жизни токена доступа в минутах
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 дней для удобства разработки, потом можно уменьшить

    # --- Service Settings ---
    AUTH_SERVICE_HOST: str = os.getenv("AUTH_SERVICE_HOST", "127.0.0.1")
    AUTH_SERVICE_PORT: int = int(os.getenv("AUTH_SERVICE_PORT", "8001"))

    # --- API Info (for Swagger UI) ---
    PROJECT_NAME: str = "Telegram Intel - Auth Service"
    API_V1_STR: str = "/api/v1" # Префикс для API роутов версии 1

    class Config:
        # Указываем Pydantic, что нужно искать .env файл (хотя мы уже загрузили его с load_dotenv)
        # env_file = str(DOTENV_PATH) # В Pydantic V2 можно не указывать, если load_dotenv уже вызван
        env_file_encoding = 'utf-8'
        extra = 'ignore' # Игнорировать лишние переменные в .env

# Создаем один экземпляр настроек, который будет импортироваться другими модулями
# Это стандартный паттерн для работы с настройками в FastAPI
settings = Settings()

# --- Отладочный вывод при импорте модуля ---
# Выводим часть настроек для проверки при запуске приложения
# print(f"Auth Service Config Loaded:")
# print(f"  PROJECT_NAME: {settings.PROJECT_NAME}")
# print(f"  DB URL (asyncpg): postgresql+asyncpg://{settings.POSTGRES_USER}:******@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}")
# print(f"  JWT Secret Key Loaded: {'Yes' if settings.JWT_SECRET_KEY else 'No'}")
# print(f"  Service Host: {settings.AUTH_SERVICE_HOST}")
# print(f"  Service Port: {settings.AUTH_SERVICE_PORT}")