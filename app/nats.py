import logging
import os
import asyncio
import nats
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


# Асинхронная функция для отправки сообщений в NATS
async def send_message_to_nats(subject: str, message: str):
    nc = await nats.connect("nats://127.0.0.1:4222")
    await nc.publish(subject, message.encode())  # Отправка сообщения
    await nc.flush()
    await nc.close()


# Асинхронная функция для получения сообщений из NATS
async def consume_messages_from_nats():
    # Подключаемся к NATS
    nc = await nats.connect("nats://127.0.0.1:4222")

    async def message_handler(msg):
        subject = msg.subject
        data = msg.data.decode()
        print(f"Received a message on '{subject}': {data}")

    # Подписываемся на сообщения из топика "updates"
    await nc.subscribe("updates", cb=message_handler)

    # Не закрываем соединение, чтобы слушать сообщения
    while True:
        await asyncio.sleep(1)


if __name__ == '__main__':
    pass
