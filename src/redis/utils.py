import json
import logging
from datetime import datetime, timedelta

from starlette.exceptions import HTTPException

from src.redis import redis_client

logger = logging.getLogger(__name__)


async def get_token_from_redis(id_token):
    """
    Get uid from JWT token and save claims to Redis
    """
    try:
        if not id_token:
            return None

        token = await redis_client.get(f"firebase_idtoken_{id_token}")
        if not token:
            return None

        token_data = json.loads(token)
        logger.debug(f"token_data_from_redis: {token_data}")

        return token_data
    except Exception as e:
        logger.exception(e)
        return None


async def add_token_to_redis(id_token, claims):
    try:
        # Получаем timestamp из токена и преобразуем в datetime
        exp_date = datetime.fromtimestamp(claims.get('exp'))
        logger.debug(f"exp_date: {exp_date}")

        # Вычисляем оставшееся время действия токена
        remaining_time = exp_date - datetime.now()
        # Устанавливаем TTL как минимальное между 5 минутами и оставшимся временем токена
        exp = min(remaining_time, timedelta(minutes=5))

        # Проверяем, что TTL положительный
        if exp.total_seconds() > 0:
            await redis_client.set(
                key=f"firebase_idtoken_{id_token}",
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
