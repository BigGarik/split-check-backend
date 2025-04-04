import asyncio
import json
# import logging
from loguru import logger
import os
from typing import Callable, Dict

from .redis_client import RedisClient

# logger = logging.getLogger(__name__)


class QueueProcessor:
    def __init__(self, redis_client: RedisClient, queue_name: str):
        self.redis_client = redis_client
        self.queue_name = queue_name
        self.task_handlers: Dict[str, Callable] = {}
        # Устанавливаем количество обработчиков на основе числа CPU ядер
        cpu_count = os.cpu_count() or 1  # Если os.cpu_count() вернёт None, используем 1
        self.queue_semaphore = asyncio.Semaphore(cpu_count * 2)  # Ограничиваем по числу ядер
        logger.info(f"Инициализирован QueueProcessor с {self.queue_semaphore} обработчиками (по числу CPU ядер)")

    def register_handler(self, task_type: str, handler: Callable):
        self.task_handlers[task_type] = handler

    async def process_queue(self):
        while True:
            try:
                # Получение задачи из очереди
                task = await self.redis_client.pop_task(self.queue_name)

                if not task:
                    await asyncio.sleep(1)  # Если нет задач, подождите 1 секунду
                    continue

                _, task_json = task  # Распаковка задачи
                task_data = json.loads(task_json)

                async with self.queue_semaphore:  # Ограничиваем количество одновременно работающих консьюмеров
                    task_type = task_data.get('type')

                    if task_type in self.task_handlers:
                        handler = self.task_handlers[task_type]
                        await asyncio.wait_for(handler(task_data), timeout=60)  # Таймаут 60 секунд
                    else:
                        logger.warning(f"Unknown message type: {task_type}")
            except asyncio.TimeoutError:
                logger.error(f"Task {task_type} exceeded 60-second timeout")
            except Exception as e:
                logger.error(f"Error processing task: {e}")
                await asyncio.sleep(1)

    async def push_task(self, task_data: dict):
        await self.redis_client.push_task(self.queue_name, json.dumps(task_data))
