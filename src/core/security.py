import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from loguru import logger

from src.config.settings import settings

# Создаем пул потоков для выполнения блокирующих операций
executor = ThreadPoolExecutor()


# Функция для выполнения хеширования в пуле потоков
async def async_hash_password(password: str) -> str:
    loop = asyncio.get_running_loop()
    hashed = await loop.run_in_executor(executor, bcrypt.hashpw, password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')


# Функция для выполнения проверки пароля
async def async_verify_password(password: str, hashed_password: str) -> bool:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, bcrypt.checkpw, password.encode('utf-8'),
                                      hashed_password.encode('utf-8'))


# OAuth2 схема
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")


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
