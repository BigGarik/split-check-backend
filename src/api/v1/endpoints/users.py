import logging
from datetime import timedelta
from typing import Dict

from fastapi import APIRouter, Depends, Request
from fastapi import HTTPException
from fastapi_mail import FastMail
from jose import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.responses import Response

from src import schemas
from src.api.deps import get_current_user
from src.config import ACCESS_TOKEN_EXPIRE_MINUTES, ACCESS_SECRET_KEY, ALGORITHM, REFRESH_TOKEN_EXPIRE_DAYS
from src.config.mail import mail_config
from src.core.exceptions import UserAlreadyExistsError, DatabaseOperationError
from src.core.security import create_token, async_hash_password
from src.models import User
from src.repositories.user import create_new_user, get_user_by_email, mark_user_as_deleted
from src.schemas import PasswordResetRequest, PasswordReset
from src.services.auth import send_password_reset_email, generate_tokens
from src.utils.db import with_db_session, get_async_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/create",
    summary="Создать пользователя",
    response_model=schemas.User,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid input data"},
        409: {"description": "User already exists"},
        500: {"description": "Internal server error"}
    }
)
async def create_user(user_data: schemas.UserCreate) -> schemas.User:
    """
    Create a new user endpoint.

    Args:
        user_data: Validated user creation data

    Returns:
        schemas.User: Created user data

    Raises:
        HTTPException: On various error conditions with appropriate status codes
    """
    try:
        return await create_new_user(user_data=user_data)
    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": str(e), "details": e.details}
        )
    except DatabaseOperationError as e:
        logger.error("Database error during user creation",
                     extra={"error_details": e.details})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )
    except Exception as e:
        logger.exception("Unexpected error during user creation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.post("/request-reset", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
        request: PasswordResetRequest,
        fastmail: FastMail = Depends(lambda: FastMail(mail_config))
) -> Dict[str, str]:
    """
    Эндпоинт для запроса сброса пароля.
    Отправляет email с токеном для сброса пароля.
    """
    try:
        user = await get_user_by_email(request.email)

        if user:
            # Генерируем временный токен для сброса пароля
            reset_token = await create_token(
                data={"email": user.email, "user_id": user.id, "type": "password_reset"},
                expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
                secret_key=ACCESS_SECRET_KEY
            )
            await send_password_reset_email(request.email, reset_token, fastmail)

        # Всегда возвращаем успешный ответ для предотвращения утечки информации
        return {"message": "If an account with this email exists, a password reset link has been sent"}
    except Exception as e:
        logger.error(f"Error in password reset request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/reset", status_code=status.HTTP_200_OK)
@with_db_session()
async def reset_password(
        reset_data: PasswordReset,
        response: Response,
        session: AsyncSession = Depends(get_async_db)
) -> Dict[str, str]:
    """
    Эндпоинт для установки нового пароля с использованием токена сброса.
    При успешном сбросе пароля также генерирует новую пару токенов для аутентификации.
    """
    try:
        # Проверяем токен сброса пароля
        payload = jwt.decode(
            reset_data.token,
            ACCESS_SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        if payload.get("type") != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type"
            )

        user = await get_user_by_email(payload["email"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        try:
            # Хешируем новый пароль
            hashed_password = await async_hash_password(reset_data.new_password)
            user.hashed_password = hashed_password
            await session.commit()
            logger.info(f"Password reset successful for user {user.email}")

            # Генерируем новую пару токенов
            tokens = await generate_tokens(user.email, user.id)

            # Устанавливаем refresh token в cookie
            response.set_cookie(
                key="refresh_token",
                value=tokens["refresh_token"],
                httponly=True,
                secure=True,
                samesite="strict",
                max_age=REFRESH_TOKEN_EXPIRE_DAYS
            )

            return tokens

        except IntegrityError as e:
            logger.error(f"Integrity error while resetting password: {e}")
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset password due to database error"
            )

    except jwt.JWTError as e:
        logger.warning(f"Invalid JWT token in password reset: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token"
        )

    except Exception as e:
        logger.error(f"Unexpected error in password reset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/delete", status_code=status.HTTP_200_OK)
@with_db_session()
async def user_delete(
        request: Request,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_db)):
    await mark_user_as_deleted(user.id, session)
    return {"detail": f"User {user.email} marked as deleted"}