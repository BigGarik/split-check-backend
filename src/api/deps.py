from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from starlette import status
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.websockets import WebSocket, WebSocketDisconnect
from loguru import logger
from src.auth.dependencies import get_firebase_user
from src.config.settings import settings
from src.core.security import verify_token
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
    try:
        claims = get_firebase_user(request)
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
