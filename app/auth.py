from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from loguru import logger
from passlib.context import CryptContext

from app.crud import get_user_by_email
from app.utils import async_verify_password
from config import settings


# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def authenticate_user(email: str, password: str):
    user = await get_user_by_email(email)
    if not user or not await async_verify_password(password, user.hashed_password):
        return False
    return user


async def create_token(
        data: Dict[str, Any],
        expires_delta: timedelta,
        secret_key: str
) -> str:
    """Создание JWT токена"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})

    try:
        return jwt.encode(
            to_encode,
            secret_key,
            algorithm=settings.algorithm
        )
    except Exception as e:
        logger.error(f"Token creation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create token"
        )


async def generate_tokens(email: str, user_id: int) -> Dict[str, str]:
    """Generate both access and refresh tokens."""
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


# Проверка токена
async def verify_token(secret_key: str, token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("email")
        user_id: int = payload.get("user_id")
        expires = payload.get("exp")
        if expires < datetime.now().timestamp():
            raise credentials_exception
        if email is None:
            raise credentials_exception
        return email, user_id
    except JWTError:
        raise credentials_exception


# Получаем текущего пользователя из токена
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        email, _ = await verify_token(settings.access_secret_key, token=token)
        user = await get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
