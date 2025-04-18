import logging
from datetime import timedelta
from typing import Dict

from fastapi import HTTPException
from fastapi_mail import FastMail, MessageSchema
from starlette import status

from src.config import ACCESS_TOKEN_EXPIRE_MINUTES, ACCESS_SECRET_KEY, REFRESH_TOKEN_EXPIRE_DAYS, REFRESH_SECRET_KEY, \
    BASE_URL
from src.core.security import async_verify_password
from src.core.security import create_token
from src.repositories.user import get_user_by_email

logger = logging.getLogger(__name__)


async def authenticate_user(email: str, password: str):
    user = await get_user_by_email(email)
    if not user or not await async_verify_password(password, user.hashed_password):
        return False
    return user


async def generate_tokens(email: str, user_id: int) -> Dict[str, str]:
    """Генерация access и refresh токенов"""
    access_token = await create_token(
        data={"email": email, "user_id": user_id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        secret_key=ACCESS_SECRET_KEY
    )

    refresh_token = await create_token(
        data={"email": email, "user_id": user_id},
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        secret_key=REFRESH_SECRET_KEY
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


async def send_password_reset_email(email: str, reset_token: str, fastmail: FastMail):
    reset_url = f"{BASE_URL}/reset-password?token={reset_token}"

    message = MessageSchema(
        subject="Сброс пароля",
        recipients=[email],
        template_body={
            "reset_url": reset_url,
            "expire_minutes": ACCESS_TOKEN_EXPIRE_MINUTES
        }
    )

    # Используем шаблон для письма
    template_name = "password_reset.html"

    try:
        await fastmail.send_message(message, template_name=template_name)
        logger.info(f"Password reset email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send password reset email"
        )
