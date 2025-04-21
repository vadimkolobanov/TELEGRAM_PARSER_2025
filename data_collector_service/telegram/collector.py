import asyncio
from typing import Optional, List, Dict, Any, Tuple, Union # Добавил Union

from telethon import TelegramClient
from telethon.tl.types import Channel, Chat, User as TLUser, ChannelParticipantsSearch, ChannelParticipantAdmin, ChannelParticipantCreator, ChannelParticipant, InputPeerChannel, InputPeerChat, InputPeerUser
# ----- ИСПРАВЛЕННЫЕ ИМПОРТЫ ЗАПРОСОВ -----
from telethon.tl.functions.channels import GetFullChannelRequest, GetParticipantsRequest
from telethon.tl.functions.messages import GetFullChatRequest
# -----------------------------------------
from telethon.errors import FloodWaitError, UserNotParticipantError, ChannelPrivateError, ChatAdminRequiredError, RPCError, ChatIdInvalidError

# Импортируем функцию получения клиента
from .client import get_telegram_client, disconnect_client
# Импортируем модели SQLAlchemy для типизации и сохранения
from shared.models import AppUser, TargetChat, User, ChatParticipant

# Определим типы для возвращаемых данных
ChatDataType = Optional[Dict[str, Any]]
ParticipantsDataType = Optional[List[Dict[str, Any]]]

async def get_chat_info(client: TelegramClient, chat_entity_or_id: Union[int, str]) -> ChatDataType:
    """
    Получает подробную информацию о чате или канале.

    Args:
        client: Авторизованный экземпляр TelegramClient.
        chat_entity_or_id: ID чата/канала (int) или его username/ссылка (str).

    Returns:
        Словарь с информацией о чате/канале или None в случае ошибки.
    """
    print(f"Attempting to get info for chat/channel: {chat_entity_or_id}")
    try:
        # Получаем сущность чата/канала
        entity = await client.get_entity(chat_entity_or_id)

        chat_info = {
            "id": entity.id,
            "title": getattr(entity, 'title', None),
            "username": getattr(entity, 'username', None),
            "access_hash": getattr(entity, 'access_hash', None),
            "type": None,
            "participants_count": None,
            "about": None,
            "is_supergroup": False,
            "is_channel": False,
            "is_group": False,
            "is_gigagroup": False,
        }

        # Определяем тип и получаем дополнительную информацию
        if isinstance(entity, Channel):
            chat_info["type"] = "channel" if entity.broadcast else ("supergroup" if entity.megagroup else "group") # Уточняем тип
            chat_info["is_channel"] = entity.broadcast
            chat_info["is_supergroup"] = entity.megagroup
            chat_info["is_gigagroup"] = getattr(entity, 'gigagroup', False)
            try:
                # Запрашиваем полную информацию (включая кол-во участников и описание)
                full_channel = await client(GetFullChannelRequest(channel=entity))
                chat_info["participants_count"] = full_channel.full_chat.participants_count
                chat_info["about"] = full_channel.full_chat.about
                # Можно добавить больше полей из full_channel.full_chat и full_channel.chats/users
            except (ValueError, RPCError) as e: # ValueError если ID/хеш неверны, RPCError для других проблем
                 print(f"Warning: Could not get full channel info for {entity.id}: {e}")

        elif isinstance(entity, Chat):
             chat_info["type"] = "group"
             chat_info["is_group"] = True
             try:
                # Запрашиваем полную информацию о группе
                full_chat = await client(GetFullChatRequest(chat_id=entity.id))
                chat_info["participants_count"] = len(full_chat.users) # Приблизительно, GetFullChatRequest может не вернуть всех
                # В full_chat.full_chat нет about для обычных групп
                # Можно получить список участников из full_chat.users
             except (ValueError, RPCError) as e:
                 print(f"Warning: Could not get full chat info for {entity.id}: {e}")

        else:
            print(f"Warning: Entity {chat_entity_or_id} is not a Channel or Chat (Type: {type(entity)}).")
            return None

        print(f"Successfully retrieved info for chat {chat_info['id']} ('{chat_info['title']}')")
        return chat_info

    except ValueError:
        print(f"Error: Could not find chat/channel: {chat_entity_or_id}. Invalid ID or username?")
        return None
    except (ChannelPrivateError, ChatAdminRequiredError):
        print(f"Error: Access denied to chat/channel: {chat_entity_or_id}. Private or requires admin rights.")
        return None
    except ChatIdInvalidError:
         print(f"Error: Invalid chat ID: {chat_entity_or_id}")
         return None
    except FloodWaitError as e:
        print(f"Error: Flood wait ({e.seconds}s) while getting chat info for {chat_entity_or_id}.")
        await asyncio.sleep(e.seconds + 1) # Ждем и пробуем еще раз (простая обработка)
        return await get_chat_info(client, chat_entity_or_id) # Рекурсивный вызов (осторожно!)
    except RPCError as e:
        print(f"Error: RPC error getting chat info for {chat_entity_or_id}: {e}")
        return None
    except Exception as e:
        print(f"Error: Unexpected error getting chat info for {chat_entity_or_id}: {e}")
        return None


