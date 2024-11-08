import asyncio
import os
from typing import Optional, List
from loguru import logger
from src.utils.image_processing import process_image


async def form_message(file_location_directory: str, prompt: Optional[str] = "") -> List[dict]:
    images = []

    # Создаем список задач для параллельной обработки всех изображений
    tasks = [
        process_image(os.path.join(file_location_directory, filename))
        for filename in os.listdir(file_location_directory)
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif'))
    ]

    # Асинхронно ждем выполнения всех задач
    processed_images = await asyncio.gather(*tasks)

    # Фильтруем успешные результаты
    images = [img for img in processed_images if img is not None]

    # Формируем итоговое сообщение
    return [
        {
            "role": "user",
            "content": [
                *images,
                {"type": "text", "text": prompt},
            ]
        }
    ]
