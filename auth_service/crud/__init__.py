# telegram-intel/auth_service/crud/__init__.py

# Экспортируем CRUD функции для модели AppUser
from .crud_app_user import get_app_user, get_app_user_by_email, create_app_user, update_app_user

# Если будут CRUD для других моделей в этом сервисе, их тоже можно экспортировать здесь
# from .crud_some_other_model import ...