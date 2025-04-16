import gc

import objgraph
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


# Создаем класс для отслеживания памяти
class MemoryTrackerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        counts_before = objgraph.typestats()
        response = await call_next(request)
        gc.collect()
        counts_after = objgraph.typestats()

        diff = {k: counts_after[k] - counts_before.get(k, 0)
                for k in counts_after
                if k in counts_before and counts_after[k] > counts_before.get(k, 0)}

        if diff:
            print(f"Memory increased after request {request.url.path}: {diff}")

        return response