from datetime import datetime, timedelta

from fastapi.security import OAuth2PasswordBearer
from loguru import logger
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.websockets import WebSocket, WebSocketDisconnect

from src.auth.dependencies import get_firebase_user
from src.redis import redis_client
from src.redis.utils import get_token_from_redis
from src.repositories.user import get_user_by_email

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# async def get_current_user(token: str = Depends(oauth2_scheme)):
#     try:
#         email, _ = await verify_token(settings.access_secret_key, token=token)
#         user = await get_user_by_email(email)
#         if not user:
#             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
#         return user
#     except JWTError:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


async def get_current_user(request: Request):
    """
    Dependency для проверки и получения текущего пользователя через Firebase
    """
    logger.debug(f"request: {request}")
    try:
        claims = await get_token_from_redis(request)
        if not claims:
            claims = get_firebase_user(request)

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

        email = claims.get('email')
        user = await get_user_by_email(email)
        return user
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=401, detail="Could not validate credentials")


async def get_token_websocket(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        raise WebSocketDisconnect(code=1008)
    return token
