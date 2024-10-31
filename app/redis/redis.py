# redis.py

import os

from dotenv import load_dotenv
from .queue_processor import QueueProcessor
from .redis_client import RedisClient

load_dotenv()


# Инициализация Redis клиента
redis_client = RedisClient(host=os.getenv('REDIS_HOST'), port=6379, db=1)

# Инициализация процессора очереди
queue_processor = QueueProcessor(redis_client, "task_queue")

# Экспортируем для использования в других модулях
__all__ = ["redis_client", "queue_processor"]
