import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import OAuth2PasswordBearer
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from src.auth.providers.auth_google import GoogleOAuth
from src.config.settings import settings
from src.models import UserProfile, User
from src.repositories.user import get_user_by_email, create_new_user
from src.schemas import UserCreate
from src.services.auth import generate_tokens
from src.utils.db import get_async_db
from loguru import logger

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
templates = Jinja2Templates(directory="templates")


@router.get("/test", response_class=HTMLResponse)
async def serve_html(request: Request):
    return templates.TemplateResponse("google_auth.html", {"request": request})


# Инициализация Google OAuth
google_oauth = GoogleOAuth(
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    redirect_uri=settings.google_redirect_uri,
)


@router.get("/google")
async def google_auth_callback(
    code: str = Query(..., description="Authorization code от Google"),
):
    """
    Обрабатывает callback от Google OAuth2 и создает пользователя,
    если его нет в базе. Также заполняет профиль пользователя.

    Args:
        code (str): Authorization code от Google.
        session (AsyncSession): Асинхронная сессия базы данных.

    Returns:
        dict: Токены доступа и обновления.
    """
    # try:
    # Получаем access token и данные пользователя от Google
    access_token = await google_oauth.get_access_token(code)

    # Получение данных пользователя
    user_info = await google_oauth.get_user_info(access_token)
    logger.debug(f"User info: {user_info}")

    email = user_info.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by Google")

    # Проверяем, существует ли пользователь
    user = await get_user_by_email(email)
    if not user:
        # Создаем нового пользователя
        user = await create_new_user(
            user_data=UserCreate(
                email=email,
                password=uuid.uuid4().hex
            ),
            profile_data={
                "nickname": user_info.get("name"),
                "avatar_url": user_info.get("picture")
            }
        )

    # Генерируем токены для пользователя
    tokens = await generate_tokens(email=user.email, user_id=user.id)
    return tokens

    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=f"Authorization failed: {str(e)}")
