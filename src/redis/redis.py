from .queue_processor import get_queue_processor
from .redis_client import RedisClient
from src.config import config

# Инициализация Redis клиента
redis_client = RedisClient(host=config.redis.host,
                           port=config.redis.port,
                           db=config.redis.db,)

# Создаем единственный экземпляр QueueProcessor через фабрику
queue_processor = get_queue_processor(redis_client, "task_queue")

# Экспортируем для использования в других модулях
__all__ = ["redis_client", "queue_processor"]