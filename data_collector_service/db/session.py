from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session # Хотя не используется напрямую, импорт может быть полезен для type hints

# Импортируем настроенный экземпляр Settings ИЗ ЭТОГО СЕРВИСА
from data_collector_service.core.config import settings

# --- Создание асинхронного движка SQLAlchemy ---
# Движок создается один раз при инициализации модуля
# Используем DATABASE_URL из настроек data_collector_service
async_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False, # Установите True для отладки SQL в этом сервисе
    # echo_pool='debug',
    pool_size=10,
    max_overflow=20
)

# --- Создание фабрики асинхронных сессий ---
AsyncSessionFactory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# --- Функция-зависимость FastAPI для получения сессии БД ---
# Эта функция будет использоваться ТОЛЬКО ВНУТРИ data_collector_service
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async SQLAlchemy session specific
    to the data_collector_service.
    """
    async with AsyncSessionFactory() as session:
        try:
            # print("Data Collector DB Session Created") # Отладка
            yield session
        except Exception as e:
            print(f"Data Collector DB Session Exception: {e}")
            await session.rollback()
            raise
        finally:
            # print("Data Collector DB Session Closed") # Отладка
            pass

# --- Функции для управления жизненным циклом в FastAPI (Lifespan) ---
# Эти функции будут вызываться в main.py этого сервиса
async def startup_db_client():
    """Initialize database connection pool for Data Collector service."""
    print("Data Collector: Attempting to connect to the database...")
    try:
        async with async_engine.connect() as connection:
            print("Data Collector: Database connection pool established successfully.")
    except Exception as e:
        print(f"Data Collector: FATAL: Failed to connect to the database during startup: {e}")
        # Можно добавить sys.exit при необходимости

async def shutdown_db_client():
    """Dispose database connection pool for Data Collector service."""
    print("Data Collector: Disposing database connection pool...")
    await async_engine.dispose()
    print("Data Collector: Database connection pool disposed.")