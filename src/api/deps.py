from fastapi import Request, HTTPException
from loguru import logger
from starlette.websockets import WebSocket, WebSocketDisconnect

from src.auth.dependencies import get_firebase_user
from src.redis.utils import get_token_from_redis, add_token_to_redis
from src.repositories.user import get_user_by_email


# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


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
    try:
        claims = await get_token_from_redis(request)
        if not claims:
            token = request.headers.get('Authorization')
            claims = get_firebase_user(request)
            await add_token_to_redis(token, claims)

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
