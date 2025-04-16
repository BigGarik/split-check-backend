from src.managers.redis_ws_manager import RedisWSManager

# Глобальная переменная, которая будет инициализирована в lifespan
redis_ws_manager = None

def get_redis_ws_manager() -> RedisWSManager:
    if redis_ws_manager is None:
        raise RuntimeError("RedisWSManager is not initialized")
    return redis_ws_manager