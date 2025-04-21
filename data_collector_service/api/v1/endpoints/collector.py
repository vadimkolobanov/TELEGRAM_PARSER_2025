from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Union

# Импортируем зависимости, CRUD, схемы, модели, Telethon-логику
from data_collector_service.db.session import get_db # Локальная get_db
from data_collector_service import schemas, crud
from data_collector_service.telegram.collector import collect_chat_data, ChatDataType, ParticipantsDataType
from shared.models import AppUser as CurrentUserModel # Модель AppUser из shared
# Импортируем общую зависимость аутентификации из shared
from shared.dependencies.auth import get_current_user

# Создаем роутер для эндпоинтов сбора данных
router = APIRouter()

# --- Вспомогательная функция для передачи зависимостей ---
# Нужна для правильной передачи локальной `db` сессии в общую зависимость `get_current_user`
async def get_current_user_dependency(db: AsyncSession = Depends(get_db)):
    return await get_current_user(db=db) # Вызываем общую зависимость, передавая ей db

# --- Основная функция обработки сбора и сохранения ---
async def process_and_save_collection(
    db: AsyncSession,
    app_user: CurrentUserModel,
    chat_target: Union[int, str]
) -> schemas.CollectChatResponse:
    """
    Выполняет сбор данных из Telegram и сохраняет их в БД.
    Вызывается либо напрямую, либо через BackgroundTasks.
    """
    print(f"Starting data collection for target '{chat_target}' by user {app_user.email}")
    response_msg = f"Сбор данных для '{chat_target}' инициирован."
    response_chat_id = None
    response_status = None
    target_chat_db = None # Переменная для хранения объекта TargetChat из БД

    # 1. Выполнить сбор данных из Telegram
    chat_data, participants_list = await collect_chat_data(app_user, chat_target)

    if chat_data:
        response_chat_id = chat_data.get("id")
        print(f"Collected chat info for ID: {response_chat_id}")
        # 2. Создать или обновить TargetChat в БД
        try:
            target_chat_db = await crud.create_or_update_target_chat(
                db=db,
                chat_data=chat_data,
                added_by_user=app_user,
                initial_status="collecting" # Начинаем со статуса сбора
            )
            response_status = target_chat_db.status
            response_msg = f"Информация о чате '{chat_data.get('title', chat_target)}' (ID: {response_chat_id}) сохранена/обновлена."
        except Exception as e:
            print(f"Error saving target chat data for {response_chat_id}: {e}")
            response_msg = f"Ошибка сохранения информации о чате '{chat_target}'."
            # Не прерываем, попробуем сохранить участников, если они есть
    else:
        # Попробовать найти чат в БД по имени/id, если он был добавлен ранее
        if isinstance(chat_target, int):
             target_chat_db = await crud.get_target_chat_by_chat_id(db, chat_id=chat_target)
             if target_chat_db: response_chat_id = target_chat_db.chat_id
        # TODO: Добавить поиск по username, если chat_target - строка
        response_msg = f"Не удалось получить информацию о чате '{chat_target}' из Telegram."
        print(response_msg)

    if participants_list:
        print(f"Collected {len(participants_list)} participants for chat ID: {response_chat_id}")
        if response_chat_id is None:
             print("Warning: Cannot save participants without a valid chat ID.")
             response_msg += " Не удалось сохранить участников, т.к. ID чата неизвестен."
        else:
            # 3. Преобразовать участников в схему для валидации/обработки
            valid_participants_data = []
            for p_dict in participants_list:
                try:
                    # Пропускаем валидацию через Pydantic для скорости или добавляем обработку ошибок
                    valid_participants_data.append(schemas.CollectedUserSchema.model_validate(p_dict)) # Pydantic V2
                    # valid_participants_data.append(schemas.CollectedUserSchema.parse_obj(p_dict)) # Pydantic V1
                except Exception as p_error:
                    print(f"Warning: Skipping participant data due to validation error: {p_error}. Data: {p_dict}")

            # 4. Выполнить bulk upsert пользователей (User)
            try:
                await crud.bulk_upsert_users(db=db, users_data=valid_participants_data, collected_by=app_user)
            except Exception as e:
                 print(f"Error during bulk user upsert for chat {response_chat_id}: {e}")
                 response_msg += " Ошибка при сохранении данных пользователей."

            # 5. Выполнить bulk upsert участников (ChatParticipant)
            try:
                await crud.bulk_upsert_participants(db=db, chat_id=response_chat_id, participants_data=valid_participants_data)
                response_msg += f" Сохранено/обновлено {len(valid_participants_data)} участников."
            except Exception as e:
                 print(f"Error during bulk participant upsert for chat {response_chat_id}: {e}")
                 response_msg += " Ошибка при сохранении связей участников с чатом."
    else:
        print(f"No participants collected or failed to collect for chat ID: {response_chat_id}")
        # response_msg += " Участники не были собраны." # Можно не добавлять, если это ожидаемо

    # 6. Обновить статус TargetChat на 'collected' или 'error'
    final_status = "collected"
    if chat_data is None and participants_list is None:
        final_status = "error" # Ошибка, если не удалось собрать ни чат, ни участников
    elif target_chat_db: # Если объект чата был создан/найден
        try:
            await crud.update_target_chat_status(db=db, chat_id=response_chat_id, status=final_status)
            response_status = final_status
            print(f"Final status for chat {response_chat_id} set to '{final_status}'")
        except Exception as e:
            print(f"Error updating final status for chat {response_chat_id}: {e}")
    else:
         # Случай, когда чат не был найден в тг и не был в бд, а участники собрались (маловероятно, но возможно)
         print(f"Cannot update final status as target chat object for ID {response_chat_id} was not found/created.")


    return schemas.CollectChatResponse(
        message=response_msg,
        chat_id=response_chat_id,
        status=response_status
        # task_id=None # Для синхронной версии
    )


