# src/services/ai/message.py
import asyncio
import logging
import os
from typing import Optional, List

from src.config import config
from src.utils.image_processing import process_image

logger = logging.getLogger(config.app.service_name)

# Ограничиваем количество одновременно обрабатываемых изображений
MAX_CONCURRENT_IMAGES = 4


async def message_for_anthropic(file_location_directory: str, prompt: Optional[str] = "") -> List[dict]:
    # Получаем список изображений
    image_files = [
        filename for filename in os.listdir(file_location_directory)
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif'))
    ]

    # Создаем семафор для ограничения одновременной обработки
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_IMAGES)

    async def process_with_limit(filepath):
        async with semaphore:
            return await process_image(filepath)

    # Создаем задачи для обработки изображений с ограничением
    tasks = [
        process_with_limit(os.path.join(file_location_directory, filename))
        for filename in image_files
    ]

    # Асинхронно ждем выполнения всех задач
    processed_images = await asyncio.gather(*tasks)

    # Фильтруем успешные результаты
    images = [img for img in processed_images if img is not None]

    # Логируем информацию о обработке
    logger.info(f"Обработано {len(images)} из {len(image_files)} изображений")

    # Формируем итоговое сообщение
    result = [
        {
            "role": "user",
            "content": [
                *images,
                {"type": "text", "text": prompt},
            ]
        }
    ]

    # Явная очистка для помощи сборщику мусора
    del processed_images, images

    return result