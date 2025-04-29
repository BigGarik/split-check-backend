from typing import Optional
from fastapi import Request, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from starlette.websockets import WebSocket
from jose import JWTError
import logging

from src.auth.dependencies import get_firebase_user
from src.config import ACCESS_SECRET_KEY
from src.core.security import verify_token
from src.redis.utils import get_token_from_redis, add_token_to_redis
from src.repositories.user import get_user_by_email

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")


async def get_user_from_token(token: Optional[str], id_token: Optional[str]) -> str:
    """
    Универсальная функция для получения email из токена.
    Принимает либо OAuth2 токен, либо Firebase id_token.
    """
    if token:
        try:
            email, _ = await verify_token(ACCESS_SECRET_KEY, token=token)
            return email
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OAuth2 token")

    if id_token:
        claims = await get_token_from_redis(id_token)
        if not claims:
            logger.debug(f"Fetching claims from Firebase for token: {id_token}")
            claims = get_firebase_user(id_token)
            await add_token_to_redis(id_token, claims)
        email = claims.get('email')
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not found in token claims")
        return email

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token not provided")


async def get_current_user(request: Request, token: Optional[str] = Depends(oauth2_scheme)):
    """
    Dependency для проверки и получения текущего пользователя через OAuth2 или Firebase для обычных HTTP запросов.
    """
    try:
        id_token = request.headers.get('Authorization')
        email = await get_user_from_token(token=token, id_token=id_token)
        user = await get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")


async def get_current_user_for_websocket(websocket: WebSocket):
    """
    Dependency для проверки и получения текущего пользователя через OAuth2 или Firebase для WebSocket соединений.
    """
    try:
        token = websocket.query_params.get('token')
        id_token = websocket.query_params.get('id_token')
        email = await get_user_from_token(token=token, id_token=id_token)
        user = await get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
