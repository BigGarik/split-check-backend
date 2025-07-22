# src/core/dependencies.py
"""
Контейнер зависимостей для управления жизненным циклом сервисов.
Использует паттерн Dependency Injection для избежания глобальных переменных.
"""
import asyncio
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

from src.config import config
from src.redis.redis_client import RedisClient
from src.redis.queue_processor import QueueProcessor
from src.websockets.manager import WSConnectionManager
from src.services.classifier.classifier import AsyncImageClassifier


class ServiceContainer:
    """Контейнер для всех сервисов приложения"""

    def __init__(self):
        # Инициализируем как None, создание происходит в startup
        self._redis_client: Optional[RedisClient] = None
        self._queue_processor: Optional[QueueProcessor] = None
        self._ws_manager: Optional[WSConnectionManager] = None
        self._classifier: Optional[AsyncImageClassifier] = None

        # Флаги состояния
        self._initialized = False
        self._shutting_down = False

        # Задачи для graceful shutdown
        self._background_tasks = []

    async def startup(self):
        """Инициализация всех сервисов при старте приложения"""
        if self._initialized:
            return

        # Создаем Redis клиент
        self._redis_client = RedisClient(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db
        )
        await self._redis_client.connect()

        # Создаем Queue Processor
        self._queue_processor = QueueProcessor(
            redis_client=self._redis_client,
            queue_name="task_queue"
        )

        # Создаем WebSocket Manager
        self._ws_manager = WSConnectionManager()

        # Создаем классификатор только в production
        if config.app.is_production:
            self._classifier = AsyncImageClassifier(
                batch_size=1,
                num_threads=2
            )

        self._initialized = True

    async def shutdown(self):
        """Корректное завершение работы всех сервисов"""
        if self._shutting_down:
            return

        self._shutting_down = True

        # Останавливаем обработку очереди
        if self._queue_processor:
            await self._queue_processor.stop()

        # Закрываем WebSocket соединения
        if self._ws_manager:
            # Отправляем всем клиентам сообщение о завершении
            await self._ws_manager.broadcast(
                '{"type": "server_shutdown", "message": "Server is shutting down"}'
            )
            # Даем время на отправку
            await asyncio.sleep(0.5)

        # Очищаем классификатор
        if self._classifier:
            self._classifier.cleanup()

        # Отключаемся от Redis
        if self._redis_client:
            await self._redis_client.disconnect()

        # Ждем завершения фоновых задач
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

    # Геттеры для сервисов с проверкой инициализации
    @property
    def redis_client(self) -> RedisClient:
        if not self._redis_client:
            raise RuntimeError("Redis client not initialized. Call startup() first.")
        return self._redis_client

    @property
    def queue_processor(self) -> QueueProcessor:
        if not self._queue_processor:
            raise RuntimeError("Queue processor not initialized. Call startup() first.")
        return self._queue_processor

    @property
    def ws_manager(self) -> WSConnectionManager:
        if not self._ws_manager:
            raise RuntimeError("WebSocket manager not initialized. Call startup() first.")
        return self._ws_manager

    @property
    def classifier(self) -> Optional[AsyncImageClassifier]:
        """Классификатор может быть None в dev окружении"""
        return self._classifier

    def add_background_task(self, task):
        """Добавляет фоновую задачу для отслеживания"""
        self._background_tasks.append(task)


# Глобальный экземпляр контейнера
_service_container: Optional[ServiceContainer] = None


def get_service_container() -> ServiceContainer:
    """Получить экземпляр контейнера сервисов"""
    global _service_container
    if _service_container is None:
        _service_container = ServiceContainer()
    return _service_container


# FastAPI Dependencies
async def get_redis_client() -> RedisClient:
    """Dependency для получения Redis клиента"""
    container = get_service_container()
    return container.redis_client


async def get_queue_processor() -> QueueProcessor:
    """Dependency для получения Queue Processor"""
    container = get_service_container()
    return container.queue_processor


async def get_ws_manager() -> WSConnectionManager:
    """Dependency для получения WebSocket Manager"""
    container = get_service_container()
    return container.ws_manager


async def get_classifier() -> Optional[AsyncImageClassifier]:
    """Dependency для получения классификатора"""
    container = get_service_container()
    return container.classifier


# Контекстный менеджер для lifespan
@asynccontextmanager
async def service_lifespan():
    """Контекстный менеджер для управления жизненным циклом сервисов"""
    container = get_service_container()

    # Startup
    await container.startup()

    try:
        yield container
    finally:
        # Shutdown
        await container.shutdown()