import asyncio
import json
from typing import Callable, Dict

from loguru import logger

from .redis_client import RedisClient


class QueueProcessor:
    def __init__(self, redis_client: RedisClient, queue_name: str):
        self.redis_client = redis_client
        self.queue_name = queue_name
        self.task_handlers: Dict[str, Callable] = {}
        self.queue_semaphore = asyncio.Semaphore(10)  # Ограничиваем до 10 одновременных обработчиков

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
                        await handler(task_data)
                    else:
                        logger.warning(f"Unknown message type: {task_type}")
            except Exception as e:
                logger.error(f"Error processing task: {e}")
                await asyncio.sleep(1)  # Prevent tight loop in case of persistent errors

    async def push_task(self, task_data: dict):
        await self.redis_client.push_task(self.queue_name, json.dumps(task_data))


if __name__ == '__main__':
    pass
