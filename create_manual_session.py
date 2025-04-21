# telegram-intel/create_manual_session.py

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from telethon import TelegramClient

# --- Настройки ---
# Загружаем переменные из .env (API_ID, API_HASH)
BASE_DIR = Path(__file__).resolve().parent
DOTENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=DOTENV_PATH)

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

if not API_ID or not API_HASH:
    print("Ошибка: API_ID или API_HASH не найдены в .env файле.")
    exit()

try:
    API_ID = int(API_ID)
except ValueError:
    print("Ошибка: API_ID в .env файле должен быть числом.")
    exit()

# Папка для сохранения сессии
SESSION_DIR = BASE_DIR / "sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

# Имя файла сессии (можете изменить на более осмысленное)
SESSION_FILENAME = "my_manual_session.session"
SESSION_PATH = SESSION_DIR / SESSION_FILENAME
# ----------------

async def main():
    print(f"Создание файла сессии: {SESSION_PATH}")
    print("Используется API_ID:", API_ID)

    # Создаем клиент, указывая путь к файлу сессии
    # Telethon сам создаст файл, если его нет
    client = TelegramClient(str(SESSION_PATH), API_ID, API_HASH)

    try:
        print("Подключение к Telegram...")
        # Подключаемся и проходим авторизацию
        # Он запросит номер телефона, код и пароль 2FA (если есть) в консоли
        await client.start()

        print("-" * 20)
        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"Авторизация прошла успешно для пользователя: {me.first_name} (@{me.username}, ID: {me.id})")
            print(f"Файл сессии '{SESSION_FILENAME}' успешно создан/обновлен в папке 'sessions/'.")
            print("Теперь вы можете прописать имя этого файла ('my_manual_session.session')")
            print("в поле 'session_file' соответствующего AppUser в базе данных.")
        else:
            print("Ошибка: Не удалось авторизоваться.")
        print("-" * 20)

    except Exception as e:
        print(f"Произошла ошибка: {e}")
    finally:
        if client.is_connected():
            await client.disconnect()
            print("Клиент отключен.")

if __name__ == "__main__":
    asyncio.run(main())