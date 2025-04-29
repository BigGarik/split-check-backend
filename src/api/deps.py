from fastapi import Request, HTTPException
from loguru import logger
from starlette.websockets import WebSocket

from src.auth.dependencies import get_firebase_user
from src.redis.utils import get_token_from_redis, add_token_to_redis
from src.repositories.user import get_user_by_email


async def get_current_user(request: Request):
    """
    Dependency для проверки и получения текущего пользователя через Firebase
    """
    try:
        id_token = request.headers.get('Authorization')
        claims = await get_token_from_redis(id_token)
        logger.debug(f"claims: {claims}")
        if not claims:
            logger.debug(f"token: {id_token}")
            claims = get_firebase_user(id_token)
            await add_token_to_redis(id_token, claims)

        email = claims.get('email')
        user = await get_user_by_email(email)
        return user
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=401, detail="Could not validate credentials")


async def get_current_user_for_websocket(websocket: WebSocket):
    """
    Dependency для проверки и получения текущего пользователя через Firebase для WebSocket
    """
    try:
        # Получаем токен из заголовков WebSocket-соединения
        logger.debug(f"websocket.query_params: {websocket.query_params}")
        id_token = websocket.query_params.get('id_token')
        # Проверяем токен в Redis
        claims = await get_token_from_redis(id_token)
        if not claims:
            logger.debug(f"token: {id_token}")
            claims = get_firebase_user(id_token)
            logger.debug(f"claims: {claims}")
            await add_token_to_redis(id_token, claims)

        email = claims.get('email')
        user = await get_user_by_email(email)
        return user
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=401, detail="Could not validate credentials")