import logging

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import ALLOWED_IPS

logger = logging.getLogger(__name__)


class RestrictDocsAccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Маршруты документации FastAPI
        docs_paths = ["/docs", "/redoc", "/docs.json", "/openapi.json"]
        client_ip = request.client.host
        # logger.info(f"allowed ips: {ALLOWED_IPS}")

        if request.url.path in docs_paths and client_ip not in ALLOWED_IPS:
            logger.warning(f"Access denied for IP: {client_ip} to {request.url.path}")
            raise HTTPException(status_code=403, detail="Access to documentation is restricted")

        return await call_next(request)
