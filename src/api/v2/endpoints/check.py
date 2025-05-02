import base64
import json
import logging
import os
import uuid
from datetime import date
from typing import Optional
from uuid import UUID

import aiofiles
from fastapi import APIRouter, UploadFile, File, Depends, Request, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from src.api.deps import get_current_user
from src.config import UPLOAD_DIRECTORY, REDIS_EXPIRATION, BASE_URL
from src.config.type_events import Events
from src.models import User, StatusEnum
from src.redis import redis_client
from src.redis.queue_processor import get_queue_processor
from src.repositories.check import get_main_page_checks, get_all_checks_for_user, get_check_data, add_check_to_database
from src.tasks import calculate_price
from src.utils.db import get_session
from src.utils.notifications import create_event_message
from src.websockets.manager import ws_manager

queue_processor = get_queue_processor()


logger = logging.getLogger(__name__)

router = APIRouter()

# Имя очереди для заданий обработки изображений
IMAGE_PROCESSING_QUEUE = "image_processing_tasks"


@router.get("/", summary="Получить все чеки")
async def get_all_check(
                        check_name: Optional[str] = None,
                        check_status: Optional[StatusEnum] = None,
                        start_date: Optional[date] = Query(None, description="Start date in YYYY-MM-DD format"),
                        end_date: Optional[date] = Query(None, description="End date in YYYY-MM-DD format"),
                        page: int = Query(default=1, ge=1),
                        page_size: int = Query(default=20, ge=1, le=100),
                        user: User = Depends(get_current_user),
                        session: AsyncSession = Depends(get_session)):
    try:
        checks_data = await get_all_checks_for_user(session, user_id=user.id, page=page, page_size=page_size,
                                                    check_name=check_name, check_status=check_status,
                                                    start_date=start_date, end_date=end_date)

        payload = {
            "checks": checks_data["items"],
            "pagination": {
                "total": checks_data["total"],
                "page": checks_data["page"],
                "pageSize": checks_data["page_size"],
                "totalPages": checks_data["total_pages"]
            }
        }
        logger.debug(f"Отправлены данные всех чеков для пользователя ИД {user.id}: {payload}")
        return payload
    except Exception as e:
        logger.error(f"Ошибка при отправке всех чеков: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении данных: {str(e)}"
        )


@router.get("/{uuid}", summary="Получить чек по UUID", response_model=None)
async def get_check(
                    uuid: UUID,
                    user: User = Depends(get_current_user),
                    session: AsyncSession = Depends(get_session)
                    ):
    try:
        check_data = await get_check_data(session, user.id, str(uuid))

        logger.debug(f"Отправлены данные чека для пользователя ИД {user.id}: {check_data}")
        return check_data

    except Exception as e:
        logger.error(f"Ошибка при отправке чека: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении данных: {str(e)}"
        )


@router.post("/upload",
             summary="Загрузка изображения",
             description="""
                    Принимает изображение чека, сохраняет его и инициирует фоновую обработку.
                    
                    **Основной поток обработки**:
                    - Изображение сохраняется на диск
                    - Кодируется в base64 и отправляется в очередь Redis (`image_processing_tasks`)
                    - Ожидается результат от `image_processor` (до 30 сек)
                    - Результат сохраняется в базу и Redis, пользователь получает уведомление через WebSocket
                    
                    **Ответ**:
                    - 200 OK: UUID задачи
                    - 504 Timeout: если результат не получен вовремя
                    - 500 Internal Error: при ошибке обработки
                """)
async def upload_image(
    request: Request,
    user: User = Depends(get_current_user),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
):
    try:
        check_uuid = str(uuid.uuid4())
        directory = os.path.join(UPLOAD_DIRECTORY, check_uuid)
        os.makedirs(directory, exist_ok=True)

        file_path = os.path.join(directory, file.filename)

        content = await file.read()  # читаем 1 раз

        # Сохраняем файл
        async with aiofiles.open(file_path, "wb") as out_file:
            await out_file.write(content)

        encoded_image = base64.b64encode(content).decode("utf-8")

        task_data = {
            "id": check_uuid,
            "type": "image_process",
            "image": encoded_image,
        }

        await queue_processor.push_task(task_data=task_data, queue_name=IMAGE_PROCESSING_QUEUE)

        result = await redis_client.wait_for_result(check_uuid, timeout=30)

        if result is None:
            raise HTTPException(status_code=504, detail="Timeout: обработка заняла слишком много времени")
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("result"))

        # check_data = calculate_price(result.get("result"))
        check_data = result.get("result")

        check_data = await add_check_to_database(session, check_uuid, user.id, check_data)

        redis_key = f"check_uuid:{check_uuid}"

        await redis_client.set(redis_key, json.dumps(check_data), expire=REDIS_EXPIRATION)

        msg = create_event_message(
            message_type=Events.IMAGE_RECOGNITION_EVENT,
            payload={"uuid": check_uuid}
        )

        await ws_manager.send_personal_message(
            message=json.dumps(msg),
            user_id=user.id
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=check_data
        )

    except Exception as e:
        logger.error(f"Ошибка при загрузке изображения: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки изображения")


@router.get("/{uuid}/images", summary="Получить список ссылок на изображения")
async def get_images(uuid: UUID, user: User = Depends(get_current_user)):
    """
    Возвращает список URL-ов на изображения из папки UUID.
    """
    folder_path = os.path.join(UPLOAD_DIRECTORY, str(uuid))
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="Папка с изображениями не найдена")

    image_files = [
        f for f in os.listdir(folder_path)
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif'))
    ]

    if not image_files:
        raise HTTPException(status_code=404, detail="Изображения не найдены")

    base_url = f"{BASE_URL}/images/{uuid}/"

    return {
        "uuid": str(uuid),
        "images": [base_url + fname for fname in image_files]
    }