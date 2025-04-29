# src/api/v1/endpoints/image.py
import logging

from fastapi import APIRouter, UploadFile, File, Depends, Request

from src.api.deps import get_current_user
from src.models.user import User
from src.redis.queue_processor import get_queue_processor
from src.services.upload_service import prepare_image_upload


queue_processor = get_queue_processor()

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload-image", summary="Загрузка изображения")
async def upload_image(request: Request,
                       user: User = Depends(get_current_user),
                       file: UploadFile = File(...)
                       ):
    # Подготовка данных для задачи и отправка в Redis
    task_data = await prepare_image_upload(user.id, file)
    await queue_processor.push_task(task_data)
    logger.debug(f"Task {task_data['check_uuid']} sent to Redis queue for processing.", extra={"current_user_id": user.id})
    return {"message": "Файл успешно загружен. Обработка..."}
