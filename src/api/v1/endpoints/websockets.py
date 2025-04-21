import logging
from typing import Annotated

from fastapi import Depends, APIRouter
from jose import JWTError
from starlette.exceptions import HTTPException
from starlette.websockets import WebSocket, WebSocketDisconnect

from src.api.deps import get_current_user_for_websocket
from src.models import User
from src.websockets.manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws", name="websocket_endpoint")
async def websocket_endpoint(websocket: WebSocket,
                             user: Annotated[User, Depends(get_current_user_for_websocket)]):
    logger.debug(f"websocket.headers: {websocket.headers}", extra={"current_user_id": user.id})
    try:
        user_id = user.id
        # Подключаем пользователя
        await ws_manager.connect(user_id, websocket)
        try:
            while True:
                # Обработка входящих сообщений от клиента
                data = await websocket.receive_text()
                logger.debug(f"Received message from {user_id}: {data}")

        except WebSocketDisconnect:
            # Отключаем пользователя при разрыве соединения
            await ws_manager.disconnect(user_id)
            logger.info(f"WebSocket disconnected for user {user_id}")
    except JWTError as e:
        # Обработка ошибок JWT
        logger.error(f"JWT error: {e}", extra={"current_user_id": user.id})
        await websocket.accept()
        await websocket.send_json({"error": "unauthorized", "message": "Invalid token. Redirect to login page."})
        await websocket.close()
    except HTTPException as e:
        # Обработка HTTP ошибок
        logger.error(f"HTTP error: {e.detail}", extra={"current_user_id": user.id})
        await websocket.accept()
        await websocket.send_json({"error": "unauthorized", "message": f"{e.detail}. Redirect to login page."})
        await websocket.close()
    except Exception as e:
        # Логируем и закрываем соединение при любой другой ошибке
        logger.error(f"Unexpected error: {e}", extra={"current_user_id": user.id})
        await websocket.close()
