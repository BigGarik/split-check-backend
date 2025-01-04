import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.providers.auth_google import GoogleOAuth
from src.config.settings import settings
from src.repositories.user import get_user_by_email, create_new_user
from src.services.auth import generate_tokens
from src.utils.db import get_async_db

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


# Инициализация Google OAuth
google_oauth = GoogleOAuth(
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    redirect_uri=settings.google_redirect_uri,
)


@router.get("/auth/google")
async def google_auth_callback(
    code: str = Query(..., description="Authorization code от Google"),
    session: AsyncSession = Depends(get_async_db),
):
    """
    Callback после авторизации через Google.
    """
    try:
        # Получение токена доступа
        access_token = await google_oauth.get_access_token(code)

        # Получение данных пользователя
        user_info = await google_oauth.get_user_info(access_token)
        email = user_info.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")

        # Проверка или создание пользователя
        user = await get_user_by_email(session, email)
        if not user:
            password = uuid.uuid4().hex
            user = await create_new_user(
                session,
                user_data={"email": email, "password": password},  # Пароль не обязателен для OAuth
            )

        # Генерация токенов
        tokens = await generate_tokens(email=user.email, user_id=user.id)
        return tokens

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authorization failed: {str(e)}")
