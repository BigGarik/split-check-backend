from celery import Celery

# Настройка Celery с использованием Redis в качестве брокера
celery_app = Celery(
    'tasks',
    broker='redis://localhost:6379/0',  # Адрес Redis для брокера сообщений
    backend='redis://localhost:6379/1',  # Адрес Redis для хранения результатов
)
