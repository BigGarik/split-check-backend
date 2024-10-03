import asyncio
import logging

from dotenv import load_dotenv
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db

load_dotenv()

router_ws = APIRouter()

logger = logging.getLogger(__name__)


# Менеджер для работы с WebSocket
class WSConnectionManager:
    def __init__(self):
        self.active_connections = {}  # Локальный словарь для хранения WebSocket по session_id

    async def connect(self, user_id: str, websocket: WebSocket):
        # Принимаем соединение
        await websocket.accept()
        # Сохраняем WebSocket соединение в локальном словаре по user_id
        self.active_connections[user_id] = websocket

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, user_id: str):
        if user_id and user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            await websocket.send_text(message)

    async def broadcast(self, message: str):
        # Широковещательная рассылка всем подключенным пользователям
        for session_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                print(f"Error sending message to session {session_id}: {e}")


# Создаем экземпляр Redis менеджера
ws_manager = WSConnectionManager()


# Обработчик сообщений из очереди Redis
# def redis_message_handler(message):
#     print("recieved next msg " + message)
#     if message and message['type'] == 'message':
#         msg = message['data'].decode()
#
#         recipient = msg['target_user_id']
#         payload = msg['payload']
#
#         print("message recieved: recipient is " + recipient + " and payload is " + payload)
#         ws_manager.send_personal_message(payload, recipient)
#
#
# # Подписываемся на рассылку сообщений из топика redis
# async def subscribe_to_redis_msg_bus_channel():
#     # Подписка на канал сообщений msg_bus
#     await ws_broadcast_redis_manager.subscribe(redis_message_handler)
#
#     # Запускаем слушатель Redis в отдельной задаче, запускается каждый раз когда в очередь с названием to_user_msgs приходит сообщение
#     asyncio.create_task(redis_message_handler())


@router_ws.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    try:
        # Пытаемся верифицировать токен
        user = await get_current_user(token, db)

        # Если токен валиден, продолжаем работу с WebSocket
        user_id = user.email  # Используем email пользователя

        # Подключаем пользователя
        await ws_manager.connect(user_id, websocket)
        # print(session_id)
        try:
            while True:
                # Получаем данные от клиента
                data = await websocket.receive_text()
                print(f"Received message ws from {user_id}: {data}")
                # Отправляем сообщение всем подключённым пользователям
                # await ws_manager.broadcast(f"{user_id}: {data}")
        except WebSocketDisconnect:
            # Отключаем пользователя
            await ws_manager.disconnect(user_id)
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
