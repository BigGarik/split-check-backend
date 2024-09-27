import os

from celery import Celery

# Настройка Celery с использованием Redis в качестве брокера
celery_app = Celery(
    'tasks',
    broker='redis://localhost:6379/0',  # Адрес Redis для брокера сообщений
    backend='redis://localhost:6379/1',  # Адрес Redis для хранения результатов
)


# Конфигурация
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Moscow',
    enable_utc=True,
)

# Используем autodiscover_tasks для автоматического поиска задач
# celery_app.autodiscover_tasks(['external_services'])

# Если задачи не находятся в `tasks.py`, укажите имя модуля:
# celery_app.autodiscover_tasks(['external_services.api_anthropic'])


@celery_app.task
def check_directory():
    current_directory = os.getcwd()
    print(f"Текущая рабочая директория: {current_directory}")


if __name__ == '__main__':
    check_directory.delay()
