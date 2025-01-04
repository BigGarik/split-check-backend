from datetime import timedelta
from typing import Dict

from fastapi import HTTPException
from loguru import logger
from fastapi_mail import FastMail, MessageSchema
from starlette import status

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


async def send_password_reset_email(email: str, reset_token: str, fastmail: FastMail):
    reset_url = f"{settings.base_url}/reset-password?token={reset_token}"

    message = MessageSchema(
        subject="Сброс пароля",
        recipients=[email],
        template_body={
            "reset_url": reset_url,
            "expire_minutes": settings.access_token_expire_minutes
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
