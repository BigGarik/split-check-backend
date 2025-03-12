import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


# Менеджер для работы с WebSocket
class WSConnectionManager:
    def __init__(self):
        self.active_connections = {}  # Локальный словарь для хранения WebSocket по session_id

    async def connect(self, user_id: int, websocket: WebSocket):
        """Принимаем новое WebSocket соединение и сохраняем его."""
        await websocket.accept()
        # Сохраняем WebSocket соединение в локальном словаре по user_id
        self.active_connections[user_id] = websocket
        logger.debug(self.active_connections)

    async def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: str, user_id: int):
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