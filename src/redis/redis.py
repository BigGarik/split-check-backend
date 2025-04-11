from .queue_processor import QueueProcessor
from .redis_client import RedisClient
from src.config.settings import settings


# Инициализация Redis клиента
redis_client = RedisClient(host=settings.redis_host,
                           port=settings.redis_port,
                           db=settings.redis_db)

# Инициализация процессора очереди
queue_processor = QueueProcessor(redis_client, "task_queue")

# Экспортируем для использования в других модулях
__all__ = ["redis_client", "queue_processor"]
