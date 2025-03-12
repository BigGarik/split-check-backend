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
    logger.debug(f"websocket.headers: {websocket.headers}")
    try:
        # Пытаемся верифицировать токен
        # user = await get_current_user(token)
        user_id = user.id
        # Подключаем пользователя
        await ws_manager.connect(user_id, websocket)
        try:
            while True:
                # Получаем данные от клиента
                data = await websocket.receive_text()
                # Логируем полученные данные
                logger.debug(f"Received message from {user_id}: {data}")

                # Пример: отправляем сообщение обратно пользователю
                # await ws_manager.send_personal_message(f"Echo: {data}", user_id)

                # Пример: отправляем сообщение всем подключённым пользователям
                # await ws_manager.broadcast(f"{user_id}: {data}")

        except WebSocketDisconnect:
            # Отключаем пользователя при разрыве соединения
            await ws_manager.disconnect(user_id)
            logger.debug(f"User {user_id} disconnected")
    except JWTError as e:
        # Обработка ошибок JWT
        logger.error(f"JWT error: {e}")
        await websocket.accept()
        await websocket.send_json({"error": "unauthorized", "message": "Invalid token. Redirect to login page."})
        await websocket.close()
    except HTTPException as e:
        # Обработка HTTP ошибок
        logger.error(f"HTTP error: {e.detail}")
        await websocket.accept()
        await websocket.send_json({"error": "unauthorized", "message": f"{e.detail}. Redirect to login page."})
        await websocket.close()
    except Exception as e:
        # Логируем и закрываем соединение при любой другой ошибке
        logger.error(f"Unexpected error: {e}")
        await websocket.close()
