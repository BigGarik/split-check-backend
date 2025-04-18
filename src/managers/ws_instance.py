# src/managers/ws_instance.py
from src.managers.redis_ws_manager import RedisWSManager


# Инициализация реального RedisWSManager и передача его в прокси-менеджер
def init_redis_ws_manager(redis_client, proxy_ws_manager):
    """Инициализация глобального экземпляра RedisWSManager и его прикрепление к прокси"""
    redis_ws_manager = RedisWSManager(redis_client)
    proxy_ws_manager.set_real_manager(redis_ws_manager)
    return redis_ws_manager
