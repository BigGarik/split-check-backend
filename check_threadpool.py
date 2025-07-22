# check_threadpool.py
# Запускать из корня проекта: python check_threadpool.py

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import psutil
import threading
from src.utils.image_processing import get_executor as get_image_executor, cleanup_executor as cleanup_image_executor
from src.core.security import get_executor as get_security_executor, cleanup_executor as cleanup_security_executor


async def main():
    """Проверка ограничения количества потоков"""

    print("=== Проверка исправлений ThreadPool ===\n")

    # Получаем информацию о процессе
    process = psutil.Process(os.getpid())
    initial_threads = process.num_threads()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    print(f"До теста:")
    print(f"  Потоков: {initial_threads}")
    print(f"  Память: {initial_memory:.2f} MB")
    print(f"  CPU ядер: {os.cpu_count()}")

    # Инициализируем executor'ы
    print("\nИнициализация executor'ов...")
    image_executor = get_image_executor()
    security_executor = get_security_executor()

    print(f"  Image executor: max_workers = {image_executor._max_workers}")
    print(f"  Security executor: max_workers = {security_executor._max_workers}")

    # Создаем нагрузку
    print("\nЗапуск 100 задач...")

    async def dummy_image_task(n):
        await asyncio.sleep(0.01)
        return n * 2

    async def dummy_security_task(n):
        await asyncio.sleep(0.01)
        return n * 3

    # Запускаем задачи
    loop = asyncio.get_event_loop()
    tasks = []

    for i in range(50):
        tasks.append(loop.run_in_executor(image_executor, lambda x: x * 2, i))
        tasks.append(loop.run_in_executor(security_executor, lambda x: x * 3, i))

    results = await asyncio.gather(*tasks)

    # Проверяем состояние после выполнения
    after_tasks_threads = process.num_threads()
    after_tasks_memory = process.memory_info().rss / 1024 / 1024

    print(f"\nПосле выполнения задач:")
    print(f"  Потоков: {after_tasks_threads} (создано: {after_tasks_threads - initial_threads})")
    print(f"  Память: {after_tasks_memory:.2f} MB (изменение: {after_tasks_memory - initial_memory:.2f} MB)")

    # Проверка ограничения
    created_threads = after_tasks_threads - initial_threads
    expected_max = image_executor._max_workers + security_executor._max_workers

    if created_threads <= expected_max:
        print(f"\n✅ УСПЕХ: Создано потоков ({created_threads}) <= ожидаемого максимума ({expected_max})")
    else:
        print(f"\n❌ ОШИБКА: Создано слишком много потоков ({created_threads}) > ожидаемого максимума ({expected_max})")

    # Очищаем executor'ы
    print("\nОчистка executor'ов...")
    cleanup_image_executor()
    cleanup_security_executor()

    # Даем время на завершение потоков
    await asyncio.sleep(0.5)

    # Финальная проверка
    final_threads = process.num_threads()
    final_memory = process.memory_info().rss / 1024 / 1024

    print(f"\nПосле очистки:")
    print(f"  Потоков: {final_threads}")
    print(f"  Память: {final_memory:.2f} MB")

    print("\n=== Тест завершен ===")


if __name__ == "__main__":
    asyncio.run(main())