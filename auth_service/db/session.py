from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session

# Импортируем настроенный экземпляр Settings
from auth_service.core.config import settings

# --- Создание асинхронного движка SQLAlchemy ---
# Движок создается один раз при инициализации модуля
async_engine = create_async_engine(
    settings.DATABASE_URL, # Берем URL из настроек
    pool_pre_ping=True,    # Проверять соединение из пула перед использованием
    echo=False,            # Установите True для логирования всех SQL запросов (полезно для отладки)
    # echo_pool='debug',   # Установите 'debug' для логирования событий пула соединений
    pool_size=10,          # Начальный размер пула соединений
    max_overflow=20        # Максимальное количество дополнительных соединений сверх pool_size
)

# --- Создание фабрики асинхронных сессий ---
# Фабрика будет создавать новые сессии по запросу
# expire_on_commit=False - объекты остаются доступными после коммита сессии
AsyncSessionFactory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# --- Функция-зависимость FastAPI для получения сессии БД ---
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async SQLAlchemy session.

    Manages the session lifecycle: creates a session, yields it to the endpoint,
    and ensures it's closed afterwards. Handles rollbacks on exceptions.
    """
    async with AsyncSessionFactory() as session:
        try:
            # print("DB Session Created") # Отладка
            yield session
            # Коммит должен делаться явно в CRUD функциях, а не здесь
            # await session.commit() # Не нужно здесь
        except Exception as e:
            print(f"DB Session Exception: {e}") # Логируем ошибку
            await session.rollback() # Откатываем транзакцию в случае ошибки
            raise # Пробрасываем исключение дальше
        finally:
            # Сессия закрывается автоматически благодаря 'async with AsyncSessionFactory() as session:'
            # print("DB Session Closed") # Отладка
            pass

# --- Функции для управления жизненным циклом в FastAPI (Lifespan) ---
async def startup_db_client():
    """
    Initialize database connection pool during application startup.
    Optionally performs a simple query to check connectivity.
    """
    print("Attempting to connect to the database...")
    try:
        # Пробуем установить соединение для проверки
        async with async_engine.connect() as connection:
            # Можно выполнить простой запрос для уверенности
            # await connection.execute(text("SELECT 1"))
            print("Database connection pool established successfully.")
    except Exception as e:
        print(f"FATAL: Failed to connect to the database during startup: {e}")
        # Здесь можно решить, нужно ли останавливать приложение, если БД недоступна
        # raise SystemExit(f"Could not connect to database: {e}")

async def shutdown_db_client():
    """
    Dispose database connection pool gracefully during application shutdown.
    """
    print("Disposing database connection pool...")
    await async_engine.dispose() # Закрывает все соединения в пуле
    print("Database connection pool disposed.")