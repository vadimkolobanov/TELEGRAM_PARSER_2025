# telegram-intel/auth_service/api/v1/endpoints/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from datetime import timedelta

from auth_service.db.session import get_db # Локальная зависимость get_db
from auth_service import crud, schemas
from auth_service.utils.security import verify_password # Утилита для пароля осталась локальной
# Импортируем из shared
from shared.security.jwt_utils import create_access_token # JWT утилита из shared
from shared.dependencies.auth import get_current_user # Зависимость из shared
from shared.models import AppUser as CurrentUserModel # Модель из shared
from auth_service.core.config import settings # Настройки из auth_service

router = APIRouter()

# --- Эндпоинт /register ---
@router.post("/register", response_model=schemas.AppUserPublic, status_code=status.HTTP_201_CREATED)
async def register_new_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: schemas.AppUserCreate
):
    # ... (код без изменений) ...
    existing_user = await crud.get_app_user_by_email(db=db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует.",
        )
    try:
        user = await crud.create_app_user(db=db, user_in=user_in)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка регистрации. Возможно, email уже используется.",
        )
    except Exception as e:
        await db.rollback()
        print(f"Error during user registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера при регистрации пользователя.",
        )
    return user

# --- Эндпоинт /login ---
@router.post("/login", response_model=schemas.TokenResponse)
async def login_for_access_token(
    *,
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    # ... (код без изменений) ...
    user = await crud.get_app_user_by_email(db=db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    print(f"User {user.email} logged in successfully via form data. Token generated.")
    return schemas.TokenResponse(access_token=access_token, token_type="bearer")

# --- Эндпоинт /me ---
# Важно: передаем локальную зависимость get_db в get_current_user
async def get_current_user_dependency(db: AsyncSession = Depends(get_db)):
    # Эта обертка нужна, чтобы правильно передать db из локальной зависимости
    # в общую зависимость get_current_user
    return await get_current_user(db=db)


@router.get("/me", response_model=schemas.AppUserPublic)
async def read_users_me(
    # Используем обертку для передачи локальной db в общую зависимость
    current_user: CurrentUserModel = Depends(get_current_user_dependency)
):
    """
    Возвращает информацию о текущем аутентифицированном пользователе.
    """
    # Зависимость get_current_user_dependency уже сделала всю работу
    return current_user