# telegram-intel/data_collector_service/crud/__init__.py

from .crud_target_chat import get_target_chat_by_chat_id, create_or_update_target_chat, update_target_chat_status
from .crud_user import get_user_by_id, upsert_user, bulk_upsert_users
from .crud_chat_participant import bulk_upsert_participants

__all__ = [
    # TargetChat
    "get_target_chat_by_chat_id",
    "create_or_update_target_chat",
    "update_target_chat_status",
    # User
    "get_user_by_id",
    "upsert_user",
    "bulk_upsert_users",
    # ChatParticipant
    "bulk_upsert_participants",
]