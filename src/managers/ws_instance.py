# src/managers/ws_instance.py
from src.managers.redis_ws_manager import RedisWSManager

# Переменная для хранения экземпляра RedisWSManager
redis_ws_manager = None

def init_redis_ws_manager(redis_client):
    """Инициализация и возврат глобального экземпляра RedisWSManager"""
    global redis_ws_manager
    if redis_ws_manager is None:
        redis_ws_manager = RedisWSManager(redis_client)
    return redis_ws_manager

def get_redis_ws_manager():
    """Возвращает экземпляр RedisWSManager, если он был инициализирован"""
    if redis_ws_manager is None:
        raise RuntimeError("RedisWSManager is not initialized. Call `init_redis_ws_manager` first.")
    return redis_ws_manager