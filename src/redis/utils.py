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
            raise HTTPException(status_code=400, detail='Token must be provided')

        # Remove 'Bearer ' if present
        # token = token.replace('Bearer ', '')

        # Decode JWT without verification to get uid

        decoded = jwt.decode(token, options={"verify_signature": False})


        uid = decoded.get('uid')

        if not uid:
            raise HTTPException(status_code=400, detail='Invalid token format')

        token_data = await redis_client.get(f"token:{uid}")
        if not token_data:
            return None
        return token_data

    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail='Invalid token')
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=401, detail='Unauthorized')


async def add_token_to_redis(claims):
    try:
        # Получаем timestamp из токена и преобразуем в datetime
        exp_date = datetime.fromtimestamp(claims.get('exp'))
        uid = claims.get('uid')

        # Вычисляем оставшееся время действия токена
        remaining_time = exp_date - datetime.now()
        # Устанавливаем TTL как минимальное между 10 минутами и оставшимся временем токена
        exp = min(remaining_time, timedelta(minutes=10))

        # Проверяем, что TTL положительный
        if exp.total_seconds() > 0:
            await redis_client.set(
                key=f"token:{uid}",
                value=claims,
                ex=int(exp.total_seconds())  # Redis ожидает TTL в секундах
            )
        else:
            # Токен уже истёк
            raise HTTPException(status_code=401, detail="Token expired")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=401, detail="Could not validate credentials")
