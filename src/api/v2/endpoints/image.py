import base64
import logging
import os
import uuid

import aiofiles
from fastapi import APIRouter, UploadFile, File, Depends, Request
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from src.api.deps import get_current_user
from src.config import UPLOAD_DIRECTORY
from src.models.user import User
from src.redis import redis_client
from src.redis.queue_processor import get_queue_processor
from src.tasks import calculate_price

queue_processor = get_queue_processor()

logger = logging.getLogger(__name__)

router = APIRouter()

# Имя очереди для заданий обработки изображений
IMAGE_PROCESSING_QUEUE = "image_processing_tasks"


@router.post("/upload", summary="Загрузка изображения")
async def upload_image(
    request: Request,
    user: User = Depends(get_current_user),
    file: UploadFile = File(...)
):
    """
    Загружает изображение чека, сохраняет его на диск, помещает задачу в очередь,
    и ждёт результат от image_processor через Redis.
    """
    try:
        # Генерируем уникальный ID для задачи
        check_uuid = str(uuid.uuid4())

        # Создаём директорию для сохранения файла
        directory = os.path.join(UPLOAD_DIRECTORY, check_uuid)
        os.makedirs(directory, exist_ok=True)

        # Сохраняем изображение в файл
        file_path = os.path.join(directory, file.filename)
        content = await file.read()
        async with aiofiles.open(file_path, "wb") as out_file:
            await out_file.write(content)

        # Кодируем изображение в base64
        encoded_image = base64.b64encode(content).decode("utf-8")

        # Формируем задачу
        task_data = {
            "id": check_uuid,
            "type": "image_process",
            "image": encoded_image,
        }

        # Отправляем задачу в очередь
        await queue_processor.push_task(task_data=task_data, queue_name=IMAGE_PROCESSING_QUEUE)

        # Ждём результата через Redis (можно заменить на WebSocket пуш позже)
        result = await redis_client.wait_for_result(check_uuid, timeout=30)

        if result is None:
            raise HTTPException(status_code=504, detail="Timeout: обработка заняла слишком много времени")

        check_data = result.get("result")

        check_data = calculate_price(check_data)

        return JSONResponse(content=check_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки изображения: {str(e)}")