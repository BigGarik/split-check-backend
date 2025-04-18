import logging
import os
import uuid

import aiofiles
from starlette.datastructures import UploadFile

from src.config import UPLOAD_DIRECTORY

logger = logging.getLogger(__name__)


async def prepare_image_upload(user_id: int, file: UploadFile) -> dict:
    """Подготовка данных для задачи загрузки и обработки изображения."""
    check_uuid = str(uuid.uuid4())
    directory = os.path.join(UPLOAD_DIRECTORY, check_uuid)
    os.makedirs(directory, exist_ok=True)

    file_name = file.filename
    file_location = os.path.join(directory, file_name)

    async with aiofiles.open(file_location, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)

    task_data = {
        "type": "recognize_image_task",
        "user_id": user_id,
        "check_uuid": check_uuid,
        "file_location_directory": directory,
        "file_name": file_name,
    }
    logger.debug(f"Task data prepared for check_uuid {check_uuid}: {task_data}")
    return task_data
