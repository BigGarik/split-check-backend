from .queue_processor import QueueProcessor
from .redis_client import RedisClient
from ..config import REDIS_HOST, REDIS_PORT, REDIS_DB

# Инициализация Redis клиента
redis_client = RedisClient(host=REDIS_HOST,
                           port=REDIS_PORT,
                           db=REDIS_DB)

# Инициализация процессора очереди
queue_processor = QueueProcessor(redis_client, "task_queue")

# Экспортируем для использования в других модулях
__all__ = ["redis_client", "queue_processor"]
