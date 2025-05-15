from typing import Optional

from fastapi import Request, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from starlette.websockets import WebSocket

from src.auth.dependencies import get_firebase_user
from src.config import ACCESS_SECRET_KEY
from src.core.security import verify_token
from src.redis.utils import get_token_from_redis, add_token_to_redis
from src.repositories.user import get_user_by_email, unmark_user_as_deleted
import logging

logger = logging.getLogger(__name__)

# Используем обе схемы аутентификации
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token", auto_error=False)
http_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
        request: Request,
        oauth2_token: Optional[str] = Depends(oauth2_scheme),
        http_auth: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer)
):
    """
    Dependency для проверки и получения текущего пользователя.
    Теперь поддерживает:
    - Куки (access_token)
    - OAuth2
    - Bearer токен
    - Firebase токен
    """
    try:
        logger.debug(f"oauth2_token: {oauth2_token}")
        logger.debug(f"http_auth: {http_auth}")

        firebase_token = None
        email = None

        # 🥇 Приоритет 0: Кука
        cookie_token = request.cookies.get('access_token')
        if cookie_token:
            logger.debug("Приоритет 0: access_token из куки")
            email, _ = await verify_token(ACCESS_SECRET_KEY, token=cookie_token)

        # 🥈 Приоритет 1: OAuth2 токен
        elif oauth2_token:
            logger.debug("Приоритет 1: OAuth2 токен")
            email, _ = await verify_token(ACCESS_SECRET_KEY, token=oauth2_token)

        # 🥉 Приоритет 2: Firebase токен из заголовка
        elif http_auth:
            logger.debug("Приоритет 2: Firebase токен")
            firebase_token = http_auth.credentials
            claims = await get_token_from_redis(firebase_token)
            if not claims:
                claims = get_firebase_user(firebase_token)
                await add_token_to_redis(firebase_token, claims)
            email = claims.get('email')

        # 🟡 Приоритет 3: Authorization header вручную
        else:
            auth_header = request.headers.get('Authorization')
            if auth_header:
                logger.debug("Приоритет 3: Authorization header")
                if auth_header.startswith('Bearer '):
                    firebase_token = auth_header.replace('Bearer ', '')
                else:
                    firebase_token = auth_header

                claims = await get_token_from_redis(firebase_token)
                if not claims:
                    claims = get_firebase_user(firebase_token)
                    await add_token_to_redis(firebase_token, claims)

                email = claims.get('email')
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Не предоставлен токен авторизации",
                    headers={"WWW-Authenticate": "Bearer"}
                )

        # 🔐 Ищем пользователя по email
        user = await get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Пользователь не найден"
            )

        if user.is_soft_deleted:
            await unmark_user_as_deleted(user)

        return user

    # 👇 Оставляем твои исключения без изменений
    except HTTPException as he:
        if request.url.path in ['/docs', '/redoc', '/openapi.json']:
            return None
        raise he
    except JWTError:
        if request.url.path in ['/docs', '/redoc', '/openapi.json']:
            return None
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        if request.url.path in ['/docs', '/redoc', '/openapi.json']:
            return None
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не удалось проверить учетные данные",
            headers={"WWW-Authenticate": "Bearer"}
        )



async def get_current_user_for_websocket(websocket: WebSocket):
    """
    Dependency для проверки пользователя через OAuth2 или Firebase для WebSocket
    """
    try:
        # Получаем токены из параметров WebSocket
        id_token = websocket.query_params.get('id_token')
        token = websocket.query_params.get('token')

        if token:
            # OAuth2 токен
            email, _ = await verify_token(ACCESS_SECRET_KEY, token=token)
        elif id_token:
            # Firebase токен
            claims = await get_token_from_redis(id_token)
            if not claims:
                claims = get_firebase_user(id_token)
                await add_token_to_redis(id_token, claims)

            email = claims.get('email')
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Не предоставлен токен авторизации"
            )

        user = await get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Пользователь не найден"
            )

        return user
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не удалось проверить учетные данные"
        )


# Дополнительная функция для защиты эндпоинтов
def require_auth(current_user=Depends(get_current_user)):
    """
    Проверяет наличие аутентифицированного пользователя
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется аутентификация",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return current_user