import os

from dotenv import load_dotenv
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from jose import JWTError
from loguru import logger

from app.auth import get_current_user
from app.websocket_manager import WSConnectionManager

load_dotenv()

access_secret_key = os.getenv('ACCESS_SECRET_KEY')
refresh_secret_key = os.getenv('REFRESH_SECRET_KEY')
access_token_expire_minutes = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES'))
refresh_token_expire_days = int(os.getenv('REFRESH_TOKEN_EXPIRE_MINUTES'))
algorithm = os.getenv('ALGORITHM')


router = APIRouter(prefix="/ws", tags=["ws"])

ws_manager = WSConnectionManager()


async def get_token_websocket(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        raise WebSocketDisconnect(code=1008)
    return token


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket,
                             token: str = Depends(get_token_websocket)):
    try:
        # Пытаемся верифицировать токен
        user = await get_current_user(token)
        user_id = user.id
        # Подключаем пользователя
        await ws_manager.connect(user_id, websocket)
        try:
            while True:
                # Получаем данные от клиента
                data = await websocket.receive_text()
                # Отправляем сообщение всем подключённым пользователям
                # await ws_manager.broadcast(f"{user_id}: {data}")
        except WebSocketDisconnect:
            # Отключаем пользователя при разрыве соединения
            await ws_manager.disconnect(user_id)
    except JWTError as e:
        # Обработка ошибок JWT - отправляем сообщение о неудачной аутентификации
        await websocket.accept()
        await websocket.send_json({"error": "unauthorized", "message": "Invalid token. Redirect to login page."})
        await websocket.close()
    except HTTPException as e:
        # Если ошибка HTTP - перенаправляем на страницу логина через сообщение
        await websocket.accept()
        await websocket.send_json({"error": "unauthorized", "message": f"{e.detail}. Redirect to login page."})
        await websocket.close()
    except Exception as e:
        # Любая другая ошибка
        logger.error(f"Error occurred: {e}")
        await websocket.close()
