import asyncio
import json
import logging
import os
from typing import Callable, Dict

from .redis_client import RedisClient

logger = logging.getLogger(__name__)


class QueueProcessor:
    def __init__(self, redis_client: RedisClient, queue_name: str):
        self.redis_client = redis_client
        self.queue_name = queue_name
        self.task_handlers: Dict[str, Callable] = {}
        # Устанавливаем количество обработчиков на основе числа CPU ядер
        cpu_count = os.cpu_count() or 1  # Если os.cpu_count() вернёт None, используем 1
        self.queue_semaphore = asyncio.Semaphore(cpu_count * 2)  # Ограничиваем по числу ядер
        logger.info(f"Инициализирован QueueProcessor с {self.queue_semaphore._value} обработчиками (по числу CPU ядер)")

    def register_handler(self, task_type: str, handler: Callable):
        self.task_handlers[task_type] = handler

    async def process_queue(self):
        # Ограничивать количество задач в обработке
        active_tasks = set()

        while True:
            try:
                # Проверяем, не слишком ли много активных задач
                if len(active_tasks) >= self.queue_semaphore._value * 2:
                    # Если слишком много задач в обработке, делаем паузу
                    await asyncio.sleep(0.5)
                    continue

                # Получение задачи из очереди с таймаутом
                try:
                    task = await asyncio.wait_for(
                        self.redis_client.pop_task(self.queue_name),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    # Если таймаут, продолжаем цикл
                    continue

                if not task:
                    await asyncio.sleep(0.5)
                    continue

                _, task_json = task  # Распаковка задачи
                task_data = json.loads(task_json)

                # Создаем и запускаем задачу асинхронно
                task_type = task_data.get('type')
                if task_type in self.task_handlers:
                    handler = self.task_handlers[task_type]

                    async def process_with_semaphore():
                        task_id = id(task_data)
                        active_tasks.add(task_id)
                        try:
                            async with self.queue_semaphore:
                                await asyncio.wait_for(handler(task_data), timeout=60)
                        except Exception as e:
                            logger.error(f"Error processing task {task_type}: {e}")
                        finally:
                            active_tasks.discard(task_id)

                    asyncio.create_task(process_with_semaphore())
                else:
                    logger.warning(f"Unknown message type: {task_type}")

            except Exception as e:
                logger.error(f"Error in queue processor: {e}")
                await asyncio.sleep(1)

    async def push_task(self, task_data: dict):
        await self.redis_client.push_task(self.queue_name, json.dumps(task_data))
