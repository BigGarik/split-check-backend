import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from src.api.deps import get_current_user
from src.models import User
from src.redis.queue_processor import get_queue_processor

from src.schemas import ItemRequest, AddItemRequest, EditItemRequest

queue_processor = get_queue_processor()

logger = logging.getLogger(__name__)

router = APIRouter()


@router.put("/item/split", summary="Разделяет позицию на части")
async def split_item(request: Request,
                     uuid: UUID,
                     item_data: ItemRequest,
                     user: User = Depends(get_current_user)):
    """Разделяет позицию на части и отправляет задачу в очередь Redis."""
    # Формируем данные задачи
    task_data = {
        "type": "split_item_task",
        "check_uuid": str(uuid),
        "user_id": user.id,
        "item_data": item_data.model_dump()
    }
    logger.debug(f"Позиция отправлена для разделения: {item_data}", extra={"current_user_id": user.id})

    # Добавляем задачу в очередь Redis
    await queue_processor.push_task(task_data)
    return {"message": "Данные отправлены в очередь для обработки"}


@router.post("/item/add", summary="Добавляет позицию в чек.")
async def add_item(request: Request,
                   uuid: UUID,
                   item_data: AddItemRequest,
                   user: User = Depends(get_current_user)):
    """Добавляет позицию в чек."""
    task_data = {
        "type": "add_item_task",
        "user_id": user.id,
        "check_uuid": str(uuid),
        "item_data": item_data.model_dump()
    }
    await queue_processor.push_task(task_data)
    return {"message": "Данные для добавления отправлены в очередь"}


@router.post("/item/edit", summary="Редактирование позиции в чеке.")
async def edit_item(request: Request,
                    uuid: UUID,
                    item_data: EditItemRequest,
                    user: User = Depends(get_current_user)):
    """Редактирование позиции в чеке."""
    task_data = {
        "type": "edit_item_task",
        "user_id": user.id,
        "check_uuid": str(uuid),
        "item_data": item_data.model_dump()
    }
    await queue_processor.push_task(task_data)
    return {"message": "Данные для добавления отправлены в очередь"}


@router.delete("/item/delete", summary="Удаление позиции из чека.")
async def delete_item(request: Request,
                      uuid: UUID,
                      item_id: int,
                      user: User = Depends(get_current_user)):
    """Удаление позиции из чека."""
    task_data = {
        "type": "delete_item_task",
        "user_id": user.id,
        "check_uuid": str(uuid),
        "item_id": item_id
    }
    await queue_processor.push_task(task_data)
    return {"message": "Данные для добавления отправлены в очередь"}
