import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


# Создаем прокси-класс для WebSocket менеджера
class LazyWSManager:
    def __init__(self):
        self._real_manager = None
        self.active_connections = {}  # Локальный словарь для резервного режима

    def set_real_manager(self, manager):
        self._real_manager = manager
        logger.info(f"Real WebSocket manager set: {type(manager).__name__}")

    async def connect(self, user_id: int, websocket: WebSocket):
        if self._real_manager is None:
            # Временное локальное хранение, если Redis-менеджер ещё не инициализирован
            await websocket.accept()
            self.active_connections[user_id] = websocket
            logger.warning("Using local WebSocket storage (Redis manager not initialized)")
        else:
            await self._real_manager.connect(user_id, websocket)

    async def disconnect(self, user_id: int):
        if self._real_manager is None:
            if user_id in self.active_connections:
                del self.active_connections[user_id]
                logger.warning(f"Disconnected user {user_id} from local storage")
        else:
            await self._real_manager.disconnect(user_id)

    async def send_personal_message(self, message: str, user_id: int):
        if self._real_manager is None:
            if user_id in self.active_connections:
                await self.active_connections[user_id].send_text(message)
                logger.warning(f"Message sent to user {user_id} via local storage")
            else:
                logger.warning(f"User {user_id} not found in local storage, message not sent")
        else:
            await self._real_manager.send_personal_message(message, user_id)

    async def broadcast(self, message: str):
        if self._real_manager is None:
            for user_id, websocket in self.active_connections.items():
                try:
                    await websocket.send_text(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}: {e}")
            logger.warning(f"Broadcast message sent to {len(self.active_connections)} users via local storage")
        else:
            await self._real_manager.broadcast(message)


# Создаем единый экземпляр прокси-менеджера
ws_manager = LazyWSManager()