import logging
import os
import uuid

from dotenv import load_dotenv
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from app.auth import verify_token
from app.database import get_db, redis_client

load_dotenv()

router_ws = APIRouter()

logger = logging.getLogger(__name__)


# Менеджер для работы с WebSocket через Redis
class RedisConnectionManager:
    def __init__(self, redis):
        self.redis = redis
        self.prefix = "ws_connections:"  # Префикс для хранения сессий в Redis
        self.active_connections = {}  # Локальный словарь для хранения WebSocket по session_id

    async def connect(self, user_id: str, websocket: WebSocket):
        # Создаем уникальный идентификатор сессии
        session_id = str(uuid.uuid4())

        # Сохраняем session_id в Redis для пользователя (user_id -> session_id)
        await self.redis.set(f"{self.prefix}{user_id}", session_id)

        # Сохраняем WebSocket соединение в локальном словаре по session_id
        self.active_connections[session_id] = websocket

        # Принимаем соединение
        await websocket.accept()

        return session_id

    async def disconnect(self, session_id: str, user_id: str):
        # Удаляем WebSocket соединение из локального словаря
        self.active_connections.pop(session_id, None)

        # Удаляем сессию пользователя из Redis
        await self.redis.delete(f"{self.prefix}{user_id}")

    async def send_personal_message(self, message: str, user_id: str):
        # Получаем session_id пользователя из Redis
        session_id = await self.redis.get(f"{self.prefix}{user_id}")
        if session_id and session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_text(message)

    async def broadcast(self, message: str):
        # Широковещательная рассылка всем подключенным пользователям
        for session_id, websocket in self.active_connections.items():
            await websocket.send_text(message)


# Создаем экземпляр Redis менеджера
ws_manager = RedisConnectionManager(redis_client)


@router_ws.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Depends(verify_token), db: Session = Depends(get_db)):
    # Аутентификация пользователя и получение user_id (например, email)
    user = verify_token(token, db)
    user_id = user.email  # Используем email как идентификатор пользователя

    # Сохраняем WebSocket-соединение и создаем session_id
    session_id = await ws_manager.connect(user_id, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received message from {user_id}: {data}")
    except WebSocketDisconnect:
        # Удаление соединения при отключении пользователя
        await ws_manager.disconnect(session_id, user_id)
        print(f"User {user_id} disconnected")


if __name__ == '__main__':
    pass