async def get_chat_participants(client: TelegramClient, chat_entity_or_id: Union[int, str], limit: int = 0) -> ParticipantsDataType:
    """
    Получает список участников чата или канала.

    Args:
        client: Авторизованный экземпляр TelegramClient.
        chat_entity_or_id: ID чата/канала (int) или его username/ссылка (str).
        limit: Максимальное количество участников для получения (0 = все).
               Внимание: Получение ВСЕХ участников может быть очень долгим и ресурсоемким!

    Returns:
        Список словарей с информацией об участниках или None в случае ошибки.
    """
    print(f"Attempting to get participants for chat/channel: {chat_entity_or_id} (Limit: {limit})")
    participants_data = []
    offset = 0
    batch_size = 200 # Максимальное количество за один запрос GetParticipantsRequest

    try:
        entity = await client.get_entity(chat_entity_or_id)
        if not isinstance(entity, (Channel, Chat)):
            print(f"Error: Entity {chat_entity_or_id} is not a Channel or Chat.")
            return None

        print(f"Starting participant collection for chat {entity.id}...")
        total_participants_processed = 0

        while True:
            print(f"Fetching participants batch: Offset={offset}, Limit={batch_size}")
            try:
                if isinstance(entity, Channel):
                    # Для каналов и супергрупп
                    participants_result = await client(GetParticipantsRequest(
                        channel=entity,
                        filter=ChannelParticipantsSearch(''), # Пустой фильтр для получения всех
                        offset=offset,
                        limit=batch_size,
                        hash=0 # hash=0 для получения свежих данных
                    ))
                    current_batch_participants = participants_result.users
                    current_batch_participant_details = participants_result.participants
                elif isinstance(entity, Chat):
                     # Для обычных групп (может работать нестабильно или требовать других методов)
                     # GetFullChatRequest может быть предпочтительнее, но вернет не всех сразу
                     print("Warning: Fetching participants for basic groups might be limited.")
                     full_chat = await client(GetFullChatRequest(chat_id=entity.id))
                     current_batch_participants = full_chat.users
                     current_batch_participant_details = getattr(full_chat.full_chat, 'participants', None) # Пытаемся получить детали, если есть
                     if offset > 0: # Для обычных групп получаем всех за один раз (предположительно)
                         break
                else:
                    break # Неожиданный тип

                if not current_batch_participants:
                    print("No more participants found in this batch or chat.")
                    break # Больше нет участников

                # Обрабатываем полученных пользователей
                for user_obj in current_batch_participants:
                    if isinstance(user_obj, TLUser): # Убедимся, что это пользователь
                        participant_details = next((p for p in current_batch_participant_details if getattr(p, 'user_id', None) == user_obj.id), None) if current_batch_participant_details else None
                        participant_type = 'member' # По умолчанию
                        inviter_id = None
                        joined_date = None

                        if participant_details:
                            joined_date = getattr(participant_details, 'date', None) # Дата присоединения
                            if isinstance(participant_details, ChannelParticipantCreator):
                                participant_type = 'creator'
                            elif isinstance(participant_details, ChannelParticipantAdmin):
                                participant_type = 'admin'
                            # Можно добавить обработку ChannelParticipantBanned, ChannelParticipantLeft
                            # inviter_id доступен в ChannelParticipant через inviter_id, если есть права
                            inviter_id = getattr(participant_details, 'inviter_id', None)


                        user_data = {
                            "id": user_obj.id,
                            "access_hash": getattr(user_obj, 'access_hash', None),
                            "username": getattr(user_obj, 'username', None),
                            "first_name": getattr(user_obj, 'first_name', None),
                            "last_name": getattr(user_obj, 'last_name', None),
                            "phone": getattr(user_obj, 'phone', None),
                            "is_bot": getattr(user_obj, 'bot', False),
                            "is_deleted": getattr(user_obj, 'deleted', False),
                            "is_verified": getattr(user_obj, 'verified', False),
                            "is_restricted": getattr(user_obj, 'restricted', False),
                            "is_scam": getattr(user_obj, 'scam', False),
                            "is_fake": getattr(user_obj, 'fake', False),
                            "lang_code": getattr(user_obj, 'lang_code', None),
                            # Telethon не предоставляет статус (online/offline) в этом запросе
                            # "status": None,
                            # "last_seen_at": None, # Нужно использовать GetUsersRequest или обновления статуса

                            # Данные из participant_details
                            "participant_type": participant_type,
                            "inviter_user_id": inviter_id,
                            "joined_date": joined_date,
                        }
                        participants_data.append(user_data)
                        total_participants_processed += 1

                offset += len(current_batch_participants)
                print(f"Processed batch. Total participants so far: {total_participants_processed}. Current offset: {offset}")

                # Проверяем лимит, если он установлен
                if limit > 0 and total_participants_processed >= limit:
                    print(f"Reached participant limit ({limit}). Stopping collection.")
                    # Обрезаем список до точного лимита
                    participants_data = participants_data[:limit]
                    break

                # Небольшая задержка между запросами, чтобы избежать флуда
                await asyncio.sleep(1)

            except FloodWaitError as e:
                print(f"Error: Flood wait ({e.seconds}s) during participant fetch. Waiting...")
                await asyncio.sleep(e.seconds + 1)
                # Продолжаем с того же места
                continue
            except (UserNotParticipantError, ChannelPrivateError, ChatAdminRequiredError):
                 print(f"Error: Access denied to participants of chat/channel: {chat_entity_or_id}.")
                 return None # Нет смысла продолжать
            except RPCError as e:
                 print(f"Error: RPC error fetching participants for {chat_entity_or_id}: {e}")
                 # Можно попробовать продолжить или прервать
                 break # Прерываем цикл при RPC ошибке
            except Exception as e:
                 print(f"Error: Unexpected error fetching participants for {chat_entity_or_id}: {e}")
                 break # Прерываем цикл

        print(f"Finished collecting participants for chat {entity.id}. Total found: {len(participants_data)}")
        return participants_data

    except ValueError:
        print(f"Error: Could not find chat/channel: {chat_entity_or_id}. Invalid ID or username?")
        return None
    except (ChannelPrivateError, ChatAdminRequiredError):
        print(f"Error: Access denied to chat/channel: {chat_entity_or_id}.")
        return None
    except ChatIdInvalidError:
         print(f"Error: Invalid chat ID: {chat_entity_or_id}")
         return None
    except FloodWaitError as e:
        print(f"Error: Flood wait ({e.seconds}s) getting entity for participants: {chat_entity_or_id}.")
        await asyncio.sleep(e.seconds + 1)
        return await get_chat_participants(client, chat_entity_or_id, limit) # Рекурсия
    except RPCError as e:
        print(f"Error: RPC error getting entity for participants: {chat_entity_or_id}: {e}")
        return None
    except Exception as e:
        print(f"Error: Unexpected error getting entity for participants: {chat_entity_or_id}: {e}")
        return None

