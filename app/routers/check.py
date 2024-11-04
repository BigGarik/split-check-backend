from fastapi import APIRouter, Query
from fastapi import File, UploadFile, Depends
from loguru import logger

from app.auth import get_current_user
from app.models import User
from app.redis import queue_processor
from app.schemas import CheckSelectionRequest, UpdateItemQuantity
from app.utils import upload_image_process

router = APIRouter(prefix="/check", tags=["check"])


@router.post("/upload-image")
async def upload_image(
        user: User = Depends(get_current_user),
        file: UploadFile = File(...),
):
    # Запускаем процесс обработки изображения
    task_data = await upload_image_process(user.id, file)
    # Отправляем данные для обработки в очередь Redis
    await queue_processor.push_task(task_data)

    return {"message": "Файл успешно загружен. Обработка..."}


@router.get("/all")
async def get_all_check(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        user: User = Depends(get_current_user)
):
    task_data = {
        "type": "send_all_checks",
        "user_id": user.id,
        "page": page,
        "page_size": page_size
    }
    # Отправляем параметры пагинации в очередь Redis
    await queue_processor.push_task(task_data)

    return {"message": "Данные чеков отправлены в очередь для передачи через WebSocket"}


@router.get("/{uuid}")
async def get_check(uuid: str, user: User = Depends(get_current_user)):

    task_data = {
        "type": "send_check_data",
        "user_id": user.id,
        "check_uuid": uuid,
    }

    # Отправляем данные чека в очередь Redis
    await queue_processor.push_task(task_data)

    return {"message": "Данные чека отправлены в очередь для передачи через WebSocket"}


@router.post("/{uuid}/select")
async def user_selection(uuid: str,
                         selection: CheckSelectionRequest,
                         user: User = Depends(get_current_user)):
    # Отправляем данные чека в очередь Redis
    task_data = {
        "type": "user_selection_task",
        "user_id": user.id,
        "check_uuid": uuid,
        "selection_data": selection.model_dump()
    }
    logger.info(selection.dict())
    await queue_processor.push_task(task_data)

    return {"message": "Данные о выборе отправлены в очередь для передачи через WebSocket"}


@router.post("/join")
async def join_check(
        uuid: str,
        user: User = Depends(get_current_user)
):
    """Присоединяет пользователя к чеку и возвращает статус операции."""
    task_data = {
        "type": "join_check_task",
        "user_id": user.id,
        "check_uuid": uuid,
    }
    await queue_processor.push_task(task_data)
    return {"message": "Данные для присоединения отправлены в очередь"}


@router.put("/item/split")
async def split_item(
        data: UpdateItemQuantity,
        user: User = Depends(get_current_user)
):
    """Разделяет позицию на части и отправляет задачу в очередь Redis."""
    # Формируем данные задачи
    task_data = {
        "type": "split_item",
        "user_id": user.id,
        "check_uuid": data.check_uuid,
        "item_id": data.item_id,
        "quantity": data.quantity,
    }
    logger.info(f"Позиция отправлена для разделения: {data}")

    # Добавляем задачу в очередь Redis
    await queue_processor.push_task(task_data)
    return {"message": "Данные отправлены в очередь для обработки"}


@router.delete("/delete")
async def delete_check(
        uuid: str,
        user: User = Depends(get_current_user)
):
    """Удаляет чек."""
    task_data = {
        "type": "check_delete",
        "user_id": user.id,
        "check_uuid": uuid,
    }
    await queue_processor.push_task(task_data)
    return {"message": "Данные для удаления отправлены в очередь"}
