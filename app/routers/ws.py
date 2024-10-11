import asyncio
import os

from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from loguru import logger

from dotenv import load_dotenv
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db

load_dotenv()

access_secret_key = os.getenv('ACCESS_SECRET_KEY')
refresh_secret_key = os.getenv('REFRESH_SECRET_KEY')
access_token_expire_minutes = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES'))
refresh_token_expire_days = int(os.getenv('REFRESH_TOKEN_EXPIRE_MINUTES'))
algorithm = os.getenv('ALGORITHM')

router_ws = APIRouter()


# Менеджер для работы с WebSocket
class WSConnectionManager:
    def __init__(self):
        self.active_connections = {}  # Локальный словарь для хранения WebSocket по session_id

    async def connect(self, user_id: str, websocket: WebSocket):
        # Принимаем соединение
        await websocket.accept()
        # Сохраняем WebSocket соединение в локальном словаре по user_id
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected to WebSocket")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected from WebSocket")

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            await websocket.send_text(message)

    async def broadcast(self, message: str):
        # Широковещательная рассылка всем подключенным пользователям
        for user_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")


ws_manager = WSConnectionManager()


async def get_token_websocket(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        raise WebSocketDisconnect(code=1008)
    return token


@router_ws.websocket("/ws-test")
async def websocket_endpoint_test(websocket: WebSocket, token: str = Depends(get_token_websocket)):
    await websocket.accept()
    try:
        payload = jwt.decode(token, access_secret_key, algorithms=[algorithm])
        username: str = payload.get("sub")
        if username is None:
            await websocket.close(code=1008)
        else:
            await websocket.send_json({"message": f"Hello, {username}"})
    except jwt.JWTError:
        await websocket.close(code=1008)
    finally:
        await websocket.close()


@router_ws.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket,
                             token: str = Depends(get_token_websocket),
                             db: Session = Depends(get_db)):
    try:
        # Пытаемся верифицировать токен
        user = await get_current_user(token, db)
        user_id = user.email  # Используем email пользователя
        # Подключаем пользователя
        await ws_manager.connect(user_id, websocket)
        try:
            while True:
                # Получаем данные от клиента
                data = await websocket.receive_text()
                logger.info(f"Received message ws from {user_id}: {data}")
                # Отправляем сообщение всем подключённым пользователям
                # await ws_manager.broadcast(f"{user_id}: {data}")
        except WebSocketDisconnect:
            # Отключаем пользователя при разрыве соединения
            await ws_manager.disconnect(user_id)
            logger.info(f"User {user_id} disconnected")
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


if __name__ == '__main__':
    pass