# --- Основная функция-обертка для сбора данных по чату ---
async def collect_chat_data(app_user: AppUser, chat_target: Union[int, str]) -> Tuple[ChatDataType, ParticipantsDataType]:
    """
    Полный цикл сбора данных: подключается к TG, получает инфо о чате и участниках.

    Args:
        app_user: Пользователь приложения, чья сессия используется.
        chat_target: ID или username целевого чата.

    Returns:
        Кортеж из двух элементов: (информация_о_чате, список_участников).
        Каждый элемент может быть None в случае ошибки.
    """
    client = None
    chat_data = None
    participants_list = None
    try:
        # 1. Получить клиента Telethon
        client = await get_telegram_client(app_user)
        if not client:
            print(f"Failed to get Telegram client for user {app_user.email}")
            return None, None # Возвращаем None, None при ошибке клиента

        # 2. Получить информацию о чате
        chat_data = await get_chat_info(client, chat_target)
        if not chat_data:
            print(f"Failed to get chat info for target: {chat_target}")
            # Продолжаем, даже если инфо о чате не получено, чтобы попробовать собрать участников
            # return None, None # Раскомментировать, если инфо о чате критично

        # 3. Получить участников (пока без лимита - осторожно!)
        # TODO: Добавить разумный лимит по умолчанию или брать из запроса API
        participants_list = await get_chat_participants(client, chat_target, limit=0) # limit=0 для всех
        if participants_list is None:
            print(f"Failed to get participants for target: {chat_target}")
            # Ошибки получения участников могут быть ожидаемы (например, нет прав)

        return chat_data, participants_list

    finally:
        # 4. Гарантированно отключить клиент
        await disconnect_client(client)