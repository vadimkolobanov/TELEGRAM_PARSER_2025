import os
from pathlib import Path
from typing import Optional

from telethon import TelegramClient
from telethon.sessions import StringSession, FilenameSession
from telethon.errors import SessionPasswordNeededError, FloodWaitError, RPCError

# Импортируем настройки сервиса (API_ID, API_HASH, папка для сессий)
from data_collector_service.core.config import settings
# Импортируем модель AppUser для получения пути к файлу сессии
# TODO: Как сервис будет получать AppUser? Через API или иначе? Пока предполагаем, что объект AppUser доступен.
from shared.models import AppUser # Модель SQLAlchemy

# --- Управление клиентом Telethon ---

async def get_telegram_client(user: AppUser) -> Optional[TelegramClient]:
    """
    Инициализирует и возвращает аутентифицированный клиент Telethon
    для указанного пользователя приложения.

    Использует файл .session, путь к которому указан в AppUser.session_file.
    Если AppUser.session_file пуст, клиент не может быть создан для этого пользователя.

    Args:
        user: Объект AppUser, для которого нужно создать клиент.

    Returns:
        Аутентифицированный экземпляр TelegramClient или None, если сессия не найдена/невалидна.
    """
    if not user.session_file:
        print(f"Error: No session file path configured for user {user.email} (ID: {user.id})")
        return None

    # Формируем полный путь к файлу сессии
    # settings.SESSION_FILES_DIR - это папка /sessions в корне проекта
    # user.session_file - это имя файла (например, user_uuid.session)
    session_path = settings.SESSION_FILES_DIR / user.session_file
    session_name = session_path.stem # Имя файла без расширения

    print(f"Attempting to initialize TelegramClient for user {user.email} using session: {session_path}")

    if not session_path.exists():
        print(f"Error: Session file not found at {session_path} for user {user.email}")
        return None

    # Создаем клиент Telethon с использованием файловой сессии
    # Используем API_ID и API_HASH из настроек
    client = TelegramClient(
        session=str(session_path), # Telethon принимает путь к сессии как строку
        api_id=settings.API_ID,
        api_hash=settings.API_HASH,
        # Настройки подключения (можно вынести в config)
        connection_retries=5,
        retry_delay=5,
        # system_version="4.16.30-vxCUSTOM" # Можно указать для имитации клиента
    )

    try:
        # Подключаемся к Telegram
        print(f"Connecting Telegram client for user {user.email}...")
        await client.connect()

        # Проверяем, авторизован ли клиент
        if not await client.is_user_authorized():
            print(f"Error: User {user.email} session ({session_path}) is not authorized or expired.")
            await client.disconnect()
            # TODO: Возможно, нужно как-то оповестить пользователя или обновить статус сессии в БД AppUser
            return None

        print(f"Telegram client for user {user.email} connected and authorized.")
        # Важно: не отключаем клиент здесь, он будет использоваться дальше
        # await client.disconnect() # НЕ ДЕЛАТЬ ЗДЕСЬ
        return client

    except SessionPasswordNeededError:
        print(f"Error: Session for user {user.email} requires 2FA password. Cannot proceed automatically.")
        await client.disconnect()
        # TODO: Обработка 2FA - очень сложная задача для автоматического сервиса.
        # Обычно требует ручного ввода пароля при первой авторизации.
        return None
    except FloodWaitError as e:
        print(f"Error: Flood wait encountered for user {user.email}. Wait {e.seconds} seconds.")
        await client.disconnect()
        # TODO: Обработка флуда - нужно ждать указанное время.
        return None
    except RPCError as e:
        print(f"Error: Telegram RPC error for user {user.email}: {e}")
        await client.disconnect()
        return None
    except Exception as e:
        print(f"Error: Unexpected error initializing Telegram client for user {user.email}: {e}")
        # Попытаемся отключиться, если клиент был создан
        if client and client.is_connected():
            await client.disconnect()
        return None


# --- Дополнительные функции (можно добавить позже) ---

async def disconnect_client(client: Optional[TelegramClient]):
    """Безопасно отключает клиент Telethon."""
    if client and client.is_connected():
        print("Disconnecting Telegram client...")
        await client.disconnect()
        print("Telegram client disconnected.")

# TODO: Нужна функция для создания сессии пользователя при его логине в auth_service
# Эта функция, вероятно, должна быть частью auth_service или вызываться им.
# Она будет запрашивать код, проверять его, запрашивать пароль 2FA (если нужно)
# и сохранять `.session` файл в папку `sessions/`, а путь записывать в `AppUser.session_file`.
# Это сложная интерактивная часть, которую пока опускаем.
# Пока мы предполагаем, что `.session` файл для пользователя УЖЕ существует
# и путь к нему записан в AppUser.session_file.