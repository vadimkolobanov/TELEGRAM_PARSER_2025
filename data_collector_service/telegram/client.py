# telegram-intel/data_collector_service/telegram/client.py

import os
from pathlib import Path
from typing import Optional

from telethon import TelegramClient
# ----- ИСПРАВЛЕННЫЙ ИМПОРТ -----
from telethon.sessions import StringSession, Session # Заменили FilenameSession на Session
# --------------------------------
from telethon.errors import SessionPasswordNeededError, FloodWaitError, RPCError

# Импортируем настройки сервиса (API_ID, API_HASH, папка для сессий)
from data_collector_service.core.config import settings
# Импортируем модель AppUser для получения пути к файлу сессии
from shared.models import AppUser # Модель SQLAlchemy

# --- Управление клиентом Telethon ---

async def get_telegram_client(user: AppUser) -> Optional[TelegramClient]:
    """
    Инициализирует и возвращает аутентифицированный клиент Telethon
    для указанного пользователя приложения.
    """
    if not user.session_file:
        print(f"Error: No session file path configured for user {user.email} (ID: {user.id})")
        return None

    session_path = settings.SESSION_FILES_DIR / user.session_file
    session_name = session_path.stem # Имя файла без расширения

    print(f"Attempting to initialize TelegramClient for user {user.email} using session: {session_path}")

    if not session_path.exists():
        print(f"Error: Session file not found at {session_path} for user {user.email}")
        return None

    # Создаем клиент Telethon, передавая путь к файлу сессии как строку.
    # Telethon сам разберется, что это файловая сессия.
    client = TelegramClient(
        session=str(session_path), # Передаем путь как строку
        api_id=settings.API_ID,
        api_hash=settings.API_HASH,
        connection_retries=5,
        retry_delay=5,
    )

    try:
        print(f"Connecting Telegram client for user {user.email}...")
        await client.connect()

        if not await client.is_user_authorized():
            print(f"Error: User {user.email} session ({session_path}) is not authorized or expired.")
            await client.disconnect()
            return None

        print(f"Telegram client for user {user.email} connected and authorized.")
        return client

    except SessionPasswordNeededError:
        print(f"Error: Session for user {user.email} requires 2FA password.")
        await client.disconnect()
        return None
    except FloodWaitError as e:
        print(f"Error: Flood wait encountered for user {user.email}. Wait {e.seconds} seconds.")
        await client.disconnect()
        return None
    except RPCError as e:
        print(f"Error: Telegram RPC error for user {user.email}: {e}")
        await client.disconnect()
        return None
    except Exception as e:
        print(f"Error: Unexpected error initializing Telegram client for user {user.email}: {e}")
        if client and client.is_connected():
            await client.disconnect()
        return None

async def disconnect_client(client: Optional[TelegramClient]):
    """Безопасно отключает клиент Telethon."""
    if client and client.is_connected():
        print("Disconnecting Telegram client...")
        await client.disconnect()
        print("Telegram client disconnected.")