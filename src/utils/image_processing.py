import asyncio
import base64
import io
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from loguru import logger
from PIL import Image

executor = ThreadPoolExecutor()


async def process_image(img_path: str) -> Optional[dict]:
    """Асинхронно обрабатывает изображение и возвращает его в формате base64."""
    try:
        # Читаем изображение и изменяем размер в отдельном потоке
        def process():
            with Image.open(img_path) as img:
                width, height = img.size
                short_side = 1024

                # Рассчитываем новые размеры с сохранением пропорций
                if width < height:
                    new_width = short_side
                    new_height = int(height * (short_side / width))
                else:
                    new_height = short_side
                    new_width = int(width * (short_side / height))

                img = img.resize((new_width, new_height), Image.LANCZOS)

                # Конвертируем изображение в RGB, если необходимо
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Преобразуем изображение в base64
                with io.BytesIO() as buffer:
                    img.save(buffer, format="JPEG")
                    img_bytes = buffer.getvalue()
                    base64_data = base64.b64encode(img_bytes).decode('utf-8')
                    return {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": base64_data
                        }
                    }

        # Выполняем обработку изображения в ThreadPoolExecutor
        return await asyncio.get_event_loop().run_in_executor(executor, process)
    except Exception as e:
        logger.error(f"Error processing image {img_path}: {e}")
        return None
