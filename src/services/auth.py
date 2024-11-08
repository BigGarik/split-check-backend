from datetime import timedelta
from typing import Dict

from src.core.security import create_token
from src.repositories.user import get_user_by_email
from src.config.settings import settings
from src.core.security import async_verify_password


async def authenticate_user(email: str, password: str):
    user = await get_user_by_email(email)
    if not user or not await async_verify_password(password, user.hashed_password):
        return False
    return user


async def generate_tokens(email: str, user_id: int) -> Dict[str, str]:
    """Генерация access и refresh токенов"""
    access_token = await create_token(
        data={"email": email, "user_id": user_id},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        secret_key=settings.access_secret_key
    )

    refresh_token = await create_token(
        data={"email": email, "user_id": user_id},
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
        secret_key=settings.refresh_secret_key
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
