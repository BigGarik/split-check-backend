import asyncio
import json
import logging
import uuid
from typing import Dict, Optional

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class RedisWSManager:
    """
    Масштабируемый менеджер WebSocket соединений с использованием Redis Pub/Sub.
    Позволяет отправлять сообщения пользователям, подключенным к любому серверу в кластере.
    """

    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.server_id = str(uuid.uuid4())[:8]  # Уникальный короткий ID сервера
        self.local_connections: Dict[int, WebSocket] = {}  # Локальные соединения: user_id -> WebSocket
        self.pubsub = None  # Redis PubSub клиент
        self.listener_task = None  # Задача прослушивания сообщений

        # Каналы
        self.server_channel = f"ws:server:{self.server_id}"  # Канал для сообщений для этого сервера
        self.broadcast_channel = "ws:broadcast"  # Канал для широковещательных сообщений

        logger.info(f"Инициализирован RedisWSManager с ID сервера: {self.server_id}")

    async def start(self):
        """Запускает прослушивание Redis PubSub каналов."""
        logger.info(f"Запуск RedisWSManager на сервере {self.server_id}")

        # Создаем отдельное подключение для PubSub
        self.pubsub = self.redis_client.client.pubsub()

        # Подписываемся на каналы
        await self.pubsub.subscribe(self.server_channel)  # Для сообщений этому серверу
        await self.pubsub.subscribe(self.broadcast_channel)  # Для широковещательных сообщений

        # Запускаем задачу прослушивания
        self.listener_task = asyncio.create_task(self._message_listener())
        logger.info(f"RedisWSManager на сервере {self.server_id} успешно запущен")

    async def stop(self):
        """Останавливает прослушивание и закрывает подключения."""
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
            self.listener_task = None

        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
            self.pubsub = None

        # Закрываем все локальные соединения
        for websocket in self.local_connections.values():
            try:
                await websocket.close()
            except Exception as e:
                logger.error(f"Ошибка при закрытии WebSocket: {e}")

        self.local_connections.clear()
        logger.info(f"RedisWSManager на сервере {self.server_id} остановлен")

    async def _message_listener(self):
        """Прослушивает сообщения из Redis PubSub и перенаправляет их клиентам."""
        logger.info(f"Запущен слушатель сообщений PubSub на сервере {self.server_id}")
        try:
            while True:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    channel = message["channel"].decode('utf-8')
                    data = message["data"]

                    if isinstance(data, bytes):
                        data = data.decode('utf-8')

                    try:
                        message_data = json.loads(data)

                        if channel == self.broadcast_channel:
                            # Широковещательное сообщение для всех
                            await self._process_broadcast_message(message_data)

                        elif channel == self.server_channel:
                            # Сообщение для конкретного пользователя на этом сервере
                            await self._process_server_message(message_data)

                    except json.JSONDecodeError:
                        logger.error(f"Невозможно декодировать JSON из сообщения: {data}")
                    except Exception as e:
                        logger.error(f"Ошибка при обработке сообщения PubSub: {e}")

                # Небольшая пауза чтобы не загружать CPU
                await asyncio.sleep(0.01)

        except asyncio.CancelledError:
            logger.info(f"Слушатель сообщений PubSub на сервере {self.server_id} остановлен")
        except Exception as e:
            logger.error(f"Неожиданная ошибка в слушателе сообщений PubSub: {e}")

    async def _process_broadcast_message(self, message_data):
        """Обрабатывает широковещательное сообщение."""
        text_message = message_data.get("message")
        if text_message:
            # Отправляем всем локальным подключениям
            for user_id, websocket in self.local_connections.items():
                try:
                    await websocket.send_text(text_message)
                except Exception as e:
                    logger.error(f"Ошибка отправки широковещательного сообщения пользователю {user_id}: {e}")

    async def _process_server_message(self, message_data):
        """Обрабатывает сообщение, адресованное конкретному пользователю на этом сервере."""
        user_id = message_data.get("user_id")
        text_message = message_data.get("message")

        if user_id is not None and text_message:
            if user_id in self.local_connections:
                try:
                    await self.local_connections[user_id].send_text(text_message)
                except Exception as e:
                    logger.error(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
                    # Если соединение разорвано, удаляем его
                    await self._remove_connection(user_id)
            else:
                logger.warning(
                    f"Получено сообщение для пользователя {user_id}, но он не подключен к серверу {self.server_id}")

    async def connect(self, user_id: int, websocket: WebSocket):
        """Принимает новое WebSocket соединение и регистрирует его."""
        await websocket.accept()

        # Сохраняем соединение локально
        self.local_connections[user_id] = websocket

        # Регистрируем информацию о соединении в Redis
        await self.redis_client.set(f"ws:user_server:{user_id}", self.server_id)

        # Сохраняем метаданные
        connection_info = {
            "server_id": self.server_id,
            "connected_at": asyncio.get_event_loop().time()
        }
        await self.redis_client.set(
            f"ws:user_meta:{user_id}",
            json.dumps(connection_info),
            expire=3600  # 1 час TTL на метаданные для автоочистки
        )

        logger.info(
            f"Пользователь {user_id} подключился к серверу {self.server_id}, всего соединений: {len(self.local_connections)}")

    async def disconnect(self, user_id: int):
        """Обрабатывает отключение WebSocket и удаляет информацию о соединении."""
        await self._remove_connection(user_id)

    async def _remove_connection(self, user_id: int):
        """Удаляет информацию о соединении из локального хранилища и Redis."""
        if user_id in self.local_connections:
            del self.local_connections[user_id]

        # Удаляем из Redis информацию о сервере этого пользователя
        await self.redis_client.client.delete(f"ws:user_server:{user_id}")
        await self.redis_client.client.delete(f"ws:user_meta:{user_id}")

        logger.info(
            f"Пользователь {user_id} отключился от сервера {self.server_id}, осталось соединений: {len(self.local_connections)}")

    async def send_personal_message(self, message: str, user_id: int):
        """Отправляет сообщение конкретному пользователю, независимо от того, к какому серверу он подключен."""
        # Проверяем, на каком сервере находится пользователь
        server_id = await self.redis_client.get(f"ws:user_server:{user_id}")

        if not server_id:
            logger.warning(f"Пользователь {user_id} не подключен ни к одному серверу")
            return False

        # Если пользователь на этом сервере, отправляем напрямую
        if server_id == self.server_id and user_id in self.local_connections:
            try:
                await self.local_connections[user_id].send_text(message)
                return True
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения пользователю {user_id} локально: {e}")
                await self._remove_connection(user_id)
                return False
        else:
            # Иначе публикуем сообщение в Redis для нужного сервера
            message_data = {
                "user_id": user_id,
                "message": message,
                "source_server": self.server_id
            }

            channel = f"ws:server:{server_id}"
            await self.redis_client.client.publish(channel, json.dumps(message_data))
            return True

    async def broadcast(self, message: str):
        """Отправляет сообщение всем подключенным пользователям на всех серверах."""
        # Публикуем сообщение в канал широковещания
        message_data = {
            "message": message,
            "source_server": self.server_id
        }

        await self.redis_client.client.publish(self.broadcast_channel, json.dumps(message_data))

        # Также отправляем всем локальным клиентам напрямую для снижения задержки
        for user_id, websocket in self.local_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Ошибка отправки широковещательного сообщения пользователю {user_id}: {e}")
                # Если соединение разорвано, планируем его удаление
                asyncio.create_task(self._remove_connection(user_id))

    async def get_active_connections_count(self) -> Dict[str, int]:
        """Возвращает количество активных соединений на всех серверах."""
        # Получаем все ключи user_server
        keys = await self.redis_client.client.keys("ws:user_server:*")

        # Группируем по серверам
        servers = {}
        for key in keys:
            server = await self.redis_client.get(key.decode('utf-8'))
            if server not in servers:
                servers[server] = 0
            servers[server] += 1

        return servers

    async def get_user_connection_info(self, user_id: int) -> Optional[dict]:
        """Возвращает информацию о соединении пользователя."""
        meta_json = await self.redis_client.get(f"ws:user_meta:{user_id}")
        if meta_json:
            try:
                return json.loads(meta_json)
            except json.JSONDecodeError:
                return None
        return None