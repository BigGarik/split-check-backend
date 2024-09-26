import logging
import os
import asyncio
import nats
from dotenv import load_dotenv

from app.routers.ws import ws_manager

load_dotenv()
logger = logging.getLogger(__name__)

#Константы для названий очередей
IMAGE_PROCESS_QUEUE = "image_process_queue"


nats_client = None


async def connect_to_nats():
    global nats_client
    nats_client = await nats.connect("nats://127.0.0.1:4222")
    await create_subscriptions()


async def message_handler(msg):
    data = msg.data.decode()
    print(f"Broadcast message received: {data}")
    ws_manager.broadcast(data)


async def create_subscriptions():
    global nats_client
    await nats_client.subscribe("broadcast", cb=message_handler)


# Асинхронная функция для отправки сообщений в NATS
async def send_message_to_nats(subject: str, message: str):
    global nats_client
    await nats_client.publish(subject, message.encode())  # Отправка сообщения
    await nats_client.flush()
    await nats_client.close()


async def create_image_process_task(message: str):
    await send_message_to_nats(IMAGE_PROCESS_QUEUE, message)


# Асинхронная функция для получения сообщений из NATS
# async def consume_messages_from_nats():
#     # Подключаемся к NATS
#     nc = await nats.connect("nats://127.0.0.1:4222")
#
#     async def message_handler(msg):
#         subject = msg.subject
#         data = msg.data.decode()
#         print(f"Received a message on '{subject}': {data}")
#
#     # Подписываемся на сообщения из топика "updates"
#     await nc.subscribe("updates", cb=message_handler)
#
#     # Не закрываем соединение, чтобы слушать сообщения
#     while True:
#         await asyncio.sleep(1)


if __name__ == '__main__':
    pass