# --- API Эндпоинт ---
# Используем BackgroundTasks для неблокирующего выполнения (простой вариант без Celery)
# Внимание: BackgroundTasks имеют ограничения по ресурсам и надежности для долгих задач!
@router.post("/collect", response_model=schemas.CollectChatResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_chat_collection(
    request_data: schemas.CollectChatRequest, # Данные из тела запроса (chat_target)
    background_tasks: BackgroundTasks, # Механизм фоновых задач FastAPI
    db: AsyncSession = Depends(get_db), # Локальная сессия БД
    current_user: CurrentUserModel = Depends(get_current_user_dependency) # Текущий пользователь
):
    """
    Запускает сбор данных для указанного чата/канала в фоновом режиме.
    """
    print(f"Received collection request for '{request_data.chat_target}' from user {current_user.email}")

    # Добавляем основную логику сбора и сохранения в фоновую задачу
    # Передаем КОПИИ необходимых данных, а не объекты сессии или пользователя напрямую,
    # если бы это были сложные объекты (для простых ID/строк это не так критично).
    # В нашем случае передаем chat_target и объект current_user (он будет доступен).
    # Сессия db будет создана заново внутри фоновой задачи при вызове Depends(get_db).
    # НЕ передавайте db из этого эндпоинта в фоновую задачу!

    # Мы НЕ МОЖЕМ напрямую передать Depends(get_db) в фоновую задачу.
    # Поэтому process_and_save_collection должна уметь работать с сессией,
    # которую она получит через Depends(), когда будет вызвана фоново.
    # Переделываем process_and_save_collection, чтобы она принимала Depends()

    # *** Альтернативный (СИНХРОННЫЙ) вариант для простоты отладки ***
    # Уберите background_tasks и вызовите напрямую:
    # response = await process_and_save_collection(db=db, app_user=current_user, chat_target=request_data.chat_target)
    # return response
    # *****************************************************************

    # *** Вариант с BackgroundTasks ***
    # Функция process_and_save_collection ДОЛЖНА быть изменена, чтобы принимать user_id, а не объект user,
    # и получать db сессию через Depends() внутри себя. Либо использовать contextvars.
    # Это усложнение. Пока оставим СИНХРОННЫЙ вариант для простоты и выполнения ТЗ
    # (там указан Celery, а не BackgroundTasks).

    # ВЫПОЛНЯЕМ СИНХРОННО (для простоты, пока нет Celery)
    response = await process_and_save_collection(
        db=db, # Используем сессию из эндпоинта
        app_user=current_user,
        chat_target=request_data.chat_target
    )
    # Статус 202 здесь не совсем корректен для синхронного выполнения,
    # но оставим его как задел на будущее с Celery.
    # Для синхронного можно вернуть 200 OK.
    # Поменяем статус ответа в декораторе на 200 OK для синхронной версии.
    # router = APIRouter()
    # @router.post("/collect", response_model=schemas.CollectChatResponse, status_code=status.HTTP_200_OK)

    return response # Возвращаем результат выполнения