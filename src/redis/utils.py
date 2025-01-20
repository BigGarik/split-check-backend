import json
from datetime import datetime, timedelta

import jwt
from loguru import logger
from starlette.exceptions import HTTPException
from starlette.requests import Request

from src.redis import redis_client


async def get_token_from_redis(request: Request):
    """
    Get uid from JWT token and save claims to Redis
    """
    try:
        # Get token from headers
        token = request.headers.get('Authorization')
        logger.debug(f"token: {token}")
        if not token:
            return None

        # Remove 'Bearer ' if present
        # token = token.replace('Bearer ', '')

        # Decode JWT without verification to get uid

        # decoded = jwt.decode(token, options={"verify_signature": False})

        token_data = json.loads(await redis_client.get(f"firebase_idtoken_{token}"))
        logger.debug(f"token_data: {token_data}")
        if not token_data:
            return None
        return token_data
    except Exception as e:
        logger.exception(e)
        return None


async def add_token_to_redis(token, claims):
    try:
        # Получаем timestamp из токена и преобразуем в datetime
        exp_date = datetime.fromtimestamp(claims.get('exp'))
        logger.debug(f"exp_date: {exp_date}")

        # Вычисляем оставшееся время действия токена
        remaining_time = exp_date - datetime.now()
        logger.debug(f"remaining_time: {remaining_time}")
        # Устанавливаем TTL как минимальное между 5 минутами и оставшимся временем токена
        exp = min(remaining_time, timedelta(minutes=5))

        # Проверяем, что TTL положительный
        if exp.total_seconds() > 0:
            await redis_client.set(
                key=f"firebase_idtoken_{token}",
                value=json.dumps(claims),
                expire=int(exp.total_seconds())  # Redis ожидает TTL в секундах
            )
        else:
            # Токен уже истёк
            raise HTTPException(status_code=401, detail="Token expired")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=401, detail="Could not validate credentials")
