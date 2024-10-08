# redis.py
import asyncio
import json
import os
from loguru import logger

import redis.asyncio as aioredis

from app.routers.ws import ws_manager
from external_services.tasks import recognize_image

WS_BROAD_CAST_REDIS_CHANNEL = "wsocket_msg_broadcast"
WS_TASK_PROCESS_CHANNEL = "ws_task_process_queue"

topic_semaphore = asyncio.Semaphore(5)  # Ограничиваем до 5 одновременно работающих консьюмеров
queue_semaphore = asyncio.Semaphore(10)  # Ограничиваем до 5 одновременно работающих консьюмеров


async def setup_redis():
    global redis_client
    # redis_url = f"redis://{os.getenv('REDIS_USERNAME')}:{os.getenv('REDIS_PASSWORD')}@{os.getenv('REDIS_HOST')}:6379"
    redis_url = f"redis://{os.getenv('REDIS_HOST')}:6379"

    redis_client = await aioredis.Redis.from_url(url=redis_url, encoding="utf-8", decode_responses=True)

    # Подписываемся на сообщения из топика (которые будут получать все инстансы)
    asyncio.create_task(redis_topic_subscribe())
    # Подписываемся на сообщения из очереди (которые будут получать все инстансы)
    asyncio.create_task(redis_queue_subscribe())


async def redis_topic_consumer(message: str):
    async with topic_semaphore:  # Ограничиваем количество одновременно работающих консьюмеров
        logger.info(f"Sending message to WS: {message}")

        # Декодируем сообщение
        msg = json.loads(message)

        # Получаем идентификатор пользователя
        # TODO получаем всех пользователей подписанных на этот чек
        user_id = msg.get("target_user_id")

        # Проверяем, подключен ли пользователь через WebSocket
        if user_id in ws_manager.active_connections:
            # Получаем WebSocket-соединение пользователя
            websocket = ws_manager.active_connections[user_id]

            try:
                # Отправляем сообщение пользователю через WebSocket
                await websocket.send_text(json.dumps(msg["payload"]))
                logger.info(f"Message sent to user {user_id} via WebSocket")
            except Exception as e:
                logger.error(f"Failed to send message to WebSocket user {user_id}: {e}")
        else:
            logger.warning(f"User {user_id} is not connected to WebSocket")


async def redis_topic_subscribe():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(WS_BROAD_CAST_REDIS_CHANNEL)
    async for message in pubsub.listen():
        if message["type"] == "message":
            logger.info(f"Received message for broadcasting: {message['data']}")
            await redis_topic_consumer(message['data'])


async def redis_topic_publish(message: str):
    await redis_client.publish(WS_BROAD_CAST_REDIS_CHANNEL, message)


# Методы для работы с очередью
async def redis_queue_consumer(message: str):
    async with queue_semaphore:  # Ограничиваем количество одновременно работающих консьюмеров
        logger.info(f"Processing message from queue: {message}")

        # Парсим сообщение
        msg = json.loads(message)

        if msg["type"] == "image_recognition":
            user_id = msg["user_id"]
            check_uuid = msg["payload"].get("check_uuid", "")
            file_location = msg["payload"].get("file_location", "")

            # Обработка изображения (симуляция оцифровки чека)
            result_json = await recognize_image(check_uuid, user_id, file_location, redis_client)

            logger.info(f"Image recognized: {result_json}")

            # Публикуем результат оцифровки в Redis
            await redis_topic_publish(json.dumps(result_json))
        else:
            logger.warning(f"Unknown message type: {msg['type']}")


async def redis_queue_subscribe():
    while True:
        message = await redis_client.lpop(WS_TASK_PROCESS_CHANNEL)  # Извлекаем из начала списка
        if message:
            await redis_queue_consumer(message)  # Обработка сообщения
        else:
            await asyncio.sleep(0.2)  # Ждем перед повторной проверкой


async def redis_queue_publish(message: str):
    await redis_client.rpush(WS_TASK_PROCESS_CHANNEL, message)
