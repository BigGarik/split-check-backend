from typing import Optional

import redis.asyncio as aioredis
from loguru import logger


class RedisClient:
    def __init__(self, host: str, port: int, db: int = 1, password: Optional[str] = None):
        self.redis_url = f"redis://{host}:{port}/{db}"
        self.password = password
        self.client: Optional[aioredis.Redis] = None

    async def get(self, key: str) -> Optional[str]:
        return await self.client.get(key)

    async def set(self, key: str, value: str, expire: int = None):
        await self.client.set(key, value, ex=expire)

    async def connect(self):
        try:
            self.client = await aioredis.from_url(
                self.redis_url,
                password=self.password,
                decode_responses=True
            )
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        if self.client:
            await self.client.close()

    async def push_task(self, queue_name: str, task_data: str):
        await self.client.lpush(queue_name, task_data)

    async def pop_task(self, queue_name: str) -> Optional[str]:
        try:
            task = await self.client.brpop(queue_name, timeout=0)
            return task
        except Exception as e:
            logger.error(f"Error popping task: {e}")
            return None
