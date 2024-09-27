import asyncio
import logging
import os
import uuid
from datetime import datetime

from dotenv import load_dotenv
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
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
        self.time_task = None  # Задача для отправки времени

    async def connect(self, user_id: str, websocket: WebSocket):
        # Создаем уникальный идентификатор сессии
        session_id = str(uuid.uuid4())

        # Сохраняем session_id в Redis для пользователя (user_id -> session_id)
        await self.redis.set(f"{self.prefix}{user_id}", session_id)

        # Сохраняем WebSocket соединение в локальном словаре по session_id
        self.active_connections[session_id] = websocket

        # Если задача отправки времени ещё не запущена, запускаем её
        # if not self.time_task:
        #     self.time_task = asyncio.create_task(self.send_time_periodically())

        return session_id

    async def disconnect(self, session_id: str, user_id: str):
        # Удаляем WebSocket соединение из локального словаря
        self.active_connections.pop(session_id, None)

        # Удаляем сессию пользователя из Redis
        await self.redis.delete(f"{self.prefix}{user_id}")

        # Если больше нет подключений, отменяем задачу отправки времени
        if not self.active_connections:
            if self.time_task:
                self.time_task.cancel()
                self.time_task = None

    async def send_time_periodically(self):
        try:
            while True:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                await self.broadcast(f"Current time: {current_time}")
                await asyncio.sleep(1)  # Отправляем время каждые 1 секунду
        except asyncio.CancelledError:
            print("Task send_time_periodically cancelled")

    async def send_personal_message(self, message: str, user_id: str):
        # Получаем session_id пользователя из Redis
        session_id = await self.redis.get(f"{self.prefix}{user_id}")
        if session_id and session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_text(message)
            except Exception as e:
                print(f"Error sending message to session {session_id}: {e}")
        else:
            print(f"Session not found for user_id: {user_id}")

    async def broadcast(self, message: str):
        # Широковещательная рассылка всем подключенным пользователям
        for session_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                print(f"Error sending message to session {session_id}: {e}")


# Создаем экземпляр Redis менеджера
ws_manager = RedisConnectionManager(redis_client)


async def send_time_periodically():
    while True:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        await ws_manager.broadcast(f"Current time: {current_time}")
        await asyncio.sleep(1)  # Отправляем время каждые 1 секунду


@router_ws.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    # Пробуем принять соединение сразу
    await websocket.accept()

    try:
        # Пытаемся верифицировать токен
        user = await get_current_user(token, db)

        # Если токен валиден, продолжаем работу с WebSocket
        user_id = user.email  # Используем email пользователя

        # Подключаем пользователя
        session_id = await ws_manager.connect(user_id, websocket)
        print(session_id)
        try:
            while True:
                # Получаем данные от клиента
                data = await websocket.receive_text()
                print(f"Received message from {user_id}: {data}")
                # Отправляем сообщение всем подключённым пользователям
                await ws_manager.broadcast(f"{user_id}: {data}")
        except WebSocketDisconnect:
            # Отключаем пользователя
            await ws_manager.disconnect(session_id, user_id)
            print(f"User {user_id} disconnected")

    except HTTPException as e:
        # Если аутентификация не удалась, возвращаем сообщение об ошибке и закрываем соединение
        await websocket.send_text(f"Authentication failed: {e.detail}")
        await websocket.close()

    except Exception as e:
        # Любая другая ошибка
        print(f"Error occurred: {e}")
        await websocket.close()


if __name__ == '__main__':
    pass
