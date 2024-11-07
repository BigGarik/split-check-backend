# logger_config.py

import logging
import sys
import json
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class DetailedFormatter(logging.Formatter):
    """Расширенный форматтер для детального логирования"""

    def format(self, record: logging.LogRecord) -> str:
        # Добавляем дополнительные поля, если они отсутствуют
        default_fields = {
            'request_id': '-',
            'user_id': '-',
            'ip': '-',
            'extra': {},
        }

        for field, default in default_fields.items():
            if not hasattr(record, field):
                setattr(record, field, default)

        # Если есть дополнительные данные в extra, преобразуем их в строку
        if hasattr(record, 'extra') and isinstance(record.extra, dict):
            record.extra = json.dumps(record.extra)

        return super().format(record)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware для логирования деталей HTTP запросов"""

    def __init__(self, app, file_logger: logging.Logger):
        super().__init__(app)
        self.file_logger = file_logger

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = datetime.now()
        request_id = str(hash(f"{start_time}{request.client.host}"))

        # Собираем информацию о запросе
        request_body = await self._get_request_body(request)
        request_info = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host,
            "headers": dict(request.headers),
            "body": request_body
        }

        # Логируем начало запроса только в файл
        self.file_logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "ip": request.client.host,
                "extra": request_info
            }
        )

        response = await call_next(request)

        # Вычисляем время выполнения
        process_time = (datetime.now() - start_time).total_seconds()

        # Логируем завершение запроса только в файл
        response_info = {
            "request_id": request_id,
            "status_code": response.status_code,
            "process_time": process_time,
            "response_headers": dict(response.headers)
        }

        self.file_logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "ip": request.client.host,
                "extra": response_info
            }
        )

        return response

    async def _get_request_body(self, request: Request) -> Optional[str]:
        """Получение тела запроса для методов POST, PUT, PATCH"""
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                return body.decode()
            except Exception:
                return None
        return None


class LogConfig:
    """Конфигурация логирования"""

    def __init__(
            self,
            log_path: Path = Path("logs"),
            log_filename: str = "app.log",
            requests_filename: str = "requests.log",
            max_bytes: int = 10 * 1024 * 1024,  # 10MB
            backup_count: int = 5,
            console_level: int = logging.INFO,
            file_level: int = logging.INFO
    ):
        self.log_path = log_path
        self.log_filename = log_filename
        self.requests_filename = requests_filename
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.console_level = console_level
        self.file_level = file_level

        # Форматы логов
        self.console_format = '%(asctime)s  %(levelname)s:   %(module)s  %(message)s'
        self.file_format = json.dumps({
            'timestamp': '%(asctime)s',
            'level': '%(levelname)s',
            'request_id': '%(request_id)s',
            'user_id': '%(user_id)s',
            'ip': '%(ip)s',
            'message': '%(message)s',
            'module': '%(module)s',
            'function': '%(funcName)s',
            'line': '%(lineno)d',
            'extra': '%(extra)s'
        })

    def setup_logging(self, app: FastAPI) -> logging.Logger:
        """Настройка логирования для FastAPI приложения"""
        # Создаем директорию для логов
        self.log_path.mkdir(exist_ok=True)

        # Настраиваем корневой логгер
        logger = logging.getLogger()
        logger.setLevel(min(self.console_level, self.file_level))

        # Очищаем существующие хендлеры
        logger.handlers.clear()

        # Добавляем хендлер для консоли
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.console_level)
        console_handler.setFormatter(logging.Formatter(self.console_format))
        logger.addHandler(console_handler)

        # Добавляем хендлер для основного файла логов
        file_handler = RotatingFileHandler(
            self.log_path / self.log_filename,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(self.file_level)
        file_handler.setFormatter(DetailedFormatter(self.file_format))
        logger.addHandler(file_handler)

        # Создаем отдельный логгер для запросов
        requests_logger = logging.getLogger('requests')
        requests_logger.setLevel(self.file_level)
        requests_logger.propagate = False  # Отключаем передачу логов родительскому логгеру

        # Добавляем хендлер для файла запросов
        requests_handler = RotatingFileHandler(
            self.log_path / self.requests_filename,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        requests_handler.setFormatter(DetailedFormatter(self.file_format))
        requests_logger.addHandler(requests_handler)

        # Добавляем middleware для логирования запросов
        app.add_middleware(RequestLoggingMiddleware, file_logger=requests_logger)

        return logger


def setup_app_logging(
        app: FastAPI,
        log_path: Path = Path("logs"),
        log_filename: str = "app.log",
        requests_filename: str = "requests.log",
        **kwargs
) -> logging.Logger:
    """
    Функция-помощник для быстрой настройки логирования

    Пример использования:
        logger = setup_app_logging(
            app,
            log_path=Path("logs"),
            log_filename="app.log",
            requests_filename="requests.log",
            max_bytes=10 * 1024 * 1024,  # 10MB
            backup_count=5,
            console_level=logging.INFO,
            file_level=logging.DEBUG
        )
    """
    config = LogConfig(
        log_path=log_path,
        log_filename=log_filename,
        requests_filename=requests_filename,
        **kwargs
    )
    return config.setup_logging(app)