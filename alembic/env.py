# telegram-intel/alembic/env.py

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
# Импорт ForeignKeyConstraint, если используется в моделях (был добавлен ранее)
from sqlalchemy import ForeignKeyConstraint

from alembic import context

# --- Добавлено: Загрузка переменных окружения из .env ---
from dotenv import load_dotenv
# Указываем путь к .env относительно env.py (один уровень вверх)
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(dotenv_path=dotenv_path)

# --- Добавлено: Добавляем корень проекта в sys.path ---
# Чтобы можно было импортировать shared.models
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------------------------

# --- Добавлено: Импорт Base и metadata из наших моделей ---
try:
    from shared.models import Base # Импортируем Base
    target_metadata = Base.metadata # Получаем metadata ИЗ Base
except ImportError as e:
    print(f"Ошибка импорта моделей из 'shared': {e}")
    print(f"Текущий sys.path: {sys.path}")
    # Можно добавить выход, если модели критичны для загрузки env.py
    # sys.exit(1)
    target_metadata = None # Или установите в None, если Alembic может работать без них на этом этапе
# ---------------------------------------------------------

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Добавлено: Формирование URL базы данных из переменных окружения ---
# Считываем переменные, загруженные из .env
db_user = os.getenv('POSTGRES_USER')
db_password = os.getenv('POSTGRES_PASSWORD')
db_host = os.getenv('POSTGRES_HOST')
db_port = os.getenv('POSTGRES_PORT')
db_name = os.getenv('POSTGRES_DB')

# Проверяем, что все переменные загружены
if not all([db_user, db_password, db_host, db_port, db_name]):
    print("Ошибка: Не все переменные окружения для базы данных установлены в .env")
    # Можно прервать выполнение, если данные некорректны
    # sys.exit(1) # Раскомментировать при необходимости
    # Устанавливаем некорректный URL, чтобы Alembic выдал ошибку при попытке подключения
    sqlalchemy_url = "postgresql+psycopg2://invalid_config_user:invalid_config_pass@invalid_config_host/invalid_config_db"
else:
    # Используем драйвер psycopg2 для Alembic - это нормально
    sqlalchemy_url = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# Передаем URL в конфигурацию Alembic
config.set_main_option('sqlalchemy.url', sqlalchemy_url)
# Отладочный вывод URL (маскируем пароль)
print(f"Alembic будет использовать URL: postgresql+psycopg2://{db_user}:******@{db_host}:{db_port}/{db_name}") # Отладка
# --------------------------------------------------------------------


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# --- Изменено: target_metadata уже определен выше ---
# target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # url = config.get_main_option("sqlalchemy.url") # Можно взять из config
    context.configure(
        url=sqlalchemy_url, # Используем наш сформированный URL
        target_metadata=target_metadata, # Используем нашу metadata
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Добавим обработку типов для UUID и JSONB, если они используются в миграциях offline
        # process_revision_directives=process_revision_directives, # Для кастомной логики
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # --- Изменено: Используем конфигурацию из config объекта ---
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}), # Используем правильную секцию из alembic.ini
        prefix="sqlalchemy.", # Префикс для параметров движка в ini
        poolclass=pool.NullPool, # Используем NullPool для Alembic, он создает соединения по мере необходимости
    )
    # -----------------------------------------------------------

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata # Используем нашу metadata
            # Добавим обработку типов для UUID и JSONB для online режима
            # process_revision_directives=process_revision_directives, # Для кастомной логики
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    print("Running migrations in offline mode...")
    run_migrations_offline()
else:
    print("Running migrations in online mode...")
    run_migrations_online()